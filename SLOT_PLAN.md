## Current review decision — 2026-10-27

**No slot selected or spent. No new TIFF is eligible.** Prior S22 inputs are scientifically compromised and S18 is a literal duplicate. Any future file needs all scientific and registry gates, then a separate selector decision and an authenticated check of the website's current limit. Earlier plans below are historical, not an active upload queue. See [current review](docs/review-8e8d86f2/REVIEW.md).

---

# Slot selection — no automatic slot (`S22-XB` and every earlier research file are held for a human decision; 0 slots spent)

> **SESSION 22 BANNER (`S22-XB`, 2026-10-26, branch `arena/c722cd53-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent (`slots_used = 0`). `OK TO DOWNLOAD: YES` | `OK TO SUBMIT: NO` (`verdict: "negative"`; failed G4_holdout_paired, G5_live_anchored_projection; [`docs/run-card-S22-XB.json`](docs/run-card-S22-XB.json)).**
> - **`gems91-s22-xbreed-c-37654dots-20261026T172226Z-26a07801-zeros.tif`** (`37,654` dots, SHA-256 `663532862e9d18492c219a147a8640844d0d1508160c7a59da60bf1dce5e031b`): unique (max 62.9% 3-px overlap vs 953 competitive rasters), LFI projection `0.178` MODEL (R0 model value 0.273; R0 USER-REPORTED 0.2778).
> - **If you want to spend slots, the evidence-ranked options are:** (1) the two calibration probes `gems32-probe-S2-SCALE-lambda-0.5` and `gems32-probe-S3-NULLADD-2000px` (identify the exact T and |G|; pre-registered predictions in `docs/s22/probe-predictions.json`; not unique, not competitive; [`docs/PROBE_PLAN_S22.md`](docs/PROBE_PLAN_S22.md)); (2) as a *unique* learning probe, the best independent file that passes the 1,099-raster protocol screen is `gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif` (max overlap 64.0%, LFI projection 0.190, SGMC >500 m 0.084; still below R0); the stronger `gems91-s18-hgbr-hgbr-e1-…` (projection 0.210) fails that screen by 0.97 points (70.97% vs a 90,000-dot sibling). Do **not** resubmit any of the nine sites' best files: each has ≥ 97.7% of its dots within 3 px of another site's best file.


# Slot selection — no automatic slot (`S20-RHTW E3` / `S19-SVHF E3` / `S18-HGBR E1` / `S17-CPAD E1` are held for human selector; 0 slots spent)

> **SESSION 20 BANNER (`S20-RHTW`, 2026-10-26, branch `arena/06420fd7-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent automatically (`slots_used = 0`). `OK TO DOWNLOAD: YES` (validated `[0, 1]` research/selector candidate) | `OK TO SUBMIT: NO` (`verdict: "negative"` / fail-closed pending separate human weekly-slot selector under Rule 6; [`docs/run-card-S20-RHTW.json`](docs/run-card-S20-RHTW.json)).**
> - **`gems91-s20-rhtw-e3-20261026T043618Z-4d501134-zeros.tif`** (`37,654` binary `{0.0, 1.0}` dots, `min_dist_catalogue = 2.236 px`, SHA-256 `06e5f52d7f231c315d427849a9e02b6fd78dc2cf3993aabb0b76b676b1150f2b`, ZIP SHA-256 `f5319f617610f8503f82f9ef1b68dc008414f8db3432cdff07fce06be07cf472`):
>   - **#1 on Primary `I2` Holdout (`0.136798 HOLDOUT-DTI` `[0.120020, 0.154533]`, `+60.45%` over `E0 = 0.085260`, `+24.40%` over external `GEMSDOE70 Phase 5 = 0.109968`) AND #1 on Isolated-Fault `I1` Holdout (`0.113298 HOLDOUT-DTI` `[0.097264, 0.128559]`, `+21.69%` over `E0 = 0.093105`).**
>   - **Non-Blanket Uniqueness PASS Across All `120` Audited Rasters:** `49.10% <= 70%` 3-px dot overlap vs `GEMSDOE32 R0`, `41.15%` vs `S18-HGBR E1`, `36.93%` vs `S19-SVHF E3`, `max non-blanket = 62.15% <= 70%`, `surface |ρ| <= 0.1803 <= 0.90` (`99.78%` on `206,895`-dot synthetic 5-px lattice witness `calib_r13lattice_00904.tif`, `IR-S16-03`).
>   - **9-Site Duplication Guard:** Forensic audit (`docs/s20_rhtw/nine_sites_forensic_matrix.json`) proves `GEMSDOE24/25/28/30/31/33/36` and `GEMSDOE27 H27` are `86.7%–100.0%` clonal trims of `19GEMSDOE H19-5` / `GEMSDOE32 R0` (`0.2778`) and **must never spend another weekly slot**. Only `GEMSDOE27 H29` (`0.2190`, `56.1%`), external `GEMSDOE70 Phase 5` (`0.2478`, `54.8%`), `S18-HGBR E1`, `S19-SVHF E3`, and `S20-RHTW E3` (`49.1%`) are non-duplicates of `R0`. Takes **no automatic slot**.

> **SESSION 19 BANNER (`S19-SVHF`, 2026-10-25, branch `arena/bcc0fcb2-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent (`slots_used = 0`). `OK TO DOWNLOAD: YES` (research/audit) | `OK TO SUBMIT: NO` (`verdict: "negative"`, `submission_ready: false`; [`docs/run-card-S19-SVHF.json`](docs/run-card-S19-SVHF.json)).**
> - **`gems91-s19-svhf-e3-oof-20261025T194830Z-5cc11f080635-zeros.tif`** (`37,654` binary `{0.0, 1.0}` dots `> 3.0 px` from catalogue and `> 3.0 px` inter-dot spacing, SHA-256 `ed26789ab7bdbe6291abe743a25b65c63a5a14c99d3f50e421a1e77e025543d3`) cleared **`90/90` preregistered (`93/93` post-merge) competitive (`<=80,000`-dot) submissions** (`max 3-px dot overlap = 53.20% <= 70%`; `43.80%` vs `GEMSDOE32 R0`, `46.71%` vs `S18-HGBR E1`, `42.87%` vs `S17-CPAD E1`, `37.84%` vs `S17-LFTG E2`, `27.31%` vs `ISO91 E1`, `13.84%` vs `S18-UNIQUE`) and lifted blind off-catalogue USGS `SGMC >500 m` discovery to **`0.093415`** (`69.16%` `>1 km` far-field), while scoring **`0.147791 HOLDOUT-DTI`** (`95% CI [0.132771, 0.162342]`) on `gems57-pooled-hide-v2` (trailing `S18-HGBR E1 = 0.200742` and `S17-CPAD E1 = 0.198183`) and measuring `99.85% > 70%` on the 206,895-dot synthetic 5-px lattice witness `calib_r13lattice_00904.tif`. Takes **no weekly slot**.

> **SESSION 18 BANNER (`S18-HGBR`, 2026-10-25, branch `arena/bba4efce-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent automatically (`slots_used = 0`). `OK TO DOWNLOAD: YES` (research/selector review) | `OK TO SUBMIT: NO` (`verdict: "negative"` due to `IR-S16-03` synthetic `calib_r13lattice_00904.tif` 5-px lattice overlap `99.84% > 70%`; [`docs/run-card-S18-HGBR.json`](docs/run-card-S18-HGBR.json)).**
> - **`gems91-s18-hgbr-hgbr-e1-20261025T184458Z-d5b042a3-zeros.tif`** (`37,654` binary `{0, 1}` dots, SHA-256 `afc1699914bc517b3c4c0ef1cc16973ced37f7e90fc74cfb7b20869da01f099b`, ZIP SHA-256 `87fb051c1d440d8a67c6fe5530be946c5784af8100fc1d8c8a0acf17800d31bd`, [`docs/run-card-S18-HGBR.json`](docs/run-card-S18-HGBR.json)):
>   - **All-Time #1 Label-Blind Holdout Score in `GEMSDOE91`:** **`0.200742 HOLDOUT-DTI`** (`95% CI [0.180482, 0.221419]`, `vendor/gems57/evaluate_holdout.py` `gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` spatial buffer), beating `S17-CPAD E1` (`0.198183`) on all 4/4 spatial folds (`+0.002560`), `INCUMBENT-PTAC-LB` (`0.194221`) by **`+0.006521`**, `INCUMBENT-PTAC-V2` (`0.192208`) by **`+0.008534`** (`95% CI [+0.002892, +0.014515]`), and `S17-LFTG E2` (`0.188596`, `USER-REPORTED` live `0.1823`) by **`+0.012146`** (`95% CI [+0.007290, +0.017609]`).
>   - **All-Time #1 Untouched Blind Off-Catalogue USGS SGMC `>1 km` Score:** **`>300 m = 0.103939`**, **`>500 m = 0.104995`**, **`>1 km = 0.101151`** (`82.21%` of dots `>1 km` from the visible catalogue), beating `GEMSDOE32 R0` (`USER-REPORTED` live `0.2778`, SGMC `>1 km = 0.082913`) by **`+22.00%` on `>1 km`** and `S17-LFTG` (`SGMC >1 km = 0.039897`) by **`+153.53%` on `>1 km`**.
>   - **Real-Submission Uniqueness PASS Across All 83 Real Rasters:** `vs GEMSDOE32 R0 = 48.77% <= 70%`, `canonical real (8) = 57.05% <= 70%`, `external fleet (37) = 51.29% <= 70%`, `in-repo downloads (45) = 61.87% <= 70%`. Takes **no automatic slot**.

> **SESSION 18 BANNER (`S18`, 2026-10-25, branch `arena/537d6d44-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent (`slots_used = 0`). No new candidate. `OK TO DOWNLOAD: RESEARCH ONLY` | `OK TO SUBMIT: NO` (`verdict: "negative"`, `promote: false`; [`docs/run-card-S18.json`](docs/run-card-S18.json)).**
> - Slot blocker, recomputed (`verify_s18.py`): lattice covers 99.87% of the footprint; at N = 37,654 the overlap lower bound is 0.8234 > 0.70. The only literal route is N ≤ 22,163 with ≥ 30% of dots on uncovered pixels, which was rejected. Decision D1 is open for the user ([review §3, §6](docs/REVIEW-S18-20261025.md)).
> - Existing negatives unchanged: OLC91 E1 and the damage-zone file. No new slot assigned.

> **SESSION 17 BANNER (`S17-CPAD`, 2026-10-25, branch `arena/aecf32eb-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent (`slots_used = 0`). `OK TO DOWNLOAD: YES` (research/audit) | `OK TO SUBMIT: NO` (`verdict: "negative"`).**
> - **`gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif`** (`37,654` binary `{0, 1}` dots `> 3.05 px` from catalogue and `> 3.05 px` inter-dot spacing, SHA-256 `690c10998798d3abd54f6a1ec1c12e56c4243d1967ede7b63a533b9ddd628cdd`, [`docs/run-card-S17-CPAD.json`](docs/run-card-S17-CPAD.json)) scored **`0.198183 HOLDOUT-DTI`** (`95% CI [0.177759, 0.217830]`, unchanged `vendor/gems57/evaluate_holdout.py`, `60,988` withheld positives, `80 px` buffer) — **#1 strict label-blind `37,654`-dot binary `gems57-pooled-hide-v2` score in `GEMSDOE91`**, beating re-evaluated label-blind `INCUMBENT-PTAC-LB` (`0.194221`, paired `+0.003962`, `95% CI [-0.001766, +0.010077]`), `CED91` (`0.070886`, paired `+0.127296`), and `S16-PGRD` (`0.069397`, paired `+0.128786`), plus **`0.068585 BLIND-SGMC-CONTROL-DTI`**. Stopped fail-closed at `51/95 r11_greedy_mp.tif` (`272,853` dots, `87.25% > 70%`) after passing `95/95` pre-placement Spearman checks and `50/50` preceding fleet rasters (`GEMSDOE32 R0 = 49.27%`). Takes **no slot**.

> **SESSION 17 BANNER (`S17-EULR`, 2026-10-25, branch `arena/597b6f3f-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent (`slots_used = 0`). `OK TO DOWNLOAD: YES` (research) | `OK TO SUBMIT: NO` (`verdict: "negative"`).**
> - **`gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif`** (`44,000` binary `{0, 1}` dots `> 3.0 px` from catalogue, SHA-256 `3d07dcb81f01e8b19b5fa2cf2d4d7dc75eb1f7ec2d319a120f6ba7c37bf369d2`, [`docs/run-card-S17-EULR.json`](docs/run-card-S17-EULR.json)) scored **`0.249626 HOLDOUT-DTI`** (`95% CI [0.234678, 0.264996]`, `gems91-hide-recover-v1.0`) and **`0.100737` Blind Off-Catalogue USGS SGMC DTI** (`+0.005351` vs `GEMSDOE32 R0`), trailing `S14-PTAC E2` (`0.267782`, point comparison) with a null Euler ablation (paired `+0.000331`, CI includes 0) and literal registry failure (lattice `99.827%`; S13 sibling `93.836%`; `41.120%` on `R0`). Takes **no slot**.

# Slot selection — no automatic slot (`S14-HVDC E2` / `S14-PTAC E2` / `S15-SCGF E2` / `S17-CDSC E1` are Rule-1 duplicate-stop negatives; 0 slots spent)

> **SESSION 17 BANNER (`S17-CDSC`, 2026-10-25, branch `arena/1722e30a-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent (`slots_used = 0`). `OK TO DOWNLOAD: YES` (research) | `OK TO SUBMIT: NO` (`verdict: "negative"`).**
> - **`gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif`** (`44,000` binary `{0, 1}` dots `> 3.0 px` from catalogue, SHA-256 `39aaac68e7640d9914f1f8431bab589ce30eda6bf7a59512e38699f705d21836`, [`docs/run-card-S17-CDSC.json`](docs/run-card-S17-CDSC.json)) remediated `IR-91-S15-06`, `IR-91-S15-07`, and `IR-91-S15-05`, scoring **`0.259972 HOLDOUT-DTI`** (`95% CI [0.244333, 0.275361]`, jumping **`+0.019339`** over `S15-SCGF E2 = 0.240633` and beating `S13-PTHA E3 = 0.244601` by **`+0.015371`** with paired 95% CI `[+0.010244, +0.021122]`). External non-calibration fleet 3-px overlap is **`53.16% <= 70% PASS`** (`43.76% <= 70% PASS` vs `GEMSDOE32 R0`), but it trails `S14-PTAC E2` (`0.267782`) by `-0.007810` and stops on literal all-raster lattice overlap (`99.834%`). Takes **no slot**.

> **PARALLEL SESSION 15 BANNER (`S15-SCGF`, 2026-10-25, branch `arena/605655a6-gemsdoe91`):**
> - **Zero weekly DrivenData slots spent (`slots_used = 0`). `OK TO DOWNLOAD: YES` (research) | `OK TO SUBMIT: NO` (`verdict: "negative"`).**
> - **`gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.tif`** (`44,000` binary `{0, 1}` dots `> 3.0 px` from catalogue, SHA-256 `0893322792aa46eaebba6f75702051d854efbe7fa5cb219e588ef863459ca3a1`, [`docs/run-card-S15-SCGF.json`](docs/run-card-S15-SCGF.json)) scored **`0.240633 HOLDOUT-DTI`** (`95% CI [0.227931, 0.254026]`) and **`0.097940` Blind Off-Catalogue USGS SGMC DTI** (`+0.002180` vs `S14-PTAC E2`; `+0.002554` vs `GEMSDOE32 R0`), trailing `S14-PTAC E2` (`0.267782`) and `S14-HVDC E2` (`0.262209`) on primary holdout and stopping on literal 3-px lattice overlap (`99.811%`, vs `44.82%` on `R0`). Takes **no slot**.

> **SESSION 14 BANNER (2026-10-24, branch `arena/08009ce4-gemsdoe91`) — CURRENT #1 HOLDOUT RESEARCH RESULT, NOT A SLOT CANDIDATE:**
> - **No weekly DrivenData slot has been spent (`slots_used = 0`). `OK TO DOWNLOAD: YES` (research) | `OK TO SUBMIT: NO` (`NEGATIVE — RULE 1 DUPLICATE STOP`).** A selector cannot override the explicit lane threshold.
> - **Current #1 Measured Research Result in `GEMSDOE91` (All-Time #1 on BOTH comparable HOLDOUT-DTI & Blind USGS SGMC):** **`gems91-s14-hvdc-e2-20261024T223000Z-0a0bb0cb-zeros.tif`** (`50,000` unit-mass binary `{0, 1}` dots `> 3.0 px` from catalogue, SHA-256 `678b75968dd023bff2f77dc7df4464b49fb02aa042ca59d34dd4941e85357720`, submission name `GEMS91-S14-HVDC-E2-d3670e31`, [`docs/run-card-S14-HVDC.json`](docs/run-card-S14-HVDC.json)):
>   - **`0.262209` `HOLDOUT-DTI`** (`95% CI [0.248940, 0.275209]`, `gems91-hide-recover-v1.0`, `60,988` withheld positives), beating former #1 `S13-PTHA E3` (`0.244601`) by **`+0.017608` (`+7.20%`) with paired 5 km bootstrap 95% CI `[+0.009179, +0.026128]`, `P(>0) = 100.0%` (`400/400` draws)**, `S12-SPAC E3` (`0.237587`) by **`+0.024622` (`+10.36%`)**, `S11-MHTR E2` (`0.206406`) by **`+0.055803` (`+27.04%`)**, and `R0 GEMSDOE32` (`0.153644`) by **`+0.108565` (`+70.66%`)**.
>   - **`0.110429` `BLIND-SGMC-CONTROL-DTI`** (`62,122` blind off-catalogue USGS SGMC bedrock fault pixels), **#1 in `GEMSDOE91`**, beating `S12-SPAC E3` (`0.107938`), `S13-PTHA E3` (`0.100815`), `S11-MHTR E2` (`0.097623`), and `R0 GEMSDOE32` (`0.095386`, `+15.77%`).
>   - **All 5 format/range `[0, 1]` validators PASS (`0` NaNs across all `12,279,160` cells), `101/101` single-feature leakage canaries PASS (`max AUC = 0.75201 <= 0.90`), canonical 8-raster registry uniqueness PASS (`<= 50.07%` 3-px overlap; `R0 = 40.31%`), and 34-raster external dotted-fleet uniqueness PASS (`<= 46.12%` 3-px overlap; `|rho| <= 0.0945`).**
> - **RULE 1 DUPLICATE STOP (`IR-91-S14-03`):** final dots exceed 70% against the synthetic lattice (`99.838%`), S13-PTHA (`84.706%`) and dense h25 context (`70.056%`). The artifact is a negative research deliverable and enters no live-slot queue; do not submit it.

> **SESSION 12 BANNER (2026-10-24, branch `arena/03c185c4-gemsdoe91`) — HISTORICAL:**
> - **No weekly DrivenData slot has been spent automatically (`slots_used = 0`).** Under [Official Rules §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (`3 submissions/week` cap) and `src/gems91/readiness.py`, live slot promotion belongs strictly to the human fleet selector.
> - **Current #1 Validated Selector Candidate in `GEMSDOE91`:** **`gems91-spac-e3-20261024T183000Z-a2740c89-zeros.tif`** (`54,000` unit-mass dots `> 3.0 px` from catalogue, SHA-256 `0265259717c4dde6bca1215b83d0be93c38f13d08ab12bd88343746f57dd91dd`, [`docs/run-card-S12.json`](docs/run-card-S12.json)):
>   - **`0.237587` `HOLDOUT-DTI`** (`95% CI [0.223387, 0.250313]`, `gems91-hide-recover-v1.0`, `60,988` withheld positives), beating `S11-MHTR E2` (`0.206406`) by **`+0.031181` (`+15.1%`) with paired 95% CI `[+0.024186, +0.038231]`, `P(>0) = 100.0%` (`200/200` draws)**, `H91-DDVTC E1` (`0.174030`) by `+36.5%`, and `B0` (`0.138999`) by `+70.9%`.
>   - **`0.107938` `SGMC-OFFCAT-CONTROL-DTI`** (`62,122` blind off-catalogue USGS SGMC fault pixels), beating both `R0` (`0.095386`, `+13.2%`) and `S11-MHTR E2` (`0.097623`, `+10.6%`).
>   - **All 5 format/range `[0, 1]` validators PASS, 95/95 leakage canaries PASS (`<= 0.78363`), and 64/64 real external & parallel-lane registry uniqueness checks PASS (`|rho| <= 0.2214 <= 0.90`, `3-px overlap <= 68.02% <= 70.0%`).**
> - **STRICT MUTUAL-EXCLUSION RULE (`IR-91-S12-05`):** `S12-SPAC E3` **formally supersedes** unsubmitted `S11-MHTR E2` (`0.206406`) and `H91-DDVTC E1` (`0.174030`). **The human selector must NEVER submit both `S12-SPAC E3` and `S11-MHTR E2`.**
> - **Synthetic Lattice Policy Check (`IR-CED-003`):** Before spending a live slot, the human selector should confirm acceptance of symmetric F1 (`0.3507 <= 0.70`) for the `206,895`-dot synthetic 5-px blanket `calib_r13lattice_00904.tif` (which covers `99.8713%` of the footprint within 3 px).

> **SESSION 10 BANNER (2026-10-24) — read before using historical entries below.**
> - **GEOD is retracted as a duplicate of R0**: 93.23 % of its dots lie within 3 px of R0 (threshold 70 %). Rank correlation 0.8951 is just under 0.90. It was removed from Pages downloads (IR-91-S10-01).
> - **No slot is recommended this session.** The only file built in session 10 (H10-1 basement-step ridge) fails its random-placement control on the holdout (0.0173 vs 0.0288, HOLDOUT-DTI). It is not promoted.
> - **Queue below is historical and unverified** for the reasons in IR-91-S10-04 (holdout measures catalogue recovery) and IR-91-S10-05 (the 0.2778 parent figure has no receipt).
> - **Band 16 (`ieq_n100a15`) is earthquake intensity or density, not a thermal layer** (IR-91-S10-07). The thermal label and the AUC attached to it in this file are wrong.
> - The 2026-12-03 deadline in this file is not verified; the rules point to the competition site for key dates (IR-91-S10-10 and the executive summary).
> - Weekly cap: three scored submissions per week (NLR rules §3.2, fetched 2026-10-24). Slot selection is a separate step and was not done here.


**Current decision: no weekly slot is selected or used.** This session produces a
negative research deliverable, not a competition-approved submission.

Read `README.md` and `docs/run-card.json`. CED91's TIFF passes format/range checks
but fails the literal final-dot novelty rule. Its paired HOLDOUT-DTI improvement
over the matched control is not resolved, and no comparable prior best is present.

Promotion belongs to a separate selector step. It requires complete-scope novelty,
an assigned lane, compatible split/evaluator evidence beating the recorded best,
and the current allowance verified on the organizer submission page. Historical
“3 per week” statements and deadline estimates are not live confirmations.

The previous queue and projected score deltas are retained only for forensics in
`docs/archive/SLOT_PLAN-before-CED91.md`. They are **not** instructions to upload.

## DENOVO merge note (2026-10-24, `arena/58a33cc1-gemsdoe91`)

`gems91-denovo-hgbctx-…-7941b7ab-zeros.tif` (`docs/denovo.html`) is recorded for the
selector's consideration only. It does not enter any queue by itself: novelty was checked
against 7 pinned registry rasters, not the complete universal registry, and no selector
approval exists. The current decision above (no slot selected) is unchanged.

## Strain lane note (merged 2026-10-24, `arena/6f079276-gemsdoe91`)

Three geodetic-strain `CONCENTRATION` arms (`strn25m10`/`strn25m20`/`strd25m10`) were built and are
predicted negative (`MODEL`, frozen SGMC-off-catalogue translator; `docs/MECHANISM_CARDS_STRAIN.md`).
By their authors' verdict they take no slot; at most `strn25m10` is a reserve if a concentration-family
receipt ever contradicts that translator. The strain question overlaps the promoted `GEOD25m10`
(IR-91-45): any slot spent on either file tests both lanes' hypothesis.

## ASC91 lane note (2026-10-24, `arena/5486e004-gemsdoe91`)

`gems91-asc91-e3-37654dots-s2p8-20261024-dc8e4d47-zeros.tif` (antisymmetric
cross-fault step lane; `docs/run-card-ASC91.json`) is a **negative**
deliverable: 0.116767 HOLDOUT-DTI on the identical whole-component instrument
vs the prior best 0.142885 (HGB-CTX). It takes **no slot** and enters no
queue. The preregistered follow-up for a future session is the step×context
fusion gated above 0.142885 with a second-instrument cross-check; selector
approval and live weekly allowance remain separate, unverified here.

## SPID91 lane note (2026-10-24, `arena/01ec3805-gemsdoe91`)

`gems91-spid-e3-20261024T190000Z-25a94861-zeros.tif` (`docs/run-card-SPID91.json`,
Upward-Continued Laplace SPI Worms + Depth-Deconfounded Conductivity + Weingarten
Scarp-Toe MoE + Exact Binary-Vertex Dinkelbach) passes all 4 `[0, 1]` GeoTIFF
validators and all 85 single-feature leakage canaries (`<= 0.6610`), cleared
`67/67` real rasters at branch base (`max 3-px dot overlap = 66.63% <= 70%`) and
`74/75` post-merge (`71.13%` vs concurrent `S12-SPAC E3`), and scored `0.151682`
`HOLDOUT-DTI` on `gems91-hide-recover-v1.0` (`0.145009` on 8-km buffer
`gems57-pooled-hide-v2`), beating `B0` (`0.138999`), `DENOVO` (`0.142885`),
`H11-1` (`0.139652`), and `CED91` (`0.062153`) while trailing `S11-MHTR E2`
(`0.206406`) and `S12-SPAC E3` (`0.237587`). Its verdict is **`negative`** —
it takes **no weekly slot** (`OK to download = YES`, `OK to submit solo = NO`).

## S11-MHTR & S12-BHAR (`BHAR91`) lane ledger (2026-10-24, `arena/8d9056a3-gemsdoe91` & `arena/4cb38f30-gemsdoe91`)

- **`S11-MHTR E2` (`gems91-mhtr-e2-20261024T170000Z-9554f718-zeros.tif`, SHA-256 `dbfe7dfc27a93792abc0e73aa9e2ade3a7bbe69e6f71ec0927e176466e588b15`, `48,000` dots `> 3.0 px`):** **`0.206406` `HOLDOUT-DTI`** (`95% CI [0.193796, 0.220176]`, `gems91-hide-recover-v1.0`, `60,988` withheld positives) and **`0.097623` `SGMC-OFFCAT-CONTROL-DTI`**. Now superseded by `S12-SPAC E3` (`0.237587`, see top banner).
- **`S12-BHAR E3` (`gems91-bhar-e3-20261024T184500Z-a4b69ca7-zeros.tif`, SHA-256 `bae83b233ddb150105986337207b8a217f3a3f3a817e0b418ad7f26f1b4c2431`, `48,022` dots `> 3.0 px`, `docs/run-card-BHAR91.json`):** **`0.198612` `HOLDOUT-DTI`** (`95% CI [0.186030, 0.210569]`; `E1 = 0.204676`, `E2 = 0.192735`; paired delta vs `S11-MHTR E2` `-0.007794`, 95% CI `[-0.016104, +0.001192]`) and **`0.099057` `SGMC-OFFCAT-CONTROL-DTI`** (`E2 = 0.100094`, beating both `S11-MHTR E2 = 0.097623` and `GEMSDOE32 = 0.095386`).
- **Slot Decision:** **Zero weekly slots consumed.** Under pre-registered `HYPOTHESES_BHAR91.md` criteria, `S12-BHAR` is recorded honestly as `verdict: "negative"` on primary `HOLDOUT-DTI` (**OK to download for research / subsurface ensemble archive; NOT OK to submit to a live weekly slot**).

## S13-PTHA lane note (2026-10-24, `arena/6a62c2ab-gemsdoe91`)

`docs/downloads/gems91-s13-ptha-e3-20261024T201500Z-660d645d-zeros.tif` (`44,000` binary `{0, 1}` dots, SHA-256 `421c589072e3b959fc0f8e71a7e879822ce8f9a81172a7f0fd24e7932eadd452`, `docs/run-card-S13.json`) achieved **`0.244601 HOLDOUT-DTI`** (`gems91-hide-recover-v1.0`, `60,988` withheld positives, `95% CI [0.230592, 0.257058]`, **#1 primary holdout in `GEMSDOE91`**, beating `S11-MHTR E2 = 0.206406` by **`+0.038195`** with paired 5 km bootstrap `95% CI [+0.029931, +0.046719]` and exceeding `S12-SPAC E3 = 0.237587` by **`+0.007014`**) AND **`0.100815` Blind Off-Catalogue USGS SGMC DTI** (beating `R0 = 0.095386`, `S11-E2 = 0.097623`, and `S12-BHAR = 0.100094`, behind `54k`-dot `S12-SPAC E3 = 0.107938`). It passes all 5 format/`[0, 1]` suites, all 75 leakage canaries (`max AUC 0.66470`), canonical 8-raster registry novelty (`≤ 51.39%`), and external dotted-fleet novelty (`≤ 47.36%`). Zero slots were spent automatically; it is **promoted to the human fleet selector** alongside `S12-SPAC E3` under strict mutual exclusion (submit at most ONE in-repo candidate), subject to human verification of the live 3/week DrivenData slot allowance, eligibility/AI attestation, and `IR-CED-003` synthetic lattice policy.



## S14-LSRG lane note (2026-10-25, `arena/eeaf78c1-gemsdoe91`)

`docs/downloads/gems91-s14-lsrg-ff-20261025T004500Z-1fcf17ee-zeros.tif` (`37,654` unit dots, SHA-256 `09f9ca2acdca7c6616df329aad7d0c8d73dec2626b04e6d8619d2b1452ea7359`, `docs/run-card-S14.json`) is the fleet's first candidate built on the 1 m LiDAR scarp stack + per-element K/Th/U radiometrics, emitted at organizer-measured winner geometry (75.0% of dots >10 px from catalogue, 3.16 px median spacing). Scores, all labelled: **HOLDOUT-DTI `0.206822`** (`gems91-hide-recover-v1.0`/`v1.1-nohalo`, 60,988 withheld, 95% CI `[0.192302, 0.220993]`) — **below** S13-PTHA `0.244601`; within-budget sibling `S14-LSRG E3@44k` scored `0.240111` but with anti-winner halo geometry (verdict negative); blind SGMC (FF) `0.0807`. Selector trade-off is explicit (IR-91-S14-06): fleet organizer outcomes anti-correlate with holdout (ρ = −0.75) and reward exactly the FF geometry. **Additional hard gate:** human licence review/rebuild of the lidar+rad derivative inputs (IR-91-26, §A.5) before any signing. Mutual exclusion: 82.8% dot overlap vs S12-SPAC — submit at most ONE in-repo candidate. Zero slots spent.
