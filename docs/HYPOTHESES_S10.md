# Session 10 — hypotheses, ranking, and what was verified

Date: 2026-10-24 (UTC). Branch `arena/5e09be50-gemsdoe91`.
Labels: **ORGANIZER-CONFIRMED** = read from an official DrivenData or NLR page this session.
**HOLDOUT-DTI** = our own emulation on withheld catalogue segments (`S10-holdout-v1`).
**REASONING** = derivation or prior, not measured. **CLAIM** = stated by a source we did not verify.

## 1. Why the high scorers scored well — what is verified and what is reasoning

### 1a. Verified facts about the scored task (ORGANIZER-CONFIRMED)

Source: DrivenData problem description, <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> (fetched 2026-10-24).

- **Metric.** Distance-weighted Tversky index with α = 0.2, β = 0.8, triangular kernel k(d) = max(1 − d/R, 0), R = 300 m (3 px at 100 m).
  TP_w = Σ_g max_x p(x)k(d(x,g)); FP_w = Σ_x p(x)[1 − max_g k(d(x,g))]; FN_w = Σ_g [1 − max_x p(x)k(d(x,g))]; DTI = TP_w / (TP_w + α·FP_w + β·FN_w + ε).
- **Continuous output is allowed.** The page asks for "pixel-wise probabilities or confidence scores between 0 and 1". Binary "unit-mass dots" are a lineage choice, not an organizer requirement.
- **Format.** Single band, float32, EPSG:32611, 100 m, same bounds as the training data, null/NaN outside bounds, values in [0, 1].
- **What is scored.** The test set is faults **not** contained in the USGS database, labelled by experts before the competition. The Final Round rescoring uses an expanded label set that adds expert-verified faults found from submissions.
- **Feature layers listed by the organizer:** surface conductivity and depth to conductive base; detrended elevation and slope; dilatation rate, shear strain rate, second invariant; isostatic gravity and slope; RTP, TMI, vertical and horizontal TMI slope, top-of-crustal magnetic source depth estimate; density of earthquakes.
- **Algebra check (REASONING, verified by hand).** With α + β = 1, the official denominator TP_w + α·FP_w + β·FN_w equals α·T + α·(S − M) + β·G, where T = TP_w, S = Σp, M = Σ_x p(x)·max_g k, G = number of truth pixels. This is the formula in `scripts/dti.py`. It is only identical when α + β = 1, which holds here.

### 1b. Leaderboard (ORGANIZER-CONFIRMED, public leaderboard)

Source: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> (fetched 2026-10-24; rows #1–#50 read; the page's last row is #50 with 0.2818).
- #1 xiaofanhu **0.4413** (29 submissions); #2 cfld__ **0.3916**; #3 Batik Shirt Brothers **0.3904**; #4 BrandenKMurray **0.3724**; #5 No Fault of Our Own **0.3539**; #20 shixing **0.3273**; #50 moongrega **0.2818**. The lineage account (`buffedlizard55-lab`) does not appear in rows #1–#50.
- **0.3195 (GEMSDOE49) does not appear on the public board.** The board is sorted by score; #23 is 0.3217 and #24 is 0.3169, so a 0.3195 row would have to sit between them. None does. **0.2778 (GEMSDOE32) is also absent**: it would rank below #50, whose score is 0.2818. Neither figure is on the public board as read. This does not prove the lineage's figures are wrong, because they may come from a different submission or a private score. Both remain CLAIM until a receipt exists.
- The public leaderboard is not the final score. Rules §3.2: public scores "may not be the same as the final scores on the private leaderboard".

### 1c. Why a dispersed, count-fixed placement can score well (REASONING)

Using 1a with a unit-mass dot at position x, let k_self be the dot's own kernel value to its nearest truth pixel and ΔT the increase in T from adding it. Then ΔD = α·(1 + ΔT − k_self), and TI rises only if ΔT/ΔD > TI. Rearranged: **a new dot pays only if its new coverage ΔT exceeds about α·TI·(1 − k_self + ΔT). At TI ≈ 0.28 that is about 0.056.**

Consequences (REASONING, not yet measured on the organizer's scorer):
- A dot far from every truth pixel always lowers the score by about α·TI/D. Mass placed in the wrong place is punished by 0.2 per unit.
- A dot that adds coverage of a new truth location pays off. A dot that stacks on coverage that already exists does not.
- So the best sparse sets are dispersed: one dot per likely location, spaced at roughly the kernel radius. A dense blob wastes α-penalty.
- The parent R0 (h33-h33-2-b2, per the lineage) has 37,654 dots, all ≥ 2.24 px from the catalogue. That is consistent with this reasoning. We have **no receipt** that ties its 0.2778 to these placements (see IR-91-S10-05).

**Untested explanation for why our holdout disagrees:** the holdout tests recovery of *catalogue* faults, while the organizer scores *new* faults. A method that is poor at catalogue recovery is not automatically poor at finding new faults, and the reverse. That makes the negative H10-1 result weaker evidence about the real score than it looks (IR-91-S10-04).

### 1d. Can a unique submission beat 0.2778? — honest answer

Not determinable from this session. We have no organizer scorer, no receipt, and no holdout result that predicts the public score. The only verified number is our own negative holdout (H10-1 0.0173 < random null 0.0288, HOLDOUT-DTI). Any "beats 0.2778" claim is CLAIM until a receipt exists.

## 2. Ranked hypotheses for next sessions

Ranking is by prior plausibility × DTI headroom ÷ implementation cost. **No DTI gain is estimated**, because none has been measured. A DTI gain can only come from a holdout run.

| Rank | ID | Layers (organizer name) | Physical signature | Why it might find non-catalogue faults | Mimic that could fool it | Cost | Status |
|---|---|---|---|---|---|---|---|
| 1 | **H10-5** Joint potential-field contrast displacement | TMI vertical gradient (band 9 `tmi_vg`) + horizontal gradient (band 3 `tmi_hg`); isostatic gravity slope (band 5) + horizontal gradient (band 18). No top-of-crustal source-depth band exists in the file (IR-91-S10-08). | Coincident magnetic and gravity lineaments with similar strike | Two independent layers agree only where a buried contact is likely; catalogue need not contain it | Lithologic contacts, intrusive margins | Medium (2 layers, coincidence test) | NOT BUILT. Needs a holdout run next session. |
| 2 | **H10-2** Dilatation-sign boundary | Dilatation rate (band 8, not used anywhere in this repo) | Zero-crossing of dilatation rate, 3 px band | Faulds et al. (see §4) argue dilation favours deep circulation on NNE faults, so dilational domain boundaries are a plausible place for blind splays (REASONING; the organizer only lists the layer) | GPS interpolation artefacts; the gradient of a smooth field | Low (one band) | NOT BUILT. **Caveat:** Hammond & Thatcher (2007) found dilatation near most Holocene normal faults was not greater than the GPS uncertainties (see §4). |
| 3 | **H10-3** Surface-conductivity lineament coherence | Surface conductivity (band 17, not used anywhere in this repo) | Linear, coherent ridges in log conductivity over ≥ 5 km | Fluid-saturated damage zones can raise conductivity (REASONING; not checked against a source this session) | Playa clays, salt, alluvial contrast | Low | NOT BUILT. |
| 4 | **H10-4** Seismicity-density edges | Density of earthquakes (band 16); distance to earthquake (band 10) | Edges of the earthquake-density field | Microseismicity can outline unmapped faults | Catalogue-completeness gradients; aftershock clusters; the 100 km smoothing kills 3 px detail | Low | NOT BUILT. High mimic risk. Lineage text mislabels band 16 as thermal (IR-91-S10-07). |
| 5 (retired) | **H10-1** Basement-step ridge | Depth to basement (band 15) | Ridge along the basement-depth gradient | Basement steps can host faults | Sedimentary thickness changes | Low | **BUILT. NEGATIVE.** HOLDOUT-DTI 0.0173 [0.0126, 0.0218] vs random null 0.0288 [0.0217, 0.0342]. Not promoted. |

Promotion rule (applies to any row): a candidate may use a weekly slot only if it beats the random-placement null at equal mass on the holdout with a CI that clears it, the leakage canary AUC ≤ 0.90, registry uniqueness passes (rank correlation ≤ 0.90 and ≤ 70 % of dots within 3 px of any registry raster), and the file passes the format gates. Slot choice is a separate selector step and was not done here.

Budget: this session ran 3 holdout experiments (E1, E2, E3), which is the protocol limit of 3 experiments / 2 h. H10-2 to H10-5 need a new session.

## 3. Irregularities found this session

See `IRREGULARITIES.md`, entries IR-91-S10-01 to -10. Two of them change conclusions here:
- IR-91-S10-04: the holdout measures catalogue recovery, but the score uses new faults.
- IR-91-S10-05: no receipt ties 0.2778 to R0.

## 4. Sources

Status column: **Fetched** = read through the fetch tool this session; **Search** = search-result snippet only, full text not read; **Not reachable** = not opened.

| Source | URL | Status | Used for |
|---|---|---|---|
| DrivenData problem description (page 967) | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> | Fetched (both chunks) | Metric, format, labels, features, test set |
| DrivenData About page (page 968) | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/> | Fetched | Context, GeoDAWN description |
| DrivenData leaderboard | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> | Fetched (chunk 0 of 3) | Public top-23 scores |
| DOE/NLR official rules, NREL/TP-5700-96647, Sept 2026 | <https://docs.nlr.gov/docs/fy26osti/96647.pdf> | Fetched (chunks 0 and 2 of 7) | Three submissions per week; generative-AI disclosure; code assets; "submissions" of one GeoTIFF per team |
| DrivenData data page | <https://www.drivendata.org/competitions/306/competition-doe-gems/data/> | Login required | Not read; data needs an account |
| GeoDAWN data release, USGS, DOI 10.5066/P93LGLVQ | <https://doi.org/10.5066/P93LGLVQ> ; <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> | Search (usgs.gov page) | Survey provenance |
| Hammond & Thatcher (2007), JGR, GPS strain, northern Walker Lane | <https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2006JB004625> | Search (abstract) | Caveat: dilatation near Holocene normal faults not greater than uncertainty |
| Faulds et al., NW Great Basin geothermal kinematics (GSN 2005) | <https://nbmg.unr.edu/staff/henry/fauldsetgeothermmineralgsn2005.pdf> | Search (snippet) | Dilation along NNE faults favours circulation |
| Faulds & Henry (2008), AGS Digest 22, Walker Lane | <https://nbmg.unr.edu/staff/faulds/33_AGS22_Faulds_and_Henry_(Walker_Lane)_final.pdf> | Search (snippet) | Walker Lane context |
| Mattéo et al. (2021), JGR, automatic fault mapping | <https://doi.org/10.1029/2020JB021269> | Cited by the organizer page; not opened | Prior work |
| Reference solution repo | <https://github.com/drivendataorg/gems-prize-reference-solution> | Fetched via GitHub API in an earlier step | U-Net baseline; output format |
| epsg.io, gbcge.org INGENIOUS, pubs.usgs.gov, gdr.openei.org | — | Not reachable from the sandbox `curl`. The fetch tool was not tried on all of them. | — |

Note: a search result also lists `buffedlizard55-lab/GEMSDOE` repositories making the same metric and submission claims. Those are lineage self-reports and are not treated as sources here.
