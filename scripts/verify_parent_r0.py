#!/usr/bin/env python3
"""Gate 0: rebuild R0 and match its sha256 (brief section 5).

What this does, precisely:

1. Fetches the pinned R0 twins from the upstream public mirror and re-hashes
   them. If either hash differs from the pin, STOP - the parent must never be
   approximated.
2. Opens R0 and audits the properties every later gate depends on: grid,
   dtype, band count, value set, dot count, footprint size.
3. Writes registry/r0_verification.json as evidence.

What this does NOT do: independently re-derive R0 from the H33 recipe. That
needs training_features.tif (419 MB, not public) plus the H33 build script.
The distinction matters and is recorded in the output under
"rebuild_kind": "pinned_artifact_retrieval" vs "independent_recompute".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems91.pinned import fetch, load_manifest, local_path_for, sha256_file  # noqa: E402

import rasterio  # noqa: E402

EXPECTED = {
    "parent_r0_zeros": {"sha256": "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
                        "bytes": 219065},
    "parent_r0_nan": {"sha256": "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd",
                      "bytes": 355443},
    "anc_d2_8": {"sha256": "91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8",
                 "bytes": 1603424},
}
N_DOTS_CLAIM = 37654
FOOTPRINT_PX_CLAIM = 5167373


def audit(path: Path) -> dict:
    with rasterio.open(path) as src:
        arr = src.read(1)
        meta = {
            "crs": str(src.crs), "dtype": src.dtypes[0], "count": src.count,
            "shape": [src.height, src.width], "res": [src.res[0], src.res[1]],
            "bounds": [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top],
            "nodata": src.nodata,
        }
    finite = np.isfinite(arr)
    pos = arr > 0
    return {
        "meta": meta,
        "finite_px": int(finite.sum()),
        "nonfinite_px": int((~finite).sum()),
        "n_positive_px": int(pos.sum()),
        "positive_values": sorted(float(v) for v in np.unique(arr[pos]))[:10],
        "min_finite": float(arr[finite].min()) if finite.any() else None,
        "max_finite": float(arr[finite].max()) if finite.any() else None,
    }


def main() -> int:
    man = load_manifest()
    by_id = {e["id"]: e for e in man["files"]}
    data_root = Path("data")
    report: dict = {"schema": "gems91.r0-verification.v1", "rebuild_kind":
                    "pinned_artifact_retrieval", "checks": {}, "ok": True}

    twins = {}
    for fid, exp in EXPECTED.items():
        entry = by_id[fid]
        ok, msg = fetch(entry, data_root)
        path = local_path_for(entry, data_root)
        got = sha256_file(path) if path.exists() else ""
        match_pin = got == entry["sha256"] == exp["sha256"]
        match_bytes = path.exists() and path.stat().st_size == exp["bytes"]
        report["checks"][fid] = {"path": str(path), "sha256": got,
                                 "expected": exp["sha256"],
                                 "bytes": path.stat().st_size if path.exists() else 0,
                                 "expected_bytes": exp["bytes"],
                                 "fetch": msg, "hash_match": match_pin,
                                 "bytes_match": bool(match_bytes)}
        report["ok"] &= bool(match_pin and match_bytes)
        twins[fid] = path

    r0 = audit(twins["parent_r0_nan"])
    audit_zeros = audit(twins["parent_r0_zeros"])
    grid_ok = (r0["meta"]["crs"] == "EPSG:32611" and r0["meta"]["dtype"] == "float32"
               and r0["meta"]["count"] == 1 and r0["meta"]["shape"] == [3730, 3292]
               and r0["meta"]["res"] == [100.0, 100.0])
    n_ok = r0["n_positive_px"] == audit_zeros["n_positive_px"] == N_DOTS_CLAIM
    footprint_ok = r0["finite_px"] == FOOTPRINT_PX_CLAIM
    report["parent_audit"] = {"nan_twin": r0, "zeros_twin": audit_zeros,
                              "grid_matches_pinned": grid_ok,
                              "dot_count_37654": n_ok,
                              "footprint_5167373": footprint_ok,
                              "twins_agree_on_dots": r0["n_positive_px"] == audit_zeros["n_positive_px"]}
    report["ok"] &= bool(grid_ok and n_ok and footprint_ok)

    Path("registry").mkdir(exist_ok=True)
    Path("registry/r0_verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": report["ok"], "rebuild_kind": report["rebuild_kind"],
                      "grid_matches_pinned": grid_ok, "dot_count_37654": n_ok,
                      "footprint_5167373": footprint_ok,
                      "hashes": {k: v["sha256"][:12] for k, v in report["checks"].items()}},
                     indent=2))
    if not report["ok"]:
        print("STOP: parent does not match the pin. Do not approximate it.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
