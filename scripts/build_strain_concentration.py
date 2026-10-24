#!/usr/bin/env python3
"""CONCENTRATION axis on R0: geodetic-strain km-scale prior (Session 8).

Implements the GEODETIC-STRAIN CONCENTRATION axis pre-proposed in the merged
`SLOT_PLAN.md` (Sessions 5-7, better-axis #1) and frozen in
`registry/strain_concentration_preregistration.json` before any candidate was
built or scored by any instrument.

Parent R0 = `h33-h33-2-b2` (GEMSDOE32), 37,654 unit-mass dots, sha256
`baeae321...` (NaN) / `c55bafc4...` (zeros), claimed 0.2778 = CLAIM (no receipt).

What is identical to the GDR thermal arms (so the comparison isolates the prior)
---------------------------------------------------------------------------------
* the same builder, `tools.run_concentration.build_concentration`;
* count fixed at 37,654, unit mass, 25 px (2.5 km) blocks, lowest/highest 30%
  of blocks, seed 91025, anchor+jitter acceptor placement, min separation 2 px,
  acceptor targets strictly > 3.0 px from the catalogue.

What differs, deliberately and recorded
---------------------------------------
1. **Prior source**: sponsor GeoDAWN geodetic bands only (pinned
   `training_features`), percentile-ranked - `src/gems91/strain.py`.
   The strain prior is near-orthogonal to the GDR prior at block scale
   (Spearman 0.075 measured before build).
2. **Donor quarantine (IR-91-42)**: R0's 2,171 inherited dots at d_cat<=3 px
   cannot be donors (IR-91-27 standard).  The GDR build let collar dots move,
   mixing a partial PRUNE into its CONCENTRATION edit; this build does not.
   Consequence: the catalogue hide-and-recover PROXY is invariant by
   construction (IR-91-28 applies) and is reported as such.

Arms (one experiment; spend at most one slot on it)
---------------------------------------------------
strn25m10  strain prior (0.5*pct band4 + 0.5*pct band7), 10% moved
strn25m20  same prior, 20% moved (the pre-proposal's falsifier dose)
strd25m10  dilatation prior (pct band8), 10% moved (extensional component)

No 50 px scale arm and no single-band-4/7 arm: block ranks at 25 vs 50 px
correlate 0.999 and bands 4/7 correlate 0.949, so either would re-run the same
experiment under a new id (measured before build; preregistration).

Predictions are the frozen translator of the preregistration (SGMC off-
catalogue relative-T, SNAP's SHRINK=0.5), never hand-picked after instruments.

Usage
-----
    python3 scripts/restore_data.py
    python3 scripts/build_strain_concentration.py --build
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import validate_raster as vr_mod  # noqa: E402
from gems91 import geom, io, prior as priors, proxy, release_gates as gates, relief, strain  # noqa: E402
from tools import raster_io, run_concentration  # noqa: E402

MANIFEST_PATH = ROOT / "registry" / "data_manifest.json"
DATA = ROOT / "data"

PARENT_TAG = "h33-h33-2-b2"
PARENT_DOTS = 37654
PARENT_DIGEST = "905cee9d4383de23d6ee6366da4627fe19a78e4f49ce3a2462a8736e9b66a027"
BUILD_DATE = "20261024"  # pinned, never datetime.now (IR-91-32)
LEDGER_DATE = "2026-10-24"
CLAIMED_LIVE = 0.2778  # CLAIM; scale of the MODEL translator only
SHRINK = 0.5           # identical to build_snap.py's surrogate-to-live shrink
SEED = 91025           # identical to the GDR concentration build
BLOCK_PX = 25
MIN_GAP_PX = 3.0
MIN_SEP_PX = 2.0
SOURCE = "SESSION 8 (arena/6f079276-gemsdoe91)"

REQUIRED_PINS = (
    "sample_submission",
    "existing_faults",
    "training_features",
    "parent_r0_zeros",
    "parent_r0_nan",
    "anc_h19_5",
    "anc_d2_8",
    "anc_solo_d2_8",
    "sgmc_faults_control",
)

ARMS = {
    "strn25m10": dict(prior="strain", frac=0.10, label="strain 10%"),
    "strn25m20": dict(prior="strain", frac=0.20, label="strain 20%"),
    "strd25m10": dict(prior="dilatation", frac=0.10, label="dilatation 10%"),
}


def verify_pinned_inputs() -> dict[str, Path]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in manifest["files"]}
    paths: dict[str, Path] = {}
    for fid in REQUIRED_PINS:
        entry = by_id[fid]
        p = DATA / entry["local_subpath"]
        if not p.is_file():
            raise SystemExit(f"STOP: missing pinned input {fid} at {p}; run scripts/restore_data.py")
        digest, size = io.sha256_file(p), p.stat().st_size
        if digest != entry["sha256"] or size != entry["bytes"]:
            raise SystemExit(
                f"STOP: pin mismatch on {fid}: got {digest} ({size} B), "
                f"expected {entry['sha256']} ({entry['bytes']} B)")
        paths[fid] = p
    return paths


def verify_parent_lineage(paths: dict[str, Path], cat: np.ndarray, dcat: np.ndarray) -> dict:
    parent_nan = io.dot_mask(io.read_grid(paths["parent_r0_nan"]))
    parent_zeros = io.dot_mask(io.read_grid(paths["parent_r0_zeros"]))
    out = {
        "parent_sha256_nan": io.sha256_file(paths["parent_r0_nan"]),
        "parent_sha256_zeros": io.sha256_file(paths["parent_r0_zeros"]),
        "parent_dot_digest": io.dot_digest(parent_nan),
        "n_dots": int(parent_nan.sum()),
        "twins_identical": bool(np.array_equal(parent_nan, parent_zeros)),
        "dots_on_catalogue": int((parent_nan & cat).sum()),
        "min_catalogue_distance_px": round(float(dcat[parent_nan].min()), 6),
        "collar_2_to_3px": int((parent_nan & (dcat > 2.0) & (dcat <= 3.0)).sum()),
        "rebuilt_from": {},
    }
    for name, key in (("d2.8", "anc_d2_8"), ("solo_d2.8", "anc_solo_d2_8")):
        anc = io.dot_mask(io.read_grid(paths[key]))
        kept = anc & (dcat > geom.CATALOGUE_FLOOR_PX)
        out["rebuilt_from"][name] = {
            "n_ancestor_dots": int(anc.sum()),
            "n_after_collar": int(kept.sum()),
            "identical_to_parent": bool(np.array_equal(kept, parent_nan)),
        }
    if not (out["twins_identical"] and out["n_dots"] == PARENT_DOTS
            and out["parent_dot_digest"] == PARENT_DIGEST
            and out["dots_on_catalogue"] == 0 and out["collar_2_to_3px"] == 2171
            and all(v["identical_to_parent"] for v in out["rebuilt_from"].values())):
        raise SystemExit(f"STOP: parent R0 verification failed (brief section 5): {out}")
    return out


def check_derived_digest(kind: str, digest: str) -> None:
    """Refuse a derived prior that does not match its registry pin (if pinned)."""
    reg = ROOT / "registry" / "derived_priors.json"
    if not reg.is_file():
        return
    for entry in json.loads(reg.read_text(encoding="utf-8")).get("strain_priors", []):
        if entry.get("kind") == kind and entry.get("array_digest") != digest:
            raise SystemExit(
                f"STOP: derived {kind} prior digest {digest} != pinned "
                f"{entry.get('array_digest')} - the input or derivation changed")


def band_canary(feat_path: Path, footprint: np.ndarray, cat: np.ndarray,
                bands: tuple[int, ...] = (4, 7, 8), stride: int = 25) -> dict:
    """Single-feature leakage canary for the bands this build reads (>0.90 => stop)."""
    labels = cat[footprint][::stride].astype(np.float64)
    out: dict[str, dict] = {}
    with rasterio.open(str(feat_path)) as src:
        names = {b: (src.descriptions[b - 1] or f"band_{b}").split(" - ")[0] for b in bands}
        for b in bands:
            vals = src.read(b)[footprint][::stride].astype(np.float64)
            ok = np.isfinite(vals) & (vals > strain.SENTINEL_MAX)
            raw = float(proxy._auc(vals[ok], labels[ok]))
            out[names[b]] = {"signed_auc": round(raw, 4),
                             "symmetric_auc": round(max(raw, 1.0 - raw), 4)}
    worst = max(v["symmetric_auc"] for v in out.values())
    if worst > 0.90:
        raise SystemExit(f"STOP: leakage canary AUC {worst} > 0.90: {out}")
    return {"bands": out, "max_symmetric_auc": worst, "stop_threshold": 0.90,
            "stride": stride, "n_sampled_px": int(len(labels))}


def decile_catalogue_rates(prior_arr: np.ndarray, footprint: np.ndarray, cat: np.ndarray) -> list[float]:
    """Descriptive only: catalogue pixel rate (%) by prior decile, low -> high."""
    vals = prior_arr[footprint]
    edges = np.quantile(vals, np.linspace(0, 1, 11))
    rates = []
    for i in range(10):
        hi_ok = prior_arr <= edges[i + 1] if i == 9 else prior_arr < edges[i + 1]
        m = footprint & (prior_arr >= edges[i]) & hi_ok
        rates.append(round(float(cat[m].mean() * 100.0), 4) if m.any() else None)
    return rates


def frozen_prediction(rel_t: float, delta_noise: float, delta_mask: float) -> tuple[float, list[float]]:
    """The preregistered translator. Nothing here is fitted to a receipt (none exists)."""
    point = round(CLAIMED_LIVE * rel_t * SHRINK, 4)
    unshrunk = CLAIMED_LIVE * rel_t
    hi = unshrunk if rel_t > 0 else CLAIMED_LIVE * rel_t * 0.25
    lowers = [delta_noise, delta_mask] + ([unshrunk] if rel_t < 0 else [])
    lo = round(min(min(lowers), point), 3)
    hi = round(max(hi, point), 3)
    return point, [lo, hi]


def update_release_manifest(new_entries: list[dict]) -> None:
    manifest_p = ROOT / "releases" / "MANIFEST.json"
    existing = {}
    if manifest_p.is_file():
        for f in json.loads(manifest_p.read_text(encoding="utf-8")).get("files", []):
            existing[f["file"]] = f
    for f in new_entries:
        existing[f["file"]] = f
    payload = {
        "schema_version": 1,
        "generated_utc": "2026-10-24T00:00:00Z",
        "note": ("Releases are NOT committed (this repo does not publish derived copies of "
                 "competition rasters). These hashes are the contract: rebuild with "
                 "`python3 scripts/restore_data.py` plus the session builder named for each "
                 "family (build_spacing / build_prune_ladder / build_concentration / "
                 "build_mass_consensus / build_relief / build_snap / build_trackb / "
                 "build_strain_concentration) and every sha256 below must reappear byte "
                 "for byte. CI enforces this."),
        "parent": "h33-h33-2-b2 (e5eb6e7e)",
        "files": [existing[k] for k in sorted(existing)],
    }
    manifest_p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_ledger_rows(rows: list[dict]) -> int:
    ledger = ROOT / "ledger" / "submissions.csv"
    existing: list[dict] = []
    newline = "\n"
    if ledger.is_file():
        raw = ledger.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            existing = list(csv.DictReader(fh))
    fieldnames = list(existing[0].keys()) if existing else list(rows[0].keys())
    by_id = {r["id"]: i for i, r in enumerate(existing)}
    seen_hash = {(r.get("sha256") or ""): r["id"] for r in existing}
    seen_triple = {(r.get("parent"), r.get("axis"), r.get("value")): r["id"] for r in existing}
    added = 0
    for r in rows:
        if seen_hash.get(r["sha256"], r["id"]) != r["id"]:
            raise SystemExit(f"STOP: sha256 already in ledger under {seen_hash[r['sha256']]}")
        triple = (r["parent"], r["axis"], r["value"])
        if seen_triple.get(triple, r["id"]) != r["id"]:
            raise SystemExit(f"STOP: (parent,axis,value) already built as {seen_triple[triple]}")
        formatted = {k: str(r.get(k, "")) for k in fieldnames}
        if r["id"] in by_id:
            if existing[by_id[r["id"]]].get("sha256") != r["sha256"]:
                raise SystemExit(f"STOP: rebuild of {r['id']} changed sha256 (non-deterministic)")
            existing[by_id[r["id"]]] = formatted
        else:
            existing.append(formatted)
            added += 1
    with ledger.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator=newline)
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return added


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args(argv)
    if not args.build:
        print(__doc__)
        return 0

    paths = verify_pinned_inputs()
    template = io.read_grid(paths["sample_submission"])
    footprint = geom.footprint_mask(template)
    cat = geom.catalogue_mask(io.read_grid(paths["existing_faults"]))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(paths["parent_r0_nan"]))
    lineage = verify_parent_lineage(paths, cat, dcat)

    # Leakage canary before any build (brief section 6: report-only, but >0.90 stops).
    canary = band_canary(paths["training_features"], footprint, cat)

    # Derived priors from the pinned stack alone.
    with rasterio.open(str(paths["training_features"])) as src:
        b4, b7, b8 = src.read(4), src.read(7), src.read(8)
        band_names = {int(b): src.descriptions[b - 1] for b in (4, 7, 8)}
    strain_arr, strain_stats = strain.strain_prior(b4, b7, footprint)
    dil_arr, dil_stats = strain.dilatation_prior(b8, footprint)
    prior_arrays = {"strain": strain_arr, "dilatation": dil_arr}
    prior_info = {}
    for kind, arr, st in (("strain", strain_arr, strain_stats), ("dilatation", dil_arr, dil_stats)):
        digest = priors.array_digest(arr)
        check_derived_digest(kind, digest)
        prior_info[kind] = {
            "array_digest": digest, "band_stats": st, "bands": band_names,
            "catalogue_rate_pct_by_prior_decile": decile_catalogue_rates(arr, footprint, cat),
        }
    prior_info["spearman_strain_vs_dilatation"] = round(
        float(spearmanr(strain_arr[footprint], dil_arr[footprint]).statistic), 4)

    # Report-only truth surrogates (identical definitions to SNAP / GDR sessions).
    with rasterio.open(str(paths["sgmc_faults_control"])) as src:
        sgmc_off = (src.read(1) > 0) & footprint & (dcat > 3.0)
    d_sgmc = ndi.distance_transform_edt(~sgmc_off)
    r0_sgmc = relief.fast_binary_dti(parent, sgmc_off, d_truth=d_sgmc)
    lineage_mask = io.dot_mask(io.read_grid(paths["anc_h19_5"])) & footprint
    d_h19 = ndi.distance_transform_edt(~lineage_mask)
    r0_h19 = relief.fast_binary_dti(parent, lineage_mask, d_truth=d_h19)
    rng_t = np.random.default_rng(SEED)
    n_noise = int(sgmc_off.sum())
    flat_idx = rng_t.choice(int(footprint.sum()), size=n_noise, replace=False)
    fr, fc = np.nonzero(footprint)
    noise_truth = np.zeros(footprint.shape, dtype=bool)
    noise_truth[fr[flat_idx], fc[flat_idx]] = True
    d_noise = ndi.distance_transform_edt(~noise_truth)
    r0_noise = relief.fast_binary_dti(parent, noise_truth, d_truth=d_noise)
    r0_hr = proxy.hide_and_recover(parent, cat, footprint)

    parent_band = np.where(footprint, parent.astype(np.float32), np.float32(0.0))
    donor_exclude = dcat <= MIN_GAP_PX
    releases_dir = ROOT / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)

    built: dict[str, dict] = {}
    manifest_entries: list[dict] = []
    ledger_rows: list[dict] = []

    for key, cfg in ARMS.items():
        arr_prior = prior_arrays[cfg["prior"]]
        band, stats = run_concentration.build_concentration(
            parent_band, arr_prior, footprint, cat, frac=cfg["frac"], block_px=BLOCK_PX,
            min_gap_px=MIN_GAP_PX, seed=SEED, min_sep_px=MIN_SEP_PX,
            donor_exclude=donor_exclude)
        dots = io.dot_mask(band)
        n_target = int(round(cfg["frac"] * PARENT_DOTS))
        if not stats["count_preserved"] or int(dots.sum()) != PARENT_DOTS:
            raise SystemExit(f"STOP: {key} changed the dot count: {stats}")
        if stats["n_dots_moved"] != n_target:
            raise SystemExit(f"STOP: {key} moved {stats['n_dots_moved']} != target {n_target} (dose not delivered)")
        if not (1.0 <= stats["pct_dots_moved"] <= 50.0):
            raise SystemExit(f"STOP: {key} pct moved outside the brief's 1-50% band: {stats['pct_dots_moved']}")
        collar_after = int(((dcat <= 3.0) & dots).sum())
        added = dots & ~parent
        if collar_after != 2171 or int(((dcat <= 3.0) & added).sum()) != 0:
            raise SystemExit(f"STOP: {key} broke the collar quarantine (IR-91-27): collar={collar_after}")
        if int((dots & cat).sum()) != 0:
            raise SystemExit(f"STOP: {key} emits mass on the catalogue")
        diff = gates.parent_diff(parent, dots)

        tmp_nan = releases_dir / f"_tmp-strain-{key}-nan.tif"
        tmp_zer = releases_dir / f"_tmp-strain-{key}-zeros.tif"
        arr_nan = np.where(footprint, dots.astype(np.float32), np.nan)
        io.write_float32(tmp_nan, arr_nan, encoding="nan", template=paths["sample_submission"])
        io.write_float32(tmp_zer, arr_nan, encoding="zeros", template=paths["sample_submission"])
        sha_nan, sha_zer = io.sha256_file(tmp_nan), io.sha256_file(tmp_zer)
        stem = f"{PARENT_TAG}-CONCENTRATION{key}-{BUILD_DATE}-{sha_nan[:8]}"
        final_nan, final_zer = releases_dir / f"{stem}.tif", releases_dir / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)

        g_nan = gates.validate_release(final_nan, template=paths["sample_submission"], catalogue=cat,
                                       encoding="nan", expect_dots=PARENT_DOTS,
                                       ledger=ROOT / "ledger" / "submissions.csv", own_id=stem)
        g_zer = gates.validate_release(final_zer, template=paths["sample_submission"], catalogue=cat,
                                       encoding="zeros", expect_dots=PARENT_DOTS,
                                       ledger=ROOT / "ledger" / "submissions.csv", own_id=stem)
        if not (g_nan["PASS"] and g_zer["PASS"]):
            raise SystemExit(f"GATE FAIL (release_gates) {stem}: nan={g_nan['failed']} zeros={g_zer['failed']}")
        vr_nan = vr_mod.validate_raster(final_nan, paths["sample_submission"],
                                        catalogue=paths["existing_faults"],
                                        ledger_csv=ROOT / "ledger" / "submissions.csv",
                                        parent=paths["parent_r0_nan"])
        vr_zer = vr_mod.validate_raster(final_zer, paths["sample_submission"],
                                        catalogue=paths["existing_faults"],
                                        ledger_csv=ROOT / "ledger" / "submissions.csv",
                                        parent=paths["parent_r0_nan"], allow_zeros_outside=True)
        if not (vr_nan.ok and vr_zer.ok):
            raise SystemExit(f"GATE FAIL (validate_raster) {stem}:\n{vr_nan.text()}\n{vr_zer.text()}")

        # Frozen-translator instruments (report-only; never arrow gates).
        sg = relief.fast_binary_dti(dots, sgmc_off, d_truth=d_sgmc)
        h19 = relief.fast_binary_dti(dots, lineage_mask, d_truth=d_h19)
        nz = relief.fast_binary_dti(dots, noise_truth, d_truth=d_noise)
        rel_t = (sg["T"] - r0_sgmc["T"]) / r0_sgmc["T"]
        delta_noise = CLAIMED_LIVE * (nz["dti"] - r0_noise["dti"]) / r0_noise["dti"]
        delta_mask = CLAIMED_LIVE * (h19["dti"] - r0_h19["dti"]) / r0_h19["dti"]
        point, rng = frozen_prediction(rel_t, delta_noise, delta_mask)

        hr = proxy.hide_and_recover(dots, cat, footprint)
        hr_delta = hr["proxy_mean_credit"] - r0_hr["proxy_mean_credit"]
        if abs(hr_delta) > 1e-12:
            raise SystemExit(
                f"STOP: {key} catalogue PROXY moved ({hr_delta}) although donors/targets are "
                "floored >3px - the quarantine is broken (IR-91-28 invariance violated)")

        pct = stats["pct_dots_moved"]
        note = (f"{PARENT_TAG}; CONC {cfg['label']}: {stats['n_dots_moved']} dots ({pct:.1f}%) "
                f"low->high 2.5km blocks, count fixed; pred MODEL:{point:+.4f}")
        assert len(note) <= 140, f"form_note exceeds 140 chars ({len(note)}): {note}"

        built[key] = {
            "id": stem, "axis": "CONCENTRATION", "value": key,
            "prior": cfg["prior"], "frac": cfg["frac"], "block_px": BLOCK_PX,
            "n_dots": PARENT_DOTS, "n_moved": stats["n_dots_moved"],
            "pct_dots_moved": round(pct, 4), "parent_diff": diff,
            "builder_stats": {k: stats[k] for k in (
                "frac_achieved", "count_preserved", "cv_before", "cv_after", "cv_excursion",
                "moved_displacement_px", "donor_block_prior_mean", "acceptor_block_prior_mean",
                "donor_excluded_dots", "blocks")},
            "block_density_cv_occupied": {
                "at_25px_before": proxy.block_density_cv(parent, footprint, 25),
                "at_25px_after": proxy.block_density_cv(dots, footprint, 25),
                "at_10px_before": proxy.block_density_cv(parent, footprint, 10),
                "at_10px_after": proxy.block_density_cv(dots, footprint, 10)},
            "collar": {"le3px_before": 2171, "le3px_after": collar_after,
                       "added_le3px": int(((dcat <= 3.0) & added).sum()),
                       "min_dcat_px": round(float(dcat[dots].min()), 6)},
            "sha256_nan": sha_nan, "sha256_zeros": sha_zer,
            "bytes_nan": final_nan.stat().st_size, "bytes_zeros": final_zer.stat().st_size,
            "dot_set_digest": g_nan["dot_set_digest"],
            "predicted_change_MODEL": f"MODEL:{point:+.4f}",
            "predicted_range": f"[{rng[0]:+.3f},{rng[1]:+.3f}]",
            "prediction_components": {
                "sgmc_T_parent": round(r0_sgmc["T"], 3), "sgmc_T_cand": round(sg["T"], 3),
                "sgmc_rel_T": round(rel_t, 6),
                "point": point, "range": rng,
                "delta_noise_truth": round(delta_noise, 4),
                "delta_lineage_mask": round(delta_mask, 4)},
            "form_note": note, "form_note_len": len(note),
            "report_only": {
                "sgmc_off_catalogue_dti": round(sg["dti"], 6),
                "sgmc_delta_vs_r0": round(sg["dti"] - r0_sgmc["dti"], 6),
                "h19_lineage_mask_dti": round(h19["dti"], 6),
                "noise_truth_dti": round(nz["dti"], 6),
                "fixed_catalogue_proxy": hr,
                "proxy_delta_vs_r0": round(hr_delta, 6),
                "proxy_reading": "invariant by construction (donors quarantined >3px, targets >3px; IR-91-28) - carries no evidence either way",
                "moved_dot_canary": proxy.canary(added, dots, cat),
                "redundancy": proxy.redundancy(dots)},
            "gates_nan": {k: g_nan[k] for k in (
                "PASS", "failed", "crs_matches_template", "shape_matches_template",
                "transform_matches_template", "single_band", "dtype_float32",
                "no_nan_inside_footprint", "nan_outside_footprint", "values_within_0_1",
                "unit_mass_dots", "zero_catalogue_mass", "min_catalogue_distance_px",
                "catalogue_floor_respected", "count_matches_parent", "sha256_not_in_ledger")},
            "gates_zeros": {k: g_zer[k] for k in (
                "PASS", "failed", "zeros_outside_footprint", "sha256_not_in_ledger")},
            "validate_raster_14_of_14": bool(vr_nan.ok and vr_zer.ok),
        }
        manifest_entries.extend([
            {"file": final_nan.name, "sha256": sha_nan, "bytes": final_nan.stat().st_size},
            {"file": final_zer.name, "sha256": sha_zer, "bytes": final_zer.stat().st_size},
        ])
        basis = ("2.5km blocks by sponsor geodetic strain prior = 0.5*pct(band4 geod_2ndinv)"
                 "+0.5*pct(band7 geod_shearrate), Sentinel-filled; donors/targets d_cat>3px (IR-91-27/42)"
                 if cfg["prior"] == "strain" else
                 "2.5km blocks by sponsor geodetic dilatation prior = pct(band8 geod_dilaterate), "
                 "Sentinel-filled; donors/targets d_cat>3px (IR-91-27/42)")
        ledger_rows.append({
            "id": stem, "parent": PARENT_TAG, "axis": "CONCENTRATION", "value": key,
            "n_dots": PARENT_DOTS, "pct_changed": f"{pct:.4f}", "pct_relocated": f"{pct:.4f}",
            "sha256": sha_nan, "sha256_zeros": sha_zer, "status": "BUILT",
            "predicted_change": f"MODEL:{point:+.4f}",
            "predicted_range": f"[{rng[0]:+.3f},{rng[1]:+.3f}]",
            "ranking_basis": basis,
            "receipt_score": "", "receipt_date": "", "date": LEDGER_DATE,
            "form_note": note, "evidence_class": "MODEL", "source": SOURCE,
            "notes": (f"moved {stats['n_dots_moved']} dots ({pct:.2f}%, Hamming {diff['pct_changed_of_parent']:.2f}%), "
                      f"mean disp {stats['moved_displacement_px']['mean_px']:.1f}px; collar 2171->2171; "
                      f"SGMC_off dDTI {sg['dti'] - r0_sgmc['dti']:+.5f} PROXY."),
            "source_url": "",
        })
        print(f"{stem}: moved={stats['n_dots_moved']} ({pct:.2f}%) sgmc_relT={rel_t:+.4f} "
              f"pred=MODEL:{point:+.4f} [{rng[0]:+.3f},{rng[1]:+.3f}]")

    # Determinism: the first arm rebuilds to the identical dot set.
    band2, _ = run_concentration.build_concentration(
        parent_band, prior_arrays["strain"], footprint, cat, frac=0.10, block_px=BLOCK_PX,
        min_gap_px=MIN_GAP_PX, seed=SEED, min_sep_px=MIN_SEP_PX, donor_exclude=donor_exclude)
    deterministic = bool(np.array_equal(
        io.dot_mask(band2), io.dot_mask(io.read_grid(releases_dir / f"{built['strn25m10']['id']}.tif"))))
    if not deterministic:
        raise SystemExit("STOP: strain build is not deterministic")

    added = append_ledger_rows(ledger_rows)
    update_release_manifest(manifest_entries)

    evidence = {
        "schema": "gems91.strain-concentration-evidence.v1",
        "build_date": LEDGER_DATE,
        "session": SOURCE,
        "git_sha": raster_io.git_sha(short=False),
        "preregistration": "registry/strain_concentration_preregistration.json",
        "axis": "CONCENTRATION",
        "parent": PARENT_TAG,
        "lineage": lineage,
        "settings": {"block_px": BLOCK_PX, "seed": SEED, "min_gap_px": MIN_GAP_PX,
                     "min_sep_px": MIN_SEP_PX, "low_q": 0.30, "high_q": 0.30,
                     "donor_quarantine": "d_cat<=3.0px dots may not be donors (IR-91-27/42)",
                     "claimed_live_CLAIM": CLAIMED_LIVE, "shrink": SHRINK},
        "priors": prior_info,
        "single_feature_leakage_canary": canary,
        "r0_baseline": {
            "n_dots": PARENT_DOTS,
            "sgmc_off_catalogue_dti": round(r0_sgmc["dti"], 6),
            "sgmc_off_catalogue_T": round(r0_sgmc["T"], 3),
            "sgmc_off_catalogue_n_px": int(sgmc_off.sum()),
            "h19_lineage_mask_dti": round(r0_h19["dti"], 6),
            "h19_lineage_mask_n_px": int(lineage_mask.sum()),
            "noise_truth_dti": round(r0_noise["dti"], 6),
            "noise_truth_n_px": n_noise,
            "fixed_catalogue_proxy": r0_hr,
            "redundancy": proxy.redundancy(parent),
            "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10),
        },
        "deterministic_rebuild_arm1": deterministic,
        "arms": built,
    }
    ev_path = ROOT / "evidence" / f"strain_concentration_{BUILD_DATE}.json"
    ev_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"\nledger new rows appended: {added}\nevidence: {ev_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
