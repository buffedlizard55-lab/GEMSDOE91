"""S28-VSD lane features (session 2026-10-31, assigned by the session prompt's
PARALLEL-RUN PROTOCOL method paragraph).

Three NEW catalogue-independent feature families (nothing here reads any fault
coordinate; the lane's "catalogue-based features only from visible faults" rule
is satisfied in its strongest form — zero catalogue dependence):

VSD-A  CDEC  Cross-Domain Edge Concordance.
    Fault zones that juxtapose bodies produce edges in BOTH the density field
    (isostatic gravity, B13/B18) and the susceptibility field (RTP magnetics,
    B02) that are co-located and co-oriented across scales.  Intrusions and
    dikes contrast magnetically but weakly in gravity at long wavelength;
    sedimentary basins contrast in gravity but smoothly in magnetics; so the
    geometric-mean × orientation-agreement statistic suppresses both mimics.
    This integrated-aerogeophysical interpretation logic follows standard
    hard-rock structure mapping practice (USGS GeoDAWN release separates
    "magnetic measurements relevant to subsurface structure/geology" from
    "radiometric measurements relevant to surface geology"; here we use only
    the potential-field bands B02/B13, no radiometrics).

VSD-B  TSR  Termination/Stepover Relay gaps.
    Coulomb-style stress transfer concentrates dilation at fault tips,
    bends, stepovers and relay ramps (USGS SIR 2026-5073 motivation; USGS
    Great Basin structural-discontinuity study).  Unmapped young faults
    therefore tend to BRIDGE gaps between nearby geophysical lineaments.
    Morphological closing of the concordant-edge support detects exactly
    those bridging gaps ("closing hits the gaps, not the lines").

VSD-C  STA  Seismo-Tectonic Alignment.
    The supplied earthquake-density band (B16 ieq_n100a15) and
    distance-to-earthquake band (B10 deq_n100a15) mark active deformation.
    Geothermal-permissive structures are where the seismicity field is
    both strong AND elongated along the same azimuth as the local
    geophysical edge.  Alignment (not raw density) is the feature, so
    diffuse swarm/magmatism seismicity — the named non-fault mimic —
    scores low unless it co-orients with a concordant edge.

All outputs are float32 ranks/normalized values in [0, 1] over footprint
cells, computed with the masked normalised convolution helpers from
gems91.cckm24 (Declared-NoData sentinels excluded, exactly like the
template's cached stack).  Zero dependence on B12/B19 (detrended elevation)
and on B06 (radiometrics) keeps the families subsurface-first.

Named non-fault mimics per family (recorded in the run card):
  CDEC: lithologic/plutonic rock-unit contacts concordant in both fields;
        GeoDAWN survey seam/gridding artifacts.
  TSR : volcanic dike step-overs and ash-flow tuff contact bridges;
        braided-drainage or shoreline lineaments that nearly touch.
  STA : magmatic/geothermal-field microseismic swarms not on faults;
        uniform seismicity clouds with no azimuthal structure.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
from scipy import ndimage as ndi

from gems91.cckm24 import EXTREME_CUTOFF, _rank01, valid_mask

VSD_NAMES: tuple[str, ...] = (
    # --- VSD-A CDEC (6) ---
    "cdec_concord_s1_300m",
    "cdec_concord_s2_600m",
    "cdec_concord_s3_1200m",
    "cdec_min_persist3",
    "cdec_mean_persist3",
    "cdec_local_ring_contrast",
    # --- VSD-B TSR (5) ---
    "tsr_gap3_ranks",
    "tsr_gap6_ranks",
    "tsr_gap10_ranks",
    "tsr_gap6_strength",
    "tsr_tip_proximity",
    # --- VSD-C STA (4) ---
    "sta_seismic_proximity",
    "sta_seismic_density",
    "sta_align_edge_vs_seismic",
    "sta_coupling_align_x_prox",
)

B02_RTP = 1   # 0-based index of band 02 'rtp'
B13_GRAV = 12  # 0-based index of band 13 'iso_grav_anom'


def _masked(band: np.ndarray, valid: np.ndarray) -> np.ndarray:
    v = np.asarray(band, dtype=np.float32)
    v = np.where(valid & (np.isfinite(v)) & (np.abs(v) < EXTREME_CUTOFF), v, 0.0)
    return v


def _masked_gauss(band: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Masked normalised Gaussian smoothing (sentinels excluded from the filter)."""
    v = _masked(band, valid)
    num = ndi.gaussian_filter(v, sigma=sigma, mode="constant")
    den = ndi.gaussian_filter(valid.astype(np.float32), sigma=sigma, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(den > 1e-6, num / np.maximum(den, 1e-6), 0.0).astype(np.float32)
    return out


def _grad_mag_theta(field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gy = ndi.sobel(field, axis=0, mode="constant")
    gx = ndi.sobel(field, axis=1, mode="constant")
    mag = np.hypot(gy, gx).astype(np.float32)
    theta = np.arctan2(gy, gx).astype(np.float32)  # gradient azimuth, radians
    return mag, theta


def _disk(radius: int) -> np.ndarray:
    y, x = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (y * y + x * x) <= radius * radius


def compute_vsd28_features(
    bands_19: np.ndarray,
    footprint: np.ndarray,
    *,
    out_fp_matrix: np.ndarray | None = None,
) -> tuple[np.ndarray | None, dict[str, np.ndarray], dict]:
    """Compute the 15 VSD features over footprint cells.

    Returns ``(X_fp_or_None, surfaces, receipt)`` where ``X_fp`` has shape
    (N_fp, 15) float32 when ``out_fp_matrix`` is None, otherwise the caller's
    memmap is filled and None returned.  ``surfaces`` carries 2-D diagnostic
    control surfaces (full-grid) for the run card and controls.
    """
    fp = np.asarray(footprint, dtype=bool)
    h, w = fp.shape
    n_fp = int(fp.sum())

    rtp = bands_19[B02_RTP]
    grav = bands_19[B13_GRAV]
    eqd = bands_19[9]    # B10 deq_n100a15 (distance to earthquake)
    eqi = bands_19[15]   # B16 ieq_n100a15 (earthquake intensity/density)

    valid = fp.copy()
    for band in (rtp, grav, eqd, eqi):
        valid &= valid_mask(band, fp)


    # ---------------- VSD-A: CDEC cross-domain edge concordance --------------
    sigmas = (1.5, 3.0, 6.0)  # ~300 m, 600 m, 1200 m smoothing scales
    concords = []
    for s in sigmas:
        rm = _masked_gauss(rtp, valid, s)
        rg = _masked_gauss(grav, valid, s)
        mm, tm = _grad_mag_theta(rm)
        mg, tg = _grad_mag_theta(rg)
        # amplitude concordance in rank space (robust to unit/scale mismatch)
        cos2 = np.cos(tm - tg) ** 2
        c = np.sqrt(_rank01(np.where(valid, mm, 0.0), valid) * _rank01(np.where(valid, mg, 0.0), valid)) * cos2
        c = np.where(valid, c, 0.0).astype(np.float32)
        concords.append(c)
    c1, c2, c3 = concords
    cmin = np.minimum(np.minimum(c1, c2), c3).astype(np.float32)
    cmean = ((c1 + c2 + c3) / 3.0).astype(np.float32)
    # ring contrast at 600 m: center minus 17-px annulus mean (edge locality)
    ring_mean = ndi.uniform_filter(c2 * valid, size=17) / np.maximum(
        ndi.uniform_filter(valid.astype(np.float32), size=17), 1e-6
    )
    ring_contrast = np.where(valid, c2 - ring_mean, 0.0).astype(np.float32)
    # keep only ring support where the annulus actually overlaps footprint
    yy, xx = np.ogrid[-8:9, -8:9]
    rr = yy * yy + xx * xx
    ring = ((rr <= 64) & (rr > 16)).astype(np.float32)  # 17x17 annulus, r in (4, 8]
    ring_contrast = np.where(
        ndi.convolve(valid.astype(np.float32), ring, mode="constant") > 8.0,
        ring_contrast, 0.0,
    ).astype(np.float32)
    del ring_mean

    # orientation-shuffled negative control (flip one azimuth field by +pi/2):
    # destroys physical concordance while preserving marginal distributions.
    rm5 = _masked_gauss(rtp, valid, 3.0)
    rg5 = _masked_gauss(grav, valid, 3.0)
    mm5, tm5 = _grad_mag_theta(rm5)
    mg5, tg5 = _grad_mag_theta(rg5)
    c_shuf = np.sqrt(_rank01(np.where(valid, mm5, 0.0), valid) * _rank01(np.where(valid, mg5, 0.0), valid)) * np.cos(
        (tm5 + np.pi / 2.0) - tg5
    ) ** 2
    control_cdec_shuffled = np.where(valid, c_shuf, 0.0).astype(np.float32)
    del rm5, rg5, mm5, mg5, tm5, tg5, c_shuf
    control_cdec_surface = c2  # 600 m concordance as the standalone control surface

    # ---------------- VSD-B: TSR relay/stepover gap morphology ---------------
    support = (c2 > np.quantile(c2[valid], 0.98)) & valid
    gaps = {}
    for r in (3, 6, 10):
        closed = ndi.binary_closing(support, structure=_disk(r), border_value=0)
        gaps[r] = (closed & ~support & valid)
    gap3_r = np.where(valid, _rank01(ndi.distance_transform_edt(~gaps[3]), valid), 0.0).astype(np.float32)
    gap6_r = np.where(valid, _rank01(ndi.distance_transform_edt(~gaps[6]), valid), 0.0).astype(np.float32)
    gap10_r = np.where(valid, _rank01(ndi.distance_transform_edt(~gaps[10]), valid), 0.0).astype(np.float32)
    # strength: gap pixels inherit mean concordance of flanking lineaments
    supp_dil = ndi.binary_dilation(support, structure=_disk(6))
    flank_mean = np.where(supp_dil, c2, 0.0)
    flank_n = ndi.uniform_filter((supp_dil & valid).astype(np.float32), size=13) + 1e-6
    flank_val = ndi.uniform_filter(flank_mean, size=13) / np.maximum(
        ndi.uniform_filter((supp_dil & valid).astype(np.float32), size=13), 1e-6
    )
    gap6_strength = np.where(gaps[6], flank_val, 0.0).astype(np.float32)
    gap6_strength = np.where(valid, gap6_strength, 0.0).astype(np.float32)
    # tip proximity: endpoints of the thinned support approximated by
    # support pixels whose 3x3 neighbourhood has <= 2 support neighbours
    neigh = ndi.convolve(support.astype(np.float32), np.ones((3, 3), np.float32), mode="constant")
    tips = support & (neigh <= 3.0)
    tip_r = np.where(valid, _rank01(ndi.distance_transform_edt(~tips), valid), 0.0).astype(np.float32)

    # ---------------- VSD-C: STA seismo-tectonic alignment -------------------
    eqd_rank = np.where(valid, 1.0 - _rank01(_masked(eqd, valid), valid), 0.0).astype(np.float32)  # closer => higher
    eqi_sm = _masked_gauss(eqi, valid, 6.0)
    eqi_rank = np.where(valid, _rank01(eqi_sm, valid), 0.0).astype(np.float32)
    # orientation of the smoothed seismicity field's gradient
    _, ts = _grad_mag_theta(_masked_gauss(eqi, valid, 9.0))
    # dominant geophysical edge orientation from the 600 m concordance field
    _, te = _grad_mag_theta(_masked_gauss(c2, valid, 4.0))
    align = (np.cos(ts - te) ** 2).astype(np.float32)
    align = np.where(valid, align, 0.0).astype(np.float32)
    coupling = (align * eqi_rank * eqd_rank).astype(np.float32)

    feats = {
        "cdec_concord_s1_300m": c1,
        "cdec_concord_s2_600m": c2,
        "cdec_concord_s3_1200m": c3,
        "cdec_min_persist3": cmin,
        "cdec_mean_persist3": cmean,
        "cdec_local_ring_contrast": ring_contrast,
        "tsr_gap3_ranks": gap3_r,
        "tsr_gap6_ranks": gap6_r,
        "tsr_gap10_ranks": gap10_r,
        "tsr_gap6_strength": gap6_strength,
        "tsr_tip_proximity": tip_r,
        "sta_seismic_proximity": eqd_rank,
        "sta_seismic_density": eqi_rank,
        "sta_align_edge_vs_seismic": align,
        "sta_coupling_align_x_prox": coupling,
    }
    assert tuple(feats.keys()) == VSD_NAMES, "feature registry drift"

    X = None
    if out_fp_matrix is None:
        X = np.empty((n_fp, len(VSD_NAMES)), dtype=np.float32)
        for j, name in enumerate(VSD_NAMES):
            X[:, j] = feats[name][fp]
    else:
        assert out_fp_matrix.shape == (n_fp, len(VSD_NAMES))
        for j, name in enumerate(VSD_NAMES):
            out_fp_matrix[:, j] = feats[name][fp]

    surfaces = {
        "control_cdec_surface": control_cdec_surface,
        "control_cdec_orient_shuffled": control_cdec_shuffled,
        "control_tsr_gap6_strength": gap6_strength,
        "control_sta_coupling": coupling,
    }
    receipt = {
        "module": "gems91.vsd28",
        "n_features": len(VSD_NAMES),
        "feature_names": list(VSD_NAMES),
        "bands_used_1based": [2, 13, 10, 16],
        "catalogue_dependent": False,
        "detrended_elevation_dependent": False,
        "radiometric_dependent": False,
        "scales_px": {"cdec": [1.5, 3.0, 6.0], "tsr_gap_radii": [3, 6, 10], "sta_smooth": [6.0, 9.0]},
        "negative_controls": {
            "cdec_orientation_shuffled": "magnetic gradient azimuth rotated +90 deg; concordance signal must drop",
        },
    }
    return X, surfaces, receipt
