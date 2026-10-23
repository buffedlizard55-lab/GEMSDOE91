"""Verify that every pinned input exists and matches its recorded sha256.

Brief section 4.2: inputs come only from files pinned in the manifest, and the
hash is verified before use. Nothing is fetched here; a missing or unpinned file
is reported as MISSING / UNVERIFIED and the exit code is non-zero.

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


def load_manifest(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check(manifest: dict, root: str | Path = ".") -> tuple[list[dict], bool]:
    root = Path(root)
    rows, all_ok = [], True
    for entry in manifest.get("inputs", []):
        rel = entry["path"]
        p = root / rel
        want = entry.get("sha256")
        row = {
            "path": rel,
            "role": entry.get("role", ""),
            "required": bool(entry.get("required", False)),
            "expected": want,
        }
        if entry.get("generated"):
            row["status"] = "PRESENT" if p.exists() else "MISSING"
            row["actual"] = sha256_file(p) if p.exists() else None
            if not p.exists():
                all_ok = False
            rows.append(row)
            continue
        if not p.exists():
            row["status"] = "MISSING"
            row["actual"] = None
            all_ok = False
        else:
            actual = sha256_file(p)
            row["actual"] = actual
            if not want:
                row["status"] = "UNPINNED"  # present but no hash recorded: cannot verify
                all_ok = False
            elif actual == want:
                row["status"] = "OK"
            else:
                row["status"] = "HASH_MISMATCH"
                all_ok = False
        rows.append(row)
    return rows, all_ok


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Verify pinned inputs against registry/data_manifest.json")
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"NO MANIFEST at {manifest_path}: every input is UNVERIFIED. Stop here (brief section 5).")
        return 2

    manifest = load_manifest(manifest_path)
    rows, all_ok = check(manifest, args.root)

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"manifest: {args.manifest}  (repo {manifest.get('repository', '?')})")
        for r in rows:
            print(f"[{r['status']:12s}] {r['path']:48s} role={r['role']}")
        ok = sum(r["status"] == "OK" for r in rows)
        print(f"\n{ok}/{len(rows)} inputs verified; {'ALL OK' if all_ok else 'NOT VERIFIED'}")

    if not all_ok:
        print(
            "\nRESULT: STOP. Brief section 5 requires R0's sha256 to match before any variant is built; "
            "with inputs missing the parent cannot be rebuilt, so no raster may be produced or named.",
            file=sys.stderr,
        )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
