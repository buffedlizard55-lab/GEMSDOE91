"""MTD91 — magnetic texture destruction / coherence-length lane.

LANE (single method; preregistered before holdout numbers):

  A concealed Basin-and-Range damage zone shortens the *horizontal magnetic
  fabric* even when no single ridge/scarp exists. We measure that with:

    1. Structure-tensor isotropy of RTP (band 2) and |TMI-VG| (band 9):
         J = G_σ[∇f ⊗ ∇f], σ = 5 px (500 m)
         anisotropy A = (λ1−λ2)/(λ1+λ2+ε)
         isotropy I = 1 − A   (high where fabric is destroyed)
    2. Coherence-length proxy = high-frequency energy fraction:
         HF = |f − G_{σ=3}(f)|
         LF = |G_{σ=8}(f) − G_{σ=16}(f)|
         dest = HF / (HF + LF + ε)   (short autocorrelation → high dest)

  Surfaces (three budgeted experiments):
    E1: percentile(dest_RTP)
    E2: (pct dest_RTP * pct dest_VG)^(1/2)
    E3: E2 * (0.55 + 0.45 * mean(pct I_RTP, pct I_VG))

  Catalogue is used ONLY as a >3 px exclusion collar (visible faults only
  on holdout). Emission: greedy spaced unit dots, n=37654, spacing 2.8 px.

NON-FAULT MIMIC: young volcanic flows and survey flight-line levelling
residuals also destroy magnetic coherence.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .denovo import greedy_spaced, pct32
from .dd_vtc_pu import _clean_band_edt

BAND_RTP = 2
BAND_TMI_VG = 9
ST_SIGMA = 5.0
HF_SIGMA = 3.0
LF_LO = 8.0
LF_HI = 16.0
N_DOTS = 37654
SPACING = 2.8
COLLAR_PX = 3.0


def _structure_tensor(field: np.ndarray, sigma: float = ST_SIGMA):
    f = field.astype(np.float64)
    med = np.nanmedian(f)
    mad = np.nanmedian(np.abs(f - med)) + 1e-6
    f = np.clip((f - med) / (1.4826 * mad), -20.0, 20.0)
    gy, gx = np.gradient(f)
    j11 = ndi.gaussian_filter(gx * gx, sigma, mode="nearest")
    j12 = ndi.gaussian_filter(gx * gy, sigma, mode="nearest")
    j22 = ndi.gaussian_filter(gy * gy, sigma, mode="nearest")
    tr = j11 + j22
    det = j11 * j22 - j12 * j12
    disc = np.clip(tr * tr - 4.0 * det, 0.0, None)
    root = np.sqrt(disc)
    lam1 = 0.5 * (tr + root)
    lam2 = 0.5 * (tr - root)
    aniso = (lam1 - lam2) / (lam1 + lam2 + 1e-12)
    energy = tr
    return aniso.astype(np.float32), energy.astype(np.float32)


def _destruction(field: np.ndarray) -> np.ndarray:
    f = field.astype(np.float64)
    med = np.nanmedian(f)
    mad = np.nanmedian(np.abs(f - med)) + 1e-6
    f = np.clip((f - med) / (1.4826 * mad), -20.0, 20.0).astype(np.float32)
    hf = np.abs(f - ndi.gaussian_filter(f, HF_SIGMA, mode="nearest"))
    lf = np.abs(
        ndi.gaussian_filter(f, LF_LO, mode="nearest")
        - ndi.gaussian_filter(f, LF_HI, mode="nearest")
    )
    return (hf / (hf + lf + 1e-12)).astype(np.float32)


def features_from_bands(rtp: np.ndarray, tmi_vg: np.ndarray, footprint: np.ndarray) -> dict[str, np.ndarray]:
    rtp_c = _clean_band_edt(rtp.astype(np.float32), footprint)
    vg_c = _clean_band_edt(np.abs(tmi_vg).astype(np.float32), footprint)
    dest_rtp = _destruction(rtp_c)
    dest_vg = _destruction(vg_c)
    aniso_rtp, _ = _structure_tensor(rtp_c)
    aniso_vg, _ = _structure_tensor(vg_c)
    iso_rtp = (1.0 - np.clip(aniso_rtp, 0.0, 1.0)).astype(np.float32)
    iso_vg = (1.0 - np.clip(aniso_vg, 0.0, 1.0)).astype(np.float32)
    names = {
        "dest_rtp": pct32(dest_rtp, footprint),
        "dest_vg": pct32(dest_vg, footprint),
        "iso_rtp": pct32(iso_rtp, footprint),
        "iso_vg": pct32(iso_vg, footprint),
    }
    return names


def surface_e1(feats: dict[str, np.ndarray], footprint: np.ndarray) -> np.ndarray:
    return np.where(footprint, feats["dest_rtp"], 0.0).astype(np.float32)


def surface_e2(feats: dict[str, np.ndarray], footprint: np.ndarray) -> np.ndarray:
    g = np.sqrt(np.clip(feats["dest_rtp"] * feats["dest_vg"], 0.0, None))
    return np.where(footprint, g, 0.0).astype(np.float32)


def surface_e3(feats: dict[str, np.ndarray], footprint: np.ndarray) -> np.ndarray:
    g = np.sqrt(np.clip(feats["dest_rtp"] * feats["dest_vg"], 0.0, None))
    iso = 0.5 * (feats["iso_rtp"] + feats["iso_vg"])
    s = g * (0.55 + 0.45 * iso)
    return np.where(footprint, s, 0.0).astype(np.float32)


def emit_dots(surface: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray,
              n_dots: int = N_DOTS, spacing: float = SPACING, collar: float = COLLAR_PX) -> np.ndarray:
    dist = ndi.distance_transform_edt(~catalogue)
    eligible = footprint & (dist > collar) & (~catalogue)
    dots = greedy_spaced(surface, eligible, n_dots, spacing_px=spacing)
    return dots
