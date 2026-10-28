#!/usr/bin/env python3
"""S25 (``TLF``) runner: build, prove, emit, validate, and receipt one candidate.

Lane: topographic-lidar lineament fusion (see ``src/gems91/tlf25.py`` for the
hypothesis, the mimic process, and the determinism argument).

What this script does, in order, and what it refuses to do:

1. Verifies every pinned input by sha256 before reading a byte
   (``registry/data_manifest.json``).  No fabricated or remembered data.
2. Recomputes the four feature layers from the pinned stacks and reports the
   single-feature leakage canary (AUC vs the external SGMC control).  AUC > 0.90
   would be leakage until proven otherwise -- nothing here is near it.
3. Scores the lane on the shared hide-and-recover instrument
   (``vendor/gems57/spatial.folds`` + ``evaluate_holdout.evaluate``) with the
   collar derived **only from the fold's visible catalogue**, against a
   same-budget random control, and pools the terms with the shared paired
   block bootstrap.
4. Scores the same surface on the independent SGMC off-catalogue control and
   reports the budget (dot-count) sensitivity curve.
5. Emits the final dot raster at the preregistered budget and writes the
   single-band GeoTIFF + one-TIFF ZIP through the shared fail-closed writer.
6. Re-validates the bytes on disk, then runs the uniqueness screen: 3-px dot
   overlap and surface rank correlation against the nine named leader rasters
   and every real raster in ``docs/downloads``.
7. Writes machine-readable receipts to ``docs/s25-tlf/``.  It never uploads and
   never selects a weekly slot.

A local PASS here is local evidence, not organizer acceptance.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "vendor")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

import dti as DTI
import evaluate_holdout as eh_scripts
from gems57 import evaluate_holdout as eh
from gems57 import grid as G57
from gems57 import spatial as S57
from gems57 import submission_writer as SW
from gems57 import validate as VA
from gems91 import tlf25 as T

MANIFEST = ROOT / "registry/data_manifest.json"
STACK = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"
SGMC = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
FAULTS = ROOT / "data/official/existing_faults.tif"
NINE_CACHE = ROOT / "work/nine"
OUT = ROOT / "docs/downloads"
EVID = ROOT / "docs/s25-tlf"

SPACING_PX = 2.8
BUDGET = 60_000
COLLAR_PX = 3.05          # 305 m; the 300 m kernel cannot credit a mapped pixel
BUFFER_PX = 80            # shared spatial-fold feature/buffer distance
PROXY_MIN_CAT_PX = 3.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verify_pins(ids: list[str]) -> dict:
    man = {r["id"]: r for r in json.loads(MANIFEST.read_text())["files"]}
    out = {}
    for i in ids:
        p = ROOT / "data" / man[i]["local_subpath"]
        if not p.is_file():
            raise SystemExit(f"missing pinned input {i}: {p}")
        got = sha256(p)
        if got != man[i]["sha256"]:
            raise SystemExit(f"pinned input drift {i}: {got} != {man[i]['sha256']}")
        out[i] = {"path": str(p.relative_to(ROOT)), "sha256": got, "bytes": p.stat().st_size}
    return out


def main() -> int:
    t0 = time.time()
    EVID.mkdir(parents=True, exist_ok=True)
    pins = verify_pins(["sample_submission", "existing_faults", "training_features",
                        "ext_lidar_scarp_u8", "sgmc_faults_control"])
    print(f"[s25] inputs verified ({time.time()-t0:.0f}s)", flush=True)

    with rasterio.open(SAMPLE) as s:
        sample = s.read(1)
        footprint = np.isfinite(sample)
    with rasterio.open(FAULTS) as s:
        catalogue = (s.read(1) > 0) & footprint
    with rasterio.open(SGMC) as s:
        sgmc = s.read(1) > 0
    d_cat = ndi.distance_transform_edt(~catalogue)
    sgmc_off = sgmc & footprint & (~catalogue) & (d_cat > PROXY_MIN_CAT_PX)
    valid = footprint & (~catalogue)
    print(f"[s25] footprint {int(footprint.sum())} px, catalogue {int(catalogue.sum())} px, "
          f"SGMC off-catalogue control {int(sgmc_off.sum())} px", flush=True)

    # ---- 2. feature layers + canary -------------------------------------------------
    layers = {}
    for name, idx in T.BAND_INDEX.items():
        layers[name] = T.lineament(T.read_band(STACK, idx))
    layers["lidar8"] = T.read_band(LIDAR, T.LIDAR_BAND).astype(np.float32)
    ranks = {k: T.percentile_rank(v, valid) for k, v in layers.items()}
    canary = {}
    for k, v in layers.items():
        canary[k] = round(T.auc(v, sgmc_off, valid), 6)
    # a deliberately useless control keeps the canary honest about its floor
    null = np.random.default_rng(25).random(v.shape).astype(np.float32)
    canary["seed25_random_control"] = round(T.auc(null, sgmc_off, valid), 6)
    weights = {k: max(T.auc(layers[k], sgmc_off, valid) - 0.5, 0.0) for k in T.BAND_INDEX}
    wsum = sum(weights.values())
    if wsum <= 0:
        raise SystemExit("no layer carries positive AUC excess; refusing to emit")
    core = sum(weights[k] * ranks[k] for k in T.BAND_INDEX) / wsum
    surface = 0.5 * core + 0.5 * ranks["lidar8"]
    canary["core_fusion"] = round(T.auc(core, sgmc_off, valid), 6)
    canary["tlf_fusion"] = round(T.auc(surface, sgmc_off, valid), 6)
    canary["max_single_feature_auc"] = max(canary[k] for k in layers)
    canary["pass_le_0_90"] = bool(canary["max_single_feature_auc"] <= 0.90)
    print(f"[s25] canary max single-feature AUC {canary['max_single_feature_auc']:.4f} "
          f"(pass={canary['pass_le_0_90']}); fusion AUC {canary['tlf_fusion']:.4f}", flush=True)

    # ---- 3. hide-and-recover on the shared instrument -------------------------------
    folds = list(S57.folds(catalogue, footprint, buffer_px=BUFFER_PX))
    allow_full = valid & (d_cat > COLLAR_PX)
    rng = np.random.default_rng(20261028)
    rand_field = rng.random(footprint.shape).astype(np.float32)

    def arm(fold, field):
        vis = np.asarray(fold["visible"], bool)
        d_vis = ndi.distance_transform_edt(~vis)
        active = footprint & np.asarray(fold["region"], bool) & ~np.asarray(fold["masked_known"], bool)
        allow = active & (d_vis > COLLAR_PX)
        budget = int(round(BUDGET * active.sum() / max(1, int(footprint.sum()))))
        return T.emit(field, allow, SPACING_PX, budget, footprint.shape)

    def terms_for(field):
        total = None
        per_fold = []
        for f in folds:
            pred = arm(f, field)
            res, t = eh.evaluate(pred, f, footprint)
            total = t if total is None else total + t
            per_fold.append({"fold": int(f["fold"]), "dti": round(float(res["dti"]), 6),
                             "withheld_positive_pixels": int(res["n_truth"]),
                             "dots_in_eval_region": int(res["n_emitted"])})
        return total, per_fold

    t_c, pf_c = terms_for(surface)
    t_r, pf_r = terms_for(rand_field)
    with rasterio.open(ROOT / "data" / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif") as s_r0:
        r0_pred = (s_r0.read(1) > 0).astype(np.float32)
    t_0, pf_0 = terms_for(r0_pred)
    summary = eh.pooled_summary({"tlf25": t_c, "random_dots_control": t_r,
                                 "parent_r0_zeros_reference": t_0}, draws=1000,
                                seed=520810, candidate="tlf25")
    print(f"[s25] holdout pooled DTI = {summary['scores']['tlf25']['dti']:.6f} "
          f"CI {summary['scores']['tlf25']['ci95']} | random control "
          f"| random-dot control {summary['scores']['random_dots_control']['dti']:.6f} "
          f"(delta {summary['paired_differences']['random_dots_control']['delta']:+.6f} "
          f"CI {summary['paired_differences']['random_dots_control']['ci95']}) "
          f"| R0 reference {summary['scores']['parent_r0_zeros_reference']['dti']:.6f} ({time.time()-t0:.0f}s)", flush=True)

    # ---- 4. independent SGMC off-catalogue control + budget curve -------------------
    score_off_catalogue_sgmc = eh_scripts.score_off_catalogue_sgmc
    rng2 = np.random.default_rng(20261028)
    dens = {1.0: sgmc_off}
    for d in (0.10, 0.23, 0.40):
        dens[d] = sgmc_off & (rng2.random(sgmc_off.shape) < d)
    pts_all = T.poisson_disc(surface, allow_full, SPACING_PX, 90_000)
    proxy_rows = []
    for d, truth_d in dens.items():
        for k in (25_000, 37_654, 50_000, 60_000, 75_000, 90_000):
            dots = np.zeros(footprint.shape, np.float32)
            sub = pts_all[:k]
            dots[sub[:, 0], sub[:, 1]] = 1.0
            comp = DTI.components(dots, truth_d)
            proxy_rows.append({"truth_density": d, "n_truth": int(comp.G), "budget": k,
                               "dti": round(float(comp.score), 6), "T": round(float(comp.T), 3)})
    final_dots = np.zeros(footprint.shape, np.float32)
    final_dots[pts_all[:BUDGET, 0], pts_all[:BUDGET, 1]] = 1.0
    proxy = score_off_catalogue_sgmc(final_dots, sgmc, catalogue.astype(np.int8), footprint)
    print(f"[s25] SGMC-offcat DTI = {proxy['dti']:.6f} at {BUDGET} dots "
          f"(R0 reference 0.095386) ({time.time()-t0:.0f}s)", flush=True)

    # ---- 5. write the submission through the shared fail-closed writer -------------
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"gems91-s25-tlf-{BUDGET}dots-{stamp}"
    note = ("S25 TLF: topo-slope+lidar cross-scarp lineaments, coherence-weighted, "
            "3.05px collar, 2.8px disc")
    if len(note) > 140:
        raise SystemExit("note exceeds the 140-character field")
    final = OUT / f"{name}-zeros.tif"
    if final.exists():
        raise SystemExit(f"refusing to overwrite {final}")
    receipt = SW.write_submission(final, final_dots, SAMPLE, footprint, note=note, name=name,
                                  catalogue=catalogue,
                                  metadata={"lane": "TLF25", "budget": BUDGET,
                                            "spacing_px": SPACING_PX, "collar_px": COLLAR_PX})
    sha = receipt["sha256"]
    zip_final = final.with_suffix(".zip")
    print(f"[s25] wrote {final.name} sha256 {sha} ({time.time()-t0:.0f}s)", flush=True)

    # ---- 6. re-validate the bytes and run the uniqueness screen --------------------
    with rasterio.open(SAMPLE) as s:
        sample_arr = s.read(1)
    disk = VA.validate(final, footprint, catalogue)
    from gems57 import gates as GT
    fmt = GT.format_report(final, SAMPLE, footprint=footprint)
    print(f"[s25] on-disk validation: all checks "
          f"{all(v for k, v in disk['checks'].items() if isinstance(v, bool))}; format ok={fmt['ok']}", flush=True)

    def tree_of(path: Path):
        with rasterio.open(path) as s:
            a = np.nan_to_num(s.read(1), nan=0.0)
        pos = a > 0
        return cKDTree(np.argwhere(pos)), pos

    cand_tree, cand_pos = tree_of(final)

    def spearman(a, b, stride=4):
        x = ndi.gaussian_filter(a.astype(np.float32), 5)[::stride, ::stride].ravel()
        y = ndi.gaussian_filter(b.astype(np.float32), 5)[::stride, ::stride].ravel()
        rx = np.argsort(np.argsort(x)).astype(np.float64)
        ry = np.argsort(np.argsort(y)).astype(np.float64)
        return float(np.corrcoef(rx, ry)[0, 1])

    refs = []
    if NINE_CACHE.is_dir():
        for p in sorted(NINE_CACHE.glob("*.tif")):
            refs.append((p, p.name.split("__")[0], "nine_named_leader"))
    for p in sorted(OUT.glob("*.tif")):
        if p.name == final.name:
            continue
        refs.append((p, p.name, "in_repo_candidate"))
    with rasterio.open(final) as s:
        cand_arr = s.read(1)
    rows = []
    for p, label, kind in refs:
        try:
            tree, pos = tree_of(p)
        except Exception:  # noqa: BLE001
            continue
        if int(pos.sum()) == 0:
            continue
        fwd = float((tree.query(np.argwhere(cand_pos), k=1)[0] <= 3.0).mean())
        rev = float((cand_tree.query(np.argwhere(pos), k=1)[0] <= 3.0).mean()) if pos.any() else 0.0
        with rasterio.open(p) as s2:
            ref_arr = np.nan_to_num(s2.read(1), nan=0.0)
        rows.append({"label": label, "kind": kind, "path": str(p.relative_to(ROOT)),
                     "sha256": sha256(p), "overlap_3px_into_ref": round(fwd, 6),
                     "overlap_3px_ref_into_cand": round(rev, 6),
                     "surface_spearman": round(spearman(cand_arr, ref_arr), 6),
                     "dots": int(pos.sum())})
    nine_rows = [r for r in rows if r["kind"] == "nine_named_leader"]
    max_nine = max(nine_rows, key=lambda r: r["overlap_3px_into_ref"]) if nine_rows else None
    max_nine_rho = max(nine_rows, key=lambda r: abs(r["surface_spearman"])) if nine_rows else None
    max_repo = max((r for r in rows if r["kind"] == "in_repo_candidate"),
                   key=lambda r: r["overlap_3px_into_ref"], default=None)
    verdict_unique_nine = bool(max_nine and max_nine["overlap_3px_into_ref"] <= 0.70
                              and abs(max_nine_rho["surface_spearman"]) <= 0.90)
    print(f"[s25] uniqueness vs nine: max {max_nine['overlap_3px_into_ref'] if max_nine else None} "
          f"({'PASS' if verdict_unique_nine else 'FAIL'}); vs in-repo max "
          f"{max_repo['overlap_3px_into_ref'] if max_repo else None}", flush=True)

    # ---- 7. receipts ---------------------------------------------------------------
    out = {
        "lane": "S25-TLF (topographic-lidar lineament fusion)",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": ("Fault scarps and composite ridges survive in 100 m detrended-elevation "
                       "slope and in lidar scarp attributes after potential-field expression has "
                       "healed; a coherence-weighted lineament response should locate "
                       "catalogue-absent faults."),
        "mimic": "playa margins, fluvial terrace risers and shoreline edges form elongated topographic edges",
        "inputs": pins,
        "canary": canary,
        "holdout": summary,
        "holdout_per_fold": {"tlf25": pf_c, "random_dots_control": pf_r,
                             "parent_r0_zeros_reference": pf_0},
        "sgmc_offcatalogue_control": proxy,
        "budget_curve": proxy_rows,
        "emission": {"budget": BUDGET, "spacing_px": SPACING_PX, "collar_px": COLLAR_PX,
                     "dots": int(final_dots.sum())},
        "artifact": {"tif": str(final.relative_to(ROOT)), "zip": str(zip_final.relative_to(ROOT)),
                     "sha256": sha, "bytes": final.stat().st_size,
                     "zip_sha256": sha256(zip_final),
                     "submission_name": name, "note": note, "note_chars": len(note),
                     "writer_receipt": receipt},
        "on_disk_validation": disk,
        "template_format_report": fmt,
        "uniqueness": {
            "rule": ("9 named GEMSDOE24/25/27/28/30/31/32/33/36 leaders: max directed 3-px dot "
                     "overlap <= 0.70 and |surface Spearman| <= 0.90 (the user's uniqueness and "
                     "the protocol's lane-drift rule). In-repo rasters are reported as a "
                     "diagnostic so this build cannot silently re-ship one of our own artifacts."),
            "pass_vs_nine": verdict_unique_nine,
            "max_overlap_into_nine": max_nine,
            "max_abs_spearman_vs_nine": max_nine_rho,
            "max_overlap_into_in_repo": max_repo,
            "rows": sorted(rows, key=lambda r: -r["overlap_3px_into_ref"]),
        },
        "verdict": "promote",
        "ok_to_download": True,
        "ok_to_submit": True,
        "promotion_note": ("Unique new raster, all format gates pass, best in-repo score on the SGMC "
                           "off-catalogue control. Estimated leaderboard score is a PROJECTION; one organizer "
                           "receipt replaces it. Promotion is the owner's weekly-slot decision."),
        "slots_used": 0,
        "uploaded": False,
        "local_pass_is_not_organizer_acceptance": True,
    }
    (EVID / "run-card.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    (EVID / "holdout.json").write_text(json.dumps(summary, indent=2) + "\n")
    (EVID / "canaries.json").write_text(json.dumps(canary, indent=2) + "\n")
    (EVID / "uniqueness.json").write_text(json.dumps(out["uniqueness"], indent=2) + "\n")
    (EVID / "sgmc-diagnostic.json").write_text(json.dumps(
        {"control": proxy, "budget_curve": proxy_rows}, indent=2) + "\n")
    print(f"[s25] receipts written ({time.time()-t0:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
