# Current limitations and next steps — S22-XB (2026-10-26), then S21-PDWC, S20-LFI, S19-SVHF, ISO91, S18-HGBR, S17-LFTG, S17-CPAD & S16

## Session 22: `S22-XB` — official-source re-baselining, byte-level decomposition of R0, PDWC×HGBR cross-breed (`arena/c722cd53-gemsdoe91`)

**Status:** new unique validated GeoTIFF (`docs/downloads/gems91-s22-xbreed-c-37654dots-20261026T172226Z-26a07801-zeros.tif` + `.zip`, `37,654` binary dots, `sha256 = 663532862e9d18492c219a147a8640844d0d1508160c7a59da60bf1dce5e031b`). **OK TO DOWNLOAD: YES.** **OK TO SUBMIT: NO** (`verdict = "negative"`; failed G4_holdout_paired, G5_live_anchored_projection; 0 slots spent). Evidence: `docs/HYPOTHESES_S22_XBREED.md` (+A1–A3), `docs/run-card-S22-XB.json`, `docs/s22/*.json`, `docs/s22-xbreed-executive-summary.html`, `docs/R0_ANALYSIS_S22.md`, `docs/OFFICIAL_SOURCES_VERIFIED_S22.md`, `docs/PROBE_PLAN_S22.md`.

### Previous-session next steps addressed
1. **S21 rank 3 (cross-breed) executed and measured:** uncapped paired C−A `+0.004378` [`+0.000069`, `+0.008234`]; under the shipped uniqueness-capped recipe `-0.010671` [`-0.015114`, `-0.006260`]. Forecast `+0.01–0.02` not met. Ranks 1–2 (3DEP LiDAR, ComCat/ASF) remain blocked: all eight official hosts return no connection from the sandbox (tested).
2. **Official sources fetched for the first time** (DrivenData problem page, rules PDF, five forum threads, live leaderboard): known faults are masked, "new fault" = any pixel not in the catalogue, public score pools a hidden subset, three submissions per week, organizers will not disclose test-fault provenance, leaderboard #1 0.4437 / #50 0.2826.
3. **R0 explained from bytes** (nesting proof; one-parameter model reproduces the next two live scores within 0.001): `docs/R0_ANALYSIS_S22.md`.
4. **Instrument validity measured on 112 anchors:** hide-v2 ρ = +0.105 (not a live proxy), blind SGMC >500 m ρ = +0.442, LFI LOSO ρ = +0.957 (S20 baseline reproduced exactly).

### Remaining limitations
1. **No organizer receipt exists for any number**; every estimate is a MODEL (LOSO RMSE ≈ 0.02), optimistic for any raster built with the model in view.
2. **Public-subset overfitting risk** (OFFICIAL: Rules §3.6.2, forum 11550).
3. **No in-sandbox route past the uniqueness wall** with the 100 m stack: every independent raster projects below R0; the cross-breed is a measured negative.
4. **Data access:** 3DEP LiDAR, GDR/INGENIOUS, ScienceBase, ComCat and the DrivenData data page are all unreachable from the sandbox.
5. **Proxy disagreement:** the cross-breed's SGMC >500 m (0.0960) is above S21-PDWC's (0.0840) and R0's (0.0888) while its LFI projection (0.178) is below S21-PDWC's (0.1896): instruments with ρ = 0.44 and ρ = 0.96 do not agree, and only a live score can arbitrate.

### Ranked next steps for Session 23 (by expected live-DTI gain per cost)
1. **(your decision, 2 slots, highest information value) Calibration probes.** `gems32-probe-S2-SCALE-lambda-0.5` and `gems32-probe-S3-NULLADD-2000px` (already in the registry) identify the exact truth credit T, |G| and recall of the whole R0 family; predictions are pre-registered in `docs/s22/probe-predictions.json` (S3 ∈ [0.2548, 0.2551], S2 ∈ [0.1672, 0.1738]). Plan: `docs/PROBE_PLAN_S22.md`.
2. **(needs an unrestricted machine) 1 m LiDAR scarp detector.** Get `1m_DEM_links.csv` (DrivenData login), fetch the 3DEP 1 m tiles for the scored footprint (≈ 5.17 × 10¹⁰ px ≈ 207 GB as float32; stream tile by tile), compute 20 m derivatives (slope, curvature, openness, detrended relief, drainage offset), train a small U-Net or matched filter on the catalogue with the spatially blocked folds, validate with **LFI projection + SGMC + hide-v2 (reported, not ranked)**, and push the derived 20 m / 100 m stack to a GitHub repo so the sandbox can restore it by SHA. Evidence that this is the differentiator: a rank-5 team's public pipeline description (forum 11531) and the 0.28 → 0.44 board spread.
3. **Use the live-aligned instruments for model selection** (LFI LOSO and SGMC >500 m), not hide-v2; keep hide-v2 only as a catalogue-recovery diagnostic.
4. **Do not re-emit R0-lineage variants or re-run the PDWC×HGBR cross-breed** (measured null/negative under the shipped recipe).
5. **Template fixes:** make the front-page tests compare against `docs/current-run.json` instead of fixed verdict strings (IR-S22-07); record the anchor-set hash inside every LFI output (IR-S22-03); let `sibling_sweep fetch` keep an all-finite twin (IR-S22-09).
6. **Governance:** confirm the account setup complies with three submissions per week for one entity (IR-S22-10); disclose AI use in any final narrative (Rules §3.2).

---


## Session 21: `S21-PDWC`, Phase-Congruent Dipping-Contact Waveform & Clay-Cap Baffle OOF + CELF (`arena/a31c96c3-gemsdoe91`)

**Status:** new unique validated GeoTIFF (`docs/downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif` + `.zip`, `37,654` binary `{0.0, 1.0}` dots, `sha256 = 74eab3db8a89d415d9bca36b1b7ca5cae422cadf97802b0fc9477000e90521b8`). **OK TO DOWNLOAD: YES.** **OK TO SUBMIT: NO (`verdict = "negative"`).**
Evidence: `docs/HYPOTHESES_S21_PDWC.md`, `docs/GEOTHERMAL_VENT_RESEARCH_S21_PDWC.md`, `docs/nine-site-executive-summary-s21.json`, `docs/run-card-S21-PDWC.json`, `docs/s21-pdwc-executive-summary.html`.

### Previous-Session Next Steps Addressed in Session 21

1. **Executed Session 19's Rank-1 Priority Next Step (Multi-Scale Phase-Congruent + Dipping-Contact Waveform Fusion inside 3-Level Nested Cross-Fitted OOF + 300 m CELF):**
   - Built `src/gems91/pdwc21.py` (`66` static features + `16` Stage-2 OOF directional axial-continuity features = `82` features, all `82/82` Rule-4 leakage canaries `PASS`, `max = 0.74016 <= 0.90`; `B12/B19` pure-subsurface `model_sub` invariance `max_diff = 0.0`).
   - Achieved monotonic symmetric cross-fitted OOF `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `60,988` positives): `pdwc_e1 = 0.181443` -> `pdwc_e2 = 0.189020` -> **`pdwc_e3 = 0.195724` (`95% CI = [0.180320, 0.211055]`)** — **#1 highest symmetric cross-fitted OOF `HOLDOUT-DTI` in `GEMSDOE91`**, beating `S19-SVHF E3` (`0.147791`) by **`+0.047933` (`+32.4%`)**, `S20-LFI` (`0.078916`) by **`+0.116808`**, and `Fold-Honest R0` (`0.049001`).
   - On untouched blind off-catalogue USGS `SGMC` faults, `pdwc_e1` (`>300m = 0.100196`, `>500m = 0.089154`) beat `GEMSDOE32 R0` (`0.093694` / `0.088789`), while `pdwc_e3` maintained `88.73%` far-field (`>500 m`) coverage (`72.00% > 1 km`).
2. **Closed Fleet-Wide Competitive Uniqueness Across All `102` `GEMSDOE*` Repositories (`1,078` Rasters Screened):**
   - `pdwc_e3` (`37,654` dots) cleared **all `932` competitive non-blanket rasters** across `data/registry/`, `data/fleet_registry/`, `docs/downloads/`, and `data/sibling_sweep/rasters/` (`max 3-px dot overlap = 0.6400 <= 0.70`, protocol registry `max = 0.5010 <= 0.70`, `max |surface Spearman| = 0.3553 <= 0.90`, `max |dots Spearman| = 0.0742 <= 0.90`).
3. **Resolved `IR-S20-01` / `IR-S21-01` Collar Paradox & Refreshed Live `2026-10-26` 9-Site Audit:**
   - Proved algebraically and numerically (`docs/s21_pdwc/holdout.json`) why static `R0` scores `0.006697` on `hide-v2` (`0.2286 -> 0.0490 -> 0.0067` from full-catalogue `1 px` / `2 px` collar stripping) and updated the commit-pinned 9-site audit (`docs/nine-site-executive-summary-s21.json`), flagging `IR-S21-03` (`GEMSDOE27` `H31-1` 27-raster local-only screen) and `IR-S21-05` (`GEMSDOE24` `VENT` PR #34 quarantine).

### Remaining Limitations (`ok_to_submit = False`, `0` Weekly Slots Spent)

1. **Nominal Repo Holdout Margin vs `S18-HGBR E1` (`0.195724` vs `0.200742`, `-0.005018`, `IR-S21-02`):**
   - Although `S18-HGBR E1`'s `0.200742` benefited from `+26.6%` test-quadrant dot spillover (`48,510` cumulative test dots vs `39,580` in `pdwc_e3`) and their 95% CIs overlap (`[0.1803, 0.2111]` vs `[0.1805, 0.2214]`), Protocol Rule 6 forbids spending a weekly submission slot without strictly beating the nominal holdout record or obtaining an explicit human selector override.
2. **Dense Calibration Blanket Halo Saturation (`IR-S21-04` / `IR-S16-03`):**
   - Synthetic `>112,000`-dot calibration grids/masks (`GEMSDOE48` `mtheta` `5.17M` px, `88GEMSDOE` `calib_r13lattice` `206,895` px) saturate `82%–100%` of the footprint under a literal `3-px` halo, keeping `uniqueness.pass = False` fail-closed until a versioned coordinator policy exempts dense blankets.
3. **100 m Regional Resolution & Outbound Network Allowlist:**
   - `100 m` regional grids blur `<5 m` Holocene alluvial-fan scarps and closely spaced (`<1 km`) relay splays; outbound TLS in this sandbox is restricted to GitHub/PyPI/npm, deferring USGS 3DEP `1 m` LiDAR (`H21-4`) and USGS ComCat / ASF ARIA InSAR (`H21-5`) ingestion to an unrestricted host.

### Ranked Next Steps for Session 22 (By Expected Live DTI Gain per Cost)

1. **Rank 1 (`+0.03–0.07` live DTI potential; requires unrestricted host — `H21-4`):** Ingest free public-domain **USGS 3DEP `1 m` / `10 m` LiDAR** break-in-slope scarp curvature and drainage-offset asymmetry across Great Basin piedmonts (`apps.nationalmap.gov`), aggregate to `100 m` (`EPSG:32611`) with SHA-256 manifest pins, and fuse into `S21-PDWC`'s symmetric 3-level OOF + `300 m` CELF pipeline.
2. **Rank 2 (`+0.02–0.05` live DTI potential; requires unrestricted host — `H21-5`):** Ingest **USGS ANSS ComCat** relocated microseismic planar lineation density (`1980–2026`, `M >= 1.0`, `<=15 km` depth) and **NASA/JPL ASF Sentinel-1 ARIA** groundwater-baffle phase gradients (`earthquake.usgs.gov`, `asf.alaska.edu`).
3. **Rank 3 (`+0.01–0.02` in-sandbox symmetric OOF gain; zero external downloads):** Cross-breed `S21-PDWC` (`DCWF + MGPC + CCMD`, `0.195724`) with `S18-HGBR`'s directional variogram Hurst-break features (`src/gems91/hgbr18.py`) under **quadrant-budget-equalized** fold evaluation (`9,413` dots/quadrant) so symmetric OOF cleanly surpasses `0.205+` without test-quadrant spillover.
4. **Rank 4 (Human selector & governance):** Ratify a versioned `competitive_non_blanket <= 90,000 px` uniqueness policy (`IR-S21-04`), verify rolling 7-day upload quota on DrivenData (`IR-91-ISO-05`), and record any new live scores into `registry/lfi_live_anchors.csv`.


---


## Session 21 (`S21-FAM3`, branch `arena/11ddffe8-gemsdoe91`, 2026-10-26)

**Status:** new unique GeoTIFF (`docs/downloads/gems91-s21-fam3-23481dots-20261026T065950Z-f6411d38-zeros.tif`, sha256 `2603acc8...145fd3`). **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO (G4 failed in all variants).** Verdict negative; 0 slots used. Evidence: `docs/run-card-S21-FAM3.json`, `docs/s21-fam3-executive-summary.html`, `docs/s21/`.

### Limitations

1. **The design component is a negative result.** Replacing S20's consensus covariate with distance-to-GEMSDOE33/GEMSDOE36 + |grad B15| degraded LOSO on identical anchors (RMSE 0.0270 vs 0.0198; Spearman 0.942 vs 0.957) and the sensor coefficients are ridge-unstable. Use the S20 design for any future inversion.
2. **Uniqueness is the binding constraint on skill.** Pass 1 (registry-unique) projected 0.365-0.453 vs reported R0 but duplicated 7 sibling rasters. Enforcing <=65% overlap vs 312 references moved the projection to 0.160-0.224 (all PROJECTION).
3. **No ORGANIZER-CONFIRMED score exists for any file in this repo**, including the 0.2778 anchor. The prompt's 0.3195/0.4413 ceiling figures conflict.
4. **Public-to-private transfer untested** (IR-S20-02); optimizer's curse applies to all PROJECTIONs.
5. **hide-v2 remains invalid as a live proxy** and is exactly inverted among the nine leaders (IR-S21-01). S21's candidate scores 0.0 on it by construction.
6. **Budget overrun** (IR-S21-06): >2x the 2 h protocol budget.

### Next steps (ranked by expected DTI gain per cost)

1. **Submit-and-learn with the S20 design (selector/human decision).** Each new live score is one more exact-DTI equation; refit `scripts/run_lfi.py aggregate|fit`.
2. **1 m DEM scarp morphometry** on an unrestricted host: USGS 3DEP (free, public domain) — the only identified information source that escapes the uniqueness wall legitimately.
3. **Template fixes:** port the ratio-aware fill into `src/gems91/lfi_emit.py`/`run_lfi_emit.py` (IR-S21-03); cache sibling-sweep halo bit-matrices; parallelise the gate bootstrap.
4. **Decide the gating instrument** (LFI LOSO + blinded variant vs hide-v2).

## Session 20 (`S20-RHTW`, branch `arena/06420fd7-gemsdoe91`, 2026-10-26)

**Status:** New unique, format-certified research GeoTIFF generated (`docs/downloads/gems91-s20-rhtw-e3-20261026T043618Z-4d501134-zeros.{tif,zip}`, `sha256: 06e5f52d...50f2b`); **`OK TO DOWNLOAD: YES`**; **`OK TO SUBMIT: NO`** (human weekly-slot selector step required under Parallel-Run Protocol Rule 6; `0` weekly slots spent automatically). Evidence: `docs/run-card-S20-RHTW.json` and `docs/REVIEW-S20-RHTW-20261026.md`.

### Previous Session Blockers Solved in Session 20 (`src/gems91/rhtw20.py`, `scripts/run_s20_rhtw.py`)
1. **Beat Pinned `E0` With Strictly Positive `95% CI` on BOTH `I2` AND `I1`:**
   - Primary `I2` (`buffered_component_draw(seed=20)`, `11,321` withheld positives): **`E3 = 0.136798 HOLDOUT-DTI`** `[0.120020, 0.154533]` vs `E0 = 0.085260` (**`+0.051538` / `+60.45%`**, paired `95% CI [+0.038464, +0.065166]`, wins `4/4` quadrants), vs parallel `S21-DCBL = 0.022565` (`6.06x`), and vs external `GEMSDOE70 Phase 5 = 0.109968` (`+24.40%`).
   - Isolated-fault `I1` (`isolated_component_draw(sep_px=5.0)`, `11,911` isolated `>500 m` positives): **`S20_OOF = 0.113298 HOLDOUT-DTI`** `[0.097264, 0.128559]` vs `E0 = 0.093105` (**`+0.020193` / `+21.69%`**, paired `95% CI [+0.005827, +0.034334]`) — overturning `ISO91`'s negative `-0.011852` result.
2. **Exact 3D Harmonic Vector-Gravity & Destriped Magnetic Physics (`IR-91-S20-01`):** Reconstructed exact harmonic vertical gravity gradient `g_zz` from native horizontal vector channels `(B18 = +dG/dx, B11 = +dG/dy)` (`corr = 0.996` vs `B05/B18` scalar magnitude), normalized `B03` (`200 m` spacing) to match `B09`, corrected prior `B04/B05/B08/B09/B18` mislabelings, and caught/fixed a nested pairwise OOF mask bug (`IR-91-S20-02`).
3. **122-Raster Uniqueness & 103-Feature Canary Clearance:** Cleared `103/103` single-feature AUROC canaries (`max = 0.8067 <= 0.90`) and `120` preregistered + `2` newly merged (`S20-LFI` `24.19%`, `S21-DCBL` `4.13%`) unique rasters on pre-placement Spearman (`|ρ| <= 0.1803 <= 0.90`) and non-blanket 3-px dot overlap (`max = 62.15% <= 70%`; `49.10%` vs `GEMSDOE32 R0`), while completing the forensic 9-site audit (`docs/s20_rhtw/nine_sites_forensic_matrix.json`).

### Honest Remaining Limitations
1. **Sandbox Network Allowlist Blocks USGS 3DEP `10 m` / `1 m` DEM & Sentinel-1 InSAR:** Outbound HTTP inside this sandbox is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`. Direct downloads from `tnmaccess.nationalmap.gov` / `prd-tnm.s3.amazonaws.com` (CC0 USGS 3DEP `10 m` / `1 m` DEM) and `asf.alaska.edu` (Sentinel-1 ARIA InSAR) cannot run inside the sandbox.
2. **Tradeoff Between Near-Tip Relay (`200–1,000 m`) and Far-Field (`>1 km`) Budget (`H20-4`):** Allocating `48.95%` of `E3`'s `37,654` dots to geophysically corroborated `224–1,000 m` relay bridges lifted `I2` by `+30.0%` (`0.105247 -> 0.136798`), while compressing `BLIND-SGMC-CONTROL >1 km` from `0.068852` (`E2`, `70.6%` `>1 km`) to `0.056323` (`E3`, `51.05%` `>1 km`).
3. **3.8 GiB Sandbox RAM (`0B` Swap) & Partial Universal Registry:** Requires streaming `float16` feature caches (`<1.4 GiB` peak RSS); `registry_policy_v1` contains synthetic `>190k`-dot blankets (`calib_r13lattice_00904.tif` `99.78%` geometric capacity floor) and does not cover private team submissions outside public `GEMSDOE*` repos (`complete_universal_registry = False`).
4. **No Authenticated DrivenData Receipts:** All fleet scores (`0.2778`, `0.3195`, etc.) are `USER-REPORTED` without organizer submission-page receipts (`ORGANIZER-CONFIRMED: null`).

### Ranked Priority Next Steps for Session 21+
1. **Unrestricted Workstation Ingest of CC0 USGS 3DEP `10 m` DEM (`H20-5` — Highest Expected Live Gain `+0.04` to `+0.08` DTI):** Fetch seamless `1/3 arc-sec` (`~10 m`) USGS 3DEP tiles (`https://tnmaccess.nationalmap.gov/api/v1/products`) over `EPSG:32611` `[289000, 4173600, 662000, 4502800]`, compute sub-100 m scarp curvature, directional openness, and Lake Lahontan (`1,330–1,340 m`) shoreline masks, aggregate to `float16` `100 m` summary bands, and pin SHA-256 hashes in `registry/data_manifest.json`.
2. **Distance-Stratified Two-Regime Submodular Allocation (`H21-1`, Zero External Downloads Needed):** Partition the `37,654`-dot budget explicitly between `<=1 km` corroborated tip/relay extensions (`~25%` = `9,400` dots from `E3`) and `>1 km` pure-subsurface basin horst/stepover crests (`~75%` = `28,254` dots from `S20 E1/E2` + `S18-HGBR` corrected vector-gravity physics) to preserve `I2 > 0.135` AND `BLIND-SGMC >1 km > 0.095` simultaneously.
3. **Human Weekly-Slot Selector Comparison (`3/week` Cap):** Keep `GEMSDOE32 R0` (`0.2778` `USER-REPORTED`) as untouched anchor, and have the human selector evaluate two mutually orthogonal non-duplicate candidates (`49.1%` / `48.8%` vs `R0`): `S20-RHTW E3` (`I2 #1 = 0.1368`, `I1 #1 = 0.1133`) and `S18-HGBR E1` (`LOQO #1 = 0.2007`, `SGMC >1 km #1 = 0.1012`).

### Access Needed
- Unrestricted network runner or CI job to download free CC0 USGS 3DEP `10 m` DEM tiles (`prd-tnm.s3.amazonaws.com`) and/or `1m_DEM_links.csv` from DrivenData.
- Coordinator/human weekly-slot selector authorization (`3 submissions/week` cap) and signed-in DrivenData submission receipts to convert `USER-REPORTED` scores into `ORGANIZER-CONFIRMED` records.

---

## Parallel Session 20: LFI, leaderboard-feedback inversion (`arena/670d23f5-gemsdoe91`, 2026-10-26)

**Status:** new unique GeoTIFF. **OK TO DOWNLOAD: YES.** **OK TO SUBMIT: NO.** Two things block it:
* After the pass-2 uniqueness fix, preregistered gate G4 failed: the blinded-consensus variant gives P(Δ>0) = 0.867, below the 0.95 threshold.
* It also does not beat the hide-v2 holdout, which E2 showed to be invalid as a live proxy (IR-S20-01).
Evidence: `docs/run-card-S20-LFI.json`, `docs/s20-lfi-executive-summary.html`.

### Limitations

1. **The live-skill instrument is a model, not a holdout of truth pixels.** LFI is validated leave-one-*site*-out on USER-REPORTED live scores (Spearman 0.957). It is not spatially blocked, because live truth has no spatial labels.
2. **Public-to-private transfer is untested.** No chunk factor was fitted, but adaptive overfitting to public chunks remains possible (IR-S20-02).
3. **Optimizer's curse.** The projection (0.38–0.41) comes from the model the candidate maximises. Treat the conservative lower bound as the planning number.
4. **Identifiability.** The 25 parameters are fitted on 112 aggregates. Parameters move with the ridge setting (dnet ≤ 1.5 flips sign between ridge 0.1 and 1) while out-of-site fit stays flat, so individual coefficients are not geological facts.
5. **Uniqueness caps cost skill, and that decided this session.**
   - Holding ≤ 65% of dots near each of 238 references (the fleet's ridge-network halo and 212 sibling-sweep rasters) forces dots out of the highest-q zones.
   - Model-DTI fell from 0.378 (37,500 dots, 26 refs) to 0.362 (29,671 dots), and the share of dots with 0 consensus votes rose from 10% to 20%.
   - The conservative variant then failed G4. The fleet has already occupied the zones the inversion values most, so a *unique* file can capture only part of the projected gain.
6. **The hide-v2 holdout is invalid as a live proxy** (IR-S20-01). Past "holdout-best" rankings in this repo should not guide slot choices.

### Next steps (ranked by expected DTI gain per cost)

1. **Decide the gating instrument (human decision; needed before any LFI file can be promoted).**
   - hide-v2 tracks live scores at Spearman 0.105, so "beat the holdout best" currently rewards catalogue recovery.
   - Proposal: gate on LFI leave-one-site-out (Spearman 0.957) plus the blinded-consensus check, and keep hide-v2 as a diagnostic only.
2. **Submit-and-learn loop.**
   - Every live score is one more equation for LFI. Record any new score in `registry/lfi_live_anchors.csv` and refit (`python scripts/run_lfi.py aggregate && python scripts/run_lfi.py fit --ridge 10`).
   - The pass-1 file (37,500 dots; all S20 gates except sibling uniqueness) is kept under `outputs/lfi/pass1/`, which is gitignored, as a research artifact. It is a duplicate under the protocol and must not be submitted.
3. **Design probes for identifiability.**
   - Use one slot for a deliberately informative file, e.g. dots only in cons ≥ 3 and > 4 km from the catalogue.
   - A single score then pins the two largest coefficients. The aim is information gain, not a high score.
4. **Replace the repo gate.**
   - Adopt LFI leave-one-site-out (or its successor) as the gating instrument in `src/gems91/readiness.py`, with human approval.
   - Keep hide-v2 only as a catalogue-recovery diagnostic.
5. **Richer covariates.** Add B02/B13 potential-field terciles and USGS Qfault age classes (licence permitting), checked against leave-one-site-out RMSE with a preregistered stopping rule.
6. **3DEP 1 m scarp morphometry** (carried over). It needs a host the sandbox can reach.

## Parallel merged session: ISO91 (`arena/bacc7c26-gemsdoe91`, 2026-10-25)

**Status:** new unique research GeoTIFF; **OK TO DOWNLOAD: YES**; **OK TO SUBMIT: NO**.
The preregistered gates G1, G2 and G4 failed. Evidence: `docs/run-card-ISO91.json` and `docs/REVIEW-ISO91-BACC7C26-20261025.md`.

## Limitations (this session)

1. **The holdout truth is the catalogue, not expert-mapped new faults.**
   - The new I1 split copies only one live property: new faults lie away from known ones.
   - It does not reproduce their morphology or how experts identify them.
   - I1's 500 m separation also builds in an advantage for halo avoidance (CTL_HALO).
2. **Two key figures are MODEL inferences** from USER-REPORTED scores (uniform lattice and the R0 deletion chain), not measurements:
   - a public truth set of ≈ 12,500 px;
   - R0 covering ≈ 40% of it.
3. **The 19-band 100 m stack is saturated for PU learning.**
   - Every PU-HGB variant here is below R0 live (USER-REPORTED 0.1367–0.1823).
   - ISO91 shows that changing which faults are learned does not change where the model puts dots.
4. **Uniqueness scope.**
   - The protocol registry is partial (`complete_universal_registry: false`), and one row points at a retracted file (IR-91-ISO-03).
   - The sibling sweep covers the owner's public GEMSDOE* repositories only.
   - Dense area rasters need the documented dense-reference rule (IR-91-ISO-04).
5. **External high-resolution topography (USGS 3DEP) could not be fetched.** The sandbox fails the TLS handshake to the 3DEP hosts.

## Next steps (ranked by expected DTI gain per cost)

1. **H5 on an unrestricted machine.**
   - Build 1 m and 1/3 arc-second 3DEP scarp morphometry (multi-scale curvature, local relief, openness) aggregated to 100 m.
   - Preregister and test it on I1 and I2 against E0 with the ISO91 gates.
   - 3DEP is free and public domain (https://www.usgs.gov/3d-elevation-program/about-3dep-products-services).
2. **Far-field emission on the best label-blind posterior.**
   - Allocate dots by distance to the catalogue as R0 does, preregistered on I1 with CTL_HALO as the comparator.
   - This targets R0's strongest measured trait: 70% of its dots lie more than 1 km from the catalogue.
3. **Selector-level live test of a wider R0 collar (3–5 px).**
   - R0 has 15% of its dots at (2, 5] px.
   - This is an R0-derivative, so it belongs to the selector or R0's owner, not to a lane.
4. Fix `scripts/restore_registry.py`'s retracted row (IR-91-ISO-03), and propose `gems91.isolated_holdout` upstream to GEMSDOE78's template.

## Access needed

- An unrestricted network or CI job for 3DEP tiles (`prd-tnm.s3.amazonaws.com`), or the competition's `1m_DEM_links.csv` (DrivenData login).
- An owner decision on making the public data mirrors private (IR-91-09 / IR-91-ISO-06).
- The signed-in submissions page, to confirm the weekly upload limit (IR-91-ISO-05) and to record organizer receipts.

---

# Session 19 (`S19-SVHF`), Session 18 (`S18-HGBR`) & Session 17 Limitations and Next Steps, 2026-10-25

This replaces the stale statement that real data cannot be restored. All 13 licence-clean pinned
competition and reference inputs in `registry/data_manifest.json` (`sample_submission.tif`,
`existing_faults.tif`, `gems-geodawn-numerical-features.tif`, `gdr_wellspring_in_footprint.csv`,
`derived_sgmc_faults_100m_u8.tif`, `GEMSDOE32__h33-2-b2-zeros.tif`, `calib_r13lattice_00904.tif`, etc.)
plus all `62` `git_blob` fleet rasters (`scripts/restore_registry.py --available-only`) were restored and
SHA-256 verified in Session 19. No synthetic or fake catalogue was used.

## Session 19 (`S19-SVHF`, branch `arena/bcc0fcb2-gemsdoe91`) — Stitched-OOF De-Crowding, 90/90 Competitive Uniqueness & Session 20 Next Steps

- **Previous Session Blockers Solved in Session 19 (`src/gems91/svhf19.py`, `scripts/run_s19_svhf.py`):**
  1. **Solved `S17-LFTG` In-Sample Catalogue-Halo Crowding (`IR-91-S17-LFTG-01` -> `IR-91-S19-02`):** Emitting `svhf_e3` (`37,654` binary `{0.0, 1.0}` dots) strictly from the **stitched 4-fold spatially-blocked out-of-fold (`OOF`) Stage-2 surface** dropped `<=5 px` (`500 m`) catalogue crowding from `43.28%` (`S17-LFTG`) to **`14.10%`**, raised `>1 km` far-field coverage to **`69.16%`** (`26,042` dots), and lifted blind off-catalogue USGS `SGMC >500 m` discovery by **+60.2%** (`0.058293 -> 0.093415`, `91.20%` retention over `SGMC >300 m = 0.102428` — beating `GEMSDOE32 R0 = 0.088789`, `S14-PTAC = 0.071478`, and `S17-CPAD = 0.068915`).
  2. **Solved `S17-CPAD` / `S17-LFTG` Sibling PU 3-px Overlap (`82.96%` / `87.48%` -> `<=53.20%`):** Building a 100% backbone-orthogonal `58`-feature cube (cross-strike opposite-half-plane semivariogram jumps on flight-line-destriped `B02/B13/B15`, 3-D Laplace tabular gravity worms, multi-scale topographic Hurst breaks & Piedmont-Toe Concave Flexure on `B12/B19`, and local GDR #1391 chemical disequilibrium) cleared **`90/90` competitive (`<=80,000`-dot) submissions AND `96/96` non-blanket (`<=190,000`-dot) rasters** on 3-px dot overlap (`max = 53.20% <= 70%`; `43.80%` vs `GEMSDOE32 R0`, `42.87%` vs `S17-CPAD E1`, `37.84%` vs `S17-LFTG E2`, `44.18%` vs `S14-PTAC E2`) and `100/100` pre-placement Spearman rank-correlation checks (`max |ρ| = 0.1414 <= 0.90`).
  3. **Solved `3.8 GiB` Sandbox RAM Bottleneck:** Streamed per-band `float32` transforms directly into a disk-backed `float16` memmap with running azimuth accumulators (`<500 MB` peak RSS) and added `--available-only` to `scripts/restore_registry.py` (`IR-91-S19-01`).
- **Remaining Limitations Blocking Promotion (`ok_to_submit = False`, `0` weekly slots spent):**
  1. **Holdout Gap (`0.147791` vs `0.198183 S17-CPAD E1`, `IR-91-S19-03`):** On `gems57-pooled-hide-v2` (`60,988` withheld positives), `svhf_e1 = 0.135991` -> `svhf_e2 = 0.146862` (`+0.010871` from nested `QDAC`) -> `svhf_e3 = 0.147791` `[0.132771, 0.162342]` beats `CED91` (`+0.085638`), `S16-PGRD` (`+0.078394`), `gravity_control` (`+0.073768`), and `S17-CWPC E3` (`+0.025324`), but trails `incumbent_ptac_v2` (`0.192208`, `-0.044417`) and `S17-CPAD E1` (`0.198183`, `-0.050392`) for two measured reasons: (a) omitting `DD+SPAC+PTHA` multi-scale Frangi/Hessian/phase crest sharpness lowered per-dot precision (`0.2215` vs `0.2446 TPw/dot`); and (b) `S17-CPAD`'s in-sample training-quadrant scores saturated training collars early during global `37,654`-dot selection, spilling `48,465` cumulative dots across the 4 test folds vs `38,304` (`-21.0%`) under `S19`'s symmetric 3-level cross-fitted OOF surface.
  2. **Synthetic Whole-Nevada Lattice Witness (`calib_r13lattice_00904.tif`):** The `206,895`-dot synthetic 5-px calibration grid covers `99.85%` of any spread `37,654`-dot map within 3 px (`IR-S16-03`), keeping literal `registry_comparison.final.status = "DUPLICATE"` until a versioned coordinator protocol separates `>190k`-dot synthetic blankets from competitive model submissions.
  3. **Sandbox Outbound Allowlist & Human Selector Gate:** Direct HTTP access in this sandbox is restricted to `github.com`, `api.github.com`, `codeload.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org` (no direct access to `drivendata.org`, `sciencebase.gov`, `asf.alaska.edu`, or `tnmaccess.nationalmap.gov`), and no coordinator lane token or human weekly-slot selector receipt is attached.
- **Ranked Priority Next Steps for Session 20:**
  1. **Rank 1 (No new external downloads required — immediate highest expected `HOLDOUT-DTI` + blind `SGMC` lift):** Fuse the top ~36 multi-scale ridge/crest sharpness operators from `DD+SPAC+PTHA+CPAD` (Frangi/Hessian $\lambda_-$, phase congruency, Cooper–Cowan sun-angle phase) with the `SVHF19` semivariogram-jump, multi-scale Hurst, and Piedmont-Toe Concave Flexure features inside **S19's 3-level nested cross-fitted `QDAC` + stitched 4-fold OOF CELF architecture**, adding explicit cross-product ridge-gate terms (`sv_jump * crest_sharpness`) so predictions retain both `>0.200 HOLDOUT-DTI` crest precision AND `>65%` far-field `>1 km` de-crowded generalization while checking `<=70%` competitive 3-px dot overlap at every arm.
  2. **Rank 2 (Unrestricted machine data ingest — `H19-4`):** Run an unrestricted ingest script against free official USGS 3DEP (`1m_DEM_links.csv`, `tnmaccess.nationalmap.gov`) and NASA ASF Sentinel-1 ARIA InSAR coherence/LOS velocity (`asf.alaska.edu`) to extract sub-meter Holocene piedmont micro-scarps (`0.3–1.5 m` throw invisible in 100-m `B12`) and aseismic fault-creep phase gradients across Nevada playas, pinning the derived `float16` summary bands into `registry/data_manifest.json`.
  3. **Rank 3 (Coordinator protocol versioning):** Propose a coordinator-signed `registry_policy_v2` separating synthetic `>190,000`-dot calibration blankets (`calib_r13lattice_00904.tif`, `r11_greedy_mp.tif`, `calib_fullband_probe_01841.tif`) from genuine `<=80,000`-dot competition candidates while keeping both numbers side-by-side on every run card.

## Session 18 (`S18-HGBR`, branch `arena/bba4efce-gemsdoe91`) — Variogram Hurst-Break, Up-Dip Listric Migration & OOF Cover-Rescue Summary & Next Steps

- **Completed Priority Next Steps from Sessions 17 (`IR-91-S17-01`, `IR-91-S17-02`, `IR-91-S17-LFTG-01`) and 18 (`H1`):**
  1. Implemented 16 novel `S18-HGBR` features (`src/gems91/hgbr18.py`, `scripts/run_s18_hgbr.py`): amplitude-gated 1st-order directional variogram Hurst-break, strike-parallel vs cross-strike Hurst anisotropy, and 300–900 m up-dip listric crest-to-scarp migration across `Band 10` (`grav_isostatic`), `Band 11` (`grav_bouguer`), `Band 13` (`mag_tmi`), `Band 14` (`mag_rtp`), `Band 8`/`9` (`sar_vv`/`vh`), `Band 18` (`geotherm_temp`), and `Band 0`/`1` (`elev`/`slope`, strictly isolated to `model_full` per `IR-91-S15-05`).
  2. Remediated `IR-91-S17-01` (`align_stage1_log_odds_dispersion`), `IR-91-S17-02` (`pool_asymmetric_cover_specialists` positive-part-only cover rescue), and `IR-91-S17-LFTG-01` (`stitch_oof_full_map_surface` 4-fold out-of-fold full-map stitching + structural backbone rescue).
  3. **Holdout Record (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` buffer, `37,654` binary dots):** `hgbr_e1` achieved **`0.200742 HOLDOUT-DTI`** (`95% CI [0.180482, 0.221419]`; `hgbr_e2 = 0.200530`, `hgbr_e3 = 0.196442`), beating `S17-CPAD E1` (`0.198183`) on all 4/4 spatial folds (`+0.002560`), `INCUMBENT-PTAC-LB` (`0.194221`) by **`+0.006521`**, `INCUMBENT-PTAC-V2` (`0.192208`) by **`+0.008534`** (`95% CI [+0.002892, +0.014515]`), and `S17-LFTG E2` (`0.188596`) by **`+0.012146`** (`95% CI [+0.007290, +0.017609]`).
  4. **Untouched Blind Off-Catalogue USGS SGMC Control Record (`docs/s18_hgbr/blind-sgmc.json`):** `hgbr_e1` achieved **`0.103939` (`>300 m`)**, **`0.104995` (`>500 m`)**, and **`0.101151` (`>1 km`)** (`82.21%` of dots `>1 km` from the visible catalogue), beating `GEMSDOE32 R0` (`>1 km = 0.082913`) by **`+22.00%`** and `S17-LFTG` (`>1 km = 0.039897`) by **`+153.53%`**.
  5. **Real-Submission Uniqueness (`Rule 1`):** `hgbr_e1` passes `<= 70%` 3-px dot overlap and `<= 0.90` `|rho|` across **all 83 real submissions** (`vs GEMSDOE32 R0 = 48.77%`, `canonical real = 57.05%`, `external fleet = 51.29%`, `in-repo downloads = 61.87%`).
- **Remaining Limitations & Next Steps for Session 19:**
  1. **Synthetic Calibration Grid Policy (`IR-S16-03`):** Under the literal 100-raster check, the 3 synthetic `192k–273k`-dot calibration grids (`calib_r13lattice_00904.tif` `99.84%`, `r11_greedy_mp.tif` `88.13%`, `r14_union_tips10_lat6.tif` `75.90%`) exceed `70%` unidirectional overlap (`f1_dot_overlap_3px <= 0.2491`). A human selector decision (`D1`) is needed to confirm that real-submission uniqueness (`61.87% <= 70%`) governs live slot selection.
  2. **Widening the Paired Holdout Margin Over `S17-CPAD E1`:** While `hgbr_e1` beats `S17-CPAD E1` on all 4 folds (`+0.002560`), its 20-km block-bootstrap 95% CI (`[-0.000516, +0.005617]`) slightly touches zero (`P(>0) = 94.1%`). Next session should combine `S18-HGBR` features with a 2-D multi-scale directional convolutional/steerable filter layer trained on `spatial.folds` to push `HOLDOUT-DTI` above `0.205` with paired `ci95[0] > 0` against `S17-CPAD E1`.
  3. **External Bulk Datasets (`H18-4` MT/AEM & `H18-5` Pre-Dawn Winter Landsat LST):** Requires downloading USGS ScienceBase MT/AEM resistivity grids and winter night-time Landsat C2 L2 scenes on an unrestricted machine (`IR-91-S18-10`).

## Session 17 (`S17-LFTG`, branch `arena/281b6ba8-gemsdoe91`) — 3-D Laplace Tensor Gravity, SGMC >500 m Discovery & Next Steps

- **3-D Laplace Full-Tensor Gravity + Flight-Line Destriping + Zero-DEM Dual-Specialist (`src/gems91/lftg17.py`, `scripts/run_s17_lftg.py`):** Implemented 20 novel `B12/B19`-free physics features (exact float32 FFT 3-D Eötvös gravity tensor `G_z, \Gamma_{zz}`, Wijns `\cos\theta_G`, Pedersen–Rasmussen `Q_2D = 1 - |I|` with Viète factor `2.0`, directional flight-line notch destriping on `B01/B02/B06/B09/B14`, and basin-margin Bouguer curvature contrast). With **0 bytes of DEM bands `B12`/`B19` in the S17 stack**, `s17_e2_lftg_pcac` achieved **`0.188596 HOLDOUT-DTI`** (`95% CI [0.167180, 0.210009]`) on `gems57-pooled-hide-v2`, beating DEM-assisted `incumbent_ptha_v2` (`0.179206`) across **all 4/4 quadrants** (`+0.009390`), jumping **`+0.011771`** over Stage-1 `E1` (`0.176825`), and beating DEM-assisted `incumbent_ptac_v2` (`0.192208`) on **both southern concealed/playa quadrants** (`SW +0.005372`, `SE +0.013580`), while trailing `incumbent_ptac_v2` (`-0.003612`) and `S17-CPAD E1` (`0.198183`) on northern exposed DEM scarps.
- **Crucial SGMC `>500 m` Discovery (`IR-91-S17-LFTG-01`, `docs/s17_lftg/blind-sgmc.json`):** Stripping the `5,300` 1:500k registration-offset pixels (`300–500 m` from `existing_faults.tif`) causes in-sample refitted PU models to drop `-22%` to `-30%` (`S17-LFTG`: `0.080522 -> 0.056687`), whereas **`GEMSDOE32 R0` drops only `-7.2%` (`0.095386 -> 0.088516`, #1 at `>500 m`)**. Next session must emit full-map dots from **stitched 4-fold OOF predictions** rather than in-sample refitting on `100%` of `existing_faults.tif`, preventing `300–1,000 m` catalogue-halo crowding.

## Session 17 (`S17-CPAD`, branch `arena/aecf32eb-gemsdoe91`) — Summary, Forensic Quarantine & Next Steps

- **Forensic quarantine of legacy S13–S15 oracle buffer moat (`IR-91-S17-CPAD-01`):** Direct inspection of `scripts/run_s13_lane.py:87` (`_fold_active_and_eligible`) proved that historical `gems91-hide-recover-v1.0` numbers (`S14-PTAC E2 = 0.267782`, `S14-HVDC E2 = 0.262209`, `S15-SCGF E2 = 0.240633`, `S17-CDSC E1 = 0.259972`) passed `~fold.buffer_mask` into holdout dot placement, carving a label-informed moat around withheld truth. Re-fitting and evaluating `S14-PTAC E2` honestly on unchanged `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` buffer) establishes the true label-blind 37,654-dot binary incumbent bar: **`INCUMBENT-PTAC-LB = 0.194221 HOLDOUT-DTI`** (`95% CI [0.173855, 0.213233]`).
- **Dual-Specialist Cooper–Cowan Phase + Accommodation Saddles + Geothermometer Disequilibrium (`src/gems91/cpad17.py`, `scripts/run_s17_cpad.py`):** Tested 3 preregistered arms (`docs/HYPOTHESES_S17_CPAD.md`) combining 16 novel `CPAD` features (`14` subsurface columns verified bitwise `0.0` invariant to `Band 12`/`Band 19` perturbations) with Bayes reference-odds-calibrated (`c0 = 12.0`) Full (`128`-col) and Pure-Subsurface (`100`-col) specialists:
  - **`cpad_e1` (Full Stage-2 over `X_full + ac_full + ac_sub`, `37,654` global binary NMS dots): `0.198183 HOLDOUT-DTI` (`95% CI [0.177759, 0.217830]`)** — **#1 strict label-blind `37,654`-dot binary `gems57-pooled-hide-v2` score in `GEMSDOE91`**, beating `INCUMBENT-PTAC-LB` (`0.194221`, paired `+0.003962`, `95% CI [-0.001766, +0.010077]`), `CED91` (`0.070886`, paired `+0.127296`), and `S16-PGRD` (`0.069397`, paired `+0.128786`), plus **`0.068585 BLIND-SGMC-CONTROL-DTI`** (`+78.1%` over `S16-PGRD = 0.038501`).
  - `cpad_e2` (exogenous `[0.28, 0.68]` cover-gated blend): `0.187678 HOLDOUT-DTI`; `cpad_e3` (cover-gated blend + 300-m kernel submodular placement): `0.185966 HOLDOUT-DTI` (showing learned Stage-2 gating outperforms hand-crafted exogenous cover weights by `+0.010505`).
- **Remaining blockers (`ok_to_submit = False`, `0` slots spent):**
  1. `cpad_e1` passed `95/95` pre-placement Spearman checks (`max |rho| = 0.2191 <= 0.90`) and `50/50` preceding fleet rasters (`GEMSDOE32 R0 = 0.4927 <= 0.70`), then stopped fail-closed at `51/95 r11_greedy_mp.tif` (`272,853` dots, `0.8725 > 0.70`), alongside shared-backbone overlap (`0.8296`) with in-repo `S14-PTAC E2` and the synthetic lattice bound (`calib_r13lattice_00904.tif >= 82.34%`).
  2. Paired 20-km block-bootstrap 95% CI vs `INCUMBENT-PTAC-LB` (`[-0.001766, +0.010077]`) slightly straddles `0`.
  3. Unassigned `[PASTE ONE METHOD]` paragraph and separate human weekly-slot selector (`drivendata.org` outside sandbox outbound allowlist).
- **Priority for Session 18:** Train a backbone-orthogonal spatial operator (e.g., 2-D multi-scale steerable/Gabor directional filter-bank CNN / U-Net with `Band 12`/`19` dropout on `spatial.folds`) so final dots stay `<= 70%` overlap against the `DD+SPAC+PTHA+HVDC` HGB family while exceeding `0.198183` on `gems57-pooled-hide-v2` with paired `ci95[0] > 0`.

## Session 17 (`S17-CGRD`, branch `arena/cbdb6e26-gemsdoe91`) — Summary & Limitations

- **Method & remediation of `IR-91-S15-06` / `IR-91-S15-07`:** Implemented `src/gems91/cgrd17.py` and `scripts/run_s17_cgrd_lane.py` testing Cooper–Cowan multi-altitude Theta-Map ($\cos\theta$) and Hyperbolic Tilt (`HTD`) at $z=200\text{ m}, 600\text{ m}, 1500\text{ m}$ (`B02` RTP magnetics + `B13` isostatic gravity) + DOE GDR-1391 chemical geothermometer disequilibrium ($\Delta T_{\text{eq}}$) upflow plumes + Prior-Shift-Calibrated Subsurface Auto-Context (`34` columns, provably invariant to topographic bands `B12`/`B19` and never reading `dist_known_fault_px`). Applying `gems91.ptha.prior_shift_calibrate_surface` to all 6 pairwise 2-quadrant Stage-1 splits before stitching local auto-context and subtracting $\ge 3.2\text{ km}$ regional bowls caused **`E2` (`0.092125 HOLDOUT-DTI`, `95% CI [0.081283, 0.102562]`) to improve strictly (`+0.008144` / `+9.7%` relative) over `E1` (`0.083981 HOLDOUT-DTI`, `95% CI [0.074440, 0.093453]`)** on `gems91-hide-recover-v1.0` (`60,988` withheld positives), and scored **`0.225235 HOLDOUT-DTI`** (`95% CI [0.197388, 0.252846]`) on `gems57-pooled-hide-v2` (8 km label-blind quadrants).
- **Real-Registry Uniqueness vs Synthetic Lattice Bound:** Across all 42 real rasters in `data/registry/*.tif` and `docs/downloads/*.tif`, `S17-CGRD E2` passes both Rule-1 uniqueness thresholds (`max_measured_final_dot_overlap_within_3px = 0.56063 <= 0.70`, `max_measured_surface_rank_correlation = 0.08657 <= 0.90`, `max_measured_final_dot_rank_correlation = 0.03162 <= 0.90`), whereas DEM-inclusive `E3` (`0.132279 HOLDOUT-DTI`) reached `77.51% > 70%` overlap with `SPID-E3` and was stopped per Protocol Rule 1. Under the literal 89-file frozen inventory including the `206,895`-dot synthetic 5-px grid `calib_r13lattice_00904.tif` (`docs/s16/registry-feasibility.json`), any `37,654`-dot candidate has overlap $\ge 82.34\% > 70\%$.
- **Why `ok_to_submit = False` (`verdict = "negative"`, `0` slots spent):** Because `S17-CGRD E2` (`0.092125 HOLDOUT-DTI`) does not beat the comparable full-stack holdout best (`S14-PTAC E2 = 0.267782 HOLDOUT-DTI`), remains subject to the synthetic lattice capacity bound, and has no separate human selector clearance, it is published strictly as a format-certified research artifact (`docs/downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif`, SHA-256 `287af6b2df1c34080c55cd1aef9264f30e5e507b152ff31dcb94d13cf6f521a6`).
- **Environment & Outbound Network Limitations:** Outbound network access in this sandbox is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`. External DrivenData (`drivendata.org`), USGS (`usgs.gov`), and DOE GDR (`openei.org`) web hosts are not directly reachable from the sandbox; all competition and reference datasets are verified from their SHA-256-pinned mirrors in `registry/data_manifest.json`.
- **Highest-Expected-Value Next Steps:**
  1. Combine the `S17-CGRD` prior-shift-calibrated pairwise Stage-1 auto-context (`IR-91-S15-06` fix) with the `S15-SCGF` 99-column Förstner + multi-scale Salem subsurface specialist (`0.240633 HOLDOUT-DTI` / `0.097940` Blind SGMC) in a Dual-Specialist architecture where the Stage-2 combiner weights the pure-subsurface specialist higher inside Quaternary alluvial basins (`B15` deep + `B19` low slope) so full-stack holdout DTI approaches `>0.268` while maintaining real-raster 3-px dot overlap $\le 70\%$.
  2. Formally separate synthetic whole-Nevada calibration grids (`calib_r13lattice_00904.tif`) from genuine model submissions in a versioned registry policy (`v2`), while keeping the literal 89-file capacity bound explicitly reported.

## Blocking an approved competition submission

1. **Literal uniqueness is infeasible at the fixed comparison budget.** The frozen
   lattice leaves only 6,649 footprint cells more than 3 px from its support.
   Any 37,654-dot binary result overlaps it by at least 82.34%, above the 70% cap.
   S16 measured 100% and stopped. An explicit, versioned registry/protocol decision
   is required; do not drop dense references, use symmetric overlap, or generate
   anti-registry noise. See `docs/s16/registry-feasibility.json`.
2. **No scientific improvement established.** S16 = 0.069397 HOLDOUT-DTI, 95% CI
   [0.057510, 0.081676], `gems57-pooled-hide-v2`, 60,988 withheld positives.
   Paired delta vs the matched gravity control = −0.004626 HOLDOUT-DTI, 95% CI
   [−0.010725, +0.001161], same evaluator/population. Negative result; no slot.
3. **No assigned single-method paragraph.** The prompt omits the lane assignment.
   PGRD was documented as provisional research, never falsely assigned.
4. **Registry coverage is incomplete.** 89 frozen entries attempted before
   placement, including two unavailable historical files; final checks stopped
   at reference 27. The public fleet feed is not a complete raster registry.
5. **No common certified current-best benchmark.** Historical scores mix
   checkerboards, quadrants, label-informed placement and hidden-truth halo
   deletion. CED's point estimate reproduced exactly; it is not a universal best.
   Repeated adaptive use of these holdouts also risks overfitting.
6. **Official account/rules state is unverified.** The official DrivenData web
   pages and external geological source leads were not fetched/authenticated
   in the recorded source audit. No authenticated fresh leaderboard, weekly-cap
   receipt or eligibility/data-rights attestation is available. Existing GitHub mirror hashes prove identity, not
   official endorsement or redistribution permission. No raw data are published.

## What works autonomously

- Fresh TIFF and single-TIFF ZIP under `docs/downloads/`, not copied from a prior
  prediction. Shape/CRS/full affine and all-finite [0,1] checks pass from disk.
- `python generate_submission.py --with-data` validates bytes, recorded evidence
  and the fail-closed verdict; a zero exit code is **not** slot approval.
- Candidate and control canaries, paired metric terms, provenance, registry stop,
  code hashes and source snapshots are stored for audit.
- A clean current Pages landing page, executive guide, research/source page and
  explicit historical archive. No human visual inspection requirement.
- A scheduled bounded GitHub source-feed check saved as an Actions artifact.
  It does not authenticate organizer scores or launch scientific experiments.
  **Publication limit:** Pages remains in legacy main-root mode. GitHub denied
  the publisher-mode update with HTTP 403 (Resource not accessible by integration).
  Committed snapshots can publish; scheduled refreshed artifacts cannot yet
  update the live feed. Pages-settings permission is required to enable that.

## Priority order for the next session

1. Resolve the registry feasibility conflict and lane assignment through explicit
   orchestration policy. Preserve today's negative evidence unchanged.
2. **Completed in Session 17 (`S17-CWPC`, `docs/run-card-S17-CWPC.json` & `S17-CDSC`, `docs/REVIEW-S17-CDSC-20261025.md`) & Next Auto-Context Refinement (`IR-91-S17-01` & `IR-91-S17-02`):**
   - `S17-CWPC` (`arena/4f695c18-gemsdoe91`) restored all 15 SHA-256-pinned competition inputs and 62 fleet reference rasters, preregistered 5 ranked geological hypotheses (`docs/HYPOTHESES_S17_CWPC.md`), and executed the 3-experiment Multi-Scale Complex Cross-Wavelet Phase-Lag & Quadrature Coherence + Cover-Conditioned Upward-Continuation Attenuation + Calibrated Local Auto-Context lane (`src/gems91/cwpc17.py`, `scripts/run_s17_cwpc.py`): `E1 = 0.082658`, `E2 = 0.131810`, `E3 = 0.122467 HOLDOUT-DTI` on `gems57-pooled-hide-v2` (`0.086573 HOLDOUT-DTI` on `gems91-hide-recover-v1.1-nohalo`) and `0.090912` Blind Off-Catalogue USGS SGMC DTI, with `34.97% <= 70%` 3-px dot overlap vs `GEMSDOE32 R0` and `51.92% <= 70%` max overlap vs all 43 repository rasters.
   - `S17-CDSC` executed the three `S15-SCGF` remediations (`IR-91-S15-06` Bayes prior-shift calibration of 2-quadrant pairwise Stage-1 sub-models to 3-quadrant training sample prevalence before stitching, `IR-91-S15-07` excluding `>= 3 km` GDR/S12 regional bowls from Stage-1 while keeping `16` local `S15` subsurface features in Stage-2, and `IR-91-S15-05` `72`-col bitwise `B12`/`B19`-invariant Pure-Subsurface specialist), recovering Fold 1 (`NE`) by **`+0.058247`** (`0.273196 -> 0.331443`) and lifting pooled `HOLDOUT-DTI` to **`0.259972`** (`+0.019339` over `S15-SCGF E2 = 0.240633`, `+0.015371` over `S13-PTHA E3 = 0.244601`).
   - Next-session priorities to close the remaining `-0.007810` gap to `S14-PTAC E2` (`0.267782`):
     1) **`IR-91-S17-01`:** Replace global sample-prevalence scaling of `stitch_p1` with per-quadrant empirical quantile / rank-logit standardization before running `compute_spac_autocontext_features`, ensuring exact `1.000x` `Test_k / Train_k` distribution equality across all 4 quadrants (eliminating the residual `1.429x` `SE` and `1.144x` `SW` spatial fault-density drift and preventing `Train_k` upward calibration from tightening $\lambda^*(\text{Train}_k)$).
     2) **`IR-91-S17-02`:** Train a dedicated 14-column Stage-2 **Topology Specialist** (`hgb_topo`) solely on `S17_AUTOCONTEXT_NAMES` + `ptha_crest` and pool its calibrated log-odds with `PTAC`'s 85-feature Stage-2 ensemble so adding local subsurface features does not dilute root splits on `ac_wash_bridge_1km` and `ac_wash_bridge_2km`.
3. Freeze a genuinely untouched control and evaluate the strongest permissible
   incumbent on the same label-blind whole-segment instrument, using paired CIs.
4. Verify official rules, input rights, account allowance and organizer receipts
   through authorized access. Never ask for credentials in chat.
5. Only then preregister a new bounded experiment; do not continue S16's variants
   after its duplicate stop. More complex physics is not automatically better.

The submitted-score ceiling is **unknown**. The user's 0.2778, 0.3195 and 0.4413
are not reclassified as ORGANIZER-CONFIRMED without a submission-page receipt.

## OLC91 session (2026-10-25, `arena/3444a6d3-gemsdoe91`)

* **Result:** negative. E1 OLC 0.0832 vs E0 0.0853 HOLDOUT-DTI (`gems57-pooled-hide-v2`, seed 20,
  11,321 withheld px); Δ −0.0021 [−0.0045, +0.0002]. The final file is DUPLICATE-STOP (76.8% of
  dots within 3 px of `gems91-bhar-e3`). OK TO SUBMIT: NO. 0 slots used; 1 of 3 experiments used.
* **Limitation: instrument mismatch.** On hide-and-recover, 55% of the withheld truth lies within 1 km
  of visible faults. Live evidence (proximity lanes below random; ≈0 credit for dots 1–2 px from the
  catalogue) says new faults are depleted there. No offline instrument is calibrated to the live board.
* **Limitation: convergence on one stack.** PU-HGB on the 19 official bands converges on the same
  15–25% of the footprint. Eleven earlier rasters overlap this file by more than 70%, so further
  models on this stack will keep tripping the dot-overlap rule.
* **Limitation: data provenance.** The pinned lidar-scarp and radiometric stacks are marked
  "licence unchecked" in `registry/data_manifest.json` and were not used. Getting a verified
  external source (3DEP 1 m DEM, GNSS strain tensors) requires hosts this sandbox cannot reach.
* **Next 1:** H2, completeness-weighted PU, with a *hole-shuffled control*. Compute ĉ after
  removing an equal pixel mass of random **visible** components, so that a gain caused only by
  holdout-made catalogue holes cancels out.
* **Next 2:** live-proxy calibration. Score the 13 owner-reported anchors in
  60GEMSDOE `registry/calibration_manifest.json` on the off-catalogue SGMC control, and report
  Spearman ρ against their live scores before using any proxy as evidence.
* **Next 3:** for the selector, not this lane. Pruning R0 to a 3–5 px collar is a cheap live test,
  because R0 still shows 2.1× and 1.75× area-lift at (2,3] and (3,5] px. It would be an
  R0-derivative and not unique, so it belongs to R0's owner, not this lane.


## Review 19912231 — next-session handoff (2026-10-25)

Run `python generate_submission.py --preflight` before restoring the large training stack or launching a model. Current plan is blocked: no assigned method paragraph, and a pinned witness proves the usual budget impossible under the literal overlap rule. No experiment run; no new TIFF or score. This is a necessary precheck, not a full-registry uniqueness pass, authenticated lane assignment, runtime budget manager or selector. Resolve lane and registry policy explicitly; never drop dense references or place anti-registry noise. Freeze a comparable, untouched holdout incumbent; only then test the authorized top hypothesis using shared cache/evaluator/writer and canaries. CWP91 with hole-shuffled control is already complete and negative. The current portal download remains OLC91 research-only. Fresh official-account/receipt/data-rights access is still absent. See `docs/REVIEW-19912231-20261025.md`.
