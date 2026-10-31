"""VCSE-30 — Vent-Concordance Strand Emission (lane module).

Single method paragraph (lane assignment source: the standing brief's explicit
instruction to pursue "the scientific discovery of geothermal vents" with
"sources of data that others are overlooking"; no other lane paragraph was
supplied — recorded as IR-S30-01):

    Predict unmapped ("new") fault strands where geothermal-vent evidence
    concurs: hydrothermal-alteration radiometric anomalies (GeoDAWN K/Th/U/TC),
    conductive clay-cap highs (cond_surf), warm-spring/well proximity (GDR),
    seismicity proximity/intensity (deq/ieq), and strain-rate intensity
    (geodetic 2nd invariant / shear / dilatation), corroborated structurally by
    magnetic/gravity edge persistence, cover-thickness steps and lidar-scarp
    persistence.  The named non-fault mimic is playa/lake-bottom conductivity
    (saline basin floors are conductive, K-poor and flat), gated out by
    requiring structural concurrence and by a basin-floor veto.  Emission is
    300 m-kernel CELF binary dots (budget 37,654; 3.05 px spacing; >3.05 px
    collar off the visible catalogue).

Every channel is computed from pinned competition/external rasters only and is
catalogue-independent except the emission collar gate (which uses the *visible*
catalogue per fold).  Sentinel handling and average-tie percentile ranks follow
`src/gems91/strain.py` exactly.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .prior import SIGMA_PX, array_digest, distance_prior, keep_remote, read_features
from .strain import band_prior, fill_sentinel, percentile_rank

VENT_CHANNELS = (
    "vent_rad_K_anom",
    "vent_rad_ThU_anom",
    "vent_rad_TC",
    "vent_cond_cap",
    "vent_gdr_thermal",
)
STRUCT_CHANNELS = (
    "struct_seismicity",
    "struct_strain",
    "struct_dilatation",
    "struct_mag_edge",
    "struct_grav_edge",
    "struct_cover_edge",
    "struct_lidar_scarp",
    "struct_relief_scarp",
)
ALL_CHANNELS = VENT_CHANNELS + STRUCT_CHANNELS

VOTE_T = 0.85          # a channel votes when its rank is in the top 15%
BANDS = {
    "tmi_hg": 3, "geod_2ndinv": 4, "iso_grav_anom_slope": 5, "tc_mag": 6,
    "geod_shearrate": 7, "geod_dilaterate": 8, "tmi_vg": 9,
    "deq_n100a15": 10, "iso_grav_anom_vg": 11, "det_elev": 12,
    "depth_to_base_surf": 15, "ieq_n100a15": 16, "cond_surf": 17,
    "iso_grav_anom_hg": 18, "det_elev_slope": 19,
}


def _load_raw(path):
    import rasterio
    with rasterio.open(path) as ds:
        arr = ds.read()
    return arr  # (19, H, W) float32


def _rank(field: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Average-tie percentile rank in [0,1]; 0 outside footprint."""
    pct = percentile_rank(field, footprint)
    return np.where(footprint, pct, 0.0).astype(np.float32)


def _local_anomaly(band: np.ndarray, footprint: np.ndarray, radius: int = 15) -> np.ndarray:
    """|x - grey opening(x, radius)| local positive anomaly, rank-normalized."""
    filled, _ = fill_sentinel(band, footprint)
    size = 2 * radius + 1
    opened = ndi.grey_opening(filled, size=(size, size))
    anom = np.abs(filled - opened)
    return _rank(anom, footprint)


def build_channels(raw19: np.ndarray, rad_u8: np.ndarray, lidar_u8: np.ndarray,
                   gdr_csv: str, footprint: np.ndarray) -> dict:
    """Compute the 13 catalogue-independent VCSE channels (float32 rank fields)."""
    fp = np.asarray(footprint, bool)
    ch: dict[str, np.ndarray] = {}

    # --- vent group -------------------------------------------------------
    k = rad_u8[0].astype(np.float64)
    th = rad_u8[1].astype(np.float64)
    u = rad_u8[2].astype(np.float64)
    tc_rad = rad_u8[3].astype(np.float64)
    ch["vent_rad_K_anom"] = _local_anomaly(k, fp)
    ratio = np.divide(th, np.maximum(u, 1.0))
    ch["vent_rad_ThU_anom"] = _local_anomaly(ratio, fp)
    ch["vent_rad_TC"] = _rank(tc_rad, fp)

    cond, _ = band_prior(raw19[BANDS["cond_surf"] - 1], fp)
    ch["vent_cond_cap"] = np.where(fp, cond, 0.0).astype(np.float32)

    feats = read_features(gdr_csv)
    prior = distance_prior(fp.shape, feats["cells"], fp, sigma_px=SIGMA_PX)
    ch["vent_gdr_thermal"] = np.where(fp, np.nan_to_num(prior, nan=0.0), 0.0).astype(np.float32)
    gdr_digest = array_digest(prior)

    # --- structural group -------------------------------------------------
    deq, _ = band_prior(raw19[BANDS["deq_n100a15"] - 1], fp)
    ieq, _ = band_prior(raw19[BANDS["ieq_n100a15"] - 1], fp)
    inv_deq = 1.0 - np.where(fp, deq, 0.0)          # closer to earthquakes = higher
    ch["struct_seismicity"] = ((np.where(fp, ieq, 0.0) + inv_deq) / 2.0).astype(np.float32)

    b4, _ = band_prior(raw19[BANDS["geod_2ndinv"] - 1], fp)
    b7, _ = band_prior(raw19[BANDS["geod_shearrate"] - 1], fp)
    b8, _ = band_prior(raw19[BANDS["geod_dilaterate"] - 1], fp)
    ch["struct_strain"] = ((np.where(fp, b4, 0.0) + np.where(fp, b7, 0.0)) / 2.0).astype(np.float32)
    ch["struct_dilatation"] = np.where(fp, b8, 0.0).astype(np.float32)

    b3, _ = band_prior(raw19[BANDS["tmi_hg"] - 1], fp)
    b6, _ = band_prior(raw19[BANDS["tc_mag"] - 1], fp)
    ch["struct_mag_edge"] = np.maximum(np.where(fp, b3, 0.0), np.where(fp, b6, 0.0)).astype(np.float32)

    b18, _ = band_prior(raw19[BANDS["iso_grav_anom_hg"] - 1], fp)
    ch["struct_grav_edge"] = np.where(fp, b18, 0.0).astype(np.float32)

    b15, _ = band_prior(raw19[BANDS["depth_to_base_surf"] - 1], fp)
    grad = np.hypot(*np.gradient(np.where(fp, b15, 0.0)))
    ch["struct_cover_edge"] = _rank(grad, fp)

    ex = lidar_u8[0].astype(np.float64)
    step = lidar_u8[2].astype(np.float64)
    down = lidar_u8[5].astype(np.float64)
    scarp = np.maximum(np.maximum(ex, step), down)
    ch["struct_lidar_scarp"] = _rank(scarp, fp)

    b19, _ = band_prior(raw19[BANDS["det_elev_slope"] - 1], fp)
    ch["struct_relief_scarp"] = np.where(fp, b19, 0.0).astype(np.float32)

    return {"channels": ch, "gdr_prior_digest": gdr_digest,
            "gdr_features": {"rows": feats["n_rows"], "cells": feats["n_cells"],
                             "thermal_rows": feats["n_thermal_rows"]}}


def vote_surface(ch: dict[str, np.ndarray], footprint: np.ndarray,
                 raw19: np.ndarray, lidar_u8: np.ndarray) -> dict:
    """Concordance vote surface with the playa/lake mimic veto.

    vent_frac   = mean of top-15% votes across the VENT group
    struct_frac = mean of top-15% votes across the STRUCT group
    base        = vent_frac * (0.45 + 0.55 * struct_frac)   (vent evidence must
                  be corroborated structurally; a lone radiometric anomaly —
                  e.g. an alluvial fan — cannot emit)
    mimic veto  = conductive + flat + lidar-incoherent + no edge/strain
                  (playa/lake-bottom conductivity signature) -> 0
    """
    fp = np.asarray(footprint, bool)
    votes_v = np.zeros(fp.shape, np.float32)
    for n in VENT_CHANNELS:
        votes_v += (ch[n] >= VOTE_T).astype(np.float32)
    votes_s = np.zeros(fp.shape, np.float32)
    for n in STRUCT_CHANNELS:
        votes_s += (ch[n] >= VOTE_T).astype(np.float32)
    vent_frac = votes_v / len(VENT_CHANNELS)
    struct_frac = votes_s / len(STRUCT_CHANNELS)
    base = vent_frac * (0.45 + 0.55 * struct_frac)

    rel_rank = ch["struct_relief_scarp"]
    ex_rank = _rank(lidar_u8[0].astype(np.float64), fp)
    step_rank = _rank(lidar_u8[2].astype(np.float64), fp)
    # Named non-fault mimic: playa/lake-bottom conductivity.  Saline basin
    # floors are conductive (cond top 5%), flat (relief and lidar step/ex in
    # the bottom 10%) and structureless (no magnetic or gravity edge).  A real
    # vent-concordant strand always shows structural relief or edges, so those
    # cells are vetoed.  (Absolute elevation is not in the pinned stack, so the
    # basin-floor signature is expressed with relief/flatness, IR-S30-02.)
    playa = ((ch["vent_cond_cap"] >= 0.95) & (rel_rank <= 0.10) & (ex_rank <= 0.35)
             & (step_rank <= 0.35) & (ch["struct_mag_edge"] <= 0.50)
             & (ch["struct_grav_edge"] <= 0.50))
    surface = np.where(playa, 0.0, base).astype(np.float32)
    surface[~fp] = 0.0
    return {"surface_e1": surface, "vent_frac": vent_frac,
            "struct_frac": struct_frac, "playa_veto_px": int((playa & fp).sum())}


def consensus_surface(ref_dots: list[np.ndarray], footprint: np.ndarray) -> np.ndarray:
    """Family-consensus field: share of reference dot fields with support within
    3 px of each cell, normalized by its footprint 99th percentile."""
    fp = np.asarray(footprint, bool)
    y_g, x_g = np.ogrid[-3:4, -3:4]
    struct_3px = (y_g * y_g + x_g * x_g) <= 9
    votes = np.zeros(fp.shape, np.float32)
    for dots in ref_dots:
        halo = ndi.binary_dilation((dots > 0) & fp, structure=struct_3px)
        votes += halo.astype(np.float32)
    q99 = float(np.percentile(votes[fp], 99.0)) if fp.any() else 1.0
    q99 = max(q99, 1.0)
    out = np.clip(votes / q99, 0.0, 1.0).astype(np.float32)
    out[~fp] = 0.0
    return out
