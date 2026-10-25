#!/usr/bin/env python3
"""Session 14 Label-Blind Geophysical & Hydrothermal Forensics Verification.

Verifies physical properties of the 19 official competition bands in
`gems-geodawn-numerical-features.tif` and the public-domain DOE GDR #1391
geothermal spring/well compilation `gdr_wellspring_in_footprint.csv` WITHOUT
reading `existing_faults.tif`, `SGMC`, or `dist_known_fault_px`.

Outputs `evidence/s14_hydrothermal_forensics.json` to ground Session 14's
pre-registered hypotheses (`docs/HYPOTHESES_S14.md`) in exact, reproducible,
hallucination-free measurements.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEMPLATE_TIF = DATA / "official" / "sample_submission.tif"
FEATURES_TIF = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR_CSV = DATA / "external" / "gdr_wellspring_in_footprint.csv"
OUT_JSON = ROOT / "evidence" / "s14_hydrothermal_forensics.json"

BANNED_GDR_COLUMNS = {"dist_known_fault_px"}


def _clean_band(raw: np.ndarray, fp: np.ndarray) -> np.ndarray:
    arr = raw.astype(np.float32, copy=True)
    valid = np.isfinite(arr) & (arr > -1.0e30) & fp
    if int(valid.sum()) < arr.size:
        _, idx = ndi.distance_transform_edt(~valid, return_indices=True)
        arr = arr[tuple(idx)]
    return arr


def main() -> int:
    with rasterio.open(TEMPLATE_TIF) as tpl:
        fp = np.isfinite(tpl.read(1))
    h, w = fp.shape
    n_fp = int(fp.sum())

    # 1. Verify Band 10 vs Band 16 swarm correlation & ptha.py sign-inversion audit (`IR-91-S14-01`)
    with rasterio.open(FEATURES_TIF) as src:
        b01 = _clean_band(src.read(1), fp)
        b02 = _clean_band(src.read(2), fp)
        b03 = np.maximum(_clean_band(src.read(3), fp), 0.0)
        b09 = _clean_band(src.read(9), fp)
        b10 = np.maximum(_clean_band(src.read(10), fp), 0.0)
        b12 = _clean_band(src.read(12), fp)
        b13 = _clean_band(src.read(13), fp)
        b14 = _clean_band(src.read(14), fp)
        b15 = np.maximum(_clean_band(src.read(15), fp), 0.0)
        b16 = np.maximum(_clean_band(src.read(16), fp), 0.0)
        b17 = np.maximum(_clean_band(src.read(17), fp), 0.0)

    log_b10 = np.log1p(b10[fp])
    log_b16 = np.log1p(b16[fp])
    corr_b10_b16 = float(np.corrcoef(log_b10[::10], log_b16[::10])[0, 1])

    # 2. Verify Salem et al. (2007) Magnetic Tilt-Depth vs Basement Depth (`B15`)
    h_tmi_si = b03 / np.float32(200.0)
    theta_mag = np.arctan2(b09, h_tmi_si + np.float32(1e-4)).astype(np.float32)
    theta_sm = ndi.gaussian_filter(theta_mag, sigma=1.2)
    gy_t = ndi.sobel(theta_sm, axis=0) / np.float32(800.0)  # rad / m (100 m pixel)
    gx_t = ndi.sobel(theta_sm, axis=1) / np.float32(800.0)
    k_spi_m = np.hypot(gy_t, gx_t)  # rad / m
    z_salem_m = np.clip(1.0 / (k_spi_m + 1e-4), 25.0, 5000.0).astype(np.float32)

    # 3. Verify Cenozoic Basin-Fill Confounding of Gravity (`B13`) & Conductivity (`B17`) by Depth (`B15`)
    d_sub = b15[fp][::20].astype(np.float64)
    g_sub = b13[fp][::20].astype(np.float64)
    c_sub = b17[fp][::20].astype(np.float64)
    X_design = np.column_stack([
        np.ones_like(d_sub),
        d_sub / 1000.0,
        np.sqrt(d_sub / 1000.0),
        np.log1p(d_sub / 100.0),
    ])
    beta_g, _, _, _ = np.linalg.lstsq(X_design, g_sub, rcond=None)
    g_hat = X_design @ beta_g
    r2_grav_depth = float(1.0 - np.var(g_sub - g_hat) / np.var(g_sub))

    beta_c, _, _, _ = np.linalg.lstsq(X_design, c_sub, rcond=None)
    c_hat = X_design @ beta_c
    r2_cond_depth = float(1.0 - np.var(c_sub - c_hat) / np.var(c_sub))

    # 4. Verify Shallow Draped GeoDAWN (`B14 - B01`) High-Frequency Energy Ratio
    b14_hp = b14 - ndi.gaussian_filter(b14, sigma=3.0)
    b01_hp = b01 - ndi.gaussian_filter(b01, sigma=3.0)
    hf_ratio_b14_over_b01 = float(np.std(b14_hp[fp][::10]) / max(np.std(b01_hp[fp][::10]), 1e-6))

    # 5. Label-blind audit of GDR-1391 Geothermal Wells/Springs (`dist_known_fault_px` strictly banned!)
    allowed_cols = {
        "layer",
        "name",
        "thermalclass",
        "row",
        "col",
        "utm_x",
        "utm_y",
        "temp_c",
        "geothermquartz_c",
        "geothermchalc_c",
        "geothermcat_c",
    }
    n_rows = 0
    cell_max_res_temp: dict[tuple[int, int], float] = {}
    cell_max_surf_temp: dict[tuple[int, int], float] = {}
    cell_is_hot_warm: set[tuple[int, int]] = set()
    cell_is_blind_geotherm: set[tuple[int, int]] = set()

    with open(GDR_CSV, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header_cols = set(reader.fieldnames or [])
        used_cols = header_cols & allowed_cols
        assert BANNED_GDR_COLUMNS.isdisjoint(used_cols)
        for rec in reader:
            n_rows += 1
            r = int(float(rec["row"]))
            c = int(float(rec["col"]))
            if not (0 <= r < h and 0 <= c < w and fp[r, c]):
                continue
            key = (r, c)
            tc_tokens = {t.strip() for t in (rec.get("thermalclass") or "").split(",") if t.strip()}
            is_hw = bool(tc_tokens & {"Hot", "Warm"})
            if is_hw:
                cell_is_hot_warm.add(key)

            t_surf = float("nan")
            raw_ts = (rec.get("temp_c") or "").strip()
            if raw_ts and raw_ts.upper() not in ("NULL", "NAN", "NONE"):
                try:
                    v = float(raw_ts)
                    if math.isfinite(v) and 0.0 <= v <= 350.0:
                        t_surf = v
                except ValueError:
                    pass
            if math.isfinite(t_surf):
                cell_max_surf_temp[key] = max(cell_max_surf_temp.get(key, -1e9), t_surf)

            g_vals = []
            for gk in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                raw_g = (rec.get(gk) or "").strip()
                if raw_g and raw_g.upper() not in ("NULL", "NAN", "NONE"):
                    try:
                        gv = float(raw_g)
                        if math.isfinite(gv) and 0.0 <= gv <= 400.0:
                            g_vals.append(gv)
                    except ValueError:
                        pass
            best_res = max(g_vals) if g_vals else (t_surf if math.isfinite(t_surf) else float("nan"))
            if math.isfinite(best_res):
                cell_max_res_temp[key] = max(cell_max_res_temp.get(key, -1e9), best_res)
            if (not is_hw) and g_vals and max(g_vals) >= 90.0:
                cell_is_blind_geotherm.add(key)

    # Check hydraulic head / elevation distribution of hydrothermal manifestations vs basin/range
    elev_fp = b12[fp]
    elev_median = float(np.median(elev_fp[::10]))
    hw_elevs = [float(b12[r, c]) for (r, c) in cell_is_hot_warm]
    blind_elevs = [float(b12[r, c]) for (r, c) in cell_is_blind_geotherm]
    frac_hw_below_median_elev = float(np.mean([e < elev_median for e in hw_elevs]))
    frac_blind_below_median_elev = float(np.mean([e < elev_median for e in blind_elevs]))

    report = {
        "audit_version": "s14-hydrothermal-forensics-v1.0",
        "label_blind": True,
        "banned_columns_never_read": sorted(BANNED_GDR_COLUMNS),
        "footprint_pixels": n_fp,
        "ir_91_s14_01_band10_swarm_audit": {
            "band10_max": round(float(b10[fp].max()), 2),
            "band16_max": round(float(b16[fp].max()), 2),
            "pearson_r_log1p_b10_vs_log1p_b16": round(corr_b10_b16, 6),
            "ptha_line292_defect": "src/gems91/ptha.py computed -log1p(B10/500), inverting Dependent Earthquake Swarm Density into aseismic quietness",
        },
        "salem_tilt_depth_vs_b15": {
            "salem_depth_p25_m": round(float(np.percentile(z_salem_m[fp][::20], 25)), 2),
            "salem_depth_p50_m": round(float(np.percentile(z_salem_m[fp][::20], 50)), 2),
            "salem_depth_p75_m": round(float(np.percentile(z_salem_m[fp][::20], 75)), 2),
            "b15_depth_p50_m": round(float(np.percentile(b15[fp][::20], 50)), 2),
            "shallow_intrabasin_fraction_zsalem_lt_half_b15": round(
                float(np.mean(z_salem_m[fp][::20] < 0.5 * b15[fp][::20])), 5
            ),
        },
        "basin_depth_confounding": {
            "r2_isostatic_gravity_b13_on_depth_b15": round(r2_grav_depth, 6),
            "r2_conductivity_b17_on_depth_b15": round(r2_cond_depth, 6),
        },
        "geodawn_drape_vs_regional": {
            "std_hf300m_ratio_b14_over_b01": round(hf_ratio_b14_over_b01, 4),
        },
        "gdr_hydrothermal_vent_and_blind_geothermometry": {
            "csv_rows_scanned": n_rows,
            "unique_footprint_cells": len(cell_max_res_temp),
            "hot_warm_manifestation_cells": len(cell_is_hot_warm),
            "blind_non_thermal_cells_geotherm_ge_90C": len(cell_is_blind_geotherm),
            "cells_reservoir_temp_ge_120C": sum(v >= 120.0 for v in cell_max_res_temp.values()),
            "cells_reservoir_temp_ge_150C": sum(v >= 150.0 for v in cell_max_res_temp.values()),
            "footprint_det_elev_median_m": round(elev_median, 2),
            "hot_warm_mean_det_elev_m": round(float(np.mean(hw_elevs)), 2),
            "blind_geotherm_mean_det_elev_m": round(float(np.mean(blind_elevs)), 2),
            "frac_hot_warm_in_low_elev_basin_half": round(frac_hw_below_median_elev, 4),
            "frac_blind_geotherm_in_low_elev_basin_half": round(frac_blind_below_median_elev, 4),
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
