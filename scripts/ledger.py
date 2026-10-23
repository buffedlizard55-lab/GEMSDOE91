"""Ledger maintenance: collapse repeats, check duplicates, append BUILT rows.

Brief section 7 says one row per variant, with the human filling receipt_score and
date. Section 4 forbids a file whose sha256 is already in the ledger, and section 6
dedupes on exact hash and on repeated (parent, axis, value).

Raw paste format (ledger/raw_paste.txt), one submission per line, tab OR pipe OR
comma separated, header optional:

    site | name | score | encoding | n_dots | sha8 | parent | receipt

Commands
    state                       print counts, repeats, slots used this week
    collapse --from raw_paste   rebuild submissions.csv, collapsing repeats
    check --sha256 H --parent P --axis A --value V   is this file new?
    add --id ...                append one BUILT row (never a score)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

LEDGER = "ledger/submissions.csv"
RAW = "ledger/raw_paste.txt"

COLUMNS = [
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "encoding",
    "sha256", "sha8", "status", "predicted_change", "claimed_score",
    "receipt_score", "receipt_date", "site", "name", "provenance", "notes",
]

RAW_KEYS = ["site", "name", "score", "encoding", "n_dots", "sha8", "parent", "receipt"]


# --------------------------------------------------------------------------- io
def read_rows(path: str | Path = LEDGER) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def write_rows(rows: list[dict], path: str | Path = LEDGER) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def split_line(line: str) -> list[str]:
    for sep in ("\t", "|", ","):
        if sep in line:
            return [c.strip() for c in line.split(sep)]
    return line.split()


def parse_raw(path: str | Path) -> list[dict]:
    """Parse a pasted submission table into ledger rows. Header row detected by content."""
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        cells = split_line(line)
        if cells and cells[0].lower() in {"site", "submission", "#"}:
            continue  # header
        if len(cells) < 3:
            continue
        rec = dict(zip(RAW_KEYS, cells + [""] * (len(RAW_KEYS) - len(cells))))
        out.append(rec)
    return out


# ----------------------------------------------------------------------- logic
def collapse(raw_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Collapse identical (site, name) submissions, keeping the highest score.

    Returns (unique_rows, repeat_rows). Repeats are the wasted slots the brief
    calls out; they are recorded, never deleted silently.
    """
    seen: dict[tuple[str, str], dict] = {}
    repeats: list[dict] = []
    for r in raw_rows:
        key = (r.get("site", ""), r.get("name", ""))
        if key in seen:
            prev = seen[key]
            if _score(r) > _score(prev):
                r["notes"] = _note(r) + "repeat; kept higher score"
                seen[key] = r
                repeats.append(prev)
            else:
                prev["notes"] = _note(prev) + "repeat"
                repeats.append(r)
        else:
            seen[key] = r
    return list(seen.values()), repeats


def _score(r: dict) -> float:
    try:
        return float(r.get("score") or r.get("receipt_score") or -1)
    except ValueError:
        return -1.0


def _note(r: dict) -> str:
    n = (r.get("notes") or "").strip()
    return (n + "; ") if n else ""


def to_ledger_rows(raw_rows: list[dict]) -> list[dict]:
    rows = []
    for r in raw_rows:
        receipt = (r.get("receipt") or "").strip().upper()
        rows.append({
            "id": r.get("name", ""),
            "parent": r.get("parent", ""),
            "axis": "", "value": "", "pct_changed": "",
            "n_dots": r.get("n_dots", ""),
            "encoding": r.get("encoding", ""),
            "sha256": "", "sha8": r.get("sha8", ""),
            "status": "SUBMITTED" if receipt.startswith("Y") else "CLAIM",
            "predicted_change": "",
            "receipt_score": r.get("score", "") if receipt.startswith("Y") else "",
            "receipt_date": "",
            "site": r.get("site", ""),
            "name": r.get("name", ""),
            "provenance": "RAW_PASTE",
            "notes": "",
        })
    return rows


def is_repeat(rows: list[dict], sha256: str | None, parent: str, axis: str, value: str) -> list[str]:
    reasons = []
    if sha256:
        s8 = sha256[:8]
        for r in rows:
            if (r.get("sha256") or "") == sha256 or (r.get("sha8") or "") == s8:
                reasons.append(f"exact hash already in ledger as {r.get('id')}")
                break
    if parent and axis:
        for r in rows:
            if (r.get("parent") or "") == parent and (r.get("axis") or "") == axis \
                    and (r.get("value") or "") == value and (r.get("axis") or ""):
                reasons.append(f"(parent, axis, value) already built as {r.get('id')}")
                break
    return reasons


def week_slots(rows: list[dict], today: dt.date | None = None, per_week: int = 3) -> tuple[int, int]:
    """(used_this_week, quota). Counts SUBMITTED rows with a receipt date in the last 7 days."""
    today = today or dt.date.today()
    used = 0
    for r in rows:
        d = (r.get("receipt_date") or "").strip()
        if not d or (r.get("status") or "") != "SUBMITTED":
            continue
        try:
            when = dt.date.fromisoformat(d)
        except ValueError:
            continue
        if 0 <= (today - when).days < 7:
            used += 1
    return used, per_week


# ------------------------------------------------------------------------- cli
def cmd_state(args) -> int:
    rows = read_rows(args.ledger)
    if not rows:
        print(f"NO LEDGER at {args.ledger}.")
        raw = Path(args.raw)
        if raw.exists():
            print(f"raw paste found at {raw}: run `collapse --from {raw}`.")
        else:
            print(f"No raw paste at {raw} either: every score is CLAIM-only and the ledger is empty.")
        return 0
    built = [r for r in rows if (r.get("status") or "") == "BUILT"]
    scored = [r for r in rows if (r.get("receipt_score") or "").strip()]
    claims = [r for r in rows if (r.get("status") or "") == "CLAIM"]
    best = max(scored, key=_score, default=None)
    used, quota = week_slots(rows)
    print(f"ledger: {args.ledger}")
    print(f"  rows={len(rows)} built={len(built)} submitted={len(scored)} claims={len(claims)}")
    if best:
        print(f"  best receipt: {best.get('id')} = {best.get('receipt_score')} ({best.get('receipt_date') or 'no date'})")
    print(f"  slots used this week: {used}/{quota}")
    missing_hash = sum(1 for r in rows if not (r.get("sha256") or r.get("sha8") or "").strip())
    if missing_hash:
        print(f"  WARNING: {missing_hash} rows carry no hash; exact-repeat detection cannot work for them")
    pairs = [(r.get("parent"), r.get("axis"), r.get("value")) for r in built]
    dupes = {p for p in pairs if p[1] and pairs.count(p) > 1}
    if dupes:
        print(f"  WARNING: repeated (parent, axis, value): {sorted(dupes)}")
    return 0


def cmd_collapse(args) -> int:
    raw_rows = parse_raw(args.source)
    if not raw_rows:
        print(f"nothing to collapse: {args.source} missing or empty", file=sys.stderr)
        return 1
    unique, repeats = collapse(raw_rows)
    rows = to_ledger_rows(unique)
    write_rows(rows, args.ledger)
    print(f"parsed={len(raw_rows)} unique={len(unique)} repeats={len(repeats)} -> {args.ledger}")
    for r in repeats:
        print(f"  repeat: {r.get('name')} score={r.get('score')} sha8={r.get('sha8')}")
    return 0


def cmd_check(args) -> int:
    rows = read_rows(args.ledger)
    reasons = is_repeat(rows, args.sha256, args.parent, args.axis, args.value)
    if reasons:
        print("REPEAT -- do not build:")
        for r in reasons:
            print(f"  {r}")
        return 1
    print("NEW: no hash collision and no existing (parent, axis, value)")
    return 0


def cmd_add(args) -> int:
    rows = read_rows(args.ledger)
    reasons = is_repeat(rows, args.sha256, args.parent, args.axis, args.value)
    if reasons:
        print("refusing to add a repeat:", *reasons, sep="\n  ", file=sys.stderr)
        return 1
    row = {k: getattr(args, k, "") or "" for k in COLUMNS}
    row["sha8"] = (args.sha256 or "")[:8]
    row["status"] = args.status
    row["provenance"] = "BUILT_THIS_SESSION"
    rows.append(row)
    write_rows(rows, args.ledger)
    print(f"added {row['id']} ({row['status']}) to {args.ledger}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--raw", default=RAW)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("state").set_defaults(func=cmd_state)

    c = sub.add_parser("collapse")
    c.add_argument("--from", dest="source", default=RAW)
    c.set_defaults(func=cmd_collapse)

    k = sub.add_parser("check")
    k.add_argument("--sha256", default=None)
    k.add_argument("--parent", default="")
    k.add_argument("--axis", default="")
    k.add_argument("--value", default="")
    k.set_defaults(func=cmd_check)

    a = sub.add_parser("add")
    a.add_argument("--id", required=True)
    for f in ("parent", "axis", "value", "n_dots", "pct_changed", "encoding", "predicted_change", "notes"):
        a.add_argument(f"--{f.replace('_', '-')}", dest=f, default="")
    a.add_argument("--sha256", required=True)
    a.add_argument("--status", default="BUILT")
    a.set_defaults(func=cmd_add)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
