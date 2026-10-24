"""ASC91 — antisymmetric cross-fault step matched filter (preregistered lane).

Frozen design: `docs/HYPOTHESES_ASC91.md` (2026-10-24, written before any
ASC91 holdout number was computed). A fault is a **step**: the level of a
physical field differs across the trace. Symmetric neighbourhood means and
ridge/crest filters cancel or ignore a pure step, so this module measures
the odd-symmetric quantity directly:

    S_F(theta) = strike_smooth[ (F(+2n)+F(+4n))/2 - (F(-2n)+F(-4n))/2 ]

for fields F in {det_elev (B12), iso_grav_anom (B13), rtp (B2),
depth_to_base_surf (B15), cond_surf (B17)} and 8 strike azimuths
theta in {0, 22.5, ..., 157.5} degrees. Sampling is bilinear
(`scipy.ndimage.shift`, order=1, mode="nearest"); the along-strike
smoothing averages offsets {-4,-2,0,+2,+4} px along strike, so only steps
that are coherent for ~900 m along strike score highly.

Azimuth convention: theta is strike measured clockwise from north.
In (row, col) grid coordinates (row increases southward):
    strike unit  s = (-cos(theta), sin(theta))
    across unit  n = (sin(theta),  cos(theta))     (s rotated 90 deg)
so theta=0 is a N-S line with n pointing east, and `S > 0` means the
field is higher on the +n (eastern) side. The sign convention is shared
by every field, which is what makes the cross-field signed-polarity
features in `scripts/build_asc91.py` meaningful.

No catalogue-derived quantity is used anywhere in this module.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

# (feature short name, 1-based band index in training_features).
# Band names verified from the file's own tags on 2026-10-24.
FIELDS = (
    ("det_elev", 12),
    ("iso_grav_anom", 13),
    ("rtp", 2),
    ("depth_to_base_surf", 15),
    ("cond_surf", 17),
)
FIELD_NAMES = tuple(name for name, _ in FIELDS)
AZIMUTHS_DEG = tuple(22.5 * i for i in range(8))
ACROSS_PX = (2.0, 4.0)
STRIKE_OFFSETS_PX = (-4.0, -2.0, 0.0, 2.0, 4.0)


def strike_across(azimuth_deg: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return (strike, across) unit vectors in (row, col) coordinates."""
    th = math.radians(float(azimuth_deg))
    s = (-math.cos(th), math.sin(th))
    n = (math.sin(th), math.cos(th))
    return s, n


def sample_at(field: np.ndarray, d_row: float, d_col: float,
              out: np.ndarray | None = None) -> np.ndarray:
    """Bilinear sample: result[p] = field[p + (d_row, d_col)]."""
    return ndi.shift(field, shift=(-float(d_row), -float(d_col)), order=1,
                     mode="nearest", output=out)


def strike_smooth(arr: np.ndarray, azimuth_deg: float) -> np.ndarray:
    """Mean of `arr` sampled at STRIKE_OFFSETS_PX along strike."""
    (sr, sc), _ = strike_across(azimuth_deg)
    acc = arr.astype(np.float32, copy=True)
    buf = np.empty_like(acc)
    for off in STRIKE_OFFSETS_PX:
        if off == 0.0:
            continue
        sample_at(arr, off * sr, off * sc, out=buf)
        acc += buf
    acc /= float(len(STRIKE_OFFSETS_PX))
    return acc


def step_response(field: np.ndarray, azimuth_deg: float) -> np.ndarray:
    """Odd-symmetric across-strike step of one field at one strike azimuth.

    Positive when the field is higher on the +n side of the candidate
    trace. A constant field and a symmetric ridge centred on the trace
    both give ~0; a level offset across the trace gives a large response.
    """
    f = np.asarray(field, dtype=np.float32)
    _, (nr, nc) = strike_across(azimuth_deg)
    acc = np.zeros(f.shape, dtype=np.float32)
    buf = np.empty_like(acc)
    for d in ACROSS_PX:
        sample_at(f, d * nr, d * nc, out=buf)
        acc += buf
        sample_at(f, -d * nr, -d * nc, out=buf)
        acc -= buf
    acc /= float(len(ACROSS_PX))
    return strike_smooth(acc, azimuth_deg)


def percentile_grid(values: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Exact footprint percentile rank in [0, 1], float32, 0 outside footprint."""
    vals = np.asarray(values, dtype=np.float32)
    fp = np.asarray(footprint, dtype=bool)
    out = np.zeros(fp.shape, dtype=np.float32)
    v = vals[fp].astype(np.float64)
    if v.size == 0:
        return out
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=np.float64)
    ranks[order] = np.arange(v.size, dtype=np.float64)
    # average ranks over exact ties (vectorised via unique boundaries)
    _, first, counts = np.unique(v[order], return_index=True, return_counts=True)
    if np.any(counts > 1):
        sorted_ranks = ranks[order]
        ends = first + counts
        csum = np.concatenate(([0.0], np.cumsum(sorted_ranks)))
        means = (csum[ends] - csum[first]) / counts
        sorted_ranks = np.repeat(means, counts)
        ranks[order] = sorted_ranks
    out[fp] = (ranks / max(1, v.size - 1)).astype(np.float32)
    return out


def axial_bin_distance(a: np.ndarray, b: np.ndarray, n_bins: int = 8) -> np.ndarray:
    """Circular distance between axial azimuth bins (bin width 180/n_bins)."""
    d = np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16)) % n_bins
    return np.minimum(d, n_bins - d)
