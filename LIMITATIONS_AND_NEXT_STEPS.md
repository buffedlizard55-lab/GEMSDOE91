# Current limitations and next steps — S17-CPAD, 2026-10-25

All 15 competition and external public inputs (`sample_submission.tif`, `existing_faults.tif`,
`gems-geodawn-numerical-features.tif`, GDR #1562 WellSpring CSV, USGS DS-1052 SGMC,
GeoDAWN radiometrics, and 100 m LiDAR scarp features) plus all 95 comparison-registry
rasters (`registry/s17_comparison_inventory.json`) were restored and SHA-256 verified in
Session 17 (`0` missing entries).

## What Session 17 (`S17-CPAD`) resolved from Session 16's handoff priorities

1. **Quarantined the legacy S13–S15 oracle buffer-moat leak (`IR-91-S17-01`) and established the true label-blind incumbent bar.**
   Forensic inspection of `scripts/run_s13_lane.py:87` (`_fold_active_and_eligible`) proved that Sessions 13–15 passed `~fold.buffer_mask` into test-time dot placement, creating an 8-km oracle exclusion moat around hidden truth that inflated `S14-PTAC E2` from **`0.194221`** to `0.267782`. Re-fitting and evaluating `S14-PTAC E2` honestly on canonical label-blind `vendor/gems57/spatial.folds` (`INCUMBENT-PTAC-LB`) established the true common-instrument incumbent bar: **`0.194221 HOLDOUT-DTI`** (`95% CI [0.173855, 0.213233]`).
2. **Closed every `Band 12` / `Band 19` topographic leak (`IR-91-S17-02`) with programmatic `0.0` bitwise verification.**
   All 14 subsurface `CPAD` columns and the 100-column Pure-Subsurface specialist (`STRICT_TOPO_FEATURE_NAMES`) were proven bitwise invariant (`max_abs_diff == 0.0`) under `+1,000 m` `Band 12` and `×50` `Band 19` perturbations.
3. **Implemented exact training-domain Bayes reference-odds calibration (`IR-91-S15-06`) and excluded `>= 2.5 km` bowls (`IR-91-S15-07`) + banned `dist_known_fault_px` (`IR-91-S17-03`).**
4. **Achieved the highest strict label-blind `gems57-pooled-hide-v2` score in `GEMSDOE91`.**
   `cpad_e1` (`gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif`, `37,654` binary `{0, 1}` dots, SHA-256 `690c10998798d3abd54f6a1ec1c12e56c4243d1967ede7b63a533b9ddd628cdd`) scored **`0.198183 HOLDOUT-DTI`** (`95% CI [0.177759, 0.217830]`, `60,988` withheld positives), beating `INCUMBENT-PTAC-LB` (`0.194221`, paired `+0.003962`), `CED91` (`0.070886`, paired `+0.127296`), and `S16-PGRD` (`0.069397`, paired `+0.128786`), plus **`0.068585 BLIND-SGMC-CONTROL-DTI`** (`+78.1%` over `S16-PGRD = 0.038501`).

## Remaining blockers preventing live DrivenData submission (`ok_to_submit = False`, `slots_used = 0`)

1. **Dense blanket / lattice registry overlap (`Rule 1`) and shared-backbone overlap.**
   `cpad_e1` passed `95/95` pre-placement full-footprint Spearman checks (`max |rho| = 0.2191 <= 0.90`) and `50/50` preceding fleet rasters on 3-px dot overlap (`max = 0.6168 <= 0.70`, including `GEMSDOE32 R0 = 0.4927 <= 0.70`), then stopped fail-closed at row `51/95` on `data/fleet_registry/r11_greedy_mp.tif` (`272,853` positive pixels = `5.28%` of footprint, `3-px overlap = 0.8725 > 0.70`), alongside the synthetic 5-px calibration lattice `calib_r13lattice_00904.tif` (`206,895` dots -> `>= 82.34%` mathematical lower bound at `37,654` dots; `IR-S16-03`). Diagnostic post-stop checks also show `82.96%` 3-px dot overlap with in-repo `S14-PTAC E2` (shared `DD + MHTR + SPAC + PTHA + HVDC` HGB backbone) vs `14.96%` on `S16-PGRD` and `13.53%` on `CED91`.
2. **Paired 20-km block-bootstrap 95% CI vs `INCUMBENT-PTAC-LB` straddles zero.**
   While `cpad_e1 - incumbent_ptac_lb = +0.003962 HOLDOUT-DTI`, the 1,000-draw 20-km paired spatial-cluster 95% CI is `[-0.001766, +0.010077]`, so `readiness.py`'s `beats_comparable_best` gate (`ci95[0] > 0`) conservatively evaluates `False`.
3. **Unassigned single-method paragraph (`assigned_lane = False`).**
   The standing prompt leaves `[PASTE ONE METHOD]` blank; `S17-CPAD` was preregistered as a provisional single lane and remains fail-closed until explicitly assigned by orchestration.
4. **Separate human weekly-slot selector & unauthenticated external portal (`separate_selector = False`).**
   Outbound sandbox access permits only GitHub, npm, and PyPI hosts (`drivendata.org`, `gdr.openei.org`, `usgs.gov`, and `docs.nlr.gov` cannot be live-fetched from inside the sandbox). Live weekly submission allowance (`3/week` cap), legal/data-rights attestation, and organizer score receipts (`0.2778`, `0.3195`, `0.4413` remain unverified `CLAIM`s; `ORGANIZER-CONFIRMED: null`) require an authenticated human browser check.
5. **GitHub Pages legacy mode.**
   Scheduled workflow runs refresh `docs/fleet-audit.json` as an Actions artifact, while live Pages serves committed `main` snapshots (`HTTP 403` when attempting to switch Pages publisher mode via integration token).

## Priority order for Session 18

1. **Protocol / orchestration decision on dense blanket references (`r11_greedy_mp.tif` 272k dots & `calib_r13lattice_00904.tif` 207k dots) and explicit `[PASTE ONE METHOD]` assignment.** Never silently drop registry files or inject anti-registry noise.
2. **Backbone-orthogonal paradigm to clear BOTH in-repo `S14-PTAC E2` (`<= 70%` 3-px overlap) AND beat `cpad_e1` (`0.198183 HOLDOUT-DTI`) with paired `ci95[0] > 0`.**
   Any future tree model reusing the `DD + SPAC + PTHA + HVDC` tabular stack will naturally converge onto >75% 3-px overlap with `S14-PTAC E2` and `S17-CPAD E1`. To achieve true `<70%` dot overlap against `S14-PTAC E2` while exceeding `0.198183`, test a genuinely distinct spatial operator family (e.g., multi-scale steerable/Gabor directional filter-bank CNN / 2-D U-Net or graph minimum-cost fault-network linker trained strictly on `spatial.folds` with `80 px` buffer and `Band 12`/`19` dropout).
3. **Human selector check on DrivenData.** Authenticate remaining weekly slots and record at least one `ORGANIZER-CONFIRMED` submission-page receipt in `ledger/submissions.csv` before any further threshold calibration.
