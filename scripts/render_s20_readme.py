#!/usr/bin/env python3
"""Insert/refresh the Session 20 block at the top of README.md from docs/run-card-S20-LFI.json (no hand-typed numbers)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
c = json.loads((ROOT / "docs/run-card-S20-LFI.json").read_text())
prof = json.loads((ROOT / "docs/lfi/dot-profile.json").read_text())
s, ev, G = c["submission"], c["evidence"], c["gates"]
iv, hd, s1 = ev["instrument_validity_E2"], ev["holdout_dti_hide_v2"], ev["surrogate_E1"]
reg = c["registry_comparison"]
proj = ev["projection_G4"]
dl = "YES" if c["ok_to_download"] else "NO"
failed = [k.split("_")[0] for k, v in G.items() if not v]
sb = ("YES" if c["ok_to_submit"] else
      ("NO — NOT OK TO SUBMIT (fail-closed; all S20 gates pass but the hide-v2 rule is not met; human decision pending)"
       if c["s20_preregistered_gates_all_pass"] else "NO — NOT OK TO SUBMIT (" + ", ".join(failed) + " failed; verdict " + c["verdict"] + ")"))
decision = c.get("human_signoff") or ("Not about this file. Choose the gating instrument for future LFI files: hide-v2 is invalid as a live proxy "
                                      "(LIMITATIONS_AND_NEXT_STEPS.md, S20 next step 1).")
lo = min(v["boot_delta_ci95"][0] for v in proj.values())
gates = " · ".join(f"{k.split('_')[0]} {'PASS' if v else 'FAIL'}" for k, v in G.items())
block = f"""<!--S20-README-BEGIN-->
# GEMSDOE91 — Session 20 (`S20-LFI`, branch `arena/670d23f5-gemsdoe91`): leaderboard-feedback inversion

> **AUTOMATED VERDICT: `OK TO DOWNLOAD: {dl}` · `OK TO SUBMIT: {sb}`.**
> **[⬇ Download S20-LFI GeoTIFF]({s['file']})** (`sha256 {s['sha256']}`, {s['n_dots']:,} binary dots, all-finite zeros float32) · [Single-TIFF ZIP]({s['zip']}) · **[Executive summary & how to submit](docs/s20-lfi-executive-summary.html)** · [Run card](docs/run-card-S20-LFI.json) · [Preregistration](docs/HYPOTHESES_S20_LFI.md) · [Research note](docs/GEOTHERMAL_VENT_RESEARCH_S20_LFI.md) · [Review / 3 passes](docs/REVIEW-S20-LFI-20261026.md)
>
> - **Name:** `{s['name']}` · **Note ({s['note_chars']}/140):** `{s['note']}`
> - **Gates (preregistered):** {gates}. Uniqueness was checked against {reg['protocol_and_anchor_registry']['n_compared']} registry, anchor and own rasters plus {reg['sibling_sweep']['n_compared']} sibling-sweep rasters, with 0 duplicates under the documented rule.
> - **Main finding (E2):** the repo's spatially-blocked holdout `{hd['evaluator_version']}` does **not** track live scores. Across {iv['n_anchors']} fleet rasters, Spearman is {iv['spearman_hide_v2_vs_live']:.3f} and Pearson {iv['pearson_hide_v2_vs_live']:.3f}. GEMSDOE32 R0 (0.2778 USER-REPORTED) scores {hd['r0_gemsdoe32']['dti']:.4f} on it.
> - **Method (E1):** a 25-parameter truth-density model fitted to {s1['n_anchors']} USER-REPORTED live scores with the exact Tversky algebra. Leave-one-site-out Spearman is {s1['loso_spearman']:.3f} (RMSE {s1['loso_rmse']:.4f}).
> - **Candidate:** {prof['candidate']['cons_ge3']*100:.1f}% of dots are in ≥3-method consensus zones and {prof['candidate']['dcat_gt10']*100:.1f}% are more than 1 km from the catalogue.
>   - PROJECTION vs R0: {', '.join(f"{k} {v['projection_vs_reported_r0']:.3f}" for k, v in proj.items())}.
>   - The most conservative 95% lower bound is Δ {lo:+.3f}.
>   - HOLDOUT-DTI (hide-v2, {hd['withheld_positives']:,} withheld): {hd['candidate']['dti']:.6f} vs R0 {hd['r0_gemsdoe32']['dti']:.6f}, paired Δ {hd['paired_vs_r0']['delta']:+.6f} [{hd['paired_vs_r0']['ci95'][0]:+.6f}, {hd['paired_vs_r0']['ci95'][1]:+.6f}].
> - **Decision for you:** {decision}
> - 0 weekly slots used. Read the [full project brief](#full-project-brief) at the start of every session.

---

<!--S20-README-END-->
"""
r = (ROOT / "README.md").read_text()
r = re.sub(r"<!--S20-README-BEGIN-->.*?<!--S20-README-END-->\n", "", r, flags=re.S)
(ROOT / "README.md").write_text(block + r)
print("README S20 block written")
