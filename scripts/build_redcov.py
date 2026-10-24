#!/usr/bin/env python3
"""SPACING/redcov axis on R0: three matched-count redundancy->coverage relocations.

    python3 scripts/build_redcov.py --build      # verify pins, build, gate, register
    python3 scripts/build_redcov.py --dry-run    # measure + predict, write nothing

Parent R0 = ``h33-h33-2-b2`` (GEMSDOE32), 37,654 unit-mass dots,
sha256 ``baeae321...`` (NaN) / ``c55bafc4...`` (zeros), CLAIM 0.2778 (no receipt).

Rule (``src/gems91/redcov.py``): donors = off-collar dots with the highest
kernel-overlap redundancy sum_{0<d<6px}(1-d/6); recipients = lineage-supported
cells (vote over anc_h19_5/h19_4/h16_1) furthest from a surviving dot, placed
greedily at >=2.8 px, all at d_cat > 3 px, R0's 2,171 collar dots quarantined
(IR-91-27), count fixed.  Arms: redcov10 (10%, vote>=1), redcov20 (20% dose),
redcov10v2 (10%, vote>=2 support bracket).

Predictions are computed from the measured exact DTI against the independent
off-catalogue SGMC control (USGS DS-1052, pinned, REPORT ONLY) with the same
transfer the SNAP session used: live = 0.2778 * relT * SHRINK(0.5); the range is
[0.5*point - 0.008, 0.2778 * relT * 1.0] (downside widened for the
selection-on-surrogate disclosure in IR-91-36).  The catalogue hide-and-recover
PROXY is invariant here by construction (IR-91-28 pattern) and is reported,
never gated on.  This script never submits anything.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import validate_raster as vr_mod  # noqa: E402
from gems91 import consensus as C  # noqa: E402
from gems91 import geom, io, proxy, redcov, relief  # noqa: E402
from gems91 import release_gates as gates  # noqa: E402

MANIFEST_PATH = ROOT / "registry" / "data_manifest.json"
DATA = ROOT / "data"

PARENT_TAG = "h33-h33-2-b2"
PARENT_DOTS = 37654
BUILD_DATE = "20261024"  # pinned, never datetime.now() (IR-91-32)
CLAIMED_LIVE = 0.2778    # CLAIM, no receipt in ledger/
SHRINK = 0.5             # surrogate-to-live shrink (SNAP session convention)
SESSION = "SESSION 9 (arena/ed1ccddf-gemsdoe91)"

REQUIRED_PINS = (
    "sample_submission", "existing_faults", "parent_r0_zeros", "parent_r0_nan",
    "anc_h19_5", "anc_h19_4", "anc_h16_1", "anc_d2_8", "anc_solo_d2_8",
    "sgmc_faults_control",
)

ARMS = {
    "redcov10": dict(frac=0.10, min_vote=1,
                     rationale="Base arm: 10% of dots moved from kernel-redundant clusters to the "
                               "supported cells furthest from any dot. Least invasive arm with "
                               "near-maximal screened coverage gain; CV enters the reported "
                               "best-file band."),
    "redcov20": dict(frac=0.20, min_vote=1,
                     rationale="Dose arm: same rule at 20%. Screened relT flattens (+8.8% vs "
                               "+7.5% at 10%), so this is the week-2 bracket if redcov10 "
                               "receipts >= +0.01, not a first slot."),
    "redcov10v2": dict(frac=0.10, min_vote=2,
                       rationale="Support bracket: recipients restricted to >=2-field support. "
                                 "Screens worse than redcov10 (recipients sit closer to existing "
                                 "dots), so it exists to decompose coverage vs support if "
                                 "redcov10 receipts near zero."),
}

RANKING_BASIS = (
    "donors=top kernel-overlap redundancy sum(1-d/6px) among d_cat>3px dots (parent geometry "
    "only); recipients=lineage vote>=N (anc_h19_5/h19_4/h16_1) cells farthest from surviving "
    "dots, >=2.8px spacing, d_cat>3px, collar quarantined (IR-91-27); NOT parent model ranking "
    "(IR-91-21)"
)


def verify_pinned_inputs() -> dict[str, Path]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in manifest["files"]}
    paths: dict[str, Path] = {}
    for fid in REQUIRED_PINS:
        entry = by_id[fid]
        p = DATA / entry["local_subpath"]
        if not p.is_file():
            raise SystemExit(f"STOP: missing pinned input {fid} at {p}; run scripts/restore_data.py")
        size, digest = p.stat().st_size, io.sha256_file(p)
        if size != entry["bytes"] or digest != entry["sha256"]:
            raise SystemExit(f"STOP: pin mismatch on {fid}: got {digest} ({size} B), "
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
            "n_ancestor_dots": int(anc.sum()), "n_after_collar": int(kept.sum()),
            "identical_to_parent": bool(np.array_equal(kept, parent_nan)),
        }
    if not (out["twins_identical"] and out["n_dots"] == PARENT_DOTS
            and out["dots_on_catalogue"] == 0 and out["collar_2_to_3px"] == 2171
            and all(v["identical_to_parent"] for v in out["rebuilt_from"].values())):
        raise SystemExit(f"STOP: parent R0 verification failed (brief section 5): {out}")
    return out


def vote_ring_canary(vote: np.ndarray, dcat: np.ndarray, footprint: np.ndarray) -> dict:
    """Leakage canary for the only feature-like input (lineage vote). REPORT ONLY.

    AUC of vote separating the 0<d_cat<=3 catalogue ring from d_cat>=7 background,
    on a fixed stride sample.  Brief section 6: a single feature at AUC > 0.90
    means stop and investigate.
    """
    ring = footprint & (dcat > 0) & (dcat <= 3.0)
    far = footprint & (dcat >= 7.0)
    scores = np.r_[vote[ring][::17], vote[far][::17]].astype(np.float64)
    labels = np.r_[np.ones(int(ring.sum() + 16) // 17), np.zeros(int(far.sum() + 16) // 17)]
    labels = labels[:len(scores)]
    auc = proxy._auc(scores, labels)
    auc = float(max(auc, 1.0 - auc))
    if auc > 0.90:
        raise SystemExit(f"STOP: leakage canary vote ring AUC={auc:.4f} > 0.90")
    return {"feature": "lineage vote (0-3)", "test": "0-3px catalogue ring vs >=7px background",
            "symmetric_auc": round(auc, 4), "stop_threshold": 0.90, "stride": 17}


def predict(rel_t: float) -> dict:
    point = CLAIMED_LIVE * rel_t * SHRINK
    return {
        "predicted": f"{point:+.3f}",
        "point_unrounded": round(point, 5),
        "range": f"[{0.5 * point - 0.008:+.3f},{CLAIMED_LIVE * rel_t:+.3f}]",
        "formula": "0.2778(CLAIM) * relT_SGMC * 0.5 shrink; range=[0.5*point-0.008, unshrunk]",
    }


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
        "generated_utc": "2026-10-24T00:00:00Z",
        "note": (
            "Releases are NOT committed (this repo does not publish derived copies of "
            "competition rasters). These hashes are the contract: rebuild with the CI "
            "lineage-job sequence (scripts/restore_data.py then every scripts/build_*.py) "
            "and every sha256 below must reappear byte for byte. CI enforces this."
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
    seen_sha = {r["sha256"] for r in existing}
    seen_key = {(r["parent"], r["axis"], r["value"]) for r in existing}
    added = 0
    for r in rows:
        formatted = {k: str(r.get(k, "")) for k in fieldnames}
        if r["id"] in by_id:  # idempotent rebuild (IR-91-32): same id must mean same bytes
            if existing[by_id[r["id"]]]["sha256"] != formatted["sha256"]:
                raise SystemExit(f"STOP: ledger id {r['id']} exists with a different sha256")
            existing[by_id[r["id"]]] = formatted
            continue
        if formatted["sha256"] in seen_sha:
            raise SystemExit(f"STOP: sha256 already in ledger under another id: {r['id']}")
        if (formatted["parent"], formatted["axis"], formatted["value"]) in seen_key:
            raise SystemExit(f"STOP: (parent,axis,value) already built: {r['id']}")
        existing.append(formatted)
        added += 1
    with ledger.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator=newline)
        w.writeheader()
        w.writerows(existing)
    return added


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the three SPACING/redcov variants of R0.")
    ap.add_argument("--build", action="store_true", help="verify pins, build 3 arms, run gates")
    ap.add_argument("--dry-run", action="store_true", help="measure and predict, write nothing")
    args = ap.parse_args(argv)
    if not (args.build or args.dry_run):
        ap.print_help()
        return 2

    paths = verify_pinned_inputs()
    print(f"[READY] {len(paths)} pinned inputs hash-verified for SPACING/redcov")
    template = io.read_grid(paths["sample_submission"])
    footprint = np.isfinite(template)
    cat = geom.catalogue_mask(io.read_grid(paths["existing_faults"]))
    dcat = geom.catalogue_distance(cat)
    lineage_report = verify_parent_lineage(paths, cat, dcat)
    parent = io.dot_mask(io.read_grid(paths["parent_r0_nan"]))

    fields = [io.read_grid(paths[k]) for k in C.FIELD_IDS]
    vote = C.vote_count([np.nan_to_num(f, nan=0.0) for f in fields])
    canary = vote_ring_canary(vote, dcat, footprint)
    print(f"vote ring canary AUC {canary['symmetric_auc']} (stop > 0.90)")

    sgmc_off = (io.read_grid(paths["sgmc_faults_control"]) > 0) & footprint & (dcat > 3.0)
    d_sgmc = ndi.distance_transform_edt(~sgmc_off)
    r0_sgmc = relief.fast_binary_dti(parent, sgmc_off, d_truth=d_sgmc)
    r0_hr = proxy.hide_and_recover(parent, cat, footprint)
    print(f"R0 SGMC-off DTI {r0_sgmc['dti']:.6f} (T={r0_sgmc['T']:.1f}, |G|={int(sgmc_off.sum())}) PROXY")

    releases_dir = ROOT / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)
    built: dict[str, dict] = {}
    manifest_entries: list[dict[str, object]] = []
    ledger_rows: list[dict[str, object]] = []

    for key, cfg in ARMS.items():
        res = redcov.apply_redcov(parent, vote, dcat, footprint,
                                  frac=cfg["frac"], min_vote=cfg["min_vote"])
        dots, st = res["child"], res["stats"]
        if st["n_dots"] != PARENT_DOTS:
            raise SystemExit(f"STOP: {key} changed the dot count: {st}")
        collar_after = int((dcat[dots] <= 3.0).sum())
        if collar_after != 2171 or int((dots & cat).sum()) != 0:
            raise SystemExit(f"STOP: {key} collar/catalogue violation: collar={collar_after}")

        sg_arm = relief.fast_binary_dti(dots, sgmc_off, d_truth=d_sgmc)
        rel_t = (sg_arm["T"] - r0_sgmc["T"]) / r0_sgmc["T"]
        pred = predict(rel_t)
        note = (f"{PARENT_TAG}; SPACING {key}: {st['n_moved']} dots ({st['pct_relocated']:.1f}%) "
                f"redundant->uncovered, count fixed; pred MODEL:{pred['predicted']}")
        assert len(note) <= 140, f"form_note exceeds 140 chars ({len(note)}): {note}"
        print(f"\n[{key}] moved {st['n_moved']} ({st['pct_relocated']:.2f}%) "
              f"SGMC relT {rel_t:+.4f} dDTI {sg_arm['dti'] - r0_sgmc['dti']:+.6f} "
              f"pred MODEL:{pred['predicted']} {pred['range']}")
        if args.dry_run:
            built[key] = {"stats": st, "relT": rel_t, "prediction": pred}
            continue

        tmp_nan = releases_dir / f"_tmp-redcov-{key}-nan.tif"
        tmp_zer = releases_dir / f"_tmp-redcov-{key}-zeros.tif"
        arr_nan = np.where(footprint, dots.astype(np.float32), np.nan)
        io.write_float32(tmp_nan, arr_nan, encoding="nan", template=paths["sample_submission"])
        io.write_float32(tmp_zer, arr_nan, encoding="zeros", template=paths["sample_submission"])
        sha_nan, sha_zer = io.sha256_file(tmp_nan), io.sha256_file(tmp_zer)
        stem = f"{PARENT_TAG}-SPACING{key}-{BUILD_DATE}-{sha_nan[:8]}"
        final_nan, final_zer = releases_dir / f"{stem}.tif", releases_dir / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)
        assert io.sha256_file(final_nan) == sha_nan and io.sha256_file(final_zer) == sha_zer

        g_nan = gates.validate_release(final_nan, template=paths["sample_submission"],
                                       catalogue=cat, encoding="nan", expect_dots=PARENT_DOTS,
                                       ledger=ROOT / "ledger" / "submissions.csv", own_id=stem)
        g_zer = gates.validate_release(final_zer, template=paths["sample_submission"],
                                       catalogue=cat, encoding="zeros", expect_dots=PARENT_DOTS,
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
        print(vr_nan.text())

        hr_fixed = proxy.hide_and_recover(dots, cat, footprint)
        built[key] = {
            "id": stem, "axis": "SPACING", "value": key, "stats": st,
            "parent_diff": gates.parent_diff(parent, dots),
            "sha256_nan": sha_nan, "sha256_zeros": sha_zer,
            "bytes_nan": final_nan.stat().st_size, "bytes_zeros": final_zer.stat().st_size,
            "dot_set_digest": g_nan["dot_set_digest"],
            "predicted_change_MODEL": f"MODEL:{pred['predicted']}",
            "predicted_range": pred["range"], "prediction_detail": pred,
            "rationale": cfg["rationale"], "form_note": note,
            "report_only": {
                "sgmc_off_catalogue_dti": round(sg_arm["dti"], 6),
                "sgmc_delta_vs_r0": round(sg_arm["dti"] - r0_sgmc["dti"], 6),
                "sgmc_T": round(sg_arm["T"], 3),
                "sgmc_T_rel_change": round(rel_t, 6),
                "fixed_catalogue_proxy": hr_fixed,
                "proxy_delta_vs_r0": round(hr_fixed["proxy_mean_credit"] - r0_hr["proxy_mean_credit"], 6),
                "moved_dot_canary": proxy.canary(res["recipients"], dots, cat),
                "redundancy": proxy.redundancy(dots),
                "block_density_cv_1km": proxy.block_density_cv(dots, footprint, 10),
                "block_density_cv_5km": proxy.block_density_cv(dots, footprint, 50),
            },
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
        ledger_rows.append({
            "id": stem, "parent": PARENT_TAG, "axis": "SPACING", "value": key,
            "n_dots": PARENT_DOTS,
            "pct_changed": f"{st['pct_changed_symdiff']:.2f}",
            "pct_relocated": f"{st['pct_relocated']:.2f}",
            "sha256": sha_nan, "sha256_zeros": sha_zer, "status": "BUILT",
            "predicted_change": f"MODEL:{pred['predicted']}",
            "predicted_range": pred["range"],
            "ranking_basis": RANKING_BASIS.replace("vote>=N", f"vote>={cfg['min_vote']}"),
            "receipt_score": "", "receipt_date": "", "date": "2026-10-24",
            "form_note": note, "evidence_class": "MODEL", "source": SESSION,
            "notes": (f"Moved {st['n_moved']} dots ({st['pct_relocated']:.2f}% relocated, "
                      f"{st['pct_changed_symdiff']:.2f}% symdiff) from redundancy maxima "
                      f"(median donor redundancy {st['donor_redundancy_median']}) to supported "
                      f"uncovered cells (median {st['recipient_dist_to_survivor_median_px']}px to "
                      f"nearest survivor); collar 2171->2171; CV1km "
                      f"{proxy.block_density_cv(parent, footprint, 10)}->"
                      f"{proxy.block_density_cv(dots, footprint, 10)}; SGMC relT {rel_t:+.4f} PROXY."),
            "source_url": "",
        })

    if args.dry_run:
        print("\ndry-run: nothing written")
        return 0

    # Determinism: rebuilding the base arm must reproduce the written file's dot set.
    again = redcov.apply_redcov(parent, vote, dcat, footprint, frac=0.10, min_vote=1)
    deterministic = bool(np.array_equal(
        again["child"], io.dot_mask(io.read_grid(releases_dir / f"{built['redcov10']['id']}.tif"))))
    if not deterministic:
        raise SystemExit("STOP: redcov build is not deterministic")

    added = append_ledger_rows(ledger_rows)
    update_release_manifest(manifest_entries)
    evidence = {
        "schema": "gems91.redcov-evidence.v1",
        "build_date": "2026-10-24",
        "session": SESSION,
        "axis": "SPACING",
        "parent": PARENT_TAG,
        "rule": {
            "donors": "top-frac off-collar dots by kernel-overlap redundancy sum_{0<d<6px}(1-d/6)",
            "recipients": "eligible (footprint, d_cat>3px, vote>=min_vote, not a donor cell) "
                          "ranked by distance to nearest surviving dot desc, greedy >=2.8px",
            "collar_policy": "dots at d_cat<=3px quarantined in place (IR-91-27)",
            "ranking_basis": RANKING_BASIS,
        },
        "prediction_model": {
            "formula": "live = CLAIMED_LIVE(0.2778) * relT_on_SGMC_control * SHRINK",
            "shrink": SHRINK,
            "range": "[0.5*point - 0.008, unshrunk] -- downside widened for screen-selection (IR-91-36)",
        },
        "deterministic_rebuild": deterministic,
        "lineage": lineage_report,
        "r0_baseline": {
            "n_dots": PARENT_DOTS,
            "sgmc_off_catalogue_dti": round(r0_sgmc["dti"], 6),
            "sgmc_T": round(r0_sgmc["T"], 3),
            "sgmc_off_catalogue_n_px": int(sgmc_off.sum()),
            "fixed_catalogue_proxy": r0_hr,
            "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10),
            "block_density_cv_5km": proxy.block_density_cv(parent, footprint, 50),
            "redundancy": proxy.redundancy(parent),
        },
        "vote_ring_leakage_canary": canary,
        "session_screen_log_PROXY": {
            "note": "Every family screened on the SGMC control this session before choosing the "
                    "axis (IR-91-36). PROXY only; none of these numbers is a score or a gate.",
            "mass_bottom_decile_precision_vs_breakeven_0.118": {
                "s_struct": 0.1126, "vote": 0.1009, "nbr5": 0.1057, "far_dcat": 0.0858,
                "conclusion": "every MASS ranking lands within ~2pp of break-even; predicted "
                              "|live delta| < 0.002 at mid denominator (IR-91-35)"},
            "fixed_count_exact_sgmc_relT": {
                "catalogue_density_concentration_10pct_1km": -0.0114,
                "catalogue_density_concentration_20pct_1km": -0.0161,
                "tip_extension_swap10": -0.0625,
                "redundancy_donors_plus_tip_recipients10": -0.0151,
                "redcov_prototype_with_donor_refill_allowed_10": 0.0746,
                "redcov_prototype_20": 0.0877,
                "redcov_prototype_10_vote2": 0.0406},
        },
        "arms": built,
    }
    ev_path = ROOT / "evidence" / f"redcov_axis_{BUILD_DATE}.json"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    ev_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"\nledger new rows appended: {added}\nevidence: {ev_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
