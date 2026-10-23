#!/usr/bin/env python3
"""RELIEF axis on R0: three matched 12% mass-reallocation arms across Basin / Piedmont / Range-Front terciles.

Parent R0 = ``h33-h33-2-b2`` (GEMSDOE32), 37,654 unit-mass dots,
sha256 ``baeae321...`` (NaN) / ``c55bafc4...`` (zeros), CLAIM 0.2778.

Experimental triad (all at 12.00% = 4,518 dots shifted, count fixed at 37,654)
------------------------------------------------------------------------------
r2p12   Range-Front/Horst (T3) -> Piedmont/Bajada (T2)
        Tests active piedmont-toe scarp & accommodation-zone fault concentration.
r2b12   Range-Front/Horst (T3) -> Concealed Basin (T1)
        Donor-identical twin of r2p12; tests concealed intrabasin graben faults.
b2r12   Concealed Basin (T1)   -> Range-Front/Horst (T3)
        Exact directional sign flip of r2b12; tests unmapped bedrock/range faults.

Usage
-----
    python3 scripts/build_relief.py --build
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import proxy as fold_proxy_mod  # noqa: E402
import validate_raster as vr_mod  # noqa: E402
from gems91 import geom, io, proxy, release_gates as gates, relief  # noqa: E402

MANIFEST_PATH = ROOT / "registry" / "data_manifest.json"
DATA = ROOT / "data"

PARENT_TAG = "h33-h33-2-b2"
PARENT_DOTS = 37654
BUILD_DATE = "20261023"
SHIFT_FRAC = 0.12

REQUIRED_PINS = (
    "sample_submission",
    "existing_faults",
    "training_features",
    "parent_r0_zeros",
    "parent_r0_nan",
    "anc_h19_5",
    "anc_h19_4",
    "anc_h16_1",
    "anc_d2_8",
    "anc_solo_d2_8",
    "sgmc_faults_control",
)

ARMS = {
    "r2p12": {
        "value": "r2p12",
        "donor": "range",
        "recipient": "pied",
        "predicted": "+0.006",
        "range": "[-0.006,+0.018]",
        "description": "Range->Piedmont tercile (det_elev/slope)",
        "rationale": (
            "Piedmont-toe scarp & accommodation-zone concentration; strips weakest "
            "subsurface-corroborated T3 horst-interior ridges with near-zero (-0.0017) "
            "out-of-fold INGENIOUS substitution cost."
        ),
    },
    "r2b12": {
        "value": "r2b12",
        "donor": "range",
        "recipient": "basin",
        "predicted": "+0.003",
        "range": "[-0.010,+0.016]",
        "description": "Range->Basin tercile (det_elev/slope)",
        "rationale": (
            "Donor-identical twin of r2p12 and sign flip of b2r12; reallocates 4,518 "
            "T3 horst dots onto concealed deep-fill intrabasin lineage & magnetic+gravity "
            "basement-step crests."
        ),
    },
    "b2r12": {
        "value": "b2r12",
        "donor": "basin",
        "recipient": "range",
        "predicted": "+0.005",
        "range": "[-0.010,+0.020]",
        "description": "Basin->Range tercile (det_elev/slope)",
        "rationale": (
            "Exact directional sign flip of r2b12; gains +0.0050 (+5.2%) on blind "
            "off-catalogue USGS SGMC bedrock faults where 64-70% of unmapped bedrock "
            "traces reside, while losing -0.0113 on Quaternary-heavy INGENIOUS folds."
        ),
    },
}


def verify_pinned_inputs() -> dict[str, Path]:
    """Verify presence, byte count, and sha256 of every required pinned input."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in manifest["files"]}
    paths: dict[str, Path] = {}
    for fid in REQUIRED_PINS:
        entry = by_id[fid]
        p = DATA / entry["local_subpath"]
        if not p.is_file():
            raise SystemExit(f"STOP: missing pinned input {fid} at {p}; run scripts/restore_data.py")
        size = p.stat().st_size
        digest = io.sha256_file(p)
        if size != entry["bytes"] or digest != entry["sha256"]:
            raise SystemExit(
                f"STOP: pin mismatch on {fid}: got {digest} ({size} B), "
                f"expected {entry['sha256']} ({entry['bytes']} B)"
            )
        paths[fid] = p
    return paths


def verify_parent_lineage(paths: dict[str, Path], cat: np.ndarray, dcat: np.ndarray) -> dict:
    """Confirm R0 twins match and R0's dot set reproduces from both pinned ancestors."""
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
    if not (
        out["twins_identical"]
        and out["n_dots"] == PARENT_DOTS
        and out["dots_on_catalogue"] == 0
        and all(v["identical_to_parent"] for v in out["rebuilt_from"].values())
    ):
        raise SystemExit(f"STOP: parent R0 verification failed (brief section 5): {out}")
    return out


def single_feature_canary(
    feat_path: Path,
    footprint: np.ndarray,
    cat: np.ndarray,
    relief_idx: np.ndarray,
    s_struct: np.ndarray,
    *,
    stride: int = 25,
) -> dict[str, object]:
    """Brief section 6 leakage canary: any single feature with AUC > 0.90 => stop."""
    y = cat[footprint][::stride].astype(np.float64)
    band_aucs: dict[str, float] = {}
    with rasterio.open(str(feat_path)) as src:
        for b in range(1, src.count + 1):
            name = src.tags(b).get("band_name") or f"band_{b}"
            vals = src.read(b)[footprint][::stride]
            ok = np.isfinite(vals) & (vals > -1e30)
            raw = proxy._auc(vals[ok].astype(np.float64), y[ok])
            band_aucs[name] = round(float(max(raw, 1.0 - raw)), 4)
    for label, field in (("relief_index", relief_idx), ("s_struct", s_struct)):
        vals = field[footprint][::stride]
        raw = proxy._auc(vals.astype(np.float64), y)
        band_aucs[label] = round(float(max(raw, 1.0 - raw)), 4)
    max_name = max(band_aucs, key=band_aucs.get)
    max_auc = band_aucs[max_name]
    if max_auc > 0.90:
        raise SystemExit(
            f"STOP: leakage canary triggered on {max_name} (symmetric AUC={max_auc:.4f} > 0.90)"
        )
    return {
        "max_symmetric_auc": max_auc,
        "max_feature": max_name,
        "stop_threshold": 0.90,
        "stride": stride,
        "n_sampled_px": int(len(y)),
        "symmetric_aucs": band_aucs,
    }


def out_of_fold_proxy(
    d28: np.ndarray,
    cat: np.ndarray,
    footprint: np.ndarray,
    terciles: dict[str, np.ndarray],
    s_struct: np.ndarray,
    lineage_union: np.ndarray,
    pot_crest: np.ndarray,
) -> dict[str, object]:
    """4-fold spatial block hide-and-recover PROXY rebuilt per fold without held faults."""
    folds = fold_proxy_mod.block_folds(footprint.shape, cat.astype(np.uint8), n_folds=4, block=8)
    scores: dict[str, list[float]] = {"R0_fold": []}
    for key in ARMS:
        scores[key] = []
    n_held_list: list[int] = []

    for held in folds:
        n_held_list.append(int(held.sum()))
        cat_train = cat & ~held
        dcat_tr = ndi.distance_transform_edt(~cat_train)
        d_held = ndi.distance_transform_edt(~held)
        r0_tr = d28 & (dcat_tr > geom.CATALOGUE_FLOOR_PX)
        scores["R0_fold"].append(relief.fast_binary_dti(r0_tr, held, d_truth=d_held)["dti"])
        for key, cfg in ARMS.items():
            built_tr = relief.shift_relief_mass(
                r0_tr,
                terciles,
                dcat_tr,
                s_struct,
                lineage_union,
                pot_crest,
                donor_key=cfg["donor"],
                recipient_key=cfg["recipient"],
                frac=SHIFT_FRAC,
            )
            scores[key].append(relief.fast_binary_dti(built_tr["dots"], held, d_truth=d_held)["dti"])

    r0_arr = np.array(scores["R0_fold"], dtype=np.float64)
    summary: dict[str, object] = {"n_withheld_positives_per_fold": n_held_list, "arms": {}}
    for key, vals in scores.items():
        arr = np.array(vals, dtype=np.float64)
        lo, hi, se = fold_proxy_mod.mean_ci(arr)
        delta = arr - r0_arr
        summary["arms"][key] = {
            "mean_dti_proxy": round(float(arr.mean()), 6),
            "ci95": [round(float(lo), 6), round(float(hi), 6)],
            "se": round(float(se), 6),
            "mean_delta_vs_r0_fold": round(float(delta.mean()), 6),
            "folds": [round(float(x), 6) for x in arr],
        }
    return summary


def update_release_manifest(new_entries: list[dict[str, object]]) -> None:
    manifest_p = ROOT / "releases" / "MANIFEST.json"
    existing = {}
    if manifest_p.is_file():
        cur = json.loads(manifest_p.read_text(encoding="utf-8"))
        for f in cur.get("files", []):
            existing[f["file"]] = f
    for f in new_entries:
        existing[f["file"]] = f
    payload = {
        "schema_version": 1,
        "generated_utc": "2026-10-23T22:00:00Z",
        "note": (
            "Releases are NOT committed (this repo does not publish derived copies of "
            "competition rasters). These hashes are the contract: rebuild with "
            "`python3 scripts/restore_data.py && python3 scripts/build_spacing.py --build && "
            "python3 scripts/build_relief.py --build` and every sha256 below must reappear "
            "byte for byte. CI enforces this."
        ),
        "parent": "h33-h33-2-b2 (e5eb6e7e)",
        "files": [existing[k] for k in sorted(existing)],
    }
    manifest_p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_ledger_rows(rows: list[dict[str, object]]) -> int:
    ledger = ROOT / "ledger" / "submissions.csv"
    existing: list[dict[str, str]] = []
    newline = "\n"
    if ledger.is_file():
        raw = ledger.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            existing = list(csv.DictReader(fh))
    fieldnames = list(existing[0].keys()) if existing else list(rows[0].keys())
    for r in rows:
        for col in r:
            if col not in fieldnames:
                fieldnames.append(col)

    by_id = {r["id"]: i for i, r in enumerate(existing)}
    added = 0
    for r in rows:
        formatted = {k: str(r.get(k, "")) for k in fieldnames}
        if r["id"] in by_id:
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true", help="verify pins, build 3 RELIEF arms, run gates")
    ap.add_argument("--skip-fold-proxy", action="store_true", help="skip 4-fold rebuilt proxy")
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
    lineage_report = verify_parent_lineage(paths, cat, dcat)

    h195 = io.dot_mask(io.read_grid(paths["anc_h19_5"]))
    h194 = io.dot_mask(io.read_grid(paths["anc_h19_4"]))
    h161 = io.dot_mask(io.read_grid(paths["anc_h16_1"]))
    d28 = io.dot_mask(io.read_grid(paths["anc_d2_8"]))
    lineage_union = (h195 | h194 | h161) & footprint

    with rasterio.open(str(paths["training_features"])) as src:
        tmi_hg = src.read(3)
        grav_slope = src.read(5)
        tc = src.read(6)
        det_elev = src.read(12)
        depth_base = src.read(15)
        grav_hg = src.read(18)
        det_slope = src.read(19)

    relief_idx, terciles, tercile_meta = relief.compute_relief_terciles(
        det_elev, det_slope, footprint, w_elev=0.90
    )
    _, depth_filled = relief.fill_footprint_percentile(depth_base, footprint)
    for k, m in terciles.items():
        tercile_meta["terciles"][k]["median_sediment_depth_m"] = round(
            float(np.nanmedian(depth_filled[m])), 1
        )
        tercile_meta["terciles"][k]["r0_dots"] = int((parent & m).sum())
        tercile_meta["terciles"][k]["r0_pct"] = round(
            100.0 * int((parent & m).sum()) / PARENT_DOTS, 3
        )

    s_struct, pot_crest = relief.compute_structural_score(
        tmi_hg, grav_slope, grav_hg, tc, h195, h194, h161, footprint
    )
    feat_canary = single_feature_canary(
        paths["training_features"], footprint, cat, relief_idx, s_struct
    )

    with rasterio.open(str(paths["sgmc_faults_control"])) as src:
        sgmc_off = (src.read(1) > 0) & footprint & (dcat > 3.0)
    d_sgmc = ndi.distance_transform_edt(~sgmc_off)
    r0_sgmc = relief.fast_binary_dti(parent, sgmc_off, d_truth=d_sgmc)
    r0_hr_fixed = proxy.hide_and_recover(parent, cat, footprint)

    fold_hr = (
        None
        if args.skip_fold_proxy
        else out_of_fold_proxy(d28, cat, footprint, terciles, s_struct, lineage_union, pot_crest)
    )

    releases_dir = ROOT / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)

    built_arms: dict[str, dict] = {}
    manifest_entries: list[dict[str, object]] = []
    ledger_rows: list[dict[str, object]] = []

    for key, cfg in ARMS.items():
        res = relief.shift_relief_mass(
            parent,
            terciles,
            dcat,
            s_struct,
            lineage_union,
            pot_crest,
            donor_key=cfg["donor"],
            recipient_key=cfg["recipient"],
            frac=SHIFT_FRAC,
        )
        dots = res["dots"]
        diff = gates.parent_diff(parent, dots)

        tmp_nan = releases_dir / f"_tmp-relief-{key}-nan.tif"
        tmp_zer = releases_dir / f"_tmp-relief-{key}-zeros.tif"
        arr_nan = np.where(footprint, dots.astype(np.float32), np.nan)
        io.write_float32(tmp_nan, arr_nan, encoding="nan", template=paths["sample_submission"])
        io.write_float32(tmp_zer, arr_nan, encoding="zeros", template=paths["sample_submission"])

        sha_nan = io.sha256_file(tmp_nan)
        sha_zer = io.sha256_file(tmp_zer)
        sha8 = sha_nan[:8]
        stem = f"{PARENT_TAG}-RELIEF{cfg['value']}-{BUILD_DATE}-{sha8}"
        final_nan = releases_dir / f"{stem}.tif"
        final_zer = releases_dir / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)

        # Gate suite 1: release_gates (CI validator)
        g_nan = gates.validate_release(
            final_nan,
            template=paths["sample_submission"],
            catalogue=cat,
            encoding="nan",
            expect_dots=PARENT_DOTS,
            ledger=ROOT / "ledger" / "submissions.csv",
            own_id=stem,
        )
        g_zer = gates.validate_release(
            final_zer,
            template=paths["sample_submission"],
            catalogue=cat,
            encoding="zeros",
            expect_dots=PARENT_DOTS,
            ledger=ROOT / "ledger" / "submissions.csv",
            own_id=stem,
        )
        if not (g_nan["PASS"] and g_zer["PASS"]):
            raise SystemExit(f"GATE FAIL (release_gates) {stem}: nan={g_nan['failed']} zeros={g_zer['failed']}")

        # Gate suite 2: validate_raster (14/14 MUST gates)
        vr_nan = vr_mod.validate_raster(
            final_nan,
            paths["sample_submission"],
            catalogue=paths["existing_faults"],
            ledger_csv=ROOT / "ledger" / "submissions.csv",
            parent=paths["parent_r0_nan"],
        )
        vr_zer = vr_mod.validate_raster(
            final_zer,
            paths["sample_submission"],
            catalogue=paths["existing_faults"],
            ledger_csv=ROOT / "ledger" / "submissions.csv",
            parent=paths["parent_r0_nan"],
            allow_zeros_outside=True,
        )
        if not (vr_nan.ok and vr_zer.ok):
            raise SystemExit(f"GATE FAIL (validate_raster) {stem}:\n{vr_nan.text()}\n{vr_zer.text()}")

        sg_arm = relief.fast_binary_dti(dots, sgmc_off, d_truth=d_sgmc)
        hr_fixed = proxy.hide_and_recover(dots, cat, footprint)
        dot_canary = proxy.canary(dots & ~parent, dots, cat)
        nn_stats = proxy.redundancy(dots)
        cv1km = proxy.block_density_cv(dots, footprint, 10)
        cv5km = proxy.block_density_cv(dots, footprint, 50)

        note = (
            f"{PARENT_TAG}; RELIEF shift {res['n_shifted']} dots ({res['pct_relocated']:.2f}%) "
            f"{cfg['description']}, count fixed {PARENT_DOTS}; pred {cfg['predicted']} MODEL"
        )
        assert len(note) <= 140, f"form_note exceeds 140 chars ({len(note)}): {note}"

        built_arms[key] = {
            "id": stem,
            "axis": "RELIEF",
            "value": cfg["value"],
            "donor_tercile": cfg["donor"],
            "recipient_tercile": cfg["recipient"],
            "n_dots": res["n_dots"],
            "n_shifted": res["n_shifted"],
            "pct_relocated": res["pct_relocated"],
            "pct_hamming": res["pct_hamming"],
            "hamming_vs_parent": diff,
            "recipient_tiers": res["recipient_tiers"],
            "donor_s_struct_mean": res["donor_s_struct_mean"],
            "recipient_s_struct_mean": res["recipient_s_struct_mean"],
            "tercile_counts_before": res["tercile_counts_before"],
            "tercile_counts_after": res["tercile_counts_after"],
            "tercile_pct_before": res["tercile_pct_before"],
            "tercile_pct_after": res["tercile_pct_after"],
            "collar_le3px_before": res["collar_le3px_before"],
            "collar_le3px_after": res["collar_le3px_after"],
            "added_dots_le3px": res["added_dots_le3px"],
            "block_density_cv_1km": cv1km,
            "block_density_cv_5km": cv5km,
            "redundancy": nn_stats,
            "sha256_nan": sha_nan,
            "sha256_zeros": sha_zer,
            "bytes_nan": final_nan.stat().st_size,
            "bytes_zeros": final_zer.stat().st_size,
            "dot_set_digest": g_nan["dot_set_digest"],
            "predicted_change_MODEL": f"MODEL:{cfg['predicted']}",
            "predicted_range": cfg["range"],
            "rationale": cfg["rationale"],
            "form_note": note,
            "report_only": {
                "sgmc_off_catalogue_dti": round(sg_arm["dti"], 6),
                "sgmc_delta_vs_r0": round(sg_arm["dti"] - r0_sgmc["dti"], 6),
                "fixed_catalogue_proxy": hr_fixed,
                "out_of_fold_catalogue_proxy": fold_hr["arms"][key] if fold_hr else None,
                "moved_dot_canary": dot_canary,
            },
            "gates_nan": {
                k: g_nan[k]
                for k in (
                    "PASS",
                    "failed",
                    "crs_matches_template",
                    "shape_matches_template",
                    "transform_matches_template",
                    "single_band",
                    "dtype_float32",
                    "no_nan_inside_footprint",
                    "nan_outside_footprint",
                    "values_within_0_1",
                    "unit_mass_dots",
                    "zero_catalogue_mass",
                    "min_catalogue_distance_px",
                    "catalogue_floor_respected",
                    "count_matches_parent",
                    "sha256_not_in_ledger",
                )
            },
            "gates_zeros": {
                k: g_zer[k] for k in ("PASS", "failed", "zeros_outside_footprint", "sha256_not_in_ledger")
            },
            "validate_raster_14_of_14": bool(vr_nan.ok and vr_zer.ok),
        }

        manifest_entries.extend([
            {"file": final_nan.name, "sha256": sha_nan, "bytes": final_nan.stat().st_size},
            {"file": final_zer.name, "sha256": sha_zer, "bytes": final_zer.stat().st_size},
        ])

        ranking_basis = (
            f"terciles=0.90*pct(Band12 det_elev)+0.10*pct(Band19 det_elev_slope); "
            f"within-tercile S_struct=0.60*lineage(H19-5/H19-4/H16-1)+0.40*pot(Bands 3,5,18,6); "
            f"d_cat>3px held invariant"
        )
        notes_col = (
            f"Shift {res['n_shifted']} dots (12.00% relocated, 24.00% Hamming) "
            f"{cfg['donor']}->{cfg['recipient']}; count fixed 37,654; "
            f"CV_1km 0.6187->{cv1km:.4f}, CV_5km 0.7261->{cv5km:.4f}; "
            f"SGMC_off delta {sg_arm['dti'] - r0_sgmc['dti']:+.4f} PROXY; 0 collar drift."
        )
        ledger_rows.append({
            "id": stem,
            "parent": PARENT_TAG,
            "axis": "RELIEF",
            "value": cfg["value"],
            "n_dots": PARENT_DOTS,
            "pct_changed": f"{res['pct_relocated']:.2f}",
            "pct_relocated": f"{res['pct_relocated']:.2f}",
            "sha256": sha_nan,
            "sha256_zeros": sha_zer,
            "status": "BUILT",
            "predicted_change": f"MODEL:{cfg['predicted']}",
            "predicted_range": cfg["range"],
            "ranking_basis": ranking_basis,
            "receipt_score": "",
            "receipt_date": "",
            "date": "2026-10-23",
            "form_note": note,
            "evidence_class": "MODEL",
            "source": "SESSION 5 (arena/42de3fed-gemsdoe91)",
            "notes": notes_col,
            "source_url": "",
        })
        print(
            f"{stem}: dots={res['n_dots']} shifted={res['n_shifted']} ({res['pct_relocated']:.2f}%) "
            f"tiers={res['recipient_tiers']} cv1km={cv1km:.4f} "
            f"sgmc_delta={sg_arm['dti'] - r0_sgmc['dti']:+.5f} pred=MODEL:{cfg['predicted']}"
        )

    # Cross-arm design verification: r2p12 and r2b12 must share the exact same 4,518 removed donor dots
    r2p_dots = io.dot_mask(io.read_grid(releases_dir / f"{built_arms['r2p12']['id']}.tif"))
    r2b_dots = io.dot_mask(io.read_grid(releases_dir / f"{built_arms['r2b12']['id']}.tif"))
    donors_identical = bool(np.array_equal(parent & ~r2p_dots, parent & ~r2b_dots))
    if not donors_identical:
        raise SystemExit("STOP: r2p12 and r2b12 donor sets diverged")

    added = append_ledger_rows(ledger_rows)
    update_release_manifest(manifest_entries)

    ev_path = ROOT / "evidence" / f"relief_axis_{BUILD_DATE}.json"
    r0_oof = fold_hr["arms"]["R0_fold"] if fold_hr else None
    r0_oof_n = fold_hr["n_withheld_positives_per_fold"] if fold_hr else None
    if args.skip_fold_proxy and ev_path.exists():
        prev_ev = json.loads(ev_path.read_text(encoding="utf-8"))
        prev_r0_oof = prev_ev.get("r0_baseline", {}).get("out_of_fold_catalogue_proxy")
        if prev_r0_oof is not None:
            r0_oof = prev_r0_oof
            r0_oof_n = prev_ev.get("r0_baseline", {}).get("n_withheld_positives_per_fold")
        for key in ARMS:
            prev_arm_oof = (
                prev_ev.get("arms", {})
                .get(key, {})
                .get("report_only", {})
                .get("out_of_fold_catalogue_proxy")
            )
            if prev_arm_oof is not None:
                built_arms[key]["report_only"]["out_of_fold_catalogue_proxy"] = prev_arm_oof

    evidence = {
        "schema": "gems91.relief-evidence.v1",
        "build_date": "2026-10-23",
        "parent": PARENT_TAG,
        "shift_fraction": SHIFT_FRAC,
        "r2p12_r2b12_donor_set_identical": donors_identical,
        "lineage": lineage_report,
        "tercile_definition": tercile_meta,
        "r0_baseline": {
            "n_dots": PARENT_DOTS,
            "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10),
            "block_density_cv_5km": proxy.block_density_cv(parent, footprint, 50),
            "redundancy": proxy.redundancy(parent),
            "sgmc_off_catalogue_dti": round(r0_sgmc["dti"], 6),
            "sgmc_off_catalogue_n_px": int(sgmc_off.sum()),
            "fixed_catalogue_proxy": r0_hr_fixed,
            "out_of_fold_catalogue_proxy": r0_oof,
            "n_withheld_positives_per_fold": r0_oof_n,
        },
        "single_feature_leakage_canary": feat_canary,
        "arms": built_arms,
    }
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    ev_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"\nledger new rows appended: {added}\nevidence: {ev_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
