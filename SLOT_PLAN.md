# Slot selection — human selector queue (`S12-SPAC E3` #1 candidate; 0 slots spent automatically)

> **SESSION 12 BANNER (2026-10-24, branch `arena/03c185c4-gemsdoe91`) — READ FIRST:**
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

