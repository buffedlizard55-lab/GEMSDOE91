# Session 20 research note: what the live truth is, and why the leaderboard is the only direct measurement of it

This note supplements `docs/GEOTHERMAL_VENT_KNOWLEDGE_BASE.md` and `docs/GEOTHERMAL_VENT_RESEARCH_S19.md`. Those notes hold the
geological source register: Great Basin structural settings, USGS Qfaults, GDR #1391 and 3DEP. Everything below was either read
this session from the named page, or measured in this repo with the named script.

## 1. Official competition facts that drive the S20 design

Source: DrivenData problem description,
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (fetched 2026-10-26).

| Fact (as stated by the organizer) | Consequence for modelling |
|---|---|
| Ground truth consists of **newly expert-labelled faults that are not in the USGS fault database** | Pixels on or next to the catalogue are depleted in truth. Recovering hidden catalogue faults (the repo's `hide-v2` holdout) measures a different target. |
| The GeoDAWN region is split into chunks for a **public** test set (leaderboard) and a **private** test set (Initial Prize Round) | A model fitted to public scores must not use chunk- or location-specific terms. LFI uses only location-free covariates. |
| Metric: Tversky index with α = 0.2, β = 0.8 and a 300 m triangular kernel. TP = Σ_g max p·k; FP = Σ p(1 − max k); FN = Σ_g(1 − max p·k) | T is linear in the truth indicator G, so a live score is an exact algebraic function of Σ G inside each raster's kernel footprint. This is what makes inversion possible. |
| Format: single-band float32, EPSG:32611, 100 m, sample bounds; values in [0, 1] | All-finite zeros encoding (NaN outside caused the form error recorded in the README). |
| External data allowed if licensed | No new external data used in S20. |

Live public-leaderboard snapshot (https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/, fetched 2026-10-26):

| Rank | Score |
|---|---|
| #1 | 0.4413 |
| #2 | 0.3916 |
| #3 | 0.3904 |
| #4 | 0.3724 |
| #5 | 0.3553 |

## 2. Measured in this repo (S20)

**E2: the hide-and-recover holdout does not track live scores.** Source: `scripts/run_lfi_holdout.py` → `docs/lfi/holdout-e2.json`.
Across 112 fleet rasters with USER-REPORTED live scores, Spearman(hide-v2, live) is about 0.1 and Pearson is about 0.
For example, gems79 scores 0.558 on hide-v2 and 0.0005 live, while GEMSDOE32 R0 scores 0.0067 on hide-v2 and 0.2778 live.
This is consistent with the organizer's definition of the truth as *new* faults.

**E1: a 25-parameter log-linear truth-density model reproduces live scores out of site.** Source: `scripts/run_lfi.py` →
`docs/lfi/fit_r10.json`. Leave-one-site-out Spearman is 0.957.

Fitted effects at ridge 10:
* Truth density rises by 1.78 log-units beyond 4 km from the catalogue. It is lowest at 200–500 m, at −0.76 to −0.78.
* It is higher on the catalogue-blind ridge network (+0.70).
* It is much higher where ≥3 independent high-scoring methods agree (+2.97).

These are statistical effects estimated from public-chunk aggregates; they are not geological measurements.

## 3. Method literature (verified links)

* Aggregate-label learning: Quadrianto, Smola, Caetano & Le (2009), *Estimating Labels from Label Proportions*, JMLR 10:2349–2374.
  https://jmlr.org/papers/v10/quadrianto09a.html. LFI is a special case in which the "bags" are the published rasters' kernel
  footprints and the proportion is recovered from the exact DTI algebra.
* Adaptive overfitting to a public leaderboard: Blum & Hardt (2015), *The Ladder: A Reliable Leaderboard for Machine Learning
  Competitions*, ICML, PMLR 37. https://proceedings.mlr.press/v37/blum15.pdf (arXiv:1502.04585). This is why the public→private
  transfer risk is flagged in `IRREGULARITIES.md` (IR-S20-02).

## 4. Physical interpretation (hypothesis-level, not verified)

The +2.97 consensus effect is consistent with faults that several independent signal families detect: topography (scarps, ridge
breaks), potential fields (gravity and magnetic gradients) and strain. It is equally consistent with shared bias, because every
fleet method reads the same 19 GeoDAWN bands.

The far-field enrichment is consistent with the organizer labelling new faults mainly where the USGS catalogue is sparse. It does
not show that such faults are geothermally active. Geothermal relevance (step-overs, terminations, accommodation zones; see the
knowledge base) is not modelled separately in S20.
