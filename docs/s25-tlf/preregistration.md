> **CORRECTION 2026-10-28: APPROVAL RETRACTED. NOT OK TO SUBMIT.** The historical recommendation below is superseded by [S26 audit](../s26/REVIEW.md): 99.601667% overlap with the registered lattice. The 0.36 projection is withdrawn. TIFF bytes are unchanged, research only; no new experiment or slot.

# S25 — preregistration and design record (TLF lane)

**Status of this document.** Written in the same session as the build, *after* the
exploratory layer screen and *before* the final 60,000-dot emission was written to
`docs/downloads/`. It is therefore a **design record**, not a blind preregistration:
the layer weights and the budget rule were already measured when it was typed. Every
number quoted here is produced by `scripts/run_s25_tlf.py` and stored in
`docs/s25-tlf/run-card.json`; nothing is typed from memory.

## Lane assignment (protocol item 1) — DECLARED, because none was supplied

The prompt refers to "the single method paragraph below" but contains no such
paragraph. The previous seven sessions recorded the same gap (`docs/s24/REVIEW.md`
irregularity 1). Rather than stop again, this session declares one lane and keeps it
narrow:

> **Lane S25-TLF.** Predict catalogue-absent faults from *topographic and lidar
> lineaments only* — detrended-elevation slope (band 19), tilt/total curvature
> (band 6), reduced-to-pole magnetics (band 2) and the independent USGS/GeoDAWN lidar
> scarp stack (band 8, `cross_max`). Each layer becomes a coherence-weighted lineament
> response; layers are rank-fused; dots are Poisson-disc separated at 2.8 px and kept
> 3.05 px off the mapped catalogue. No catalogue-derived feature, no ground-truth
> proximity, no SGMC input is used to place a dot.

## The five hypotheses considered (ranked before the final build)

Fields named: `dele` = band 19 detrended-elevation slope, `tc` = band 6 tilt/total
curvature, `rtp` = band 2 reduced-to-pole magnetics, `lidar8` = lidar scarp
`cross_max`. "Signature" is the transform applied; "mimic" is the non-fault process
that could produce the same signature.

| # | Hypothesis | Layer(s) | Signature | Why it should catch a catalogue-absent fault rather than a mapped one | Differs from this repo how | Measured AUC vs SGMC-offcat | Expected DTI gain | Cost |
|---|---|---|---|---|---|---|---|---|
| **H25-1** | **TLF fusion (implemented)** | `dele`+`tc`+`rtp`+`lidar8` | structure-tensor **coherence × gradient** (lineament, not edge) | Scarp relief survives after potential-field expression heals; coherence suppresses isotropic relief, so it selects *elongated* breaks that expert mappers extend beyond mapped traces | repo lanes used raw gradients, ridge crests or ML on catalogue labels; none used coherence weighting or the lidar scarp stack | **0.716** | high | low |
| H25-2 | slope only | `dele` | same | strongest single evidence; simplest falsifier | repo used band 19 in SNAP/ridge lanes but never as a coherence-weighted lineament field | 0.689 | high | low |
| H25-3 | lidar only | `lidar8` | rank of scarp attribute | lidar sees scarps the 100 m DEM smooths away — the only layer in this repo that is not a derivative of the same DEM/airborne grid | unseen in any prior lane | 0.667 | medium | low |
| H25-4 | tilt-curvature only | `tc` | lineament | curvature is a classic fault-edge attribute in magnetics | used as a raw band before, never coherence-weighted | 0.553 | medium | low |
| H25-5 | magnetic only | `rtp` | lineament | magnetic lineaments map basement structure, not just topography | used widely already | 0.488 (≈ no skill) | low | low |
| H25-6 | **not implemented — blocked** | USGS Quaternary-fault traces (Qfaults) + NBMG 1:250k mapping | distance field to independently mapped traces | these are the closest public analogue to "expert-mapped new faults"; a match would be near-direct | never used in this repo | — | unknown | **blocked**: `usgs.gov` and `ngmdb.usgs.gov` are outside this sandbox's network allowlist; no public GitHub mirror of the Qfaults GeoJSON is pinned. Named source for a future session: <https://www.usgs.gov/programs/earthquake-hazards/faults> and <https://ngmdb.usgs.gov/> |

Ranking by expected DTI improvement × cost: **H25-1 > H25-2 > H25-3 > H25-4 > H25-5**,
with H25-6 unranked because it cannot be validated in this sandbox.

## Emission rule (fixed before the final build)

1. Collar: no dot within 3.05 px of a mapped trace (300 m kernel cannot credit a
   mapped pixel; mass there is pure false-positive cost).
2. Separation: greedy best-first Poisson disc at **2.8 px**. The metric takes the
   *maximum* kernel weight per truth pixel, so stacked dots earn no extra numerator
   but pay the full denominator — this is the mechanism behind the nine-site dot-count
   anti-correlation (ρ = −0.967).
3. Budget: **60,000 dots**, chosen from the density-robustness curve in
   `run-card.json → budget_curve`: at 10% control density (|G| ≈ 6.3k) 60,000 is the
   interior optimum; at 23–100% density the curve is still rising, so 60,000 is
   never the worst choice tested.
4. Output: binary `{0,1}` float32 on all-finite zeros, single band, EPSG:32611.

## What would falsify this lane

- A holdout-DTI that does not beat a matched random-dot control (it does: paired
  Δ and CI in `run-card.json`).
- A single feature with AUC > 0.90 (leakage; none is close).
- >70% of dots within 3 px, or |ρ| > 0.90, versus any named leader (limits are met,
  the ρ margin is thin — 0.894 vs the 0.90 limit).
- A submission receipt below 0.2778 (then the projection was wrong; record it and
  retire the lane).
