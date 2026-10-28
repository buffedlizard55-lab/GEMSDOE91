#!/usr/bin/env python3
"""S25 dot-geography profile (post-hoc, descriptive; creates no candidate).

Explains mechanically why the LFI MODEL projection of the frozen S25 raster
is low despite its holdout win: histograms of emitted dots by distance to the
competition catalogue, distance to the H19-5 multiline network, and LFI
consensus votes, for the candidate and three comparators. All inputs are
SHA-verified pinned rasters. Output: docs/s25/dot-profile.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(rel):
    with rasterio.open(ROOT / rel) as ds:
        return ds.read(1)


def main() -> int:
    man = {r["id"]: r for r in json.loads((ROOT / "registry/data_manifest.json").read_text())["files"]}
    for rid in ("sample_submission", "existing_faults", "parent_r0_zeros"):
        p = ROOT / "data" / man[rid]["local_subpath"]
        if sha(p) != man[rid]["sha256"]:
            raise ValueError(f"pinned drift {rid}")
    rc = json.loads((ROOT / "docs/s25/run-card.json").read_text())
    fp = np.isfinite(load("data/official/sample_submission.tif"))
    cat = (load("data/official/existing_faults.tif") > 0) & fp
    net = (np.nan_to_num(load("data/fleet_registry/19GEMSDOE__h19-5-powerlaw-budget-multiline.tif")) > 0) & fp
    dcat = ndi.distance_transform_edt(~cat)
    dnet = ndi.distance_transform_edt(~net)
    votes = np.load(ROOT / "work/lfi/cons_votes.npy")

    targets = {
        "s25_fabric_e2_candidate": rc["artifact"]["tif"],
        "parent_r0_gemsdoe32": "data/" + man["parent_r0_zeros"]["local_subpath"],
        "s21_pdwc_e3": "docs/downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif",
        "s24_cckm_e2": "docs/downloads/gems91-s24-cckm-e2-37654dots-20261027T190354Z-d69650bd-zeros.tif",
    }
    dcat_edges = [(0, 3), (3, 5), (5, 10), (10, 20), (20, 40), (40, float("inf"))]
    dnet_edges = [(0, 1.5), (1.5, 3), (3, 6), (6, float("inf"))]

    def hist(v, edges):
        return {f"({lo},{hi}]": round(float(((v > lo) & (v <= hi)).mean()), 4)
                for lo, hi in edges}

    rows = []
    for name, rel in targets.items():
        a = np.nan_to_num(load(rel))
        dots = (a > 0) & fp
        dc, dn, vt = dcat[dots], dnet[dots], votes[dots]
        rows.append({
            "name": name, "path": rel, "sha256": sha(ROOT / rel),
            "n_dots": int(dots.sum()),
            "dcat_px_hist": hist(dc, dcat_edges),
            "dcat_px_median": round(float(np.median(dc)), 3),
            "dnet_px_hist": hist(dn, dnet_edges),
            "dnet_px_median": round(float(np.median(dn)), 3),
            "cons_votes_hist": {"0": round(float((vt == 0).mean()), 4),
                                "1": round(float((vt == 1).mean()), 4),
                                "2": round(float((vt == 2).mean()), 4),
                                ">=3": round(float((vt >= 3).mean()), 4)},
        })
        print(name, "median dcat", rows[-1]["dcat_px_median"],
              "frac 3-5px", rows[-1]["dcat_px_hist"]["(3,5]"], flush=True)
    fit = json.loads((ROOT / "work/lfi/fit_r1.0_fNone.json").read_text())
    out = {"label": "DESCRIPTIVE DOT PROFILE (not a score)",
           "lfi_refit_theta_dcat": {k: v for k, v in fit["theta"].items()
                                    if k.startswith("dcat")},
           "rows": rows}
    p = ROOT / "docs/s25/dot-profile.json"
    p.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
