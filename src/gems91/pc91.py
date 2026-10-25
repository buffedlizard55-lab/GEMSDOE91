"""PC91 — Kovesi phase congruency via the monogenic signal (preregistered lane).

Frozen design: `docs/HYPOTHESES_S16.md` (2026-10-25, written before any PC91
holdout number was computed). A fault offset is a multi-scale phase alignment:
at a step/line, the Fourier components of the field agree in *phase* even when
their *amplitude* is tiny (deep basement fault under basin fill). Amplitude
detectors (gradient magnitude, tilt, Frangi, ASC step filter) rank such faults
below shallow high-amplitude noise; phase congruency normalizes amplitude away:

    PC = W * sum_s A_s * max(cos(phi_s - phi_bar) - |sin(phi_s - phi_bar)|, 0)
         / (sum_s A_s + eps)

with the Kovesi frequency-spread weight W (suppresses the single-scale
pathology where one active scale trivially agrees with itself). Per scale the
monogenic triple comes from a radial log-Gabor bandpass times the Riesz
multipliers (-i kr/|k|, -i kc/|k|). Orientation is carried by the summed odd
(Riesz) vector; its double-angle gives strike-invariant agreement features.

Memory: single-precision FFTs (scipy.fft preserves float32 -> complex64) and
streaming per-scale accumulation — the sandbox has ~3 GB RAM and a float64
implementation OOM-killed on the full 3730x3292 grid (S16 first run).

No catalogue-derived quantity is used anywhere in this module.
"""
from __future__ import annotations

import numpy as np
from scipy import fft as sfft
from scipy import ndimage as ndi

WAVELENGTHS_PX = (3.0, 6.0, 12.0, 24.0)
SIGMA_ONF = 0.55  # log-Gabor bandwidth ratio (Kovesi default)
FIELDS = (("rtp", 2), ("det_elev", 12), ("iso_grav_anom", 13))


def phase_congruency_features(field: np.ndarray, wavelengths=WAVELENGTHS_PX) -> dict[str, np.ndarray]:
    """Return pc / energy / ampsum / cos2 / sin2 / coh as float32 grids."""
    f = np.asarray(field, dtype=np.float32)
    f = (f - float(f.mean(dtype=np.float64))).astype(np.float32)
    h, w = f.shape
    F = sfft.fft2(f)  # complex64
    del f
    kr = sfft.fftfreq(h).astype(np.float32)[:, None]
    kc = sfft.fftfreq(w).astype(np.float32)[None, :]
    radius = np.sqrt(kr * kr + kc * kc, dtype=np.float32)
    inv_r = np.where(radius > 0, 1.0 / np.where(radius > 0, radius, np.float32(1.0)), np.float32(0.0)).astype(np.float32)
    riesz_r_im = (-kr * inv_r).astype(np.float32)  # multiplier is 1j * this
    riesz_c_im = (-kc * inv_r).astype(np.float32)
    del kr, kc, inv_r
    log_r = np.where(radius > 0, np.log(np.where(radius > 0, radius, np.float32(1.0))), np.float32(0.0)).astype(np.float32)
    pos = radius > 0
    del radius
    log_sigma = float(np.log(SIGMA_ONF))

    sum_e = np.zeros((h, w), dtype=np.float32)
    sum_or = np.zeros((h, w), dtype=np.float32)
    sum_oc = np.zeros((h, w), dtype=np.float32)
    sum_a = np.zeros((h, w), dtype=np.float32)
    amps: list[np.ndarray] = []
    phis: list[np.ndarray] = []
    for wl in wavelengths:
        G = np.where(pos, np.exp(-((log_r - np.log(1.0 / float(wl))) ** 2) / (2.0 * log_sigma ** 2)), np.float32(0.0)).astype(np.float32)
        B = F * G
        del G
        even = sfft.ifft2(B).real.astype(np.float32)
        odd_r = sfft.ifft2(B * (1j * riesz_r_im)).real.astype(np.float32)
        odd_c = sfft.ifft2(B * (1j * riesz_c_im)).real.astype(np.float32)
        del B
        a = np.sqrt(even * even + odd_r * odd_r + odd_c * odd_c, dtype=np.float32)
        amps.append(a)
        phis.append(np.arctan2(np.hypot(odd_r, odd_c), even).astype(np.float32))
        sum_e += even
        sum_or += odd_r
        sum_oc += odd_c
        sum_a += a
        del even, odd_r, odd_c
    del F, log_r, pos, riesz_r_im, riesz_c_im

    energy = np.sqrt(sum_e ** 2 + sum_or ** 2 + sum_oc ** 2, dtype=np.float32)
    eps = np.float32(1e-12)
    phi_bar = np.arctan2(np.hypot(sum_or, sum_oc), sum_e)
    numer = np.zeros((h, w), dtype=np.float32)
    a_max = np.maximum.reduce(amps)
    for a, ph in zip(amps, phis):
        d = ph - phi_bar
        numer += a * np.maximum(np.cos(d) - np.abs(np.sin(d)), np.float32(0.0))
    del amps, phis, phi_bar
    spread = sum_a / (len(wavelengths) * np.maximum(a_max, eps))
    del a_max
    weight = 1.0 / (1.0 + np.exp(np.clip(10.0 * (0.5 - spread), -60.0, 60.0)))
    del spread
    pc = np.clip(weight * numer / (sum_a + eps), 0.0, 1.0).astype(np.float32)
    del weight, numer

    m2 = sum_or ** 2 + sum_oc ** 2
    cos2 = np.where(m2 > 0, (sum_oc ** 2 - sum_or ** 2) / np.where(m2 > 0, m2, np.float32(1.0)), np.float32(0.0)).astype(np.float32)
    sin2 = np.where(m2 > 0, (2.0 * sum_oc * sum_or) / np.where(m2 > 0, m2, np.float32(1.0)), np.float32(0.0)).astype(np.float32)
    sm_or = ndi.gaussian_filter(sum_or, 1.5)
    sm_oc = ndi.gaussian_filter(sum_oc, 1.5)
    sm_mag = ndi.gaussian_filter(np.sqrt(m2, dtype=np.float32), 1.5)
    coh = np.clip(np.hypot(sm_or, sm_oc) / (sm_mag + eps), 0.0, 1.0).astype(np.float32)
    return {
        "pc": pc,
        "energy": energy.astype(np.float32),
        "ampsum": sum_a.astype(np.float32),
        "cos2": cos2,
        "sin2": sin2,
        "coh": coh,
    }
