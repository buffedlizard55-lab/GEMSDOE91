# OLC91 — preregistration (written before any experiment ran)

> **Evidence correction from active review `arena/05c6d613-gemsdoe91` (2026-10-25):** The claimed `0.2778` is USER-REPORTED, not ORGANIZER-CONFIRMED. The immutable GEMSDOE32 project page states “NO ORGANISER SCORE EXISTS” for any artifact in that repository and labels its projected value “a MODEL, not a score.” The raster-only fact reverified here is a 40,199-dot parent pruned to a 37,654-dot exact subset by removing 2,545 pixels within 200 m of the catalogue, with no additions. All causal language and score-gain values below are hypotheses/user-reported context, not verified hidden-score effects. See [the current audit](REVIEW-05C6D613-20261025.md) and [pixel forensics](s16/gems32-forensics.json).

**Lane (single method paragraph).** No lane was supplied in the prompt, so this session
declares one: *Oriented Line-integral Coherence (OLC).* A positive-unlabeled (PU)
gradient-boosting posterior is trained on the 19 official GeoDAWN numerical bands plus their
gradient magnitudes. It is then multiplied (geometric mean) by its own **strike-coherent line
support**: the maximum, over 12 azimuths, of a 1.1 km (11 px) line average of the posterior.
The combined surface is emitted as sparse 3 px dots, with no dots on or within 2 px of mapped
faults. Physically, a fault is a *line*: a lithology, offset or damage contrast that persists
along strike. Its pixel-level evidence is noisy and fragmented, and averaging along the best
strike raises its signal-to-noise roughly as √L. Isolated, equidimensional high-posterior blobs
are suppressed, such as an outcrop patch, an alluvial fan or a magnetic body. The prior is
**catalogue-blind**, so it can rank an unmapped linear structure as highly as a mapped one.

Run date 2026-10-25. Branch `arena/3444a6d3-gemsdoe91`. Budget: 3 experiments / 2 hours.

## 1. GEMSDOE32's `0.2778` claim and reverified raster lineage

The value and stepwise scores below are USER-REPORTED; the immutable GEMSDOE32 page says no organizer score exists. Only the raster geometry was independently rechecked here (`work/forensics_r0.json`; containment check in `docs/run-card-OLC91.json`). These score claims were not reproduced with hidden truth, an authenticated leaderboard, or a submission receipt.

| Step | Raster | Dots / px | Geometry / claimed change | User-reported live-value claim |
|---|---|---:|---|---:|
| 0 | `h16-1` topo+geophys multiscale ridges | 123,939 px | base ridge network | 0.1855 |
| 1 | `h19-5` power-law-budget, 4-line corroborated re-gate of h16-1 | 121,131 px in 26,645 fragments (median 2 px) | re-ranked ridge network | 0.1922 |
| 2 | `d2-8` dotted h19-5 (2.8 px spacing) | 44,090 dots, all ⊂ h19-5 | −63.6% mass, coverage mostly kept | 0.2600 |
| 3 | `solo` | 40,199 = d2-8 − 3,891 dots at **exactly 1.0 px** from the catalogue | collar prune 1 | 0.2708 |
| 4 | **R0 `h33-2-b2`** | 37,654 = solo − 2,545 dots at **√2–2.0 px** | collar prune 2 | **0.2778** |

The official problem description specifies a distance-weighted Tversky index with 300 m triangular support and α=0.2, β=0.8. That metric makes sparse pruning a plausible mechanism, but it does not verify a submitted score:

1. **Reverified geometry, not score causation.** The 37,654-dot R0 is an exact subset of the 40,199-dot parent after 2,545 catalogue-proximate pixels (≤2 px) are removed; no dots are added. This establishes a delete-only distance prune, not that a score improved or why.
2. **Plausible metric mechanism.** Under a max-kernel TP, redundant predictions may add false-positive cost while contributing little additional truth coverage. Removing them could improve DTI only if the lost weighted TP is smaller than the FP-cost reduction. Hidden truth is unavailable here, so the net effect is unidentified.
3. **Claimed stepwise gains are not measured here.** The user-reported sequence implies 0.1922→0.2600 on dotting and 0.2600→0.2708→0.2778 on two pruning steps. Those differences are arithmetic on unverified claims, not reproduced `HOLDOUT-DTI` scores or organizer receipts; they cannot establish that the operations caused the reported changes.
4. **Any top-score comparison is also unverified.** The often-cited 0.4413 appears in an S18 source record but was not freshly fetched or independently confirmed in this checkout. The ≈0.62 coverage figure in the earlier discussion is a model inversion conditioned on reported values, not an observed score or validated requirement.
5. **Other proximity numbers are not evidence in this review.** The inherited 0.0106 / 0.0053 / 0.0009 values and ≈0.052 random comparison lack a verified organizer receipt and are not presented here as `HOLDOUT-DTI`; no conclusion about the distribution of new faults follows from those claims alone.

**Can this method be shown to beat the reported 0.2778?** Not with the available offline evidence. R0 was built with the full catalogue, so it cannot be evaluated as a proper held-out candidate on these hide-and-recover folds, and no offline instrument has a verified calibration to the live board. A prior 19GEMSDOE source record reports Spearman ρ = +0.11 for known-fault proxies across 15 live files; that statistic was not recomputed in this review. This lane could only test OLC against a comparable incumbent on identical folds. Any live-score claim remains unknown until an organizer receipt exists.

## 2. Ranked untried hypotheses

| Rank | ID | Layers | Physical signature / transform | Why it should find *unmapped* faults | Difference from repo | Expected ΔDTI | Cost |
|---|---|---|---|---|---|---|---|
| 1 | **H1 OLC** (tested as E1) | PU posterior from 19 official bands + gradients | max over 12 azimuths of an 11 px line mean of the posterior; surface = √(p·C) | Catalogue-blind linearity prior; rewards along-strike persistence wherever it occurs | `dd_vtc_pu` used zero-mean oriented kernels on *raw inputs*; h16/h19 used Hessian ridges of raw topo/geophysics. Nothing integrates the *learned posterior* along strike before emission | small–moderate (+0.005 to +0.02 holdout) | low |
| 2 | H2 completeness-weighted PU | PU posterior + visible-catalogue density | p·(1 − ĉ), ĉ = clip(G_σ*catalogue / G_σ*p̂) | PU with spatially varying label frequency: P(unlabelled positive \| x) ∝ p(x)(1 − c(x)). It matches the live depletion near mapped faults | No repo lane models label frequency spatially | uncertain sign offline: hide-and-recover makes artificial holes, so a gain could be artefactual | low |
| 3 | H3 pluvial-shoreline mimic suppression | det_elev, det_elev_slope, posterior | suppress lineaments parallel to elevation contours, i.e. strike ∥ contour | Lake Lahontan shoreline terraces are horizontal scarps; fault scarps cross contours | No repo lane tests the contour-parallel angle | uncertain | medium (needs the det_elev datum verified: absolute or detrended?) |
| 4 | H4 Andersonian strain-orientation prior | GNSS strain-rate tensor azimuths | favour strikes ⟂ to the principal extension direction | Active normal faults strike ⟂ to extension; scalar strain bands carry no azimuth | Stack has only scalar strain rates | uncertain | high: needs EarthScope/GAGE velocities, **not reachable from this sandbox, so not verified obtainable** |

## 3. Instrument (frozen)

* Template `vendor/gems57/holdout.buffered_component_draw(grid, seed=20, hide_frac=0.20,
  buffer_px=3, boundary_px=12)`: whole 8-connected components, 20% of each eroded
  quadrant's catalogue pixels. There is a 3 px feature-context collar, the visible catalogue is
  kept as context, and the remaining catalogue is masked pixel-exactly.
* Leave-one-quadrant-out models: training excludes everything within 40 px of the scored
  quadrant. Positives are visible catalogue pixels; hidden components stay **unlabelled** (PU).
* Scorer `vendor/gems57/evaluate_holdout.evaluate` + `pooled_summary` (`gems57-pooled-hide-v2`):
  pooled DTI, α 0.2, β 0.8, 300 m triangular kernel, paired 20 km-block bootstrap (1,000 draws).
* Emission is identical for every arm: `gems91.dd_vtc_pu.submodular_dti_emit`, a budget of
  37,654 × (scored-region area / footprint area), and no dots on or within 2 px of any
  catalogue pixel that is still known in that fold.
* Arms: **E0** incumbent recipe (posterior p only). **E1** OLC √(p·C). **RND** uniform random dots
  in the same eligible mask (floor control).
* Experiment 2 is a replication on draw seed 21 if E1 wins on seed 20. Experiment 3 is H2,
  only if time remains.

## 4. Gates (frozen)

* **Promote** E1 only if the paired bootstrap Δ(E1 − E0) has its 95% CI lower bound > 0 on seed 20,
  and the replication sign agrees.
* **Leakage canary:** each input feature alone on the holdout truth vs unlabelled scored pixels;
  max(AUC, 1 − AUC) > 0.90 means STOP.
* **Uniqueness:** checked on the continuous surface before placement and on the final dots.
  This covers 7 local registry files, 62 fleet registry rasters (60GEMSDOE@02563d07) and this
  repo's own prior downloads. Duplicate-stop applies if |Spearman| > 0.90 or > 70% of dots lie
  within 3 px of one raster's positives. Blanket rasters (3 px footprint coverage ≥ 0.70) make
  the literal overlap uninformative. For them the literal value AND a chance-corrected value
  (obs − chance)/(1 − chance) are both reported. **This is flagged as an irregularity and no
  reference is dropped.**
* Every number is labelled HOLDOUT-DTI with evaluator version, withheld positives and 95% CI.
  No projection is presented as a score.

---

## 5. Results (appended after the run; everything above was frozen first)

**Experiment 1 (seed 20): NEGATIVE.** HOLDOUT-DTI, `gems57-pooled-hide-v2`, 11,321 withheld
positive px in 606 whole components, LOQO models, identical emission for every arm:

| Arm | Pooled HOLDOUT-DTI | 95% CI | NW fold diagnostic | NE fold diagnostic | SW fold diagnostic | SE fold diagnostic |
|---|---:|---|---:|---:|---:|---:|
| E1 OLC √(p·C) | 0.083186 | [0.066866, 0.100482] | 0.0811 | 0.0980 | 0.0653 | 0.0922 |
| E0 incumbent recipe | 0.085260 | [0.068716, 0.102299] | 0.0814 | 0.1011 | 0.0683 | 0.0936 |
| RND floor | 0.043165 | [0.037666, 0.048476] | 0.0364 | 0.0422 | 0.0446 | 0.0475 |

The four per-fold values are descriptive diagnostics only, without standalone 95% CIs; the reportable scores are the pooled values and intervals above. Paired E1−E0 = `−0.0020745794 HOLDOUT-DTI` (same evaluator and 11,321 withheld positives), 95% CI [−0.0045433461, +0.0002357064]. E1 was lower in 4/4 folds, so the preregistered rule says: no promotion and no seed-21 replication. Paired E1−RND = `+0.0400209384 HOLDOUT-DTI` (same evaluator/population), 95% CI [+0.0240261042, +0.0568989031].

**Leakage canary: PASS.** Worst individual feature, `grad_det_elev_slope`, had `0.601 LEAKAGE-CANARY-AUC` (not DTI).

**Coverage by distance of the withheld truth to the visible catalogue:**

| Arm | 4–10 px | 10–30 px | >30 px |
|---|---:|---:|---:|
| E0 | 0.114 | 0.134 | 0.136 |
| E1 | 0.114 | 0.127 | 0.130 |
| RND | 0.061 | 0.065 | 0.054 |

The truth itself splits 55% / 39% / 7% across these bands (n = 6,171 / 4,402 / 748).

Coverage is flat with distance, so the arms are not proximity-driven. The *instrument's*
truth is strongly catalogue-proximal, however: 55% lies within 1 km of visible faults, against
the live evidence that new faults are depleted near mapped ones. This is an instrument-mismatch
irregularity.

**Why OLC failed, mechanistically.** The submodular emitter already applies 4-axis ridge NMS and
a 3 px kernel. The posterior at 100 m is spatially smooth, because the input geophysics is smooth.
A 1.1 km line mean therefore mostly blurs the posterior, and slightly favours long features over
the short components that dominate the withheld set.

**Final file and uniqueness: DUPLICATE-STOP.** The surface check passed (max |ρ| 0.216 vs
`calib_hedgev2_01563_sample`). Final dots reach 76.8% within 3 px of
`docs/downloads/gems91-bhar-e3-…-zeros.tif` (71.8% chance-corrected). Ten more rasters exceed 70%,
all earlier PU-HGB lanes plus `calib_h25ctx` and `calib_h28ridge`. The blanket lattices r13
(99.8%), r11 (88.1%) and r14 (80.5%) fall to −0.59, 0.57 and 0.18 after chance correction.
**Lesson:** HGB-on-19-bands surfaces converge on the same 15–25% of the footprint, so a unique
file needs a new information source, not another model on this stack.

**H3 feasibility note.** The band description of `det_elev` is *detrended* elevation, so the
absolute Lake Lahontan highstand datum (~1,330 m) cannot be recovered from the stack. H3 needs an
external DEM with verified provenance.
