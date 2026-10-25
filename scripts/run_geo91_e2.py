#!/usr/bin/env python3
"""GEO91 Experiment 2: habitat-stratified broad coverage (pre-registered after E1).

E1 result (evidence/geo91/holdout.json): tip/relay/band geometry HOLDOUT-DTI
0.001338 [0.000671, 0.002171] vs uniform-random control 0.076603
[0.074395, 0.079022] on gems91-hide-recover-v1.1-nohalo (60,988 withheld).
Whole-segment buffering structurally removes near-catalogue credit, matching
the live fleet pattern (pure relay lanes 0.005-0.016; broad dotted habitat
surfaces 0.25-0.28). E2 therefore tests the opposite geometry: footprint-wide
Poisson-disk-style coverage (6 px suppression), score = 0.5*fault-density +
0.5*U(0,1) (seeded), strict >3 px collar, N=37,654. Same folds, same scorer,
same random control design as E1. This is experiment 2 of the max-3 budget;
no further tuning after E2 regardless of outcome (E3 reserved, unused unless
E2 beats the random control, in which case E2 itself is the candidate).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor"))

import evaluate_holdout as EH  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from run_geo91_lane import (COLLAR_PX, EVID, FAULTS, N_DOTS, R0, SAMPLE,  # noqa: E402
                            SEED, overlap_3px, robust01, sha256_file,
                            spearman_sample)

SEP_CELL = 6  # px hash-cell suppression for broad coverage


def emit_broad(score: np.ndarray, dist: np.ndarray, footprint: np.ndarray,
               F: np.ndarray, n: int = N_DOTS) -> np.ndarray:
    cand = footprint & ~F & (dist > COLLAR_PX)
    ys, xs = np.nonzero(cand)
    order = np.argsort(-score[ys, xs], kind="stable")
    ys, xs = ys[order], xs[order]
    occupied: set[tuple[int, int]] = set()
    out = np.zeros(score.shape, np.float32)
    placed = 0
    for y, x in zip(ys.tolist(), xs.tolist()):
        cy, cx = y // SEP_CELL, x // SEP_CELL
        if any((cy + dy, cx + dx) in occupied for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
            continue
        out[y, x] = 1.0
        occupied.add((cy, cx))
        placed += 1
        if placed >= n:
            break
    if placed < n:  # relax suppression for any shortfall, same score order
        for y, x in zip(ys.tolist(), xs.tolist()):
            if placed >= n:
                break
            if out[y, x] == 0 and out[max(0, y - 2):y + 3, max(0, x - 2):x + 3].sum() == 0:
                out[y, x] = 1.0
                placed += 1
    assert placed == n, placed
    return out


def score_surface(F: np.ndarray, footprint: np.ndarray, rng: np.random.Generator):
    dist = ndi.distance_transform_edt(~F).astype(np.float32)
    density = ndi.uniform_filter(F.astype(np.float32), size=31, mode="constant")
    d01 = robust01(density, footprint & ~F, rng)
    score = (0.5 * d01 + 0.5 * rng.random(d01.shape, dtype=np.float32)).astype(np.float32)
    return score, dist


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED + 2)
    with rasterio.open(SAMPLE) as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(FAULTS) as ds:
        catalogue = (ds.read(1) == 1) & footprint

    folds = EH.build_segment_buffered_folds(catalogue.astype(np.float32), footprint)
    fold_pred, fold_rand = {}, {}
    for f in folds:
        score_f, dist_f = score_surface(f.visible_faults, footprint, rng)
        fold_pred[f.fold_id] = emit_broad(score_f, dist_f, footprint, f.visible_faults)
        rand = rng.random(score_f.shape, dtype=np.float32)
        fold_rand[f.fold_id] = emit_broad(rand, dist_f, footprint, f.visible_faults)
        print(f"[geo91-e2] fold {f.fold_id} done", flush=True)
    hold = EH.score_pooled_holdout(fold_pred, folds, footprint, n_boot=200, seed=SEED)
    hold_rand = EH.score_pooled_holdout(fold_rand, folds, footprint, n_boot=200, seed=SEED)
    (EVID / "holdout_e2.json").write_text(json.dumps(
        {"candidate_e2": hold, "control_random_broad": hold_rand}, indent=1, default=float))
    print("[geo91-e2] candidate", hold.get("holdout_dti"), hold.get("ci_95"),
          "| random-broad", hold_rand.get("holdout_dti"), hold_rand.get("ci_95"), flush=True)

    score, dist = score_surface(catalogue, footprint, rng)
    with rasterio.open(R0) as ds:
        r0 = ds.read(1).astype(np.float32)
    rho = spearman_sample(score, r0, footprint & ~catalogue, rng)
    pred = emit_broad(score, dist, footprint, catalogue)
    ov = overlap_3px(pred, r0)
    per = {}
    for p in sorted((ROOT / "docs/downloads").glob("*-zeros.tif")):
        with rasterio.open(p) as ds:
            ref = ds.read(1)
        if ref.shape == pred.shape and "geo91-tiprelay" not in p.name:
            per[p.name] = overlap_3px(pred, ref)
    print(f"[geo91-e2] rho={rho:.4f} overlapR0={ov:.4f} maxDL={max(per.values(), default=0):.4f}",
          flush=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"gems91-geo91e2-stratcover-collar3-{stamp}"
    note = "GEO91-E2 habitat-stratified broad coverage, collar>3px, 37654 dotted; see run-card-GEO91.json gates."
    assert len(note) <= 140
    out = ROOT / "docs/downloads" / f"{name}-zeros.tif"
    write_submission(out, pred, SAMPLE, footprint, note=note, name=name,
                     catalogue=catalogue,
                     metadata={"lane": "GEO91-E2", "seed": SEED + 2, "n_dots": N_DOTS})
    sha = sha256_file(out)
    beats_random = float(hold["holdout_dti"]) > float(hold_rand["holdout_dti"])
    card_path = ROOT / "docs/run-card-GEO91.json"
    card = json.loads(card_path.read_text())
    card.update({
        "experiments_run": 2, "e2_holdout_dti": hold, "e2_control_random_broad": hold_rand,
        "e2_beats_random_control": beats_random,
        "e2_registry": {"surface_spearman_vs_R0": rho, "dot_overlap3px_vs_R0": ov,
                        "per_download_overlap3px": per},
        "e2_raster_sha256": sha, "e2_raster_path": str(out.relative_to(ROOT)),
        "e2_submission_name": name, "e2_note": note,
        "elapsed_s_total": round(time.time() - t0, 1),
    })
    card_path.write_text(json.dumps(card, indent=1, default=float))
    print(f"[geo91-e2] wrote {out.name} sha={sha} beats_random={beats_random}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
