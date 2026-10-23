"""Build one variant from a named parent, gate it, and stage it for the ledger.

    python scripts/build.py --axis PRUNE --value 3 --id R0-PRUNE3-20261023

Order of operations is the brief's, not mine: verify the parent's hash, apply ONE
axis, write the release pair (NaN-outside and zeros-outside twins), re-read from
disk, run every MUST gate, then print the ledger row. It writes nothing to the
ledger itself and never submits.

Run today this stops at step 1, because no input is pinned (see
registry/data_manifest.json and IRREGULARITIES.md item 2). That is the intended
behaviour, not a bug.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))

import axes as A  # noqa: E402
import validate_raster as V  # noqa: E402
from verify_manifest import check, load_manifest  # noqa: E402


def _load(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(1)


def _write_pair(arr: np.ndarray, ref_path: Path, out_dir: Path, base: str) -> tuple[Path, Path]:
    """Write the NaN-outside release and the zeros-outside fallback twin."""
    with rasterio.open(ref_path) as ref:
        profile = ref.profile.copy()
        fp = np.isfinite(ref.read(1))
    profile.update(dtype="float32", count=1, nodata=np.nan, compress="deflate")

    out_dir.mkdir(parents=True, exist_ok=True)
    nan_path = out_dir / f"{base}.tif"
    with rasterio.open(nan_path, "w", **profile) as dst:
        dst.write(arr.astype(np.float32), 1)

    zeros_profile = profile.copy()
    zeros_profile.update(nodata=np.nan)
    zeros_arr = np.where(fp, np.nan_to_num(arr, nan=0.0), 0.0).astype(np.float32)
    zeros_path = out_dir / f"{base}-zeros.tif"
    with rasterio.open(zeros_path, "w", **zeros_profile) as dst:
        dst.write(zeros_arr, 1)
    return nan_path, zeros_path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build one axis variant from a named parent.")
    ap.add_argument("--axis", required=True, choices=["MASS", "PRUNE", "SNAP", "CONCENTRATION"])
    ap.add_argument("--value", required=True, help="axis parameter, e.g. 3 for PRUNE <=3 px")
    ap.add_argument("--id", required=True, help="variant id, e.g. R0-PRUNE3-20261023-ab12cd34")
    ap.add_argument("--parent", default="data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif")
    ap.add_argument("--reference", default="data/official/sample_submission.tif")
    ap.add_argument("--catalogue", default="data/derived/catalogue_mask.tif")
    ap.add_argument("--rank", default="data/bridge/rank.tif", help="parent's own ranking (MASS, PRUNE refill)")
    ap.add_argument("--driver", default=None, help="edge/response raster for SNAP")
    ap.add_argument("--prior", default=None, help="km-scale prior raster for CONCENTRATION")
    ap.add_argument("--fraction", type=float, default=0.10)
    ap.add_argument("--block-px", type=int, default=16)
    ap.add_argument("--radius", type=int, default=2)
    ap.add_argument("--out", default="releases")
    ap.add_argument("--manifest", default="registry/data_manifest.json")
    ap.add_argument("--skip-manifest", action="store_true", help="only after the human confirms hashes by hand")
    args = ap.parse_args(argv)

    # STEP 1 -- the inputs THIS axis needs must be pinned, present and hash-verified
    if not args.skip_manifest:
        mp = Path(args.manifest)
        if not mp.exists():
            print("STOP: no manifest. Every input is UNVERIFIED.", file=sys.stderr)
            return 2
        manifest = load_manifest(mp)
        rows, _ = check(manifest, "data")
        ok_ids = {r["id"] for r in rows if r["status"] == "OK"}
        for r in rows:
            if r["status"] == "OK":
                print(f"[OK      ] {r['id']}")
        needs = manifest.get("axis_requirements", {}).get(args.axis, [])
        missing = [n for n in needs if n not in ok_ids]
        if missing:
            print(
                f"\nSTOP: {args.axis} needs {', '.join(missing)}, which is not pinned, present and "
                "hash-verified. Brief sections 4.2 and 5 forbid building from an unverified input.",
                file=sys.stderr,
            )
            return 2
        print(f"[READY   ] all {len(needs)} inputs required by {args.axis} are hash-verified")

    parent_p, ref_p, cat_p = Path(args.parent), Path(args.reference), Path(args.catalogue)
    for p in (parent_p, ref_p, cat_p):
        if not p.exists():
            print(f"STOP: missing input {p}", file=sys.stderr)
            return 2

    # STEP 2 -- exactly one axis
    parent, ref, cat = _load(parent_p), _load(ref_p), _load(cat_p)
    rank = _load(Path(args.rank)) if Path(args.rank).exists() else None

    if args.axis == "MASS":
        if rank is None:
            print("STOP: MASS needs the parent's ranking at --rank", file=sys.stderr)
            return 2
        mode = "add" if str(args.value).startswith("add") else "drop"
        res = A.mass(parent, ref, rank, cat, args.fraction, mode)
        res.value = str(args.value)
    elif args.axis == "PRUNE":
        res = A.prune(parent, ref, cat, rank, float(args.value))
    elif args.axis == "SNAP":
        if not args.driver:
            print("STOP: SNAP needs --driver", file=sys.stderr)
            return 2
        res = A.snap(parent, ref, _load(Path(args.driver)), cat, args.radius)
    else:
        if not args.prior:
            print("STOP: CONCENTRATION needs --prior", file=sys.stderr)
            return 2
        res = A.concentration(parent, ref, _load(Path(args.prior)), cat, args.block_px, args.fraction)

    pct = res.stats["pct_changed"]
    if args.axis != "SNAP" and pct == 0.0:
        print(
            f"STOP: {args.axis} changed 0% of dots -- this parameter is a no-op on this parent, so the "
            "file would be a repeat in substance and the slot would be wasted. Pick a parameter that bites.",
            file=sys.stderr,
        )
        return 2
    if args.axis != "SNAP" and not 1.0 <= pct <= 50.0:
        print(f"STOP: axis changed {pct}% of dots; brief requires 1-50% (SNAP is exempt: same-count move)",
              file=sys.stderr)
        return 2

    # STEP 3 -- write both twins
    nan_path, zeros_path = _write_pair(res.array, ref_p, Path(args.out), args.id)
    print(res.summary())
    print(f"wrote {nan_path}\nwrote {zeros_path}")

    # STEP 4 -- gates, including a re-read from disk
    rep = V.validate_raster(nan_path, ref_p, catalogue=cat_p, ledger_csv="ledger/submissions.csv", parent=parent_p)
    print(rep.text())
    print("\nRESULT:", "PASS" if rep.ok else "FAIL")
    if not rep.ok:
        return 1

    # STEP 5 -- the row the human pastes (score/date left empty on purpose)
    digest = V.sha256_file(nan_path)
    print("\nledger row:")
    print(f"  id={args.id} parent={parent_p.stem} axis={res.axis} value={res.value} "
          f"n_dots={res.stats['n_dots']} pct_changed={res.stats['pct_changed']} sha256={digest}")
    print(f"  date={dt.date.today().isoformat()}  status=BUILT  receipt_score= (human)  receipt_date= (human)")
    print("No submission was made by this script; the human uploads one file per slot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
