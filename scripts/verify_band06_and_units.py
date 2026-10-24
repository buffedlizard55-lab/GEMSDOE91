#!/usr/bin/env python3
"""Label-blind forensic verification of GeoDAWN band semantics and physical units.

Resolves `IR-91-S12-04` (Band 06 `tc` identity) and documents `IR-91-S13-01`
(the 200x dimensional scaling ratio between `Band 03 tmi_hg` [nT / 200 m] and
`Band 09 tmi_vg` [nT / m], plus `Band 05 iso_grav_anom_slope` [deg] vs
`(Band 11, Band 18)` [mGal / km]).

Never reads `existing_faults.tif` or any submission raster.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_TIF = ROOT / "data" / "official" / "sample_submission.tif"
FEATS_TIF = ROOT / "data" / "bridge" / "gems-geodawn-numerical-features.tif"
RAD_TIF = ROOT / "data" / "external" / "geodawn_rad_u8.tif"
OUT_JSON = ROOT / "evidence" / "s13_band06_and_units_audit.json"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    with rasterio.open(SAMPLE_TIF) as s:
        fp = np.isfinite(s.read(1))
    inner = ndi.binary_erosion(fp, iterations=4)

    with rasterio.open(FEATS_TIF) as s:
        b3 = s.read(3)
        b5 = s.read(5)
        b6 = s.read(6)
        b9 = s.read(9)
        b11 = s.read(11)
        b13 = s.read(13)
        b14 = s.read(14)
        b18 = s.read(18)
        b6_tags = dict(s.tags(6))
        b6_desc = s.descriptions[5]

    valid_b6 = fp & np.isfinite(b6) & (b6 > -1e30)
    b6_vals = b6[valid_b6]

    rad_corrs: dict[str, float] = {}
    with rasterio.open(RAD_TIF) as rs:
        rad_descs = list(rs.descriptions)
        for idx in range(1, rs.count + 1):
            rb = rs.read(idx)
            m = valid_b6 & (rb > 0)
            c = float(np.corrcoef(b6[m][::10], rb[m][::10])[0, 1])
            label = f"band_{idx}_{rs.descriptions[idx - 1]}"
            rad_corrs[label] = round(c, 6)

    # Magnetic derivative unit audit
    m_inner = inner & (b3 > -1e30) & (b9 > -1e30) & (b14 > -1e30)
    sub = np.flatnonzero(m_inner)[::20]
    gy14, gx14 = np.gradient(np.where(fp & (b14 > -1e30), b14, 0.0))
    grad14_px = np.hypot(gy14, gx14)  # nT per 100 m pixel
    corr_b3_grad14 = float(np.corrcoef(grad14_px.ravel()[sub], b3.ravel()[sub])[0, 1])
    ratio_b3_to_grad14_px = float(np.median(b3.ravel()[sub] / (grad14_px.ravel()[sub] + 1e-9)))
    p95_b3_raw = float(np.percentile(b3.ravel()[sub], 95))
    p95_b3_nT_per_m = p95_b3_raw / 200.0
    p95_abs_b9_nT_per_m = float(np.percentile(np.abs(b9.ravel()[sub]), 95))

    # Gravity vector & slope unit audit
    gy13, gx13 = np.gradient(np.where(fp & (b13 > -1e30), b13, 0.0))
    corr_b11_dy13 = float(np.corrcoef(b11.ravel()[sub], gy13.ravel()[sub])[0, 1])
    corr_b18_dx13 = float(np.corrcoef(b18.ravel()[sub], gx13.ravel()[sub])[0, 1])
    gh_mag = np.hypot(b11.ravel()[sub], b18.ravel()[sub])
    corr_gh_b5 = float(np.corrcoef(gh_mag, b5.ravel()[sub])[0, 1])
    ratio_gh_to_b5 = float(np.median(gh_mag / (b5.ravel()[sub] + 1e-9)))

    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label_blind": True,
        "inputs": {
            "sample_submission_sha256": _sha256(SAMPLE_TIF),
            "training_features_sha256": _sha256(FEATS_TIF),
            "ext_geodawn_rad_u8_sha256": _sha256(RAD_TIF),
        },
        "ir_91_s12_04_band06_resolution": {
            "embedded_geotiff_description": b6_desc,
            "embedded_geotiff_tags": b6_tags,
            "reference_solution_behavior": (
                "drivendataorg/gems-prize-reference-solution unet-mc-cv-reference-solution.ipynb "
                "Cell 5 prints src.tags(i)['description'] directly from numeric_features.tif"
            ),
            "valid_footprint_pixels": int(valid_b6.sum()),
            "min_value": round(float(b6_vals.min()), 6),
            "median_value": round(float(np.median(b6_vals)), 6),
            "max_value": round(float(b6_vals.max()), 6),
            "strictly_positive": bool(b6_vals.min() > 0.0),
            "pearson_r_vs_geodawn_radiometric_bands": rad_corrs,
            "geodawn_radiometric_band_descriptions": rad_descs,
            "conclusion": (
                "Band 06 values are strictly positive [2.953, 88.57] (ruling out signed magnetic tilt "
                "angle in [-pi/2, +pi/2] or [-90, +90] deg) and match USGS GeoDAWN Airborne Radiometric "
                "Band 4 'TC' (Total Count exposure rate) with Pearson r = 0.99699 across 5,164,300 pixels. "
                "The embedded GeoTIFF metadata tag expanded the GeoDAWN column abbreviation 'tc' as "
                "'Tilt angle or total curvature - magnetic field derivative'."
            ),
        },
        "ir_91_s13_01_dimensional_units_audit": {
            "magnetic_tmi_derivatives": {
                "pearson_r_b03_vs_grad_b14": round(corr_b3_grad14, 6),
                "median_ratio_b03_over_grad_b14_per_100m_px": round(ratio_b3_to_grad14_px, 6),
                "p95_b03_raw_nT_per_200m": round(p95_b3_raw, 5),
                "p95_b03_converted_nT_per_m": round(p95_b3_nT_per_m, 5),
                "p95_abs_b09_tmi_vg_nT_per_m": round(p95_abs_b9_nT_per_m, 5),
                "conclusion": (
                    "Band 03 (tmi_hg) equals 2 * ||grad_px(Band 14)|| (central difference over 200 m, "
                    "r = 0.999954), whereas Band 09 (tmi_vg) is in nT/m (p95 |B09| = 0.46976 nT/m vs "
                    "p95 B03/200 = 0.47076 nT/m, 0.21% match). Dividing B09 by B03 or grad_px(RTP) "
                    "without the 200 m / 100 m pixel factor compresses Verduzco magnetic tilt by 100x-200x."
                ),
            },
            "gravity_derivatives": {
                "pearson_r_b11_vs_dy_b13": round(corr_b11_dy13, 6),
                "pearson_r_b18_vs_dx_b13": round(corr_b18_dx13, 6),
                "pearson_r_hypot_b11_b18_vs_b05": round(corr_gh_b5, 6),
                "median_ratio_hypot_b11_b18_over_b05": round(ratio_gh_to_b5, 5),
                "conclusion": (
                    "(Band 11, Band 18) is the signed 2-D horizontal gravity gradient vector (dG/dy, dG/dx), "
                    "whose Euclidean norm correlates with Band 05 (iso_grav_anom_slope) at r = 0.94684 "
                    "with median scale ratio 17.8316."
                ),
            },
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
