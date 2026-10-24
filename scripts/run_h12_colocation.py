#!/usr/bin/env python3
"""H12-1 (session 12, experiment E1): physics-only gravity-magnetic edge co-location.

Pre-registered before running. The emission has NO tuned parameters and is never
selected on the holdout:

    z_mag  = max(robust_z(B03 tmi_hg), 0)            # magnetic horizontal gradient
    z_grav = max(robust_z(hypot(B11, B18)), 0)        # gravity horizontal-gradient magnitude
    score  = z_mag * z_grav                           # co-location (both fields edge)

B18 is signed and is ONE component of the 2-D gravity gradient vector (B11, B18), per
IR-91-S11-02; the magnitude is hypot(B11, B18). The first attempt used |B18| alone and was
stopped after its holdout line was printed (IR-91-S12-03); it is recorded as an
aborted attempt in the run card, not as a result. Dots are placed greedily by score on eligible pixels with
3.05 px minimum spacing, using the S11 lane's fold quotas and eligibility rule.

Negative controls (same placement code, same quotas): random eligible placement,
gravity-only, and magnetic-only. The experiment is counted as ONE of the 3-experiment
budget; the controls are nulls, not candidates.

Outputs are NEW files under evidence/h12/. Nothing in docs/, releases/, or the
existing evidence/ JSON files is written.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path[:0] = [str(SCRIPTS), str(ROOT / "src"), str(ROOT)]

import evaluate_holdout as EH  # noqa: E402
import run_s11_lane as S11  # noqa: E402  (reuses pinned paths, quota and eligibility rules)

OUT_DIR = ROOT / "evidence" / "h12"
EXPERIMENT_ID = "H12-1-E1"
BAND_MAG = 3
BAND_GRAV_Y = 11
BAND_GRAV_X = 18
EXPECTED_DESC = {
    BAND_MAG: "tmi_hg",
    BAND_GRAV_Y: "iso_grav_anom_vg",
    BAND_GRAV_X: "iso_grav_anom_hg",
}
SPACING_PX = 3.05
SENTINEL = 1e30


def _log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def robust_z(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    v = a[valid]
    med = float(np.median(v))
    q1, q3 = np.percentile(v, [25, 75])
    scale = max(float(q3 - q1) / 1.349, 1e-9)
    z = (a - med) / scale
    z = np.where(valid, z, 0.0)
    return np.clip(z, 0.0, None).astype(np.float32)


def emit(score: np.ndarray, eligible: np.ndarray, n: int) -> tuple[np.ndarray, int]:
    """Greedy top-score placement with minimum spacing. Returns (binary dots, count)."""
    H, W = score.shape
    s = np.where(eligible, score, -1.0).ravel()
    k = min(s.size, max(4 * n, 200_000))
    idx = np.argpartition(-s, k - 1)[:k]
    idx = idx[np.argsort(-s[idx], kind="stable")]
    r = int(np.ceil(SPACING_PX))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (yy ** 2 + xx ** 2) <= SPACING_PX ** 2
    blocked = np.zeros((H, W), dtype=bool)
    dots = np.zeros((H, W), dtype=np.float32)
    count = 0
    for flat in idx:
        if count >= n or s[flat] < 0:
            break
        y, x = divmod(int(flat), W)
        if blocked[y, x]:
            continue
        dots[y, x] = 1.0
        count += 1
        y0, y1 = max(0, y - r), min(H, y + r + 1)
        x0, x1 = max(0, x - r), min(W, x + r + 1)
        blocked[y0:y1, x0:x1] |= disk[(y0 - y + r):(y1 - y + r), (x0 - x + r):(x1 - x + r)]
    return dots, count


def main() -> int:
    t0 = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for req in (S11.TEMPLATE_TIF, S11.CATALOGUE_TIF, S11.FEATURES_TIF):
        if not req.is_file():
            raise FileNotFoundError(f"missing pinned input {req}; run scripts/restore_data.py first")

    with rasterio.open(S11.TEMPLATE_TIF) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(S11.CATALOGUE_TIF) as src:
        cat_mask = (src.read(1) > 0) & footprint

    with rasterio.open(S11.FEATURES_TIF) as src:
        for b, expect in EXPECTED_DESC.items():
            desc = (src.descriptions[b - 1] or "")
            if expect not in desc:
                raise ValueError(f"band {b} description {desc!r} does not contain {expect!r}")
        mag = src.read(BAND_MAG).astype(np.float64)
        gy = src.read(BAND_GRAV_Y).astype(np.float64)
        gx = src.read(BAND_GRAV_X).astype(np.float64)
    valid_mag = footprint & np.isfinite(mag) & (np.abs(mag) < SENTINEL)
    valid_grav = footprint & np.isfinite(gx) & np.isfinite(gy) & (np.abs(gx) < SENTINEL) & (np.abs(gy) < SENTINEL)
    valid = valid_mag & valid_grav
    mag = np.where(valid_mag, mag, 0.0)
    grav = np.where(valid_grav, np.hypot(np.where(valid_grav, gy, 0.0), np.where(valid_grav, gx, 0.0)), 0.0)

    z_mag = robust_z(mag, valid)
    z_grav = robust_z(grav, valid)
    colocation = (z_mag * z_grav).astype(np.float32)
    colocation = np.where(valid, colocation, 0.0).astype(np.float32)
    _log(f"Features loaded: footprint={int(footprint.sum())} valid={int(valid.sum())}")

    folds = EH.build_segment_buffered_folds(cat_mask, footprint, bridge_px=3, buffer_px=10.0)
    fold_elig: dict[int, np.ndarray] = {}
    active_counts: dict[int, int] = {}
    for f in folds:
        act, elig = S11._fold_active_and_eligible(f, folds, footprint, collar_px=3.0)
        fold_elig[f.fold_id] = elig
        active_counts[f.fold_id] = int(act.sum())
    total_active = sum(active_counts.values())
    quota: dict[int, int] = {}
    assigned = 0
    for f in folds:
        if f.fold_id < 3:
            quota[f.fold_id] = int(round(S11.FULL_DOT_BUDGET * active_counts[f.fold_id] / total_active))
            assigned += quota[f.fold_id]
        else:
            quota[f.fold_id] = S11.FULL_DOT_BUDGET - assigned
    _log(f"Folds={len(folds)} quotas={quota}")

    rng = np.random.default_rng(91)
    candidates = {
        "E1_colocation_mag_x_grav": colocation,
        "C_random_placement": rng.random(footprint.shape).astype(np.float32),
        "C_gravity_only": z_grav,
        "C_magnetic_only": z_mag,
    }

    results: dict[str, dict] = {}
    for name, surface in candidates.items():
        fold_dots: dict[int, np.ndarray] = {}
        placed: dict[int, int] = {}
        for f in folds:
            dots, cnt = emit(surface, fold_elig[f.fold_id], quota[f.fold_id])
            if cnt < quota[f.fold_id]:
                raise RuntimeError(f"{name} fold {f.fold_id}: placed {cnt} < quota {quota[f.fold_id]}")
            fold_dots[f.fold_id] = dots
            placed[f.fold_id] = cnt
        union = np.zeros(footprint.shape, dtype=np.float32)
        for d in fold_dots.values():
            union = np.maximum(union, d)
        ho = EH.score_pooled_holdout(fold_dots, folds, footprint, n_boot=200, seed=91)
        uniq = EH.check_registry_uniqueness(
            surface[footprint], union, footprint, EH.default_registry_paths()
        )
        results[name] = {
            "holdout_dti": ho["holdout_dti"],
            "ci_95": ho["ci_95"],
            "metric_label": ho["metric_label"],
            "evaluator_version": ho["evaluator_version"],
            "n_withheld_positives": ho["n_withheld_positives"],
            "dots_placed": placed,
            "registry_uniqueness_pass": bool(uniq["uniqueness_pass"]),
            "registry_uniqueness": {k: v for k, v in uniq.items() if k not in ("comparisons",)},
        }
        _log(f"{name}: HOLDOUT-DTI={ho['holdout_dti']:.6f} CI={ho['ci_95']} "
             f"uniqueness_pass={results[name]['registry_uniqueness_pass']}")

    # Leakage canary on the three physics features, folds-aware (symmetric AUC).
    feats = np.stack([z_mag[footprint], z_grav[footprint], colocation[footprint]], axis=1)
    canary = EH.run_leakage_canary(feats, ["z_mag", "z_grav", "colocation"], folds, footprint)
    _log(f"Leakage canary: all_pass={canary['all_pass']} worst={canary['worst_feature']} "
         f"symmetric_AUC={canary['worst_symmetric_auc']} (max allowed {canary['max_allowed_auc']})")

    out = {
        "experiment_id": EXPERIMENT_ID,
        "hypothesis": "H12-1: co-located gravity and magnetic horizontal-gradient maxima mark "
                      "fault-scale contacts without catalogue information",
        "pre_registered_parameters": {
            "score": "max(z(tmi_hg),0) * max(z(hypot(B11,B18)),0)",
            "robust_z": "(x - median)/(IQR/1.349) over footprint-valid pixels",
            "spacing_px": SPACING_PX,
            "quotas": "S11 lane fold quotas (48,000 total)",
            "tuned_on_holdout": False,
        },
        "labels": {"holdout_metric": "HOLDOUT-DTI", "organizer_confirmed": None},
        "results": results,
        "leakage_canary": canary,
        "runtime_s": round(time.perf_counter() - t0, 1),
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out_path = OUT_DIR / "h12_colocation_E1.json"
    out_path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
    _log(f"Wrote {out_path.relative_to(ROOT)} in {out['runtime_s']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
