# GEMSDOE91 — Executive summary (2026-10-31)

**Bottom line.** A new, unique submission raster was generated end-to-end by the
project's automated pipeline (S30-VCSE vent-concordance lane). It passes every
technical gate (validator 13/13, values strictly in [0, 1], unique vs every
listed GEMSDOE site and every registry raster). **Verdict:**

> **OK-TO-DOWNLOAD: YES · OK-TO-SUBMIT (weekly slot): NO — HOLD.**
> The standing protocol (frozen in `docs/s30-vcse/preregistration-amendment.md`)
> promotes a candidate to a submission slot only if it beats the registered
> holdout best **0.159482** (S27-OSDR E2, same instrument). The candidate's
> pooled HOLDOUT-DTI is **0.052966 [0.046011, 0.060650]** — it does not clear the
> bar, so **0 weekly submission slots were and will be spent**. A negative
> result remains a deliverable (rule: "A negative result remains a deliverable").

**Submission identity (if a slot were ever spent):**

* name: `gems91-s30-vcse-e3-44090dots-20261031T021738Z-d23f1602-zeros`
* note (82 chars ≤ 140): `S30 VCSE vent-concordance rad+cond+GDR+seis+strain CELF dots cap0.64; see run-card`
* file: [`docs/downloads/gems91-s30-vcse-e3-44090dots-20261031T021738Z-d23f1602-zeros.tif`](downloads/gems91-s30-vcse-e3-44090dots-20261031T021738Z-d23f1602-zeros.tif)
  (sha256 `a5993d3a520aa280ce70744ad2dd772090d54cd248e1d6fdc9d1950fdc8e83ae`, 135,773 bytes; zip alongside)

All numbers below are evidence-classed. **HOLDOUT-DTI** = our hide-and-recover
instrument `gems57-pooled-hide-v2` (60,988 withheld positives, label-blind
quadrant folds v3, 80 px feature buffer, 20 km block bootstrap, 1,000 draws,
95% CI). **ORGANIZER-CONFIRMED** = a score on a submission receipt. **USER-REPORTED
(public)** = figures from the prompt or user messages — unverified by us, shown
for context only, never as scores. **MODEL** = arithmetic projection — never a
score.

## 1. The nine focus sites — file, estimated score, uniqueness

Estimated score column = **HOLDOUT-DTI (gems57-pooled-hide-v2; 60,988 withheld
positives; 95% CI)**, measured by `scripts/s30_score_nine_sites.py`
(receipt: `docs/s30-vcse/nine-site-holdout-estimates.json`). These rasters were
fit on the full catalogue; the estimate measures their recovery of hidden
(off-catalogue) truth on our instrument and is **not** an organizer score.

| Site | File to download (learning copy) | Estimated score — HOLDOUT-DTI (gems57-pooled-hide-v2; 60,988 withheld; 95% CI) | USER-REPORTED public DTI (unverified) | Unique vs the other listed sites? |
|---|---|---|---|---|
| GEMSDOE24 | `data/s22-nine-sites/GEMSDOE24.tif` | 0.171690 [0.157528, 0.185257] | 0.2477 | **NO** — 100% of dots within 3 px of GEMSDOE30 (one duplicate family) |
| GEMSDOE25 | `data/s22-nine-sites/GEMSDOE25.tif` | 0.161506 [0.147915, 0.174658] | 0.2600 | **NO** — identical dots to GEMSDOE30 (100% both ways) |
| GEMSDOE27 | `data/s22-nine-sites/GEMSDOE27.tif` | 0.172501 [0.158210, 0.185985] | 0.2449 | **NO** — 99.71% of GEMSDOE33's dots within 3 px of it |
| GEMSDOE28 | `data/s22-nine-sites/GEMSDOE28.tif` | 0.046137 [0.042047, 0.050054] | 0.2710 | **NO** — 100% vs GEMSDOE30 |
| GEMSDOE30 | `data/s22-nine-sites/GEMSDOE30.tif` | 0.161506 [0.147915, 0.174658] | 0.2600 | **NO** — hub of the duplicate family (24/25/28/31 all 100%) |
| GEMSDOE31 | `data/s22-nine-sites/GEMSDOE31.tif` | 0.049001 [0.044887, 0.053046] | 0.2708 | **NO** — 100% vs GEMSDOE30 |
| GEMSDOE32 | `data/s22-nine-sites/GEMSDOE32.tif` | 0.006697 [0.005990, 0.007368] | 0.2778 | **NO** — 100% vs GEMSDOE36 (dot sets coincide) |
| GEMSDOE33 | `data/s22-nine-sites/GEMSDOE33.tif` | 0.086392 [0.079234, 0.092845] | 0.2632 | **NO** — 99.71% inside GEMSDOE27 |
| GEMSDOE36 | `data/s22-nine-sites/GEMSDOE36.tif` | 0.006918 [0.006202, 0.007605] | 0.2750 | **NO** — 100% vs GEMSDOE32 |
| **GEMSDOE91 (new, this work)** | `docs/downloads/gems91-s30-vcse-e3-44090dots-20261031T021738Z-d23f1602-zeros.tif` | **0.052966 [0.046011, 0.060650]** | — (not submitted) | **YES** — max 3 px overlap 11.80% vs any listed site (13.54% vs any registry raster); surface rank-corr max 0.0286 |

**No ORGANIZER-CONFIRMED score exists in this repository** — no submission
receipts are recorded in `ledger/submissions.csv` for any of these files, and
this session spent 0 slots. Every score above is a labelled HOLDOUT-DTI.

Uniqueness evidence (required gates): rank-correlation of the final surface vs
every gate-set raster ≤ **0.0286** (gate ≤ 0.90, `docs/s30-vcse/surface-checks.json`);
≤70% of final dots within 3 px of any gate-set raster — measured max **13.54%**
(`docs/s30-vcse/dot-checks.json`). Gate set = the nine listed sites + `data/registry/`
(34 sha-unique rasters; see IR-S30-05 below).

## 2. Why GEMSDOE32's `h33-h33-2-b2` (0.2778, USER-REPORTED) leads the nine — and did we beat it?

Study: `docs/R0_ANALYSIS_S22.md`, `docs/s22/nine-site-audit.json`,
`docs/review-20261031/nine-site-geometry.json`.

* The nine "sites" are one construction lineage (H19-5 → D2.8 → H27-4 → R0),
  not nine independent ideas; their pairwise dot overlap reaches 100%
  (table above). The R0 recipe — **2.8–3 px dotting (+0.0678 reported)**,
  **collar pruning around the mapped catalogue (+0.0178 reported)**, and
  family cross-consistency — is what the reported 0.24–0.28 band reflects.
  The prompt's leaderboard highs (0.3195 / 0.4413) are **stale**; the
  2026-10-29 public snapshot (`evidence/public-leaderboard-2026-10-29.json`)
  shows leaders at 0.4544 / 0.3916 / 0.3911 — none of the nine sites.
* **We did not beat 0.2778 on any organizer-confirmed metric** (no slot was
  spent). We did beat R0 where we can measure blind: **SGMC off-catalogue
  control DTI (>5 px from catalogue): candidate 0.113455 vs parent R0
  0.088516 vs GEMSDOE36 0.089855** (`docs/s30-vcse/run-card.json`,
  metric `SGMC-OFFCAT-CONTROL-DTI`, blind proxy truth, not a leaderboard
  score). On the pooled-hide instrument the candidate also exceeds R0
  (0.052966 vs 0.006697) but sits **below the matched random-NMS control
  (0.070228–0.080091)** and far below the family leaders (0.16–0.173).
  The two instruments disagree; hide-and-recover holdout is a weak live
  proxy (Spearman +0.105 [−0.093, +0.294] vs live, `docs/R0_ANALYSIS_S22.md`),
  so no live-score claim is made either way.
* Family-inversion bracket (**MODEL, not a score**): 0.0699–0.2075 under
  stated assumptions (per-dot truth credit 0.03–0.08; |G| 12,100–13,400;
  matched mass 0.10–0.25·n). Overlaps the family band from below;
  inconclusive — consistent with HOLD.

## 3. The new geological hypothesis (validated first, as required)

Five hypotheses were generated and ranked in
[`docs/s30-vcse/hypotheses.md`](s30-vcse/hypotheses.md). The top-ranked one —
**vent/alteration + strain concordance on off-catalogue strands (hydrothermal
upflow signature: K-depletion/Th-U-fractionation, conductive clay caps, warm
springs, seismicity, strain-rate corridors; mimic: playa conductivity, gated by
the basin-floor veto + structural concurrence)** — was validated on the
spatially-blocked holdout **before** any submission slot: three preregistered
experiments (E1 vent-vote scout 0.048030 [0.041466, 0.055027]; E2
consensus-fused 0.000000 (honest 80 px guard zeroes consensus near withheld
truth — anti-informative instrument interaction); E3 supervised-OOF + vent
fusion 0.052966 [0.046011, 0.060650]), budget 3 of 3 experiments spent,
weekly slots 0. Full run card: [`docs/s30-vcse/run-card.json`](s30-vcse/run-card.json)
(hypothesis, mechanism, non-fault mimic, holdout DTI+CI, registry
correlation/overlap, raster sha256, validator output, submission name+note,
verdict).

## 4. Verdicts (automated, no human inspection)

| Gate | Result | Evidence |
|---|---|---|
| DrivenData validator (13 checks: band, dtype, dims, CRS, transform, no NaN/Inf/sentinel, range ⊂ [0,1], footprint, no dots on mapped catalogue) | **PASS 13/13** | receipt JSON alongside the TIF |
| Prediction values ⊂ [0, 1] (past rejection: "Predicted values must be in range [0, 1]") | **PASS** (float32 {0,1} zeros-encoding) | `submission_writer.write_submission` enforces |
| Uniqueness — final dots ≤70% within 3 px of any listed site / registry raster | **PASS** (max 13.54%; 11.80% vs the nine) | `docs/s30-vcse/dot-checks.json` |
| Uniqueness — surface rank-corr ≤ 0.90 | **PASS** (max 0.0286) | `docs/s30-vcse/surface-checks.json` |
| Leakage canary per feature (AUC > 0.90 = leakage) | **PASS** (max 0.6135, vent_rad_TC fold3) | `docs/s30-vcse/canaries.json` |
| G5 blind SGMC (>5 px) > parent R0 | **PASS** (0.113455 vs 0.088516) | `run-card.json` `diagnostics_sgmc` |
| Holdout gate: pooled HOLDOUT-DTI ≥ 0.159482 | **FAIL** (0.052966) | `run-card.json` `holdout_gate` |
| **Overall verdict (preregistered rule)** | **negative — HOLD the weekly slot** | `run-card.json` `verdict` |

**OK-TO-DOWNLOAD: YES. OK-TO-SUBMIT this week: NO.**

## 5. Irregularities flagged for review

1. **IR-S30-04/05 (emitter + gate set).** The first packaged E3 raster
   collapsed to 591 dots: the shared CELF emitter's per-reference quotas were
   evaluated against a 58-raster set that included dense learning probes
   (`r11_greedy_mp`, 272,853 dots — 3 px halo covering 99.87% of the candidate
   domain), making the quotas infeasible. Fixed in the shared tool
   (`src/gems91/pdwc21.py`): off-quota reserve outside the largest halo +
   duplicate-gate set = nine listed sites + `data/registry/`. Superseded
   artifacts kept in `docs/s30-vcse/superseded/` with a README note. Both fixes
   are covered by the shared test suite (10/10: `tests/test_s21_pdwc.py`,
   `tests/test_s27_cvdc_unit.py`).
2. **Amendment drift.** `preregistration-amendment.md` froze E3 at 37,654 dots
   @3.05 px, but the executed code used 44,090 dots @2.8 px (the family budget).
   The addendum in that file records the drift; the numbers reported here are
   the executed ones. Selection rule, gates, and metric were unchanged.
3. **Shared-tool fix (template, not fork).** `scripts/evaluate_holdout.py`
   `score_off_catalogue_sgmc` crashed on numeric footprints; coerced to bool in
   place.
4. **Instrument disagreement** (holdout vs blind control vs MODEL bracket) is
   reported as-is; no cherry-picking. The pooled-hide instrument ranks the
   public-best site (GEMSDOE32, USER-REPORTED 0.2778) second-worst of nine —
   the hide-and-recover holdout is a weak live proxy and the decision rule
   follows the preregistered gate regardless.

## 6. Remaining next steps and limitations

* **Next steps:** (a) run the G5-style blind diagnostics on a *de novo*
  differential-depth edge lane (hypothesis C, cheapest untested) under a fresh
  run card if another experiment cycle is opened; (b) attempt the holdout
  paradox study (why catalogue-recovery and live diverge) with the
  `lfi_live_anchors.csv` rows as calibration; (c) if a slot is ever spent,
  use the candidate name/note above unchanged and file the receipt into
  `ledger/submissions.csv`.
* **Limitations:** no organizer score exists for anything we generated (0
  slots); the holdout instrument's live correlation is weak and its CI is
  conditional on fitted folds; the MODEL bracket is arithmetic, not evidence;
  the nine-site public figures are user-reported; E2's zero is an
  instrument/guard interaction, not proof that consensus carries no signal;
  SGMC-blind control uses a public USGS derivative (free, official,
  `data/external/derived_sgmc_faults_100m_u8.tif`, digest pinned in
  `docs/s30-vcse/feature-receipt.json`).
