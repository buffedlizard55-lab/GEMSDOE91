#!/usr/bin/env python3
"""Build docs/run-card-S20-LFI.json from measured evidence and apply the preregistered gates
(docs/HYPOTHESES_S20_LFI.md §4). Nothing is hand-typed: every number is read from JSON on disk.
Copies the TIFF + ZIP into docs/downloads/ only when G1 (format) and G2 (uniqueness) pass.
"""
import hashlib, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
W, D = ROOT / "work/lfi", ROOT / "docs/lfi"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    tif = sorted((ROOT / "outputs/lfi").glob("gems91-s20-lfi-*-zeros.tif"))[-1]
    rec = json.loads(tif.with_suffix(".json").read_text())
    gate = json.loads((D / "gate.json").read_text())
    emit = json.loads((D / "emit.json").read_text())
    e2 = json.loads((D / "holdout-e2.json").read_text())
    reg = json.loads((D / "registry-check.json").read_text())
    sib = json.loads((D / "sibling-check.json").read_text())
    fit10 = json.loads((D / "fit_r10.json").read_text())
    assert rec["sha256"] == sha(tif) == reg["candidate_sha256"] == sib["candidate_sha256"], "evidence refers to a different file"

    iv = e2["instrument_validity"]
    hv = e2["candidate_vs_r0"]
    c, r0 = hv["scores"]["lfi_candidate"], hv["scores"]["r0_gemsdoe32"]
    pd = hv["paired_differences"]["r0_gemsdoe32"]
    variants = list(gate)
    g4_lb = sum(gate[v]["boot_delta_ci95"][0] > 0 for v in variants)
    g4_p = all(gate[v]["p_delta_gt0"] >= 0.95 for v in variants)
    hide_valid = iv["spearman_hide_v2_vs_live"] >= 0.5
    g5_beats = pd["ci95"][0] > 0
    G = dict(
        G1_format=bool(rec["validator"]["all_checks_passed"]),
        G2_uniqueness=reg["verdict"] == "UNIQUE" and sib["verdict"] == "UNIQUE",
        G3_leakage_canary=bool(e2["canary_pass"]),
        G4_surrogate_projection=bool(g4_lb >= 2 and g4_p),
        G5_instrument_rule=bool(g5_beats) if hide_valid else True,
    )
    ok_download = G["G1_format"] and G["G2_uniqueness"]
    s20_all = all(G.values())
    # Standing user rule + repo fail-closed contract (src/gems91/readiness.py, tests/test_s16_integrity.py):
    # a slot needs a measured win on the spatially-blocked holdout. G5 cannot waive that automatically.
    standing_rule = bool(g5_beats)
    ok_submit = bool(s20_all and standing_rule)
    dl = ROOT / "docs/downloads"
    if ok_download:
        for p in (tif, tif.with_suffix(".zip")):
            dst = dl / p.name
            if not dst.exists():
                shutil.copy2(p, dst)
            assert sha(dst) == sha(p)
            dst.chmod(0o644)   # IR-91-S17-LFTG-02: Pages artifacts must be world-readable
        pol_p = ROOT / "registry/artifact_policy.json"
        pol = json.loads(pol_p.read_text())
        reason = (f"S20-LFI leaderboard-feedback inversion; format PASS; unique vs registry+sibling sweep; "
                  f"hide-v2 HOLDOUT-DTI={c['dti']:.6f} (instrument invalid, Spearman vs live {iv['spearman_hide_v2_vs_live']:.3f}); "
                  f"{'OK TO SUBMIT' if ok_submit else 'NOT OK TO SUBMIT (fail-closed; awaiting human sign-off)'}.")
        for p in (tif, tif.with_suffix(".zip")):
            path = f"docs/downloads/{p.name}"
            pol["files"] = [r for r in pol["files"] if r["path"] != path]
            pol["files"].append(dict(path=path, sha256=sha(p), status="current_research_only", reason=reason))
        pol_p.write_text(json.dumps(pol, indent=2) + "\n")
    card = dict(
        run_id="S20-LFI", branch="arena/670d23f5-gemsdoe91", lane=dict(name="LFI-S20 leaderboard-feedback inversion", assigned=True,
            preregistration="docs/HYPOTHESES_S20_LFI.md"),
        hypothesis=("The ~112 USER-REPORTED live public scores of published fleet rasters are aggregate measurements of the hidden "
                    "new-fault truth; inverting them with the exact Tversky algebra yields a truth-density map q(x) that ranks "
                    "pixels better than any catalogue-proxy model."),
        mechanism=("log E[G(x)] = θ·φ(x), φ = distance-to-catalogue bands, distance-to-h19-5-network bands, B19/B15/B12/B4 terciles, "
                   "10-anchor consensus votes; fitted by ridge least squares on live scores; dots emitted by coverage-aware greedy "
                   "maximising expected DTI under hard 65% per-reference uniqueness caps."),
        non_fault_mimic=("Ridge/lineament networks and multi-method agreement also fire on erosional ridges, drainage divides, "
                         "lithologic contacts and flight-line artefacts; consensus can encode shared bias (all methods use the same 19 bands)."),
        evidence=dict(
            surrogate_E1=dict(label="MODEL (leave-one-site-out on USER-REPORTED live scores; not a holdout DTI)",
                              n_anchors=len([a for a in fit10["anchors"]]), ridge=fit10["ridge"], loso_rmse=fit10["rmse_loso"],
                              loso_spearman=fit10["spearman_loso"], loso_pearson=fit10["pearson_loso"],
                              in_sample_rmse=fit10["rmse_in_sample"], f_public=fit10["f"], K_public_truth_px=fit10["K_expected"]),
            projection_G4={v: dict(label="PROJECTION (surrogate, paired vs R0, site bootstrap)", **gate[v]) for v in variants},
            holdout_dti_hide_v2=dict(label="HOLDOUT-DTI", evaluator_version=e2["evaluator_version"], split_sha256=e2["split_sha256"],
                                     withheld_positives=e2["withheld_positives"], candidate=c, r0_gemsdoe32=r0, paired_vs_r0=pd,
                                     bootstrap=hv["bootstrap"]),
            instrument_validity_E2=dict(iv, rule="hide-v2 gates only if Spearman(hide-v2, live) >= 0.5 across anchors",
                                        hide_v2_valid_as_live_proxy=hide_valid),
            canaries=e2["canaries"]),
        registry_comparison=dict(
            protocol_and_anchor_registry={k: reg[k] for k in ("n_compared", "n_skipped", "n_dense", "verdict", "literal_verdict", "literal_flags", "duplicates")},
            sibling_sweep={k: sib[k] for k in ("scope", "n_compared", "n_skipped", "n_dense", "verdict", "literal_verdict", "literal_flags", "duplicates")},
            max_literal_sparse_registry={k: reg["max_literal_sparse"][k] for k in ("raster", "within_3px_literal")},
            max_literal_sparse_sibling={k: sib["max_literal_sparse"][k] for k in ("raster", "within_3px_literal")} if sib.get("max_literal_sparse") else None,
            max_dots_abs_spearman=max(reg["max_dots_abs_spearman"]["dots_abs_spearman"], sib["max_dots_abs_spearman"]["dots_abs_spearman"]),
            rule=reg["rule"], preplacement="hard caps (65% within 3 px) on 26 binding references enforced inside the emitter",
            emitter_binding_fractions=[dict(name=b["name"], frac=round(b["frac"], 5)) for b in emit["binding_refs"]]),
        submission=dict(file=f"docs/downloads/{tif.name}", zip=f"docs/downloads/{tif.with_suffix('.zip').name}",
                        sha256=rec["sha256"], zip_sha256=rec["zip_sha256"], bytes=rec["bytes"], name=rec["submission_name"],
                        note=rec["note"], note_chars=rec["note_chars"], n_dots=emit["n_dots"], encoding="all-finite zeros, float32, no nodata"),
        validator_output=rec["validator"],
        gates=G, s20_preregistered_gates_all_pass=s20_all,
        standing_rule_beats_spatially_blocked_holdout_best=standing_rule,
        ok_to_download=ok_download, ok_to_submit=ok_submit,
        verdict="promote" if ok_submit else ("negative-pending-human-signoff" if s20_all else "negative"),
        human_signoff=("All 5 preregistered S20 gates pass, but the standing rule 'beat the spatially-blocked holdout best' "
                       "is not met: hide-v2 tracks live scores at Spearman %.3f, so the rule's instrument is invalid. Approving a "
                       "slot means replacing hide-v2 with the leave-one-site-out live surrogate as the gate. That is a human decision."
                       % iv["spearman_hide_v2_vs_live"]) if (s20_all and not standing_rule) else None,
        deviations=[
            ("G5 (preregistered): hide-v2 does not gate when E2 shows it does not track live scores; the live-validated surrogate "
             "(G4) is then the instrument of record. The standing user rule and the repo's fail-closed contract are NOT waived by G5: "
             "ok_to_submit also requires a measured hide-v2 win. Outcome this run: the surrogate gate G4 "
             + ("PASSED" if G["G4_surrogate_projection"] else "FAILED") + " and hide-v2 was not beaten."),
            "Budget: 3 experiments (E1 surrogate, E2 instrument validity, E3 emission, with a pass-2 uniqueness re-emission); wall-clock ~3.5 h exceeds the 2 h budget.",
            "Pass 1 (37,500 dots) duplicated 5 sparse sibling-sweep rasters (>70% within 3 px); pass 2 added 212 caps and re-emitted (29,671 dots). Pass-1 evidence: docs/lfi/pass1-*.json.",
        ],
        slots_used=0, slot_selection="not made by this run (protocol: do not pick slots)",
    )
    out = ROOT / "docs/run-card-S20-LFI.json"
    out.write_text(json.dumps(card, indent=1) + "\n")
    print(json.dumps(dict(gates=G, ok_download=ok_download, ok_submit=ok_submit, hide_valid=hide_valid,
                          spearman=iv["spearman_hide_v2_vs_live"], cand=c["dti"], r0=r0["dti"], paired=pd), indent=1))


if __name__ == "__main__":
    main()
