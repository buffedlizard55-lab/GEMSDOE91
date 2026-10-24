#!/usr/bin/env python3
"""Hide-and-recover HOLDOUT-DTI evaluator (session 10, GEMSDOE91).

PROVENANCE: the protocol names a shared `evaluate_holdout.py` template.  No such file
exists in this repository or in the organizer reference solution, so this is a NEW
evaluator written in session 10 and labelled EVALUATOR_VERSION below.  It reuses the
DTI components from scripts/dti.py (T, S, M, G; alpha 0.2, beta 0.8, 3 px triangular
kernel) and does not fork that algebra.

Design (pre-registered, see docs/HYPOTHESES_S10.md):
  * Positives = the catalogue (existing_faults == 1), split into connected segments
    (8-connectivity).  Segments are assigned whole to 10 spatial blocks (5 row bands x
    2 column bands) by their centroid.
  * Fold k withholds the segments of block k (W_k).  The candidate is REBUILT per fold
    from the visible catalogue only (catalogue minus W_k); visible catalogue cells
    receive zero mass.  The 3 px buffer ring around W_k is COUNTED and reported
    (visible_buffer_px) but not hidden: the S10 candidate reads the catalogue only as a
    mask, so buffer hiding would change nothing (IR-91-S10-03).  Any future candidate
    that reads catalogue-derived features must also hide the buffer.
  * Per fold we get T_k, S_k, M_k, G_k.  Pooled DTI = sum T_k / sum(alpha T_k +
    alpha (S_k - M_k) + beta G_k): components are pooled before the ratio.
  * 95 % CI = fold bootstrap (2000 resamples over the 10 folds, seed 91).  This is NOT
    the segment bootstrap the protocol asks for; it is reported as a deviation (IR-91-S10-02).
  * Leakage canary: each input band alone, plus the candidate's own score field, is
    scored by pixel AUC (withheld catalogue vs non-catalogue footprint).  AUC > 0.90 in
    either direction is a leak until proven otherwise.

Usage:
    python3 scripts/evaluate_holdout.py --experiment E1 --out evidence/holdout_S10_E1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import dti as dti_mod  # noqa: E402  (components(): T, S, M, G)
from gems91 import basement  # noqa: E402

EVALUATOR_VERSION = "S10-holdout-v1 (new in session 10; wraps scripts/dti.py)"
ROW_BANDS, COL_BANDS = 5, 2
BUFFER_PX = 3
BOOT_B = 2000
SEED = 91
CANARY_AUC_LIMIT = 0.90

DATA = ROOT / "data"
SAMPLE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
FEATURES = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
MANIFEST = ROOT / "registry" / "data_manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_inputs() -> dict:
    """Every input must match its pinned sha256 before a byte is used."""
    pins = {f["id"]: f for f in json.loads(MANIFEST.read_text())["files"]}
    out = {}
    for key, path in [
        ("sample_submission", SAMPLE),
        ("existing_faults", CATALOGUE),
        ("training_features", FEATURES),
    ]:
        digest = sha256_file(path)
        want = pins[key]["sha256"]
        if digest != want:
            raise SystemExit(f"PIN MISMATCH {key}: {digest} != {want}")
        out[key] = digest
    return out


def load_grids():
    with rasterio.open(SAMPLE) as s:
        footprint = np.isfinite(s.read(1))
        grid = {"crs": str(s.crs), "shape": list(s.shape), "transform": list(s.transform)[:6]}
    with rasterio.open(CATALOGUE) as s:
        cat = s.read(1) == 1
    with rasterio.open(FEATURES) as s:
        bands = s.read().astype(np.float64)  # (19, H, W)
    bands[bands < basement.NODATA_CUTOFF] = np.nan
    return footprint, cat, bands, grid


def segments(cat: np.ndarray):
    lab, n = ndi.label(cat, structure=np.ones((3, 3), dtype=int))
    centres = np.array(ndi.center_of_mass(cat, lab, index=np.arange(1, n + 1)))
    return lab, n, centres


def block_of_segments(centres: np.ndarray, shape) -> np.ndarray:
    h, w = shape
    rb = np.minimum((centres[:, 0] / h * ROW_BANDS).astype(int), ROW_BANDS - 1)
    cb = np.minimum((centres[:, 1] / w * COL_BANDS).astype(int), COL_BANDS - 1)
    return rb * COL_BANDS + cb  # 0..9


def buffer_ring(withheld: np.ndarray) -> np.ndarray:
    yy, xx = np.mgrid[-BUFFER_PX : BUFFER_PX + 1, -BUFFER_PX : BUFFER_PX + 1]
    disk = (yy**2 + xx**2) <= BUFFER_PX**2
    return ndi.binary_dilation(withheld, structure=disk) & ~withheld


def fold_iter(cat, lab, n, centres, shape):
    block = block_of_segments(centres, shape)
    seg_ids = np.arange(1, n + 1)
    for k in range(ROW_BANDS * COL_BANDS):
        in_k = seg_ids[block == k]
        withheld = np.isin(lab, in_k)
        visible = cat & ~withheld
        yield k, in_k.size, withheld, visible, buffer_ring(withheld) & visible


def pooled_dti(folds: list[dict], alpha=dti_mod.ALPHA, beta=dti_mod.BETA):
    T = np.array([f["T"] for f in folds])
    den = np.array([alpha * f["T"] + alpha * (f["S"] - f["M"]) + beta * f["G"] for f in folds])
    G = np.array([f["G"] for f in folds])
    point = float(T.sum() / den.sum()) if den.sum() > 0 else 0.0
    rng = np.random.default_rng(SEED)
    boots = np.empty(BOOT_B)
    m = len(folds)
    for b in range(BOOT_B):
        idx = rng.integers(0, m, size=m)
        d = den[idx].sum()
        boots[b] = T[idx].sum() / d if d > 0 else 0.0
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"dti": point, "ci95": [float(lo), float(hi)], "withheld_positives": int(G.sum())}


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC of pos over neg (ties counted half)."""
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[: pos.size].sum() - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))


def canary(bands: np.ndarray, footprint, cat, extra: dict[str, np.ndarray] | None = None, n_bg=300_000):
    rng = np.random.default_rng(SEED)
    bg_pool = np.flatnonzero((footprint & ~cat).ravel())
    bg = rng.choice(bg_pool, size=min(n_bg, bg_pool.size), replace=False)
    pos_idx = np.flatnonzero(cat.ravel())
    rows = []
    fields = {f"band{i + 1:02d}": bands[i].ravel() for i in range(bands.shape[0])}
    for name, arr in (extra or {}).items():
        fields[name] = arr.ravel()
    for name, arr in fields.items():
        p = arr[pos_idx]
        q = arr[bg]
        p = p[np.isfinite(p)]
        q = q[np.isfinite(q)]
        a = auc(p, q)
        rows.append({"feature": name, "auc": round(a, 4), "auc_direction_free": round(max(a, 1 - a), 4),
                     "leak_flag": bool(max(a, 1 - a) > CANARY_AUC_LIMIT)})
    return rows


def run_experiment(name: str, use_nms: bool, mode: str, out: Path | None):
    """mode: 'ridge' (candidate builder) or 'random' (null placement)."""
    checks = verify_inputs()
    footprint, cat, bands, grid = load_grids()
    depth = bands[14]  # band 15, depth_to_base_surf (1-based index 15)
    lab, n, centres = segments(cat)
    folds = []
    for k, n_seg, withheld, visible, buf in fold_iter(cat, lab, n, centres, cat.shape):
        if mode == "ridge":
            P = basement.build_candidate(depth, footprint, visible, use_nms=use_nms)
        elif mode == "random":
            P = basement.random_placement(footprint, visible, basement.K_DEFAULT, seed=SEED + k)
        else:
            raise ValueError(mode)
        P = np.where(footprint, P, 0.0)
        comp = dti_mod.components(P, withheld.astype(np.float64))
        folds.append({"fold": k, "segments_withheld": int(n_seg), "visible_buffer_px": int(buf.sum()),
                      "T": comp.T, "S": comp.S, "M": comp.M, "G": comp.G, "dti_fold": comp.score})
        print(f"[{name}] fold {k}: G={comp.G:.0f} T={comp.T:.1f} S={comp.S:.1f} M={comp.M:.1f} "
              f"dti_fold={comp.score:.4f}", flush=True)
    pooled = pooled_dti(folds)
    result = {
        "experiment": name,
        "mode": mode,
        "use_nms": use_nms,
        "evaluator_version": EVALUATOR_VERSION,
        "label": "HOLDOUT-DTI",
        "k": basement.K_DEFAULT,
        "pooled": pooled,
        "folds": folds,
        "pins_verified": checks,
        "grid": grid,
        "catalogue_segments": int(n),
        "ci_method": f"fold bootstrap, B={BOOT_B}, seed={SEED}, 10 spatial folds (NOT segment bootstrap; IR-91-S10-02)",
    }
    if mode == "ridge" and use_nms:
        score = basement.score_field(depth, footprint, use_nms=True)
        bands_plus = {"basement_ridge_score": np.where(footprint, score, 0.0)}
        result["canary"] = canary(bands, footprint, cat, extra=bands_plus)
    else:
        result["canary"] = canary(bands, footprint, cat)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"experiment": name, "pooled": pooled}, indent=2))
    return result


EXPERIMENTS = {
    "E1": dict(use_nms=True, mode="ridge"),    # pre-registered candidate
    "E2": dict(use_nms=False, mode="ridge"),   # ablation: no ridge thinning
    "E3": dict(use_nms=True, mode="random"),   # null: random placement, same budget/encoding
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--experiment", choices=sorted(EXPERIMENTS), required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    run_experiment(args.experiment, out=args.out, **EXPERIMENTS[args.experiment])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
