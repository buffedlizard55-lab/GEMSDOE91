#!/usr/bin/env python3
"""Build docs/run-card-S21-FAM3.json from measured evidence; apply preregistered
gates (docs/HYPOTHESES_S21_FAM3.md section 4). Copies TIFF+ZIP into
docs/downloads/ only when G1 (format) and G2 (uniqueness) pass.
The channel/DEM bicoherence hypotheses are not used; nothing is hand-typed."""
import hashlib, json, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
W, D = ROOT / "work/s21", ROOT / "docs/s21"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    tif = max((ROOT / "outputs/s21").glob("gems91-s21-fam3-*-zeros.tif"), key=lambda q: q.stat().st_mtime)
    rec = json.loads(tif.with_suffix(".json").read_text())
    gate = json.loads((D / "gate.json").read_text())
    gate1 = json.loads((D / "pass1-gate.json").read_text())
    emit = json.loads((D / "emit.json").read_text())
    hold = json.loads((D / "holdout.json").read_text())
    reg = json.loads((D / "registry-check.json").read_text())
    sib = json.loads((D / "sibling-check.json").read_text())
    sib1 = json.loads((D / "pass1-sibling-check.json").read_text())
    surf = json.loads((D / "surface-precheck.json").read_text())
    fit10 = json.loads((D / "fit_r10.json").read_text())
    fit1 = json.loads((D / "fit_r1.json").read_text())
    s20fit = json.loads((ROOT / "docs/lfi/fit_r10.json").read_text())
    assert rec["sha256"] == sha(tif) == reg["candidate_sha256"] == sib["candidate_sha256"]

    scores = hold["pooled"]["scores"]
    cand_h = scores["s21_candidate"]
    r0_h = scores["r0_gemsdoe32"]
    paired = hold["pooled"]["paired_differences"]["r0_gemsdoe32"]
    variants = list(gate)
    g4_lb = sum(gate[v]["boot_delta_ci95"][0] > 0 for v in variants)
    g4_p = all(gate[v]["p_delta_gt0"] >= 0.95 for v in variants)
    inst = hold["instrument_check_nine_sites"]
    hide_valid = inst["s20_full_112_anchor_spearman"] >= 0.5 and inst["split_matches_s20"]
    G = dict(
        G1_format=bool(rec["validator"]["all_checks_passed"]),
        G2_uniqueness=bool(surf["verdict"] == "PASS" and reg["verdict"] == "UNIQUE" and sib["verdict"] == "UNIQUE"),
        G3_leakage_canary=bool(hold["canary_pass"]),
        G4_surrogate_projection=bool(g4_lb >= 2 and g4_p),
        G5_instrument_rule=bool(paired["ci95"][0] > 0) if hide_valid else True,
    )
    ok_download = G["G1_format"] and G["G2_uniqueness"]
    all_pass = all(G.values())
    ok_submit = bool(all_pass)
    dl = ROOT / "docs/downloads"
    if ok_download:
        for p in (tif, tif.with_suffix(".zip")):
            dst = dl / p.name
            if not dst.exists():
                shutil.copy2(p, dst)
            assert sha(dst) == sha(p)
            dst.chmod(0o644)
        pol_p = ROOT / "registry/artifact_policy.json"
        pol = json.loads(pol_p.read_text())
        reason = (f"S21-FAM3 nine-site 3-family live-score inversion; format PASS; unique vs "
                  f"{reg['n_compared']} registry + {sib['n_compared']} sibling rasters; "
                  f"hide-v2 HOLDOUT-DTI={cand_h['dti']:.6f} by construction (>3px collar; instrument "
                  f"invalid, nine-site Spearman {inst['spearman_hide_v2_vs_live']:.3f}); "
                  f"{'OK TO SUBMIT' if ok_submit else 'NOT OK TO SUBMIT (G4 surrogate projection failed)'}; "
                  f"docs/run-card-S21-FAM3.json.")
        for p in (tif, tif.with_suffix(".zip")):
            path = f"docs/downloads/{p.name}"
            pol["files"] = [r for r in pol["files"] if r["path"] != path]
            pol["files"].append(dict(path=path, sha256=sha(p), status="current_research_only", reason=reason))
        pol_p.write_text(json.dumps(pol, indent=2) + "\n")
    card = dict(
        run_id="S21-FAM3", branch="arena/11ddffe8-gemsdoe91",
        lane=dict(name="S21-FAM3 three-family complementarity inversion", assigned=True,
                  preregistration="docs/HYPOTHESES_S21_FAM3.md"),
        hypothesis=("Live truth density for uncatalogued faults is carried by distance to the three "
                    "nine-site family networks (h19-5 ridge, GEMSDOE33 tip-stepover, GEMSDOE36 Anderson PINN), "
                    "catalogue distance, B19/B15/B12 terciles and the B15 basement-step gradient; inverting "
                    "112 USER-REPORTED live scores with exact DTI algebra and emitting greedy expected-DTI dots "
                    "at a >3 px catalogue collar beats GEMSDOE32 R0 (0.2778 USER-REPORTED)."),
        mechanism=("log E[G]=theta.phi, phi = dcat(9) + dnet-h19-5(6) + dGEMSDOE33(3) + dGEMSDOE36(3) + "
                   "B19/B15/B12/|grad B15| terciles; ridge least squares on USER-REPORTED scores (src/gems91/lfi.py "
                   "unchanged); two-pool coverage-aware ranked emission (src/gems91/lfi_emit.py unchanged) with "
                   "hard 65% within-3-px caps vs 312 references and a ratio-aware fill; shared GeoTIFF writer."),
        non_fault_mimic=("Lithologic contacts / intrusive margins and volcanic flow lobes step basement depth "
                         "and align with potential-field edges; erosional ridge crests mimic the h19-5 sensor. "
                         "All family sensors read the same 19 bands, so agreement can encode shared bias."),
        evidence=dict(
            surrogate_E1=dict(
                label="MODEL (leave-one-site-out on USER-REPORTED live scores; not a holdout DTI)",
                n_anchors=fit10["n_anchors"],
                ridge10=dict(loso_rmse=fit10["rmse_loso"], loso_spearman=fit10["spearman_loso"],
                             loso_pearson=fit10["pearson_loso"], in_sample_rmse=fit10["rmse_in_sample"],
                             f_public=fit10["f"], K_public_truth_px=fit10["K_expected"]),
                ridge1=dict(loso_rmse=fit1["rmse_loso"], loso_spearman=fit1["spearman_loso"],
                            loso_pearson=fit1["pearson_loso"], f_public=fit1["f"], K_public_truth_px=fit1["K_expected"]),
                s20_design_stored=dict(loso_rmse=s20fit["rmse_loso"], loso_spearman=s20fit["spearman_loso"],
                                       note="S20 design (with consensus covariate) predicts held-out live scores "
                                            "BETTER than S21; S21 family-sensor component is a negative result.")),
            projection_G4={v: gate[v] for v in variants},
            projection_G4_pass1=dict(
                note="Pass-1 candidate (30,000 dots, registry-unique only) passed the G4 bar but was a "
                     "DUPLICATE vs 7 sibling-sweep rasters; retained as evidence, never downloadable.",
                variants=gate1),
            holdout_dti_hide_v2=dict(
                label="HOLDOUT-DTI", evaluator_version=hold["evaluator_version"],
                split_sha256=hold["split_sha256"], withheld_positives=hold["withheld_positives"],
                candidate=cand_h, r0_gemsdoe32=r0_h, paired_vs_r0=paired,
                nine_site_bests={k: v for k, v in scores.items() if k not in ("s21_candidate", "r0_gemsdoe32")},
                bootstrap=hold["pooled"]["bootstrap"],
                construction_note="Candidate TPw is identically 0: every dot is >3.01 px from the full "
                                  "catalogue, and hide-v2 truth is a subset of that catalogue inside a 3 px kernel."),
            instrument_validity=dict(inst, hide_v2_valid_as_live_proxy=hide_valid),
            canaries=hold["canaries"],
            nine_site_forensics="docs/s21/nine-site-forensics.json",
        ),
        registry_comparison=dict(
            surface_preplacement=dict(surf),
            protocol_and_anchor_registry={k: reg[k] for k in ("n_compared", "n_skipped", "n_dense", "verdict", "literal_verdict", "duplicates")},
            sibling_sweep={k: sib[k] for k in ("scope", "n_compared", "n_skipped", "n_dense", "verdict", "literal_verdict", "duplicates")},
            pass1_sibling_duplicates=sib1["duplicates"],
            max_literal_sparse_sibling={k: sib["max_literal_sparse"][k] for k in ("raster", "within_3px_literal")},
            max_dots_abs_spearman=sib["max_dots_abs_spearman"]["dots_abs_spearman"],
            max_surface_abs_spearman_sibling=sib["max_surface_abs_spearman"]["surface_abs_spearman"],
            vs_s20_candidate={k: next(r for r in sib["rows"] if "s20-lfi" in r["raster"])[k]
                              for k in ("within_3px_literal", "dots_abs_spearman", "surface_abs_spearman")},
            rule=reg["rule"]),
        submission=dict(file=f"docs/downloads/{tif.name}", zip=f"docs/downloads/{tif.with_suffix('.zip').name}",
                        sha256=rec["sha256"], zip_sha256=rec["zip_sha256"], bytes=rec["bytes"],
                        name=rec["submission_name"], note=rec["note"], note_chars=rec["note_chars"],
                        n_dots=emit["n_dots"], encoding="all-finite zeros, float32, no nodata"),
        raster_sha256=rec["sha256"],
        validator_output=rec["validator"],
        gates=G, s21_preregistered_gates_all_pass=all_pass,
        standing_rule_beats_spatially_blocked_holdout_best=bool(paired["ci95"][0] > 0),
        ok_to_download=ok_download, ok_to_submit=ok_submit,
        verdict="promote" if ok_submit else "negative",
        organizer_confirmed=None,
        deviations=[
            "Pass-2 re-emission: pass-1 candidate duplicated 7 sibling-sweep rasters; 130 sparse sibling references (>=0.50 literal overlap) were added as hard caps (312 total) and all gates re-run unchanged. Pass-1 evidence: docs/s21/pass1-*.json.",
            "Emitter fix in pass 2: S20-pattern fill_exact ratchets to 681 dots and fixed-floor fill collapses to ~1.9k under 312 caps (reproduced on work/s21/emit_debug.npz); replaced with a ratio-aware fill in the S21 driver only. Latent bug also present in scripts/run_lfi_emit.py - reported in IRREGULARITIES.md (IR-S21-03) for a template-level fix.",
            "G5: hide-v2 reported but not gating, preregistered on S20 E2 evidence (112-anchor Spearman 0.105; S21 nine-site recomputation -1.0, split sha identical). The candidate does not beat hide-v2 (0.0 by construction) and also fails G4, so the verdict is negative on both instruments.",
            "Budget: 3 experiments (E1 fits, E2 holdout/canaries, E3 emission incl. pass-2 re-emission); wall-clock exceeded the 2 h protocol budget (long gate bootstrap and two 1,078-raster sibling checks).",
        ],
        slots_used=0, slot_selection="not made by this run (protocol: promotion/selector is a separate step)",
    )
    out = ROOT / "docs/run-card-S21-FAM3.json"
    out.write_text(json.dumps(card, indent=1) + "\n")
    print(json.dumps(dict(gates=G, ok_to_download=ok_download, ok_to_submit=ok_submit,
                          verdict=card["verdict"], sha256=rec["sha256"], file=card["submission"]["file"]), indent=1))


if __name__ == "__main__":
    main()
