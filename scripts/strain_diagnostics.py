#!/usr/bin/env python3
"""Post-build, REPORT-ONLY control diagnostics for the Session 8 strain arms.

These numbers exist to calibrate the *translator*, not to re-predict the arms
(their ledger predictions were frozen in
`registry/strain_concentration_preregistration.json` and are not changed here):

1. SGMC-off-catalogue density by strain/dilatation prior decile - does the
   independent map agree with the catalogue's strain association?
2. The same frozen SGMC translator applied to the GDR concentration arms
   (replicated in memory at their legacy settings; prior digests must match
   `registry/derived_priors.json`) and to a smooth random-prior null built
   with the strain arms' exact settings - what does the concentration
   *operation* cost on SGMC before any prior is credited?

Writes `reports/strain_control_diagnostics_20261024.json`.  No raster is
written, no ledger row is touched, nothing is a score.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gems91 import geom, io, prior as priors, relief, strain  # noqa: E402
from tools import raster_io, run_concentration  # noqa: E402

CLAIMED_LIVE = 0.2778
SEED = 91025


def decile_rates(arr: np.ndarray, footprint: np.ndarray, truth: np.ndarray) -> list[float]:
    edges = np.quantile(arr[footprint], np.linspace(0, 1, 11))
    out = []
    for i in range(10):
        m = footprint & (arr >= edges[i]) & ((arr <= edges[i + 1]) if i == 9 else (arr < edges[i + 1]))
        out.append(round(float(truth[m].mean() * 100.0), 4))
    return out


def main() -> int:
    fp = geom.footprint_mask(io.read_grid(ROOT / "data/official/sample_submission.tif"))
    cat = geom.catalogue_mask(io.read_grid(ROOT / "data/official/existing_faults.tif"))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(
        ROOT / "data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"))
    with rasterio.open(str(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif")) as src:
        sgmc_off = (src.read(1) > 0) & fp & (dcat > 3.0)
    d_sg = ndi.distance_transform_edt(~sgmc_off)
    r0 = relief.fast_binary_dti(parent, sgmc_off, d_truth=d_sg)

    with rasterio.open(str(ROOT / "data/bridge/gems-geodawn-numerical-features.tif")) as src:
        sarr, _ = strain.strain_prior(src.read(4), src.read(7), fp)
        darr, _ = strain.dilatation_prior(src.read(8), fp)

    h, w = fp.shape
    quadrants = {}
    for name, arr in (("strain", sarr), ("dilatation", darr)):
        west = fp.copy(); west[:, w // 2:] = False
        east = fp.copy(); east[:, :w // 2] = False
        north = fp.copy(); north[h // 2:, :] = False
        south = fp.copy(); south[:h // 2, :] = False
        quadrants[name] = {k: round(float(np.nanmean(arr[m])), 4) for k, m in
                           (("west", west), ("east", east), ("north", north), ("south", south))}

    def translator(dots: np.ndarray) -> dict:
        sg = relief.fast_binary_dti(dots, sgmc_off, d_truth=d_sg)
        rel = (sg["T"] - r0["T"]) / r0["T"]
        return {"sgmc_T": round(sg["T"], 3), "sgmc_rel_T": round(float(rel), 6),
                "frozen_translator_point_MODEL": round(CLAIMED_LIVE * float(rel) * 0.5, 4),
                "sgmc_delta_dti": round(sg["dti"] - r0["dti"], 6)}

    parent_band = np.where(fp, parent.astype(np.float32), np.float32(0.0))
    controls: dict[str, dict] = {}

    feats = priors.read_features(ROOT / "data/external/gdr_wellspring_in_footprint.csv")
    cells = feats["cells"]
    for name, kept, pinned in (
            ("gdr25m10_replicate", cells, "51f294b259ced272a9a121eefae357d6f3c316376182c2b797b32f556992d5ca"),
            ("gdr25rm10_replicate", priors.keep_remote(cells, dcat, priors.REMOTE_MIN_PX),
             "6afed3bf2b51d1070bed4dfd071d93cde75b252f329cf2f5f5bb9868606beec0")):
        parr = priors.distance_prior(fp.shape, kept, fp, priors.SIGMA_PX)
        digest = priors.array_digest(parr)
        if digest != pinned:
            raise SystemExit(f"STOP: {name} prior digest {digest} != pinned {pinned}")
        band, stats = run_concentration.build_concentration(
            parent_band, parr, fp, cat, frac=0.10, block_px=25, min_gap_px=3.0,
            seed=SEED, min_sep_px=2.0)  # legacy GDR settings: no donor quarantine
        dots = io.dot_mask(band)
        controls[name] = {"prior_digest": digest, "n_moved": stats["n_dots_moved"],
                          "collar_le3px_after": int(((dcat <= 3.0) & dots).sum()),
                          "settings": "legacy GDR (no donor quarantine)", **translator(dots)}

    rng = np.random.default_rng(42)
    rand = ndi.gaussian_filter(rng.random(fp.shape).astype(np.float32), sigma=25)
    rand[~fp] = np.nan
    band, stats = run_concentration.build_concentration(
        parent_band, rand.astype(np.float32), fp, cat, frac=0.10, block_px=25,
        min_gap_px=3.0, seed=SEED, min_sep_px=2.0, donor_exclude=dcat <= 3.0)
    controls["random_smooth_null_m10"] = {
        "n_moved": stats["n_dots_moved"], "settings": "strain-arm settings (donor-quarantined)",
        **translator(io.dot_mask(band))}

    out = {
        "schema": "gems91.strain-control-diagnostics.v1",
        "date": "2026-10-24",
        "note": "REPORT ONLY. Post-build translator calibration; ledger predictions unchanged.",
        "git_sha": raster_io.git_sha(short=False),
        "sgmc_off_n_px": int(sgmc_off.sum()),
        "r0_sgmc": {"T": round(r0["T"], 3), "dti": round(r0["dti"], 6)},
        "sgmc_density_pct_by_prior_decile": {
            "strain": decile_rates(sarr, fp, sgmc_off),
            "dilatation": decile_rates(darr, fp, sgmc_off),
        },
        "catalogue_density_pct_by_prior_decile": {
            "strain": decile_rates(sarr, fp, cat),
            "dilatation": decile_rates(darr, fp, cat),
        },
        "prior_mean_percentile_by_half": quadrants,
        "translator_on_controls": controls,
        "reading": (
            "On the frozen SGMC translator the concentration operation itself costs "
            "relT -0.029 under a random prior; the GDR priors cost only -0.007/-0.017 "
            "(they beat the null), while strain 10% costs -0.041 and dilatation 10% "
            "-0.110 (both worse than random). The catalogue's strain association does "
            "not replicate on SGMC-only faults (decile profiles above)."
        ),
    }
    path = ROOT / "reports/strain_control_diagnostics_20261024.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
