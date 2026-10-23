"""Verify that every pinned input is present and matches its recorded sha256.

Reads the repository's canonical manifest, ``registry/data_manifest.json``, whose
schema is ``{"files": [{id, local_subpath, sha256, bytes, role, verified_here}]}``
with ``local_subpath`` relative to ``--data-root`` (default ``data/``).

Brief section 4.2: inputs come only from pinned files and the hash is verified
before use. Nothing is fetched here; a missing or mismatched file is reported and
the exit code is non-zero, which blocks ``scripts/build.py``.

This script never downloads anything and never contacts drivendata.org.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_raster import sha256_file  # noqa: E402

MANIFEST = "registry/data_manifest.json"


def check(manifest: dict, data_root: str | Path = "data") -> tuple[list[dict], bool]:
    """Returns (rows, all_required_ok). ``derived`` files are hashed too if present."""
    root = Path(data_root)
    rows, all_ok = [], True
    entries = list(manifest.get("files", [])) + list(manifest.get("derived", []))
    for entry in entries:
        rel = entry.get("local_subpath") or entry.get("path")
        want = entry.get("sha256")
        p = root / rel
        row = {"id": entry.get("id") or rel, "path": str(p), "role": entry.get("role", ""),
               "expected": want, "derived": "local_subpath" not in entry}
        if not p.exists():
            row.update(status="MISSING", actual=None)
            # a derived file is reported, not fatal: it is rebuilt from a pinned input
            if not row["derived"]:
                all_ok = False
        else:
            actual = sha256_file(p)
            row["actual"] = actual
            if not want:
                row["status"] = "UNPINNED"
                all_ok = False
            elif actual == want:
                row["status"] = "OK"
            else:
                row["status"] = "HASH_MISMATCH"
                all_ok = False
        rows.append(row)
    return rows, all_ok


def verified_ids(manifest: dict, data_root: str | Path = "data") -> set[str]:
    rows, _ = check(manifest, data_root)
    return {r["id"] for r in rows if r["status"] == "OK"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Verify pinned inputs against registry/data_manifest.json")
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    mp = Path(args.manifest)
    if not mp.exists():
        print(f"NO MANIFEST at {mp}: every input is UNVERIFIED. Stop here (brief section 5).")
        return 2
    manifest = json.loads(mp.read_text())
    rows, all_ok = check(manifest, args.data_root)
    ok_ids = {r["id"] for r in rows if r["status"] == "OK"}
    readiness = {}
    for axis, needs in manifest.get("axis_requirements", {}).items():
        missing = [n for n in needs if n not in ok_ids]
        readiness[axis] = {"ready": not missing, "missing": missing}

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"manifest: {args.manifest}  (data root: {args.data_root})")
        for r in rows:
            tag = r["status"] + ("*" if r["derived"] else "")
            print(f"[{tag:14s}] {r['id']:28s} {r['path']}")
        ok = sum(r["status"] == "OK" for r in rows)
        print(f"\n{ok}/{len(rows)} entries verified")
        if not all_ok:
            print("\nNot every pinned entry is present. That is NOT automatically fatal:")
            print("an axis only needs the entries listed for it in axis_requirements.")
        print("\naxis readiness:")
        for axis, st in readiness.items():
            mark = "READY  " if st["ready"] else "blocked"
            extra = "" if st["ready"] else f"  (missing: {', '.join(st['missing'])})"
            print(f"  [{mark}] {axis}{extra}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


def load_manifest(path: str | Path = MANIFEST) -> dict:
    """Read the canonical manifest. Kept here so builders import one module."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
