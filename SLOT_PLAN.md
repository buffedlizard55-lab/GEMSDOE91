# Slot selection — blocked, no candidate chosen

> **SESSION 10 BANNER (2026-10-24) — read before using this plan.**
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

## S12-SPID lane note (2026-10-24, `arena/01ec3805-gemsdoe91`)

`gems91-spid-e3-20261024T190000Z-25a94861-zeros.tif` (`docs/run-card-S12.json`,
Laplace-Fourier SPI + Depth-Deconfounded Conductivity + Weingarten Scarp-Toe MoE +
Self-Credit Bayes-Dinkelbach) is certified `[0, 1]` across all 4 validator suites,
clears all 85 leakage canaries (`<= 0.6610`) and all 67 real fault rasters
(`max 3-px dot overlap = 66.63% <= 70%`), and beats `B0` (`0.138999`), `DENOVO`
(`0.142885`), `H11-1` (`0.139652` vs `0.145009` on 8-km buffer `gems57-pooled-hide-v2`),
and `CED91` (`0.062153`), but achieves `0.151682` `HOLDOUT-DTI` vs Repository #1
`S11-MHTR E2` (`0.206406` on `v1.0`; `0.194267` on `gems57-v2`). Its verdict is
**`negative` for solo weekly-slot promotion** — **do not spend a live weekly slot on
`S12-SPID E3` solo**; retain `S11-MHTR E2` as Repository #1 for human fleet-selector
review while archiving `S12-SPID E3`'s `15,751` orthogonal concealed-basin dots for
cross-fleet ensembling.

