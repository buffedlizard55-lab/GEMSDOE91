"""DENOVO-TRI3 lane (GEMSDOE91, 2026-10-24) — a de novo fault surface.

LANE (the single method of this session; preregistered here before any holdout
number was computed):

    Surface = (R_mag * R_grav * R_topo) ** (1/3) * (0.6 + 0.4*P_step)
              * (0.85 + 0.15*P_strain)

    R_fam   = percentile rank, inside the footprint, of the 500 m high-pass
              (field - Gaussian(field, sigma=5 px)) of the family field.
    Family field = mean of per-band footprint percentiles:
        MAG   bands 3  tmi_hg, 6 tc, 9 |tmi_vg|
        GRAV  bands 5  |iso_grav_anom_slope|, 11 |iso_grav_anom_vg|,
              18 |iso_grav_anom_hg|
        TOPO  band 19 det_elev_slope and |Laplacian(band 12 det_elev)|
    P_step  = percentile of |grad(band 15 depth_to_base_surf)| (basement step)
    P_strain= percentile of band 4 geod_2ndinv (active strain-rate magnitude)

    Emission: greedy spaced dots (surface order, deterministic tie-break by
    flat index), min spacing `spacing_px` (default 2.8), candidates restricted
    to the footprint and > 3 px from the catalogue, unit mass {0, 1}.

WHY THIS SHOULD CATCH FAULTS MISSING FROM THE CATALOGUE (mechanism):
A concealed Basin-and-Range normal fault offsets magnetic basement, density
structure and (where young) topography at the *same* map location, while the
non-fault mimics of each single dataset (a lithologic magnetic contact, an
intrabasement density edge, a shoreline/terrace scarp) do not coincide across
all three independent physics. The geometric mean is a concordance AND-gate:
it is high only where magnetics, gravity and topography each carry a
lineament-scale (high-pass) anomaly. The basement-step term favours the
range-front/piedmont structural position and the strain term favours
presently-active structures, but neither can create a candidate alone
(multipliers are bounded in [0.6, 1.0] and [0.85, 1.0]).

WHAT IT IS NOT: no dot, mask, ranking or value is read from R0 or any ancestor
raster; the catalogue is used ONLY for the > 3 px exclusion (and, in the
holdout, the exclusion is derived from the *visible* catalogue only). No
external dataset is used (the unlicensed lidar layer is deliberately excluded;
see IR-91-39). Every input band comes from the pinned sponsor file
`training_features` (registry/data_manifest.json sha256 4371c82e...3bc5).

NON-FAULT MIMIC (named, per protocol): coincident lithologic contacts —
e.g. a buried volcanic/intrusive margin can produce a magnetic edge, a gravity
edge and a subdued topographic break at the same place without being a
Quaternary fault. Survey artefacts (GeoDAWN flight-line levelling residuals
at 400 m line spacing) can also align across the magnetic derivatives, though
not across gravity/topography.

This module builds the surface and the dot emission only. Scoring is
`scripts/dti.py` (official max-per-truth-pixel DTI); writing is
`gems91.io.write_float32`; gating is `scripts/validate_raster.py` +
`gems91.release_gates`.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .relief import fill_footprint_percentile

# 1-based band indices in training_features (names verified from file tags
# 2026-10-24; see scripts/build_denovo.py report).
BANDS = {
    "tmi_hg": 3,
    "geod_2ndinv": 4,
    "iso_grav_anom_slope": 5,
    "tc": 6,
    "tmi_vg": 9,
    "iso_grav_anom_vg": 11,
    "det_elev": 12,
    "depth_to_base_surf": 15,
    "iso_grav_anom_hg": 18,
    "det_elev_slope": 19,
}

FAMILIES = {
    "mag": ("tmi_hg", "tc", "tmi_vg"),
    "grav": ("iso_grav_anom_slope", "iso_grav_anom_vg", "iso_grav_anom_hg"),
    "topo": ("det_elev_slope",),  # + |Laplacian(det_elev)|, added in code
}

HIGH_PASS_SIGMA_PX = 5.0


def pct32(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Footprint percentile rank in [0, 1], float32, 0 outside the footprint."""
    pct, _ = fill_footprint_percentile(arr, footprint)
    out = np.where(footprint, pct, 0.0).astype(np.float32)
    return out


def _high_pass(field: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    f = field.astype(np.float32)
    smooth = ndi.gaussian_filter(f, HIGH_PASS_SIGMA_PX, mode="nearest")
    hp = np.where(footprint, f - smooth, 0.0).astype(np.float32)
    del f, smooth
    return hp


def family_field(band_arrays: dict[str, np.ndarray], footprint: np.ndarray,
                 names: tuple[str, ...], *, det_elev: np.ndarray | None = None) -> np.ndarray:
    """Mean of per-band footprint percentiles for one physics family."""
    acc = np.zeros(footprint.shape, dtype=np.float32)
    n = 0
    for name in names:
        a = band_arrays[name]
        if name in ("tmi_vg", "iso_grav_anom_slope", "iso_grav_anom_vg", "iso_grav_anom_hg"):
            a = np.abs(a)
        acc += pct32(a, footprint)
        n += 1
        del a
    if det_elev is not None:  # TOPO also carries the elevation step curvature
        filled = det_elev.astype(np.float32)
        bad = ~np.isfinite(filled) | (filled < -1e30)
        if bad.any():
            _, idx = ndi.distance_transform_edt(bad, return_indices=True)
            filled = filled[idx[0], idx[1]]
        lap = np.abs(ndi.laplace(ndi.gaussian_filter(filled, 1.0, mode="nearest")))
        acc += pct32(lap, footprint)
        n += 1
        del filled, lap
    return (acc / float(n)).astype(np.float32)


def build_surface(band_arrays: dict[str, np.ndarray], footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    """The frozen TRI3 concordance surface. Returns (surface float32, audit)."""
    audit: dict = {"families": {}}
    ridges: dict[str, np.ndarray] = {}
    for fam, names in FAMILIES.items():
        field = family_field(band_arrays, footprint, names,
                             det_elev=band_arrays["det_elev"] if fam == "topo" else None)
        ridges[fam] = pct32(_high_pass(field, footprint), footprint)
        audit["families"][fam] = {"bands": list(names) + (["|lap det_elev|"] if fam == "topo" else [])}
        del field

    # basement-step gate: |gradient| of depth-to-basement, lightly smoothed
    base = band_arrays["depth_to_base_surf"].astype(np.float32)
    bad = ~np.isfinite(base) | (base < -1e30)
    if bad.any():
        _, idx = ndi.distance_transform_edt(bad, return_indices=True)
        base = base[idx[0], idx[1]]
    gy, gx = np.gradient(ndi.gaussian_filter(base, 2.0, mode="nearest"))
    p_step = pct32(np.hypot(gx, gy), footprint)
    del base, gy, gx

    p_strain = pct32(band_arrays["geod_2ndinv"], footprint)

    prod = ridges["mag"] * ridges["grav"] * ridges["topo"]
    surface = (np.power(np.clip(prod, 0.0, None), 1.0 / 3.0)
               * (0.6 + 0.4 * p_step) * (0.85 + 0.15 * p_strain)).astype(np.float32)
    surface = np.where(footprint, surface, 0.0).astype(np.float32)
    audit["formula"] = ("(Rmag*Rgrav*Rtopo)^(1/3) * (0.6+0.4*Pstep) * (0.85+0.15*Pstrain); "
                        "R = pct of 5px-high-pass of mean band percentiles")
    audit["surface_family_ridges"] = {k: None for k in ridges}  # values not serialised
    return surface, audit


def disk_offsets(radius: float) -> list[tuple[int, int]]:
    r = int(np.ceil(radius))
    return [(dr, dc) for dr in range(-r, r + 1) for dc in range(-r, r + 1)
            if np.hypot(dr, dc) < radius]


def greedy_spaced(surface: np.ndarray, eligible: np.ndarray, n_dots: int,
                  *, spacing_px: float = 2.8, pool_factor: int = 30) -> np.ndarray:
    """Greedy unit dots in surface order with a hard minimum spacing.

    Deterministic: candidates are sorted by surface value descending with a
    stable sort over flat indices, so ties resolve to the lower flat index.
    Returns a boolean dot mask with exactly `n_dots` True (or fewer only if
    the eligible set cannot support that many spaced dots — callers assert).
    """
    if n_dots <= 0:
        return np.zeros(surface.shape, dtype=bool)
    flat_idx = np.flatnonzero(eligible)
    if flat_idx.size == 0:
        return np.zeros(surface.shape, dtype=bool)
    vals = surface.ravel()[flat_idx]
    order = np.argsort(-vals, kind="stable")
    cand = flat_idx[order]
    del flat_idx, vals, order

    h, w = surface.shape
    blocked = np.zeros(surface.shape, dtype=bool)
    dots = np.zeros(surface.shape, dtype=bool)
    offsets = disk_offsets(spacing_px)
    placed = 0
    pool = cand[: max(n_dots * pool_factor, n_dots)]
    for start in (0,):
        for fidx in pool:
            if placed >= n_dots:
                break
            r, c = divmod(int(fidx), w)
            if blocked[r, c]:
                continue
            dots[r, c] = True
            placed += 1
            for dr, dc in offsets:
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w:
                    blocked[rr, cc] = True
    if placed < n_dots:  # widen to the full eligible order (rare; keeps the count exact)
        for fidx in cand[len(pool):]:
            if placed >= n_dots:
                break
            r, c = divmod(int(fidx), w)
            if blocked[r, c]:
                continue
            dots[r, c] = True
            placed += 1
            for dr, dc in offsets:
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w:
                    blocked[rr, cc] = True
    return dots
