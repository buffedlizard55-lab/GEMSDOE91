"""Ledger storage for ledger/submissions.csv.

One row = one experiment. Columns are fixed by brief section 7; the human fills
receipt_score and receipt_date after submitting from their own account. Nothing in
this module talks to the network or to a leaderboard.

Status vocabulary
  BUILT     raster written, gates may or may not have been run yet
  GATED     every MUST gate passed, ready for a slot
  REFUSED   a gate failed; keep the row so the failure is not repeated
  SENT      human reports it was submitted (no score yet)
  SCORED    receipt_score filled from the submission-page receipt  -> RECEIPT
  CLAIM     owner-reported number with no receipt                    -> CLAIM
"""

from __future__ import annotations

import csv
import datetime as _dt
from pathlib import Path

LEDGER = Path("ledger/submissions.csv")

COLUMNS = [
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256", "sha8",
    "status", "predicted_change", "receipt_score", "receipt_date", "built_utc",
    "git_sha", "script", "note",
]

PREDICTED = {  # MODEL texts; replace with measured text once a receipt exists
    "MASS": "+0.006 to +0.015 (adding mass near truth raises T at linear cost in S)",
    "CONCENTRATION": "+0.004 to +0.020 (fixed-count mass moved to high-prior km blocks)",
    "SNAP": "+0.000 to +0.010 (same count, better centring on the response; uncertain sign)",
    "PRUNE": "+0.003 to +0.012 (removing near-catalogue dots lowers S and M together)",
    "RELIEF": "+0.000 to +0.008 (tercile reweighting; weak mechanism, cheap test)",
    "SPACING": "-0.010 to +0.005 (lowest priority; spacing is not the binding constraint)",
    "TRACKB": "n/a (Phase 2 deliverable, not a weekly slot)",
}


def ledger_row(**kw) -> dict:
    row = {c: "" for c in COLUMNS}
    row["built_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    row["git_sha"] = kw.pop("git_sha", None) or _git_sha()
    for k, v in kw.items():
        if k not in row:
            raise KeyError(f"unknown ledger column {k!r}; known: {COLUMNS}")
        row[k] = v
    row["sha8"] = (row["sha256"] or "")[:8]
    if row["axis"] in PREDICTED and not row["predicted_change"]:
        row["predicted_change"] = PREDICTED[row["axis"]]
    return row


def _git_sha() -> str:
    try:
        import subprocess

        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def append_ledger(row: dict, path: Path = LEDGER) -> Path:
    """Append one row, refusing exact-hash and repeated (parent, axis, value) rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_ledger(path)
    if row.get("sha256"):
        for r in existing:
            if r.get("sha256") == row["sha256"]:
                raise SystemExit(
                    f"refusing to append: sha256 {row['sha256'][:12]} already in the ledger as "
                    f"{r.get('id')} (exact repeat, brief section 3)."
                )
    for r in existing:
        if (r.get("parent"), r.get("axis"), r.get("value")) == (row.get("parent"), row.get("axis"), row.get("value")):
            raise SystemExit(
                f"refusing to append: (parent, axis, value) = "
                f"{(row.get('parent'), row.get('axis'), row.get('value'))} already built as {r.get('id')}. "
                "Each (AXIS, value) pair is built once across all sessions."
            )
    new = not path.exists()
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in COLUMNS})
    return path


def read_ledger(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="inspect or initialise ledger/submissions.csv")
    ap.add_argument("--init", action="store_true", help="create the CSV with a header only")
    ap.add_argument("--path", type=Path, default=LEDGER)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.init:
        args.path.parent.mkdir(parents=True, exist_ok=True)
        if not args.path.exists():
            with open(args.path, "w", newline="") as fh:
                csv.DictWriter(fh, fieldnames=COLUMNS).writeheader()
            print(f"initialised {args.path}")
        else:
            print(f"{args.path} already exists; not touched")
        return 0
    rows = read_ledger(args.path)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    print(f"{len(rows)} rows in {args.path}")
    for r in rows:
        score = r.get("receipt_score") or "-"
        print(f"  {r.get('id','?'):44s} {r.get('axis',''):14s} {score:>8s} {r.get('status','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
