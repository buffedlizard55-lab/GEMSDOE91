# Three-Pass Audit & Scientific Review — Session 14 (`S14-UCSD`, 2026-10-24)

**Branch:** `arena/c1c46404-gemsdoe91`  
**Preregistration:** [`docs/HYPOTHESES_S14.md`](HYPOTHESES_S14.md) (`sha256: 513905bfb1945085…`)  
**Machine-Readable Run Card:** [`docs/run-card-S14.json`](run-card-S14.json) / [`evidence/s14_ucsd_metrics_20261024.json`](../evidence/s14_ucsd_metrics_20261024.json)  
**Primary Range-Safe `[0, 1]` GeoTIFF:** [`docs/downloads/gems91-s14-ucsd-e3-20261024T223000Z-60e02944-zeros.tif`](downloads/gems91-s14-ucsd-e3-20261024T223000Z-60e02944-zeros.tif) (`sha256: 1f8fa6e9e2c881d50c8518b9d9ed980c98d9d1115980fd176676ecb11b3517ee`, `276,513` bytes, `54,000` binary `{0.0, 1.0}` dots)  
**Single-Member ZIP:** [`docs/downloads/gems91-s14-ucsd-e3-20261024T223000Z-60e02944-zeros.zip`](downloads/gems91-s14-ucsd-e3-20261024T223000Z-60e02944-zeros.zip) (`sha256: d56d87a3a3517bd7fb0c55a36f4c9a0e0b0e431678c42f5176ebeb0a6e9fd18f`, `242,058` bytes)

---

## Pass 1 — Implementation & Verification Summary

1. **Prior-Session Next Steps Completed First:**
   - Restored all 15 competition/external files (`registry/data_manifest.json`), 8 canonical registry rasters (`data/registry/`), and all 64 frozen comparison-inventory references (`62` in `data/fleet_registry/` + `2` retracted `GEOD25m10` blobs `ce7a7e3a6270fef922ade0b47a26f5287e16071b` and `26b756e08bd365a61aa3cb22f5a87af223bc9fe5` in `data/retracted_geod/`), resolving `IR-91-PTHA-02`.
   - Audited and expanded `PTHA.TOPO_FEATURE_NAMES` across `X_static`, `X_s11`, `X_s12`, `X_ptha`, and `X_ucsd` so the 100% Topography-Blind Subsurface HGB Specialist (`HGB-Sub`) trains strictly on the `70` non-topographic features.
2. **Pre-Registered 5 Geological Hypotheses & 3-Experiment Execution (`src/gems91/ucsd.py`, `scripts/run_s14_lane.py`):**
   - **Rule 4 Single-Feature Leakage Canary (`evidence/s14_leakage_canary_receipt.json`):** Executed across all `115` static candidate features on `gems91-hide-recover-v1.0` (`60,988` withheld positives) prior to model training. All `115/115` passed (`worst_feature = ptha_step_elev_abs` at `0.66470 <= 0.90`).
   - **`E1` (`H14-1`, `99` features):** `0.222353 HOLDOUT-DTI` (`95% CI [0.209338, 0.236149]`, `+0.015947` vs `S11-MHTR E2`).
   - **`E2` (`H14-1 + H14-2 + H14-3b`, `125` features):** `0.233970 HOLDOUT-DTI` (`95% CI [0.222390, 0.246528]`, `+0.027564` vs `S11-MHTR E2`).
   - **`E3` (`H14-1 + H14-2 + H14-3`, Regime-Coupled Dinkelbach Allocation):** **`0.261556 HOLDOUT-DTI`** (`95% CI [0.245857, 0.277258]`, **`+0.016955` vs `S13-PTHA E3 = 0.244601`** with paired 95% CI `[+0.008966, +0.024760]`, and **`+0.055150` vs `S11-MHTR E2 = 0.206406`** with paired 95% CI `[+0.047038, +0.063392]`).
   - **Full-Map Blind Off-Catalogue USGS SGMC Control (`62,122` positives `>300 m` from catalogue):** **`0.105103 BLIND-SGMC-CONTROL-DTI`** (`+0.009717` vs `R0 = 0.095386`, `+0.004288` vs `S13-PTHA E3 = 0.100815`).

---

## Pass 2 — Bug, Edge-Case & Assumption Audit (Found & Fixed)

1. **Cgroup Memory Pressure from Multi-Memmap Page Caching (`FIXED`):**
   - *Finding:* Slicing 5 open `np.memmap` files (`2.47 GB` combined) inside a `3,939 MB` RAM / `0` swap container caused OS page-cache accumulation and `1.4 GB` temporary `float64` allocations during `StandardScaler.transform` + `np.clip`.
   - *Fix:* Added `arr._mmap.madvise(mmap.MADV_DONTNEED)` after every memmap slice read, used `chunk = 250_000` with in-place `np.clip(X_sc, -6.0, 6.0, out=X_sc)`, and backed Stage-2 auto-context inference with `data/derived/s14_ac_scratch.dat`.
2. **Dinkelbach Fold Emitter Quota Re-Emission Defect (`FIXED`):**
   - *Finding:* An initial implementation of `dinkelbach_regime_coupled_fold_emit` discarded the dots emitted by `PTHA.dinkelbach_fold_independent_emit` and re-emitted `n_fold_budget` dots via `SC.spac_three_regime_submodular_emit`, which recomputed `q_floor` inside a single quadrant and forced `32%` off-corridor quotas in barren quadrants.
   - *Fix:* Synthesized the multi-regime physical crest surface (`0.58 * ucsd_core_crest + 0.24 * ucsd_sub_edge + 0.18 * wash_bridge_grid`) across `piedmont_mask | subsurface_mask` and passed it directly into `PTHA.dinkelbach_fold_independent_emit`, lifting `E3` to **`0.261556 HOLDOUT-DTI`**.
3. **Validator Verdict String Mismatch in `run_s14_lane.py` (`FIXED`):**
   - *Finding:* `scripts/run_s14_lane.py` initially checked `audit["validators"]["gems91_gates_verdict"] == "VALID_TO_DOWNLOAD"` instead of `"CERTIFIED"`, causing `RD.gates(card)["format"]` to evaluate to `False`.
   - *Fix:* Updated `scripts/run_s14_lane.py` and `docs/run-card-S14.json` to check `"CERTIFIED"`, restoring `RD.gates(card)["format"] == True` while keeping `RD.submission_ready(card) == False`.
4. **Root `docs/run-card.json` Preservation (`FIXED`):**
   - *Finding:* `scripts/verify_current_artifact.py` and `tests/test_submission_portal.py` validate the historical `CED91` run card at `docs/run-card.json`, whereas session-specific run cards live at `docs/run-card-S11..S14.json`.
   - *Fix:* Kept `docs/run-card.json` intact for `CED91` verification and wrote Session 14's run card to `docs/run-card-S14.json` and `evidence/s14_ucsd_metrics_20261024.json`.

---

## Pass 3 — Line-by-Line Verification Against Prompt & Official Sources

- **Prompt preserved in `README.md`:** Verified via `test_readme_contains_full_starting_brief_and_visible_negative_download`.
- **PhD analysis of `GEMSDOE32` (`0.2778` CLAIM) & leaderboard highs (`0.3195` / `0.4413`):** Documented with strict provenance labels (`CLAIM` vs `HOLDOUT-DTI` vs `ORGANIZER-CONFIRMED`) in `docs/HYPOTHESES_S14.md`, `docs/SESSION_BRIEF_S14.md`, and `docs/s14-ucsd.html`.
- **5 ranked candidate geological hypotheses (`H14-1`..`H14-5`):** Frozen before holdout runs in `docs/HYPOTHESES_S14.md`.
- **Parallel-Run Protocol Rules 1–6:**
  - Rule 1 (Uniqueness): Canonical registry `<= 48.13%`, external dotted fleet `<= 44.68%`, all 44 external non-lattice rasters `<= 67.06% <= 70.0%` (`calib_h25ctx_01280 = 66.85%`, `calib_h28ridge_01839 = 67.06%`), surface `|\rho| <= 0.2428 <= 0.90`.
  - Rule 2 (Shared tools): Used `scripts/evaluate_holdout.py` and `scripts/submission_writer.py`.
  - Rule 3 (Score labels): Every metric labelled `HOLDOUT-DTI` (`gems91-hide-recover-v1.0`, `60,988` withheld positives, 95% CI) or `BLIND-SGMC-CONTROL-DTI`; `ORGANIZER-CONFIRMED = null`.
  - Rule 4 (Leakage canary): `115/115` features passed (`max symmetric AUC = 0.66470 <= 0.90`).
  - Rule 5 (Budget): Exactly 3 experiments (`E1`, `E2`, `E3`) executed in `238.1s` (`< 7200s`).
  - Rule 6 (Run card): Emitted in `docs/run-card-S14.json` and at the end of the session response.
