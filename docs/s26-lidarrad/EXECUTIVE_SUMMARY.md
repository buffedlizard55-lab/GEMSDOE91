# S26 Executive Summary — 2026-10-29 (branch `arena/18fec2a7-gemsdoe91`)

## ⛔ VERDICT AT THE TOP — READ FIRST

| Question | Answer |
|---|---|
| Is there a NEW unique TIF? | **YES** — `gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros.tif` (37,654 binary dots) |
| OK TO DOWNLOAD? | **YES — for research/inspection only** → [`../downloads/gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros.tif`](../downloads/gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros.tif) · [ZIP](../downloads/gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros.zip) |
| **OK TO SUBMIT?** | **NO — DO NOT SUBMIT.** Its pooled `HOLDOUT-DTI = 0.1332 [0.1111, 0.1553]` did **not** beat the repo holdout best (S21-PDWC 0.1957, different split version — see IR-S26-07). Per the parallel-run protocol, an idea that has not beaten the holdout best must not spend a weekly slot. |
| Is it unique vs the nine focus sites / registry? | **YES (measured)** — max 3-px dot overlap **40.82%** (limit 70%) vs all 8 restored registry rasters incl. GEMSDOE32 R0 (**32.45%**); surface Spearman vs R0 **+0.047 / +0.063** (limit 0.90). |
| Format valid? | **YES** — single-band float32, EPSG:32611, 3,730×3,292, transform identical to `sample_submission.tif`, values only {0.0, 1.0}, 0 NaN/Inf, 0 mass outside footprint. This fixes the historical “Predicted values must be in range [0, 1]” failure (zeros encoding, no NaN). |
| Submission name (if a human selector overrides) | `gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros` |
| DrivenData note (≤140 chars) | `S26 lidar-scarp x radiometric HGB dotted2.8 collar3.05 37654d; HOLDOUT-DTI 0.1332 v3split; verdict negative do-not-submit` (117 chars) |
| Estimated leaderboard score | **NOT ESTIMABLE — no number is claimed.** The only live anchor (R0: USER-REPORTED 0.2778) has HOLDOUT-DTI 0.0067 under this instrument, i.e. a live/holdout ratio of ~41×, so any ratio projection would be fabrication. The 0.1332 figure is `HOLDOUT-DTI` only, never a leaderboard score. |

## Nine focus sites — best claimed submission per site (all USER-REPORTED, none ORGANIZER-CONFIRMED)

Source: `docs/nine-site-20261028/nine-site-leaders-20261028.json` (pinned-commit file/hash audit, re-read this session).

| Site | Best file (short) | Claimed score | Dots | Unique vs others? |
|---|---|---|---|---|
| GEMSDOE32 | h33-h33-2-b2-…-zeros | **0.2778** | 37,654 | Parent R0 lineage |
| GEMSDOE36 | anderson-geothermal-pinn-38854-… | 0.2750 | 38,854 | H19-5 descendant family |
| GEMSDOE28 | h36-1-rung30-blind-r1-… | 0.2710 | 37,660 | H19-5 descendant family |
| GEMSDOE31 | h27-4-solo-d28-… | 0.2708 | 40,199 | H19-5 descendant family |
| GEMSDOE33 | h33d-analog-tip-stepover-r30-… | 0.2632 | 41,865 | H19-5 descendant family |
| GEMSDOE25 | dotted-h19-5-d2-8-… | 0.2600 | 44,090 | H19-5 ancestor |
| GEMSDOE30 | d28-poisson300m-offcat-44090-… | 0.2600 | 44,090 | Same bytes lineage as GEMSDOE25 file (sha `91eae1ca…` dot set) |
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5-… | 0.2477 | 60,069 | H19-5 ancestor |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5-… | 0.2449 | 61,328 | H19-5 descendant |
| **GEMSDOE91 S26 (new)** | **gems91-s26-lidarrad-37654dots-…-zeros** | **HOLDOUT-DTI 0.1332 (not a leaderboard score)** | 37,654 | **YES — max overlap 40.8%, ρ≤0.063** |

**Which is “the best submission to submit”?** On evidence: **none of the nine is cleared** — every score above is USER-REPORTED with no organizer receipt, and all nine are the *same H19-5 lineage family*, so re-submitting any of them is neither unique nor new information. The honest recommendation remains **do not submit any of them, and do not submit S26 either** (holdout-negative). This is the “Own the Outcome” answer even though it is not the hoped-for one.

## Why did GEMSDOE32's 0.2778 win (PhD-level reading, evidence-bounded)?

1. **It is a catalogue-collar prune, not a discovery model.** Repo forensics (README R0 analysis, re-verified lineage files): R0 = the 0.2600 H19-5/d2-8 raster **minus 6,436 dots within 2 px of the catalogue**, nothing else. Organizers mask known-fault pixels and score only off-catalogue truth (DrivenData forum, cited in repo), so dots spent near known faults are wasted mass; removing them raises the Tversky-style DTI denominator efficiency.
2. **Dot economics of DTI (α=0.2, β=0.8, 300 m triangular kernel):** each dot costs α-weighted false-positive mass but can earn ≤1 kernel credit per true pixel. The 37,654-dot, widely-spaced (“dotted”) emission sits near the empirical optimum of the precision/recall trade-off found across the fleet (44k→0.2600, 60–61k→0.245–0.248, 37.65k→0.271–0.278).
3. **Why we cannot honestly claim to beat it yet:** under this session's buffered whole-component holdout, R0 scores only 0.0067 — its live strength comes from continuations of *visible* catalogue structure, which a hide-and-recover instrument deliberately removes. The instrument and the live task reward different things; our LFI/SGMC anchors in prior sessions (Spearman up to +0.957 / +0.442, repo evidence) are the better live proxies, and S26 was not run through them — another reason it is not promoted.

## S26 experiment (1 of max 3 used)

- **Hypothesis:** LiDAR scarp morphology (11 bands) × GeoDawn radiometrics (K/Th/U/TC) fused with the 19 GeoDawn numerical bands in one HGB classifier recovers uncatalogued scarps that pure-catalogue-continuation methods miss.
- **Mechanism:** fault scarps juxtapose radiometric units and produce a persistent topographic step; neither signal alone is diagnostic.
- **Named non-fault mimic:** terrace risers, road cuts, shorelines and lithologic contacts produce identical scarp+radiometric anomalies.
- **Protocol:** shared `vendor/gems57` whole-component buffered folds (buffer 80 px, split v3); features derived without catalogue inputs, so no catalogue leakage by construction; per-feature canary max symmetric AUC 0.587 (rad_K) — PASS ≤0.90; dotted emission 2.8 px spacing, 3.05 px catalogue collar, 37,654 dots.
- **Result:** HOLDOUT-DTI (gems57-pooled-hide-v2 formula, split v3) **0.1332 [0.1111, 0.1553]**, 60,988 withheld positives; vs random equal-budget 0.0729 (Δ +0.0604 [0.0420, 0.0795]) and vs R0-static 0.0067. Fold DTIs: 0.064 / 0.161 / 0.221 / 0.192 (NW fold weak — flagged).
- **Verdict: negative** (did not beat repo holdout best; no slot spent).

## Ranked untried hypotheses (next, cheapest first)

1. **S26b — LFI/SGMC-anchor-weighted S26 surface** (same features, emission weighted by off-catalogue SGMC control): cost low, directly targets the live proxy that actually correlates.
2. **Radionuclide ratio edges (K/Th, eU/K) × scarp strike coherence** — hydrothermal alteration signature; layers already local.
3. **Geodetic strain-rate tensor eigen-direction × tilt-worm persistence** — partially tried in fleet (GEMSDOE76/63), not in this repo as one lane.
4. **Depth-to-basement step (band 15) × conductivity (band 17) discontinuity** — needs canary first; both bands already local.
5. **Seismicity alignment (bands 10/16) anisotropic density** — earthquake lineations; needs external USGS catalogue check (free, official: https://earthquake.usgs.gov/earthquakes/search/).

## How to submit (only after a future candidate turns verdict = promote)
DrivenData → competition 306 → Submit → upload the single `.tif` (or the ZIP containing exactly that one TIF) → paste the note above → Create submission. Rules/format: https://www.drivendata.org/competitions/306/competition-doe-gems/ · Official leaderboard (fetched 2026-10-29): **#1 = 0.4544** — the prompt's 0.4413/0.3195 are stale (IR-S26-01). The prompt's “current top 0.3195” is in fact ~#24 territory.
