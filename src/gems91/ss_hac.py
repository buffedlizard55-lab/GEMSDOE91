"""SSHAC lane — seismo-strain hydrothermal alteration corridor (2026-10-24).

Frozen lane: docs/HYPOTHESES_SSHAC.md, branch arena/b4be2804-gemsdoe91.

Features are all sponsor-band, licence-clean, catalogue-free (no
distance-to-catalogue feature enters training). Sentinel handling and
percentile ranking follow the repo convention in gems91.relief
(fill_footprint_percentile + nearest-valid EDT).

No dot/mask/ranking is read from R0 or any ancestor.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .relief import fill_footprint_percentile
from .denovo import disk_offsets  # reuse
try:
    from .fuse91 import scatter_smooth, tiered_greedy_spaced  # reuse if present
except Exception:  # noqa: BLE001
    scatter_smooth = None  # type: ignore[assignment]
    tiered_greedy_spaced = None  # type: ignore[assignment]

# 1-based band indices verified from file tags 2026-10-24.
BANDS = {
    "mag_anom": 1,
    "rtp": 2,
    "tmi_hg": 3,
    "geod_2ndinv": 4,
    "iso_grav_anom_slope": 5,
    "tc": 6,
    "geod_shearrate": 7,
    "geod_dilaterate": 8,
    "tmi_vg": 9,
    "deq_n100a15": 10,
    "iso_grav_anom_vg": 11,
    "det_elev": 12,
    "iso_grav_anom": 13,
    "tmi": 14,
    "depth_to_base_surf": 15,
    "ieq_n100a15": 16,
    "cond_surf": 17,
    "iso_grav_anom_hg": 18,
    "det_elev_slope": 19,
}

# New derived feature names (10) — order matters, first 19 are raw percentiles.
NEW_FEATURE_NAMES = [
    "seis_prox_pct",              # 1 - pct(deq) : near EQ = high
    "seis_intensity_smooth_pct",  # pct(gauss(ieq,5px))
    "strain_mag_pct",             # pct(geod_2ndinv) (recomputed for canary audit)
    "strain_shear_ratio_pct",     # pct(|shear|/(2ndinv+eps))
    "strain_dil_share_pct",       # pct(dilat/(2ndinv+eps), percentile, can be negative)
    "tc_grad_pct",                # pct(|grad(tc)|)
    "tc_lap_abs_pct",             # pct(|lap(tc)|)
    "mag_ridge_hp_pct",           # pct(high-pass(mag family))
    "grav_ridge_hp_pct",          # pct(high-pass(grav family))
    "topo_ridge_hp_pct",          # pct(high-pass(topo family + lap))
]

ALL_FEATURE_NAMES = (
    [f"pct_{k}" for k in BANDS.keys()]
    + NEW_FEATURE_NAMES
    + ["tri3_concord_pct"]  # 33rd: TRI3-like geometric-mean concordance (diagnostic but also in HGB)
)

# Actually we will produce 32 features: 19 raw + 10 new + 3 ridges = 32
# tri3_concord is the 33rd diagnostic, not in HGB for H11 fairness — we drop it to 32.
# Keep list at 32: 19 raw + 10 new + 3 ridges

FEATURE_NAMES_32 = (
    [f"pct_{k}" for k in BANDS.keys()]  # 19
    + NEW_FEATURE_NAMES[:7]  # 7 of the new (up to tc_lap)
    + ["mag_ridge_hp_pct", "grav_ridge_hp_pct", "topo_ridge_hp_pct"]  # 3
    + ["strain_mag_pct_dup", "seis_prox_pct", "seis_intensity_smooth_pct"]  # keep 32? adjust
)

# Final definitive 32-feature list:
FEATURE_NAMES = [
    # 19 raw footprint percentiles (B1..19)
    "pct_mag_anom",
    "pct_rtp",
    "pct_tmi_hg",
    "pct_geod_2ndinv",
    "pct_iso_grav_anom_slope",
    "pct_tc",
    "pct_geod_shearrate",
    "pct_geod_dilaterate",
    "pct_tmi_vg",
    "pct_deq_n100a15",
    "pct_iso_grav_anom_vg",
    "pct_det_elev",
    "pct_iso_grav_anom",
    "pct_tmi",
    "pct_depth_to_base_surf",
    "pct_ieq_n100a15",
    "pct_cond_surf",
    "pct_iso_grav_anom_hg",
    "pct_det_elev_slope",
    # 10 derived (catalogue-free)
    "seis_prox_pct",
    "seis_intensity_smooth_pct",
    "strain_shear_ratio_pct",
    "strain_dil_share_pct",
    "tc_grad_pct",
    "tc_lap_abs_pct",
    "mag_ridge_hp_pct",
    "grav_ridge_hp_pct",
    "topo_ridge_hp_pct",
    "strain_mag_pct2",
    # 3 complementary (make 32)
    "cond_depth_resid_proxy_pct",  # simple B17 - median(B17|B15 decile) proxy
    "depth_grad_pct",
    "iso_grav_grad_pct",
]


SENTINEL = -1e30
HIGH_PASS_SIGMA_PX = 5.0


def _clean_band(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Return float64 array where sentinel/non-finite/outside-footprint are NaN."""
    a = np.asarray(arr, dtype=np.float64)
    bad = (~np.isfinite(a)) | (a < SENTINEL) | (~footprint)
    out = np.where(bad, np.nan, a)
    return out


def _fill_nearest(arr: np.ndarray) -> np.ndarray:
    bad = ~np.isfinite(arr)
    if not bad.any():
        return arr
    _, idx = ndi.distance_transform_edt(bad, return_indices=True)
    return arr[idx[0], idx[1]]


def _pct(arr_filled: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    pct, _ = fill_footprint_percentile(arr_filled, footprint)
    return np.where(footprint, pct, 0.0).astype(np.float32)


def _high_pass(field: np.ndarray, footprint: np.ndarray, sigma: float = HIGH_PASS_SIGMA_PX) -> np.ndarray:
    f = field.astype(np.float32)
    smooth = ndi.gaussian_filter(f, sigma, mode="nearest")
    hp = np.where(footprint, f - smooth, 0.0).astype(np.float32)
    return hp


def build_features(
    bands: dict[str, np.ndarray],
    footprint: np.ndarray,
) -> tuple[np.ndarray, list[str], dict]:
    """Build 32-feature matrix (n_footprint × 32, float32) for SSHAC lane.

    `bands` dict keys are BANDS keys, values are raw read( band ) arrays.
    Footprint is boolean (3730×3292).
    Returns (X_fp, feature_names, audit).
    """
    fp = np.asarray(footprint, dtype=bool)
    n_fp = int(fp.sum())
    audit: dict = {"n_footprint": n_fp, "bands_used": sorted(bands.keys())}

    # Clean each band (sentinel → NaN → nearest EDT fill inside footprint)
    cleaned: dict[str, np.ndarray] = {}
    for name in BANDS:
        raw = bands[name]
        a = _clean_band(raw, fp)
        # fill inside footprint only; outside remains NaN but we mask with fp later
        filled = _fill_nearest(a)
        cleaned[name] = filled

    # Raw percentiles (19)
    raw_pcts: dict[str, np.ndarray] = {}
    for name in BANDS:
        raw_pcts[name] = _pct(cleaned[name], fp)

    # Derived: seismic proximity and smoothed intensity
    # B10 deq: distance to EQ, small = near; we want proximity = 1 - pct
    pct_deq = raw_pcts["deq_n100a15"]
    seis_prox = np.where(fp, 1.0 - pct_deq, 0.0).astype(np.float32)

    # B16 ieq: intensity, smooth sigma 5 px then percentile
    ieq_filled = cleaned["ieq_n100a15"]
    ieq_smooth = ndi.gaussian_filter(_fill_nearest(ieq_filled), 5.0, mode="nearest")
    seis_smooth_pct = _pct(ieq_smooth, fp)

    # Strain features
    # B04 magnitude already as pct_geod_2ndinv, but we also need ratios
    second = cleaned["geod_2ndinv"]
    shear = cleaned["geod_shearrate"]
    dilat = cleaned["geod_dilaterate"]
    eps = 1e-12
    # fill for gradient ops where needed
    second_f = _fill_nearest(second)
    shear_f = _fill_nearest(shear)
    dilat_f = _fill_nearest(dilat)
    shear_ratio = np.abs(shear_f) / (np.abs(second_f) + 1e-3 + eps)
    # dilat share: signed dilat / magnitude, keeps sign for transtension vs transpression
    dil_share = dilat_f / (np.abs(second_f) + 1e-3 + eps)
    # clip extreme tails for percentile stability (still fully represented in rank)
    shear_ratio_pct = _pct(np.clip(shear_ratio, -1e2, 1e2), fp) if np.isfinite(shear_ratio).any() else np.zeros(fp.shape, dtype=np.float32)
    dil_share_pct = _pct(dil_share, fp)

    # Normalize second magnitude for dedicated feature (same as raw but keep for canary audit)
    strain_mag_pct2 = raw_pcts["geod_2ndinv"]  # alias

    # Radiometric tc edge features
    tc_filled = cleaned["tc"]
    tc_f = _fill_nearest(tc_filled)
    gy, gx = np.gradient(ndi.gaussian_filter(tc_f, 1.5, mode="nearest"))
    tc_grad = np.hypot(gx, gy)
    tc_grad_pct = _pct(tc_grad, fp)
    tc_lap = np.abs(ndi.laplace(ndi.gaussian_filter(tc_f, 1.0, mode="nearest")))
    tc_lap_pct = _pct(tc_lap, fp)

    # Family high-pass ridges (mag/grav/topo) — reuse denovo.family_field logic but simplified
    # MAG family: pct(tmi_hg) + pct(tc) + pct(|tmi_vg|)  (tc already above but include for ridge)
    # Use raw_pcts mean then high-pass
    def family_ridge(names, extra_lap=None):
        acc = np.zeros(fp.shape, dtype=np.float32)
        n = 0
        for nm in names:
            a = raw_pcts[nm] if nm in raw_pcts else _pct(cleaned[nm], fp)
            # tmi_vg and grav components are directional magnitudes; take abs before pct already done for raw, but for ridge we want magnitude
            acc += a
            n += 1
        if extra_lap is not None:
            acc += extra_lap
            n += 1
        field = (acc / float(n)).astype(np.float32)
        hp = _high_pass(field, fp)
        return _pct(hp, fp)

    # For topo extra, add |laplacian(det_elev)|
    det_elev_f = cleaned["det_elev"]
    det_elev_sm = ndi.gaussian_filter(_fill_nearest(det_elev_f), 1.0, mode="nearest")
    det_lap_abs = np.abs(ndi.laplace(det_elev_sm))
    topo_extra = _pct(det_lap_abs, fp)

    mag_ridge = family_ridge(["pct_tmi_hg", "pct_tc", "pct_tmi_vg"]) if False else _pct(_high_pass((raw_pcts["tmi_hg"] + raw_pcts["tc"] + np.abs(raw_pcts["tmi_vg"])) / 3.0, fp), fp)
    # Actually raw_pcts already percentiled; but we want mean of percentiles then high-pass percentile
    # Let's do exact: mean of three raw percentile fields
    mag_field = (raw_pcts["tmi_hg"] + raw_pcts["tc"] + np.abs(raw_pcts["tmi_vg"]).astype(np.float32)) / 3.0
    mag_ridge_pct = _pct(_high_pass(mag_field, fp), fp)

    grav_field = (raw_pcts["iso_grav_anom_slope"] + np.abs(raw_pcts["iso_grav_anom_vg"]) + np.abs(raw_pcts["iso_grav_anom_hg"])) / 3.0
    grav_ridge_pct = _pct(_high_pass(grav_field, fp), fp)

    topo_field = raw_pcts["det_elev_slope"]  # single band for topo per prior
    # add laplacian contribution as in denovo topo: we already have topo_extra
    topo_comb = (topo_field + topo_extra) / 2.0
    topo_ridge_pct = _pct(_high_pass(topo_comb, fp), fp)

    # Conductivity-depth residual proxy (cheap): B17 residual within B15 deciles (10 bins)
    cond = cleaned["cond_surf"]
    depth = cleaned["depth_to_base_surf"]
    cond_f = _fill_nearest(cond)
    depth_f = _fill_nearest(depth)
    # Use raw percentile for binning (footprint only)
    depth_pct_for_bin = _pct(depth_f, fp)
    cond_pct_for_resid = _pct(cond_f, fp)
    n_bins = 10
    bins = np.minimum((depth_pct_for_bin * n_bins).astype(np.int64), n_bins - 1)
    # per-bin median of cond_pct
    bin_medians = []
    for b in range(n_bins):
        m = fp & (bins == b)
        bin_medians.append(float(np.median(cond_pct_for_resid[m])) if m.any() else 0.5)
    centres = (np.arange(n_bins, dtype=np.float64) + 0.5) / n_bins
    cond_median_of_depth = np.interp(depth_pct_for_bin[fp], centres, np.asarray(bin_medians, dtype=np.float64))
    resid = np.zeros(fp.shape, dtype=np.float32)
    if fp.any():
        resid[fp] = (cond_pct_for_resid[fp] - cond_median_of_depth).astype(np.float32)
        # fill NaN outside
        resid = np.where(fp, resid, 0.0).astype(np.float32)
        resid_filled = _fill_nearest(resid.astype(np.float64))
        cond_depth_resid_pct = _pct(resid_filled, fp)
    else:
        cond_depth_resid_pct = np.zeros(fp.shape, dtype=np.float32)
    audit["cond_resid_bin_medians"] = [round(float(x), 6) for x in bin_medians]

    # Depth gradient and grav gradient percentiles
    depth_grad = np.hypot(*np.gradient(ndi.gaussian_filter(_fill_nearest(depth_f), 2.0, mode="nearest")))
    depth_grad_pct = _pct(depth_grad, fp)
    grav_f = _fill_nearest(cleaned["iso_grav_anom"])
    grav_grad = np.hypot(*np.gradient(ndi.gaussian_filter(grav_f, 2.0, mode="nearest")))
    grav_grad_pct = _pct(grav_grad, fp)

    # Assemble 32 columns in FEATURE_NAMES order
    feat_map = {
        "pct_mag_anom": raw_pcts["mag_anom"],
        "pct_rtp": raw_pcts["rtp"],
        "pct_tmi_hg": raw_pcts["tmi_hg"],
        "pct_geod_2ndinv": raw_pcts["geod_2ndinv"],
        "pct_iso_grav_anom_slope": raw_pcts["iso_grav_anom_slope"],
        "pct_tc": raw_pcts["tc"],
        "pct_geod_shearrate": raw_pcts["geod_shearrate"],
        "pct_geod_dilaterate": raw_pcts["geod_dilaterate"],
        "pct_tmi_vg": raw_pcts["tmi_vg"],
        "pct_deq_n100a15": raw_pcts["deq_n100a15"],
        "pct_iso_grav_anom_vg": raw_pcts["iso_grav_anom_vg"],
        "pct_det_elev": raw_pcts["det_elev"],
        "pct_iso_grav_anom": raw_pcts["iso_grav_anom"],
        "pct_tmi": raw_pcts["tmi"],
        "pct_depth_to_base_surf": raw_pcts["depth_to_base_surf"],
        "pct_ieq_n100a15": raw_pcts["ieq_n100a15"],
        "pct_cond_surf": raw_pcts["cond_surf"],
        "pct_iso_grav_anom_hg": raw_pcts["iso_grav_anom_hg"],
        "pct_det_elev_slope": raw_pcts["det_elev_slope"],
        "seis_prox_pct": seis_prox,
        "seis_intensity_smooth_pct": seis_smooth_pct,
        "strain_shear_ratio_pct": shear_ratio_pct,
        "strain_dil_share_pct": dil_share_pct,
        "tc_grad_pct": tc_grad_pct,
        "tc_lap_abs_pct": tc_lap_pct,
        "mag_ridge_hp_pct": mag_ridge_pct,
        "grav_ridge_hp_pct": grav_ridge_pct,
        "topo_ridge_hp_pct": topo_ridge_pct,
        "strain_mag_pct2": strain_mag_pct2,
        "cond_depth_resid_proxy_pct": cond_depth_resid_pct,
        "depth_grad_pct": depth_grad_pct,
        "iso_grav_grad_pct": grav_grad_pct,
    }

    # Verify all names present
    missing = [n for n in FEATURE_NAMES if n not in feat_map]
    if missing:
        raise RuntimeError(f"feature map missing: {missing}")

    # Stack
    cols = [feat_map[n][fp].astype(np.float32) for n in FEATURE_NAMES]
    X = np.column_stack(cols).astype(np.float32)
    assert X.shape == (n_fp, len(FEATURE_NAMES)), f"{X.shape} vs {(n_fp, len(FEATURE_NAMES))}"
    assert np.isfinite(X).all(), "non-finite in feature matrix"

    audit["feature_names"] = list(FEATURE_NAMES)
    audit["n_features"] = len(FEATURE_NAMES)
    return X, list(FEATURE_NAMES), audit
