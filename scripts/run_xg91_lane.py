#!/usr/bin/env python3
"""XG91 lane runner. Uses the pinned template evaluator and writer.

Does not fork the metric. Stops an arm when the shared uniqueness gate says
the surface or the dots have drifted into another registry raster.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import spatial  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems91 import xg91  # noqa: E402
import evaluate_holdout as LEG  # noqa: E402

NODATA = -3.4028234663852886e38
FEATURES = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CATALOGUE = ROOT / "data/official/existing_faults.tif"
PRIOR_BEST_V2 = {
    "value": 0.1942673386089294,
    "evaluator_version": "gems57-pooled-hide-v2",
    "source": "evidence/spid91_gems57_holdout.json",
    "note": "Highest gems57-pooled-hide-v2 value found in this repo before XG91. Not re-scored here. Not comparable to gems91-hide-recover-v1.0 0.267782.",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def load_band(index: int) -> np.ndarray:
    with rasterio.open(FEATURES) as ds:
        a = ds.read(index).astype(np.float32)
    a[a <= NODATA / 2] = np.nan
    return a


def load_grid():
    with rasterio.open(SAMPLE) as ds:
        sample = ds.read(1)
        fp = np.isfinite(sample)
        crs = str(ds.crs)
        transform = tuple(ds.transform)[:6]
        shape = (ds.height, ds.width)
    with rasterio.open(CATALOGUE) as ds:
        cat = (ds.read(1) > 0) & fp
    return fp, cat, crs, transform, shape


def finite_registry(fp: np.ndarray, roots: list[Path]) -> list[Path]:
    paths = []
    candidates = []
    for root in roots:
        candidates.extend(root.glob("*.tif"))
    for p in sorted(set(candidates)):
        try:
            with rasterio.open(p) as ds:
                if ds.count != 1 or (ds.height, ds.width) != fp.shape:
                    continue
                a = ds.read(1)
        except Exception as exc:  # noqa: BLE001 — inventory, not a silent pass
            log(f"registry skip {p.name}: {exc}")
            continue
        inside = a[fp]
        if not np.isfinite(inside).all():
            log(f"registry skip nonfinite-inside {p.name}")
            continue
        if float(np.nanmax(inside) - np.nanmin(inside)) == 0.0:
            log(f"registry skip constant {p.name}")
            continue
        paths.append(p)
    if not paths:
        raise RuntimeError("no finite registry rasters")
    return paths


def surface_gate(surface: np.ndarray, fp: np.ndarray, paths: list[Path]) -> dict:
    return LEG.check_registry_surface_uniqueness(surface[fp].astype(np.float64), fp, paths)


def dot_gate(surface: np.ndarray, dots: np.ndarray, fp: np.ndarray, paths: list[Path]) -> dict:
    return LEG.check_registry_uniqueness(surface[fp].astype(np.float64), dots, fp, paths)


def score_arm(pred: np.ndarray, folds, fp: np.ndarray) -> dict:
    terms = []
    per = []
    withheld = 0
    for f in folds:
        res, tr = EH.evaluate(pred, f, fp, block_side=200)
        terms.append(tr)
        withheld += int(res["n_truth"])
        per.append({
            "fold": int(f["fold"]),
            "n_truth": int(res["n_truth"]),
            "n_emitted": int(res["emitted"]),
            "dti": float(res["dti"]),
        })
    arr = np.concatenate(terms)
    summary = EH.pooled_summary({"cand": arr}, draws=400, seed=91, candidate="cand")
    score = summary["scores"]["cand"]
    return {
        "label": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
        "withheld_positives": int(score["withheld_positive_pixels"]),
        "value": float(score["dti"]),
        "ci95": [float(x) for x in score["ci95"]],
        "tpw": float(score["tpw"]),
        "fpw": float(score["fpw"]),
        "fnw": float(score["fnw"]),
        "folds": per,
        "fold_truth_sum": withheld,
        "implementation_sha256": EH.implementation_hashes(),
    }


def emit_holdout(score: np.ndarray, folds, fp: np.ndarray, cat: np.ndarray, spacing: float, budget: int) -> np.ndarray:
    """Place dots from the label-free score, excluding only visible faults."""
    off = int((fp & ~cat).sum())
    pred = np.zeros(fp.shape, dtype=np.float32)
    for f in folds:
        elig = f["region"] & fp & ~f["visible"]
        n = max(1, int(round(budget * elig.sum() / max(off, 1))))
        pred[f["region"]] = xg91.emit_spaced_dots(score, elig, spacing_px=spacing, n_dots=n)[f["region"]]
    pred = np.where(fp, pred, 0.0).astype(np.float32)
    return pred


def random_control(folds, fp: np.ndarray, cat: np.ndarray, spacing: float, budget: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.random(fp.shape).astype(np.float32)
    return emit_holdout(noise, folds, fp, cat, spacing, budget)


def canary(features: dict[str, np.ndarray], folds, fp: np.ndarray) -> dict:
    names = list(features)
    out = {}
    worst = 0.0
    worst_name = ""
    for j, name in enumerate(names):
        aucs = []
        for f in folds:
            region = np.asarray(f["region"], bool) & fp
            truth = np.asarray(f["truth"], bool)
            visible = np.asarray(f["visible"], bool)
            eval_mask = region & ~visible
            y = truth[eval_mask]
            if int(y.sum()) < 20 or int((~y).sum()) < 20:
                raise RuntimeError(f"canary fold too small for {name}")
            # Keep all positives and a deterministic stride of negatives.
            idx = np.flatnonzero(eval_mask)
            pos = truth.ravel()[idx]
            keep = pos | ((np.arange(idx.size) % 25) == 0)
            scores = features[name].ravel()[idx[keep]]
            labels = pos[keep]
            auc = LEG.fast_mann_whitney_auc(scores, labels)
            if not np.isfinite(auc):
                raise RuntimeError(f"undefined canary {name}")
            sym = max(auc, 1.0 - auc)
            aucs.append(sym)
        mx = float(max(aucs))
        out[name] = {"max_symmetric_auc": round(mx, 5), "pass": mx <= 0.90}
        if mx > worst:
            worst = mx
            worst_name = name
    return {
        "status": "PASS" if worst <= 0.90 else "LEAKAGE_SUSPECTED",
        "max_symmetric_auc": round(worst, 5),
        "worst_feature": worst_name,
        "n_features": len(out),
        "features": out,
        "split": "vendor/gems57/spatial.folds buffer_px=80, same folds as the score",
    }


def slim_gate(gate: dict) -> dict:
    return {k: v for k, v in gate.items() if k != "comparisons"} | {
        "n_comparisons": len(gate.get("comparisons", [])),
        "closest": [
            c for c in sorted(
                gate.get("comparisons", []),
                key=lambda c: c.get("surface_abs_rank_corr") or c.get("dot_overlap_3px") or 0,
                reverse=True,
            )[:8]
        ],
    }


def main() -> int:
    t0 = time.time()
    fp, cat, crs, transform, shape = load_grid()
    log(f"grid {shape} crs {crs} footprint {int(fp.sum())} catalogue {int(cat.sum())}")
    if crs != "EPSG:32611" or transform != (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0):
        raise SystemExit("sample grid does not match the pinned EPSG:32611 transform")
    rtp = load_band(2)
    grav = load_band(13)
    depth = load_band(15)
    mag_edge = load_band(3)
    log("bands loaded")
    fields = xg91.concordance_surface(rtp, grav, fp)
    shadow, shift = xg91.updip_shadow(fields["xg_concord"], depth, fp)
    soft = xg91.deep_cover_weight(depth, fp, soft=True)
    hard = xg91.deep_cover_weight(depth, fp, soft=False)
    e2_surface = np.where(fp, shadow * soft, 0).astype(np.float32)
    e3_surface = np.where(fp, shadow * hard, 0).astype(np.float32)
    log(f"surfaces built in {time.time()-t0:.1f}s shift p50 {float(np.median(shift[fp])):.2f}")
    del rtp, grav
    method_paths = finite_registry(fp, [ROOT / "data/registry", ROOT / "docs/downloads"])
    lattice_paths = finite_registry(fp, [ROOT / "data/fleet_registry"])
    paths = method_paths + lattice_paths
    log(f"registry rasters finite inside footprint: {len(paths)} (method {len(method_paths)}, lattice {len(lattice_paths)})")
    folds = list(spatial.folds(cat, fp, buffer_px=80))
    log(f"template folds {len(folds)} truth {sum(int(f['truth'].sum()) for f in folds)}")
    features = {
        "xg_concord_s2": fields["xg_concord_s2"],
        "xg_concord_s6": fields["xg_concord_s6"],
        "xg_concord": fields["xg_concord"],
        "xg_shadow": shadow,
        "cover_weight_soft": soft,
        "mag_edge_control": np.where(fp, np.abs(xg91.fill_nearest(mag_edge, fp)), 0).astype(np.float32),
    }
    can = canary(features, folds, fp)
    log(f"canary {can['status']} max AUC {can['max_symmetric_auc']} ({can['worst_feature']})")
    if can["status"] != "PASS":
        raise SystemExit("leakage canary failed; refusing to score or write")

    experiments = []
    stopped = False
    arms = [
        ("E1", "unshifted cross-gradient crest", fields["xg_concord"], 2.8, 37654),
        ("E2", "updip shadow, soft cover weight", e2_surface, 3.0, 32000),
        ("E3", "deep-cover shadow, depth >= p75", e3_surface, 3.5, 12000),
    ]
    chosen = None
    for exp_id, mechanism, surface, spacing, budget in arms:
        if stopped:
            experiments.append({"id": exp_id, "status": "NOT_RUN", "reason": "previous arm duplicate-stopped the lane"})
            continue
        if not np.isfinite(surface[fp]).all() or float(surface[fp].max()) <= 0:
            experiments.append({"id": exp_id, "status": "NOT_RUN", "reason": "surface not finite and positive"})
            continue
        gate_s = surface_gate(surface, fp, paths)
        log(f"{exp_id} surface rho {gate_s['surface_max_abs_rank_corr']} duplicate {gate_s['is_duplicate']} closest {gate_s['surface_closest_raster']}")
        row = {"id": exp_id, "mechanism": mechanism, "spacing_px": spacing, "budget": budget,
               "surface_gate": slim_gate(gate_s)}
        if gate_s["is_duplicate"]:
            row["status"] = "DUPLICATE_STOP_SURFACE"
            experiments.append(row)
            stopped = True
            continue
        pred = emit_holdout(surface, folds, fp, cat, spacing, budget)
        # Deployment raster excludes the full public catalogue. Holdout emission
        # excludes only visible faults, so withheld traces can still be recovered.
        deploy = xg91.emit_spaced_dots(surface, fp & ~cat, spacing_px=spacing, n_dots=budget)
        deploy = np.where(fp, deploy, 0).astype(np.float32)
        gate_method = dot_gate(surface, deploy, fp, method_paths)
        gate_lattice = dot_gate(surface, deploy, fp, lattice_paths) if lattice_paths else None
        row["dot_gate_method"] = slim_gate(gate_method)
        row["dot_gate_lattice"] = None if gate_lattice is None else slim_gate(gate_lattice)
        row["deploy_dots"] = int((deploy > 0).sum())
        log(
            f"{exp_id} dots {row['deploy_dots']} method overlap {gate_method['dots_max_3px_overlap']} "
            f"lattice overlap {None if gate_lattice is None else gate_lattice['dots_max_3px_overlap']}"
        )
        if gate_method["is_duplicate"]:
            row["status"] = "DUPLICATE_STOP_DOTS"
            row["dot_gate"] = gate_method
            experiments.append(row)
            stopped = True
            continue
        if gate_lattice is not None and gate_lattice["is_duplicate"]:
            # The synthetic blanket is not another scientific lane, but the
            # literal 3 px rule fails. Log it, do not dodge it with a later arm,
            # and do not promote. The file may still be written as a negative.
            row["status"] = "DUPLICATE_CAPACITY_LATTICE"
            row["dot_gate"] = gate_lattice
            experiments.append(row)
            stopped = True
            hold = score_arm(pred, folds, fp)
            row["holdout_dti"] = hold
            log(f"{exp_id} lattice-capacity stop; HOLDOUT-DTI {hold['value']:.6f}")
            chosen = {"id": exp_id, "surface": surface, "spacing": spacing, "budget": budget,
                      "deploy": deploy, "holdout_dti": hold, "dot_gate": gate_lattice,
                      "surface_gate": gate_s, "capacity_stop": True}
            continue
        hold = score_arm(pred, folds, fp)
        row["holdout_dti"] = hold
        row["status"] = "SCORED"
        log(f"{exp_id} HOLDOUT-DTI {hold['value']:.6f} CI {hold['ci95']} n {hold['withheld_positives']}")
        if exp_id == "E1":
            ctrl = random_control(folds, fp, cat, spacing, budget, seed=91)
            row["random_control"] = score_arm(ctrl, folds, fp)
            mag = emit_holdout(features["mag_edge_control"], folds, fp, cat, spacing, budget)
            row["magnetic_edge_control"] = score_arm(mag, folds, fp)
            log(f"E1 random {row['random_control']['value']:.6f} mag-edge {row['magnetic_edge_control']['value']:.6f}")
        experiments.append(row)
        if chosen is None or hold["value"] > chosen["holdout_dti"]["value"]:
            chosen = {"id": exp_id, "surface": surface, "spacing": spacing, "budget": budget,
                      "deploy": deploy, "holdout_dti": hold, "dot_gate": gate_method,
                      "surface_gate": gate_s, "capacity_stop": False}

    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    # Persist scores before any page write so a crash cannot invent a number.
    (evidence / "xg91_experiments.json").write_text(json.dumps({
        "experiments": experiments,
        "canary": can,
        "elapsed_s": time.time() - t0,
        "prior_best_v2": PRIOR_BEST_V2,
    }, indent=2, default=str))

    if chosen is None:
        card = {
            "schema": "gems91.run-card.v2",
            "lane": {"name": "XG91", "assigned": False,
                     "reason": "Prompt omitted the method paragraph. XG91 was preregistered here and duplicate-stopped or produced no scorable unique arm."},
            "hypothesis": "Covered normal faults produce parallel RTP and isostatic-gravity gradients downdip of the buried trace.",
            "mechanism": "Gallardo-Meju cross-gradient parallelism, optional updip shadow.",
            "non_fault_mimic": "Buried volcanic-flow edge or basin onlap.",
            "experiments": [{k: v for k, v in e.items() if k != "surface"} for e in experiments],
            "canaries": can,
            "verdict": "negative",
            "ok_to_download": False,
            "ok_to_submit": False,
            "slots_used": 0,
            "organizer_confirmed": None,
            "submission_name": None,
            "note": None,
            "raster_sha256": None,
        }
        (ROOT / "docs/run-card-XG91.json").write_text(json.dumps(card, indent=2))
        log("NO UNIQUE SCORED ARM")
        return 2

    deploy = chosen["deploy"]
    if int(((deploy > 0) & cat).sum()) != 0 or not np.isfinite(deploy).all() or deploy.min() < 0 or deploy.max() > 1:
        raise SystemExit("deployment raster failed range/catalogue check before write")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    digest = hashlib.sha256(np.packbits(deploy > 0).tobytes()).hexdigest()[:8]
    name = f"gems91-xg91-{chosen['id'].lower()}-{stamp}-{digest}-zeros"
    arm = next(e["mechanism"] for e in experiments if e["id"] == chosen["id"])
    note = (
        f"XG91 {chosen['id']} {arm}; HOLDOUT-DTI see run card; research file, not slot approval"
    )[:140]
    out = ROOT / "docs/downloads" / f"{name}.tif"
    receipt = write_submission(
        out, deploy, SAMPLE, fp, note=note, name=name[:140], catalogue=cat,
        metadata={"lane": "XG91", "experiment": chosen["id"]},
    )
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    hold = chosen["holdout_dti"]
    beats = (
        hold["value"] > PRIOR_BEST_V2["value"]
        and hold["evaluator_version"] == PRIOR_BEST_V2["evaluator_version"]
        and not chosen.get("capacity_stop")
    )
    # Promotion still requires an assigned lane, a complete universal registry,
    # a paired CI against a re-scored incumbent, and a selector receipt.
    # This runner never grants those. A lattice-capacity failure is also a stop.
    ok_submit = False
    card = {
        "schema": "gems91.run-card.v2",
        "lane": {
            "name": "XG91",
            "assigned": False,
            "method_paragraph": (
                "Cross-gradient parallelism of sponsor RTP (band 2) and isostatic gravity "
                "(band 13) at 200 m and 600 m, sampled up-dip along the basement-depth "
                "gradient (band 15) by clip(H*cot(55 deg)/100 m, 2, 8) px; unit dots, "
                "exact catalogue pixels excluded."
            ),
            "reason": "The prompt's assigned method paragraph was absent. This paragraph was preregistered in docs/HYPOTHESES_XG91.md before scoring. assigned=false so readiness cannot treat it as an orchestrated lane.",
        },
        "hypothesis": "A covered Basin-and-Range normal fault juxtaposes susceptibility and density downdip of the buried surface trace, which the USGS/INGENIOUS catalogue often misses.",
        "mechanism": chosen["id"] + ": " + next(e["mechanism"] for e in experiments if e["id"] == chosen["id"]),
        "non_fault_mimic": "Buried volcanic-flow edge or sedimentary basin onlap that aligns magnetic and gravity gradients without fault offset.",
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "status": "COMPLETED",
            "evaluator_version": hold["evaluator_version"],
            "withheld_positives": hold["withheld_positives"],
            "value": hold["value"],
            "ci95": hold["ci95"],
            "tpw": hold["tpw"],
            "fpw": hold["fpw"],
            "fnw": hold["fnw"],
            "folds": hold["folds"],
        },
        "comparable_prior_holdout_best": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": PRIOR_BEST_V2["evaluator_version"],
            "value": PRIOR_BEST_V2["value"],
            "source": PRIOR_BEST_V2["source"],
            "same_split_recomputed_here": False,
            "note": PRIOR_BEST_V2["note"],
        },
        "beats_recorded_v2_point_estimate": beats,
        "canaries": can,
        "registry_comparison": {
            "complete_universal_registry": False,
            "scope": "finite single-band rasters in data/registry, data/fleet_registry (includes the synthetic 5 px lattice), and docs/downloads",
            "n_checked": chosen["surface_gate"]["n_registry_rasters_checked"],
            "preplacement": {
                "status": "PASS_WITHIN_INDEXED_SCOPE" if chosen["surface_gate"]["uniqueness_pass"] else "DUPLICATE",
                "max_abs_spearman": chosen["surface_gate"]["surface_max_abs_rank_corr"],
                "closest": chosen["surface_gate"]["surface_closest_raster"],
            },
            "final": {
                "status": "PASS_WITHIN_INDEXED_SCOPE" if chosen["dot_gate"]["uniqueness_pass"] else "DUPLICATE",
                "max_abs_spearman": chosen["dot_gate"].get("dots_max_abs_rank_corr"),
                "max_3px_overlap": chosen["dot_gate"]["dots_max_3px_overlap"],
                "closest": chosen["dot_gate"]["dots_closest_raster"],
            },
        },
        "experiments": experiments,
        "raster_sha256": sha,
        "raster_path": str(out.relative_to(ROOT)),
        "validator_output": receipt["validator"],
        "submission_name": name[:140],
        "note": note,
        "artifact": {
            "file": f"downloads/{name}.tif",
            "zip": f"downloads/{name}.zip",
            "receipt": f"downloads/{name}.json",
            "bytes": out.stat().st_size,
            "dots": int((deploy > 0).sum()),
        },
        "ok_to_download": True,
        "ok_to_submit": ok_submit,
        "verdict": "negative",
        "capacity_stop_synthetic_lattice": bool(chosen.get("capacity_stop")),
        "negative_reason": (
            "NOT OK TO SUBMIT. "
            + (
                "Literal 3 px overlap with the synthetic blanket lattice exceeds 70 percent; logged as a capacity duplicate and not promoted. "
                if chosen.get("capacity_stop") else
                "Indexed-registry uniqueness passed, but that scope is not a universal registry. "
            )
            + "Lane was not assigned by the prompt; the recorded v2 incumbent was not re-scored on this split; no selector receipt; weekly slot not spent."
            + ("" if beats else " Point estimate does not exceed the recorded gems57-pooled-hide-v2 best.")
        ),
        "slots_used": 0,
        "organizer_confirmed": None,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (ROOT / "docs/run-card-XG91.json").write_text(json.dumps(card, indent=2, default=str))
    log(json.dumps({"name": name, "sha": sha, "dti": hold["value"], "ci": hold["ci95"],
                    "dots": card["artifact"]["dots"], "beats_v2_point": beats, "ok_to_submit": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
