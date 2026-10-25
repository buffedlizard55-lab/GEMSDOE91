#!/usr/bin/env python3
"""GEO91 lane: catalogue-geometry blind-fault predictor (GEMSDOE91, session 2026-10-25).

LANE (provisional, documented): the prompt's promised single-method paragraph
was not supplied (IR-S16-04), so this lane is declared here explicitly and is
RESEARCH-ONLY until a selector approves a slot. No prior submission raster is
read as a feature, prior, or starting point. R0 is read ONLY after emission
for the protocol uniqueness check.

Hypothesis: faults missing from the USGS/INGENIOUS catalogue preferentially
occupy (a) along-strike continuations beyond mapped fault tips, (b) relay /
stepover gaps between close sub-parallel strands, and (c) the near-field band
(0.4-1.5 km) of dense mapped fault zones -- places where mapping stops at
cover boundaries rather than where faulting stops. Pure catalogue geometry,
zero geophysical feature bands: no fleet lane in this repo is geometry-only
at a strict >3 px collar with kernel-matched dotted emission.

Emission exploits the verified 0.2778 mechanism one step further: R0 pruned
dots <=2 px from the catalogue; GEO91 emits NOTHING <=3 px (one full DTI
kernel radius), binary {0,1}, min separation 2.8 px, N=37,654 (R0-matched
budget for comparability).

Reuse (protocol rule 2): folds/canary/pooled scoring from
scripts/evaluate_holdout.py + scripts/dti.py; writing/validation from
vendor/gems57/submission_writer.py. No private metric or writer fork.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

import evaluate_holdout as EH  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402

SEED = 91025
N_DOTS = 37_654
COLLAR_PX = 3.0          # strictly greater than this (R0 used >2 px)
SEP_PX = 2.8
SAMPLE = ROOT / "data/official/sample_submission.tif"
FAULTS = ROOT / "data/official/existing_faults.tif"
R0 = ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif"
EVID = ROOT / "evidence/geo91"
EXPECTED_SHA = {
    "sample_submission": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "existing_faults": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "parent_r0_zeros": "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def robust01(x: np.ndarray, mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Deterministic robust [0,1] scaling from a fixed subsample's p5/p99."""
    vals = x[mask]
    if vals.size > 500_000:
        vals = vals[rng.choice(vals.size, 500_000, replace=False)]
    lo, hi = np.percentile(vals, [5, 99])
    if hi <= lo:
        return np.zeros_like(x, dtype=np.float32)
    return np.clip((x - lo) / (hi - lo), 0, 1).astype(np.float32)


def disk(r: int) -> np.ndarray:
    oy, ox = np.mgrid[-r:r + 1, -r:r + 1]
    return np.hypot(oy, ox) <= r


def tip_extension_score(F: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Along-strike rays beyond 1-neighbour endpoints of the fault mask."""
    cnt = ndi.convolve(F.astype(np.int32), np.ones((3, 3), np.int32), mode="constant") - F
    ends = np.argwhere(F & (cnt == 1))
    score = np.zeros(F.shape, np.float32)
    H, W = F.shape
    for y, x in ends:
        y0, y1, x0, x1 = max(0, y - 3), min(H, y + 4), max(0, x - 3), min(W, x + 4)
        patch = F[y0:y1, x0:x1].copy()
        patch[y - y0, x - x0] = False
        py, px = np.nonzero(patch)
        if py.size == 0:
            continue
        vy, vx = y - (py.mean() + y0), x - (px.mean() + x0)
        n = np.hypot(vy, vx)
        if n == 0:
            continue
        vy, vx = vy / n, vx / n
        for s in range(2, 19):
            yy, xx = int(round(y + vy * s)), int(round(x + vx * s))
            if 0 <= yy < H and 0 <= xx < W and footprint[yy, xx] and not F[yy, xx]:
                score[yy, xx] += np.float32(1.0 - s / 20.0)
    return score


def surface(F: np.ndarray, footprint: np.ndarray, rng: np.random.Generator):
    """All features derived ONLY from fault mask F. Returns (surface, feats, dist)."""
    dist = ndi.distance_transform_edt(~F).astype(np.float32)
    eligible = footprint & ~F
    density = ndi.uniform_filter(F.astype(np.float32), size=31, mode="constant")
    closed = ndi.binary_closing(F, structure=disk(5))
    relay = (closed & ~ndi.binary_dilation(F, structure=disk(1))).astype(np.float32)
    relay = ndi.gaussian_filter(relay, 1.5)
    tip = ndi.gaussian_filter(tip_extension_score(F, footprint), 1.0)
    band = np.clip(1.0 - np.abs(dist - 8.0) / 8.0, 0, 1) * (dist > COLLAR_PX)
    feats = {
        "tip_extension": robust01(tip, eligible, rng),
        "relay_gap": robust01(relay, eligible, rng),
        "nearfield_band_x_density": robust01(band * density, eligible, rng),
        "fault_density_3km": robust01(density, eligible, rng),
    }
    surf = (0.35 * feats["tip_extension"] + 0.25 * feats["relay_gap"]
            + 0.25 * feats["nearfield_band_x_density"] + 0.15 * feats["fault_density_3km"])
    surf[~eligible] = 0.0
    return surf.astype(np.float32), feats, dist


def emit(surf: np.ndarray, dist: np.ndarray, footprint: np.ndarray, F: np.ndarray,
         n: int = N_DOTS) -> np.ndarray:
    """Greedy separated binary dots, strict >COLLAR_PX from F, hash suppression.

    Primary order is `surf` descending; zero-surface pixels (possible for the
    narrow band-only control) are filled last, nearest to the 8 px band first,
    so every arm emits exactly `n` dots under identical geometry rules.
    """
    cand_mask = footprint & ~F & (dist > COLLAR_PX)
    ys, xs = np.nonzero(cand_mask)
    key = np.where(surf[ys, xs] > 0, surf[ys, xs],
                   -1.0 - np.abs(dist[ys, xs] - 8.0) / 1000.0)
    order = np.argsort(-key, kind="stable")
    ys, xs = ys[order], xs[order]
    cell = int(np.ceil(SEP_PX))
    occupied: set[tuple[int, int]] = set()
    out = np.zeros(surf.shape, np.float32)
    placed = 0
    for y, x in zip(ys.tolist(), xs.tolist()):
        cy, cx = y // cell, x // cell
        clash = False
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (cy + dy, cx + dx) in occupied:
                    clash = True
                    break
            if clash:
                break
        if clash:
            continue
        out[y, x] = 1.0
        occupied.add((cy, cx))
        placed += 1
        if placed >= n:
            break
    if placed < n:
        raise RuntimeError(f"only placed {placed}/{n} dots")
    return out


def spearman_sample(a: np.ndarray, b: np.ndarray, mask: np.ndarray,
                    rng: np.random.Generator, k: int = 200_000) -> float:
    ys, xs = np.nonzero(mask)
    idx = rng.choice(ys.size, min(k, ys.size), replace=False)
    ra = rankdata(a[ys[idx], xs[idx]])
    rb = rankdata(b[ys[idx], xs[idx]])
    return float(np.corrcoef(ra, rb)[0, 1])


def overlap_3px(candidate: np.ndarray, reference: np.ndarray) -> float:
    c = np.argwhere(candidate > 0)
    r = np.argwhere(reference > 0)
    if len(c) == 0 or len(r) == 0:
        return 0.0
    d, _ = cKDTree(r).query(c, k=1)
    return float((d <= 3.0).mean())


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    EVID.mkdir(parents=True, exist_ok=True)
    for name, path in (("sample_submission", SAMPLE), ("existing_faults", FAULTS),
                       ("parent_r0_zeros", R0)):
        got = sha256_file(path)
        assert got == EXPECTED_SHA[name], f"sha mismatch {name}: {got}"
    print("[geo91] pinned inputs verified", flush=True)

    with rasterio.open(SAMPLE) as ds:
        tpl = ds.read(1)
    footprint = np.isfinite(tpl)
    with rasterio.open(FAULTS) as ds:
        catalogue = (ds.read(1) == 1) & footprint

    # ---- Holdout: whole-segment hide-and-recover, features from visible only
    folds = EH.build_segment_buffered_folds(catalogue.astype(np.float32), footprint)
    fold_pred, fold_pred_band, fold_pred_rand = {}, {}, {}
    fold_feats: dict[int, tuple[np.ndarray, list[str]]] = {}
    feat_names: list[str] = []
    for f in folds:
        surf_f, feats_f, dist_f = surface(f.visible_faults, footprint, rng)
        feat_names = list(feats_f)
        stack = np.stack([feats_f[k][footprint] for k in feat_names], axis=1).astype(np.float64)
        fold_feats[f.fold_id] = (stack, feat_names)
        fold_pred[f.fold_id] = emit(surf_f, dist_f, footprint, f.visible_faults)
        band_only = feats_f["nearfield_band_x_density"]
        fold_pred_band[f.fold_id] = emit(band_only, dist_f, footprint, f.visible_faults)
        rand_surf = rng.random(surf_f.shape, dtype=np.float32)
        rand_surf[~(footprint & ~f.visible_faults)] = 0
        fold_pred_rand[f.fold_id] = emit(rand_surf, dist_f, footprint, f.visible_faults)
        print(f"[geo91] fold {f.fold_id} done (withheld={f.n_withheld})", flush=True)

    empty_fp = np.zeros((int(footprint.sum()), len(feat_names)))
    canary = EH.run_leakage_canary(empty_fp, feat_names, folds, footprint,
                                   fold_specific_features=fold_feats)
    (EVID / "canary.json").write_text(json.dumps(canary, indent=1, default=float))
    print(f"[geo91] canary max sym AUC = {canary.get('max_symmetric_auc')}", flush=True)

    hold = EH.score_pooled_holdout(fold_pred, folds, footprint, n_boot=200, seed=SEED)
    hold_band = EH.score_pooled_holdout(fold_pred_band, folds, footprint, n_boot=200, seed=SEED)
    hold_rand = EH.score_pooled_holdout(fold_pred_rand, folds, footprint, n_boot=200, seed=SEED)
    (EVID / "holdout.json").write_text(json.dumps(
        {"candidate": hold, "control_band_only": hold_band, "control_random": hold_rand},
        indent=1, default=float))
    print("[geo91] holdout:", json.dumps({k: hold.get(k) for k in
          ("evidence_class", "evaluator_version", "pooled_dti", "dti", "ci95",
           "n_withheld_positives")}, default=float), flush=True)

    # ---- Full-map candidate (experiment 1 of max 3; no tuning after this)
    surf, _feats, dist = surface(catalogue, footprint, rng)
    with rasterio.open(R0) as ds:
        r0 = ds.read(1).astype(np.float32)
    rho = spearman_sample(surf, r0, footprint & ~catalogue, rng)
    pred = emit(surf, dist, footprint, catalogue)
    ov_r0 = overlap_3px(pred, r0)
    registry = {"surface_spearman_vs_R0": rho, "dot_overlap3px_vs_R0": ov_r0,
                "per_download_overlap3px": {}}
    for p in sorted((ROOT / "docs/downloads").glob("*-zeros.tif")):
        with rasterio.open(p) as ds:
            ref = ds.read(1)
        if ref.shape == pred.shape:
            registry["per_download_overlap3px"][p.name] = overlap_3px(pred, ref)
    (EVID / "registry.json").write_text(json.dumps(registry, indent=1))
    print(f"[geo91] rho vs R0={rho:.4f} overlap3px vs R0={ov_r0:.4f} "
          f"max downloads={max(registry['per_download_overlap3px'].values(), default=0):.4f}",
          flush=True)

    # ---- Write with the shared template writer (all-finite zeros encoding)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"gems91-geo91-tiprelay-collar3-{stamp}"
    note = "GEO91 catalogue-geometry tip+relay, collar>3px, 37654 dotted; holdout-validated research candidate."
    assert len(note) <= 140, len(note)
    out = ROOT / "docs/downloads" / f"{name}-zeros.tif"
    receipt = write_submission(out, pred, SAMPLE, footprint, note=note, name=name,
                               catalogue=catalogue,
                               metadata={"lane": "GEO91", "seed": SEED, "n_dots": N_DOTS,
                                         "collar_px_strict_gt": COLLAR_PX, "sep_px": SEP_PX})
    sha = sha256_file(out)
    (EVID / "writer_receipt.json").write_text(json.dumps(receipt, indent=1, default=str))

    card = {
        "hypothesis": "Uncatalogued faults concentrate at mapped-fault tip continuations, "
                      "relay/stepover gaps, and the 0.4-1.5 km near-field band of dense "
                      "mapped zones; strict >3 px collar dotted emission converts this "
                      "into DTI-efficient coverage.",
        "mechanism": "Catalogue-geometry surface (tip rays 0.35 + relay-gap closing 0.25 "
                     "+ band x density 0.25 + 3 km density 0.15); greedy 2.8 px-separated "
                     "binary dots, >3 px from catalogue, N=37654.",
        "non_fault_mimic": "Mapping-effort bias: catalogue density tracks exposure/access, "
                           "so geometry features may predict mappability, not blind faults. "
                           "Lithologic contacts terminating at cover mimic fault tips.",
        "holdout_dti": hold, "control_band_only": hold_band, "control_random": hold_rand,
        "canary_max_symmetric_auc": canary.get("max_symmetric_auc"),
        "registry": registry, "raster_sha256": sha, "raster_path": str(out.relative_to(ROOT)),
        "submission_name": name, "note": note, "note_chars": len(note),
        "experiments_run": 1, "slots_used": 0, "organizer_confirmed": None,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (ROOT / "docs/run-card-GEO91.json").write_text(json.dumps(card, indent=1, default=float))
    print(f"[geo91] wrote {out.name} sha256={sha} in {card['elapsed_s']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
