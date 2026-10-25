"""CWP91: completeness-weighted PU transform.

Preregistration: ``docs/HYPOTHESES_CWP91.md`` (frozen before any CWP91 score).

Theory (Elkan & Noto 2008, spatially-varying label frequency)
-------------------------------------------------------------
Let ``s=1`` mean "in the USGS/INGENIOUS catalogue" and ``y=1`` mean "is a fault".
A PU classifier trained with catalogue pixels as positives estimates
``p_s(x) = P(s=1 | x)``.  Where mapping is locally complete, a high ``p_s`` is
most likely an *already-mapped* fault; where the catalogue is sparser than the
geology predicts, the same ``p_s`` is a discovery candidate.  With a spatially
varying label frequency ``c(x) = P(s=1 | y=1, x)``,

    P(y=1, s=0 | x)  ∝  p_y(x) * (1 - c(x)),

where ``p_y`` is the Elkan-calibrated fault posterior.  Up to the global
constant ``1 / c_bar`` this is ranking-equivalent to ``p_s * (1 - c(x))``,
which is the frozen CWP91 surface.

Frozen estimator (see preregistration §3 addendum)
--------------------------------------------------
* ``c_bar`` = mean of ``p_s`` over *visible* catalogue pixels in the calibration
  domain (Elkan-Noto estimate of the global label frequency).
* ``p_y = clip(p_s / c_bar, 0, 1)``.
* ``chat = clip( (G_sigma * cat_vis) / (G_sigma * p_y), 0, 1 )`` with
  ``sigma = 10 px`` (1 km), Gaussian ``truncate=3.0``, ``mode='constant'``;
  where the denominator is ~0, ``chat = 0`` (no expected faults, no suppression;
  the surface is ~0 there anyway).
* ``surface = clip(p_s, 0, 1) * (1 - chat)``, zero outside the footprint.

Every catalogue-derived quantity uses **visible faults only**.  Nothing here
reads any withheld/hidden truth, any other submission, or any external layer.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

SIGMA_PX = 10.0          # 1 km completeness scale (frozen, untuned)
TRUNCATE = 3.0           # Gaussian support = 30 px (frozen)
SHIFT_YX = (173, -211)   # hole-shuffled control offset (frozen)
_EPS = 1e-6


def elkan_c_bar(p_s: np.ndarray, visible_catalogue: np.ndarray,
                calibration_mask: np.ndarray) -> float:
    """Elkan-Noto global label-frequency estimate from visible faults only."""
    sel = visible_catalogue & calibration_mask
    n = int(sel.sum())
    if n == 0:
        raise ValueError("no visible catalogue pixels in the calibration domain")
    vals = np.asarray(p_s, dtype=np.float64)[sel]
    if not np.isfinite(vals).all():
        raise ValueError("non-finite posterior at visible catalogue pixels")
    c_bar = float(vals.mean())
    if not (0.0 < c_bar <= 1.0):
        raise ValueError(f"degenerate Elkan c_bar={c_bar}")
    return c_bar


def _smooth(field: np.ndarray, footprint: np.ndarray, sigma: float) -> np.ndarray:
    f = np.where(footprint, np.asarray(field, dtype=np.float32), 0.0).astype(np.float32)
    return ndi.gaussian_filter(f, sigma=sigma, mode="constant", cval=0.0,
                               truncate=TRUNCATE)


def completeness_field(visible_catalogue: np.ndarray, p_s: np.ndarray,
                       footprint: np.ndarray, *,
                       calibration_mask: np.ndarray,
                       sigma: float = SIGMA_PX) -> tuple[np.ndarray, dict]:
    """Return ``(chat, diagnostics)``; ``chat`` in [0, 1], 0 outside footprint.

    ``visible_catalogue`` must already exclude anything withheld.  ``p_s`` is
    the PU posterior (0 where not predicted).  ``calibration_mask`` selects the
    domain over which ``c_bar`` is estimated (visible faults only).
    """
    cat = np.asarray(visible_catalogue, bool) & footprint
    p = np.clip(np.nan_to_num(np.asarray(p_s, dtype=np.float32),
                              nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    c_bar = elkan_c_bar(p, cat, calibration_mask & footprint)
    p_y = np.clip(p / c_bar, 0.0, 1.0).astype(np.float32)

    num = _smooth(cat.astype(np.float32), footprint, sigma)
    den = _smooth(p_y, footprint, sigma)
    chat = np.where(den > _EPS, np.clip(num / np.maximum(den, _EPS), 0.0, 1.0), 0.0)
    chat = np.where(footprint, chat, 0.0).astype(np.float32)

    in_fp = chat[footprint]
    diag = dict(
        c_bar=round(c_bar, 6),
        sigma_px=float(sigma),
        chat_mean_in_fp=round(float(in_fp.mean()), 6),
        chat_median_in_fp=round(float(np.median(in_fp)), 6),
        chat_frac_eq_1_in_fp=round(float((in_fp >= 1.0).mean()), 6),
        chat_frac_eq_0_in_fp=round(float((in_fp <= 0.0).mean()), 6),
        n_visible_catalogue_px=int(cat.sum()),
    )
    return chat, diag


def shifted_catalogue(visible_catalogue: np.ndarray, footprint: np.ndarray,
                      shift_yx: tuple[int, int] = SHIFT_YX) -> np.ndarray:
    """Rigidly shifted catalogue for the hole-shuffled control (frozen offset).

    ``np.roll`` wraps at the grid edge; the result is re-masked to the
    footprint.  Density-field statistics are preserved; alignment between true
    completeness and true hole locations is destroyed.
    """
    cat = np.asarray(visible_catalogue, bool)
    rolled = np.roll(cat, shift=(int(shift_yx[0]), int(shift_yx[1])), axis=(0, 1))
    return rolled & footprint


def cwp_surface(p_s: np.ndarray, visible_catalogue: np.ndarray,
                footprint: np.ndarray, *, calibration_mask: np.ndarray,
                sigma: float = SIGMA_PX) -> tuple[np.ndarray, np.ndarray, dict]:
    """Frozen CWP91 surface ``p_s * (1 - chat)``. Returns (surface, chat, diag)."""
    chat, diag = completeness_field(visible_catalogue, p_s, footprint,
                                    calibration_mask=calibration_mask, sigma=sigma)
    p = np.clip(np.nan_to_num(np.asarray(p_s, dtype=np.float32),
                              nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    s = np.where(footprint, p * (1.0 - chat), 0.0).astype(np.float32)
    return s, chat, diag


def ctl_surface(p_s: np.ndarray, visible_catalogue: np.ndarray,
                footprint: np.ndarray, *, calibration_mask: np.ndarray,
                sigma: float = SIGMA_PX) -> tuple[np.ndarray, np.ndarray, dict]:
    """Hole-shuffled control surface: CWP with a shifted catalogue density.

    The Elkan ``c_bar`` scalar is kept from the *true* visible catalogue; only
    the spatial density field in the numerator is shifted.
    """
    shifted = shifted_catalogue(visible_catalogue, footprint)
    cat = np.asarray(visible_catalogue, bool) & footprint
    p = np.clip(np.nan_to_num(np.asarray(p_s, dtype=np.float32),
                              nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    c_bar = elkan_c_bar(p, cat, calibration_mask & footprint)
    p_y = np.clip(p / c_bar, 0.0, 1.0).astype(np.float32)
    num = _smooth(shifted.astype(np.float32), footprint, sigma)
    den = _smooth(p_y, footprint, sigma)
    chat = np.where(den > _EPS, np.clip(num / np.maximum(den, _EPS), 0.0, 1.0), 0.0)
    chat = np.where(footprint, chat, 0.0).astype(np.float32)
    s = np.where(footprint, p * (1.0 - chat), 0.0).astype(np.float32)
    diag = dict(c_bar=round(c_bar, 6), sigma_px=float(sigma),
                shift_yx=list(SHIFT_YX),
                n_shifted_catalogue_px=int(shifted.sum()),
                n_visible_catalogue_px=int(cat.sum()))
    return s, chat, diag
