"""Preflight: is this repository allowed to build anything yet?

Checks, in order, and stops at the first blocking failure:

  1. registry/data_manifest.json exists and parses
  2. every input marked required for the requested axis is present on disk
  3. every present input matches its pinned sha256 (and is pinned at all)
  4. for the parent: its sha256 equals `parent_sha256_expected`
  5. the raster inputs share the sample's grid (CRS/shape/transform)

Exit 0 = clear to build. 2 = blocked (prints exactly what to supply). 1 = bad usage.

    python -m tools.preflight --axis CONCENTRATION
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import rasterio

MANIFEST = Path("registry/data_manifest.json")

# what each axis needs beyond the always-required sample_submission
AXIS_INPUTS = {
    "MASS": ["R0_parent", "R0_ranking"],
    "CONCENTRATION": ["R0_parent", "catalogue_mask", "km_prior"],
    "SNAP": ["R0_parent", "catalogue_mask", "tmi_gradient", "gravity_gradient"],
    "PRUNE": ["R0_parent", "catalogue_mask", "R0_ranking"],
    "RELIEF": ["R0_parent", "catalogue_mask", "detrended_elevation"],
    "SPACING": ["R0_parent", "catalogue_mask"],
    "TRACKB": ["R0_parent", "R0_ranking", "catalogue_mask"],
}


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def check(axis: str, manifest_path: Path = MANIFEST, quiet: bool = False) -> tuple[bool, list[dict]]:
    results: list[dict] = []

    def add(ok: bool, item: str, detail: str, blocking: bool = True):
        results.append({"ok": ok, "item": item, "detail": detail, "blocking": blocking})
        if not quiet:
            tag = "ok  " if ok else ("FAIL" if blocking else "warn")
            print(f"[{tag}] {item}: {detail}")

    if not manifest_path.exists():
        add(False, "manifest", f"{manifest_path} not found - nothing is pinned, nothing may be built")
        return False, results
    try:
        man = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        add(False, "manifest", f"unparseable: {exc}")
        return False, results
    inputs = {i["id"]: i for i in man.get("inputs", [])}
    add(True, "manifest", f"{len(inputs)} inputs declared")

    need = ["sample_submission"] + AXIS_INPUTS.get(axis, [])
    for input_id in need:
        entry = inputs.get(input_id)
        if entry is None:
            add(False, f"input {input_id}", "not declared in the manifest (axis needs it)")
            continue
        path = Path(entry["path"])
        if not path.exists():
            add(False, f"input {input_id}", f"missing on disk: {path}")
            continue
        pinned = entry.get("sha256")
        if not pinned:
            add(False, f"input {input_id}", f"present but UNPINNED (sha256 null): {path}")
            continue
        actual = sha256_file(path)
        ok = actual == pinned
        add(ok, f"input {input_id}", f"{path} sha256 {'matches' if ok else 'MISMATCH: ' + actual}")

    # parent must be the exact parent, byte for byte
    parent = inputs.get("R0_parent")
    if parent and Path(parent["path"]).exists():
        expected = parent.get("parent_sha256_expected")
        actual = sha256_file(Path(parent["path"]))
        if not expected:
            add(False, "R0 identity", "parent_sha256_expected is null: record the parent's sha256 "
                                       "before rebuilding it, otherwise 'R0 matched' cannot be claimed")
        else:
            add(actual == expected, "R0 identity",
               f"sha256 {'matches the recorded parent' if actual == expected else 'differs from the recorded parent'}")

    # grid agreement
    sample = inputs.get("sample_submission")
    if sample and Path(sample["path"]).exists():
        with rasterio.open(sample["path"]) as sds:
            ref = (str(sds.crs), sds.height, sds.width, tuple(sds.transform)[:6])
        for input_id in need:
            entry = inputs.get(input_id)
            if not entry or input_id == "sample_submission":
                continue
            p = Path(entry["path"])
            if not p.exists() or p.suffix.lower() not in (".tif", ".tiff"):
                continue
            with rasterio.open(p) as ds:
                got = (str(ds.crs), ds.height, ds.width, tuple(ds.transform)[:6])
            add(got == ref, f"grid {input_id}", "same grid as sample_submission" if got == ref
                else f"DIFFERENT grid: {got[:3]} vs {ref[:3]}")

    blocked = [r for r in results if not r["ok"] and r["blocking"]]
    return not blocked, results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--axis", default="CONCENTRATION", choices=sorted(AXIS_INPUTS) + ["ALL"])
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)

    axes = sorted(AXIS_INPUTS) if args.axis == "ALL" else [args.axis]
    summary = {}
    for axis in axes:
        print(f"\n== {axis} ==")
        ok, results = check(axis, args.manifest)
        summary[axis] = {"clear_to_build": ok, "blocking": [r for r in results if not r["ok"] and r["blocking"]]}
        print(f"   -> {'CLEAR' if ok else 'BLOCKED'}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, indent=2))

    print("\nNothing was built. Supply the missing inputs listed above (pinned by sha256) "
          "to unblock.", file=sys.stderr if not all(v["clear_to_build"] for v in summary.values()) else sys.stdout)
    return 0 if all(v["clear_to_build"] for v in summary.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
