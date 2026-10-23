"""Pin checks against registry/data_manifest.json (the merged repository schema).

`scripts/preflight.py` owns the *verdict* ("may this repo build anything?"). This
module answers the narrower question a builder must ask before it reads a byte:
"is this exact file one of the pinned inputs?"

Rule (brief §4.2): inputs are only files pinned in the manifest, and their sha256 is
verified before use. Anything else is refused, never approximated.

Manifest schema (owned by the other session, do not edit here):
    {"schema_version": 1, "policy": {...},
     "files": [{"id", "local_subpath" (relative to data/), "sha256", "bytes", ...}, ...]}
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

MANIFEST = Path("registry/data_manifest.json")
DATA_ROOT = Path("data")

# Which pinned inputs each axis needs. Extra ids beyond the parent exist because an
# axis that only reads the parent is not testing a mechanism, it is re-spending a slot.
AXIS_INPUTS: dict[str, list[str]] = {
    # MASS ranks by cross-field support over the lineage's own pinned fields, because
    # the parent's continuous ranking is not recoverable (IR-91-17). training_features
    # is not read: it has no mirror and is absent.
    "MASS": ["parent_r0_nan", "existing_faults", "anc_h19_5", "anc_h19_4", "anc_h16_1"],
    "CONCENTRATION": ["parent_r0_nan", "existing_faults", "training_features"],
    "SNAP": ["parent_r0_nan", "existing_faults", "training_features"],
    "PRUNE": ["parent_r0_nan", "existing_faults", "training_features"],
    "RELIEF": ["parent_r0_nan", "existing_faults", "training_features"],
    "SPACING": ["parent_r0_nan", "existing_faults"],
    "TRACKB": ["parent_r0_nan", "existing_faults", "training_features"],
}


def sha256_file(path: Path | str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load(manifest_path: Path = MANIFEST) -> dict:
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} not found - nothing is pinned, nothing may be built")
    return json.loads(manifest_path.read_text())


def pinned_hashes(manifest: dict) -> dict[str, dict]:
    """sha256 -> manifest entry, for every pinned file."""
    return {f["sha256"]: f for f in manifest.get("files", []) if f.get("sha256")}


def resolve(input_id: str, manifest: dict, data_root: Path = DATA_ROOT) -> Path:
    """Local path a pinned input should occupy (whether or not it exists)."""
    for f in manifest.get("files", []):
        if f["id"] == input_id:
            return data_root / f["local_subpath"]
    raise KeyError(f"{input_id} is not in the manifest")


def check_paths(paths: list[Path], manifest_path: Path = MANIFEST) -> tuple[bool, list[dict]]:
    """Every path must be a pinned input, byte for byte. Returns (ok, results)."""
    manifest = load(manifest_path)
    by_hash = pinned_hashes(manifest)
    results: list[dict] = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            results.append({"ok": False, "path": str(p), "detail": "missing on disk"})
            continue
        digest = sha256_file(p)
        entry = by_hash.get(digest)
        if entry is None:
            results.append({"ok": False, "path": str(p), "detail": f"UNPINNED (sha256 {digest[:12]}… not in manifest)"})
        else:
            results.append({"ok": True, "path": str(p), "id": entry["id"],
                            "detail": f"pinned as {entry['id']}"})
    return all(r["ok"] for r in results), results


def missing_ids(axis: str, manifest_path: Path = MANIFEST, data_root: Path = DATA_ROOT) -> list[str]:
    """Pinned inputs this axis needs that are absent locally."""
    manifest = load(manifest_path)
    out = []
    for input_id in AXIS_INPUTS.get(axis, []):
        p = resolve(input_id, manifest, data_root)
        if not p.exists():
            out.append(f"{input_id} -> {p}")
    return out


def check_axis(axis: str, manifest_path: Path = MANIFEST, data_root: Path = DATA_ROOT) -> tuple[bool, list[str]]:
    """Convenience for a builder: (clear_to_build, human-readable reasons)."""
    try:
        missing = missing_ids(axis, manifest_path, data_root)
    except FileNotFoundError as exc:
        return False, [str(exc)]
    if missing:
        return False, [f"missing pinned input: {m}" for m in missing]
    return True, []


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="check pinned inputs for an axis")
    ap.add_argument("--axis", default="CONCENTRATION", choices=sorted(AXIS_INPUTS))
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    args = ap.parse_args(argv)
    clear, reasons = check_axis(args.axis, args.manifest)
    for r in reasons:
        print(f"[BLOCKED] {r}")
    print(f"{args.axis}: {'CLEAR' if clear else 'BLOCKED'}")
    return 0 if clear else 2


if __name__ == "__main__":
    raise SystemExit(main())
