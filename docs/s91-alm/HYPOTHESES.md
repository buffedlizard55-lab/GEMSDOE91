# S91-ALM — new, ranked, untested geological hypotheses (2026-10-31)

**Status: research proposals only. None is a tested winner, a receipt, or a score.** `S91-ALM` (this lane) is a unique
negative-control candidate; the proposals below are for the next session's 3-experiment / 2-hour budget.

## Ranked shortlist

| Rank | Hypothesis | Layers | Physical signature | Why it should catch a fault missing from USGS/INGENIOUS | Difference vs everything already implemented | Expected ΔDTI | Cost |
|---|---|---|---|---|---|---|---|
| 1 | **Alteration × magnetic-low × gravity-gradient discordance with submodular emission** | B14, B01, B06, B17, B13 | Hydrothermal magnetite destruction (B14−B01 low) + clay cap (B17 high) + K-depletion (B06 low) + isostatic gravity-gradient peak (B13) | Concealed basin-fill faults have no scarp but leave an alteration halo that the scarp-based catalogue cannot map | S91-ALM used the same fields but a **greedy** top-score selection; this fuses them through the **shared CELF submodular emitter** with a strike-coherence gate | +0.005–0.020 | Low–Med (CPU, cached layers) |
| 2 | **Seismicity fluid-swarm-excess concealed conduits** | B10, B16, B17, B07 | Dependent-swarm vs independent-mainshock seismicity excess ln((1+B10)/(1+B16)) coupled to clay-cap B17 and geodetic shear B07 | Active geothermal fluids drive earthquake swarms along blind conduits that surface mapping misses | No lane used the **swarm-excess ratio** as a primary prior; S12-2 used it as a secondary seismicity feature only | +0.003–0.012 | Low (cached layers) |
| 3 | **Ordinal-pattern entropy (OPE) texture disorder** | B02, B06 | Bandt–Pompe permutation entropy contrast across a candidate strike; faulted/altered side is more disordered | Hydrothermal alteration and brecciation increase texture disorder along a damage zone without an amplitude step | **No lane used ordinal/compression-based texture.** All prior lanes used gradient/curvature/Hessian magnitudes | +0.005–0.015 | Med (sliding ordinal histograms) |
| 4 | **3DEP 10 m DEM scarp persistence through relay zones** | external CC0 USGS 3DEP 10 m DEM | Multiscale bare-earth scarp/slope-break persistence bridging magnetic/gravity edge segments through a relay/termination | Young surface rupture or persistent deformation expresses a bare-earth scarp even where aerial mapping missed it | S16-lidar and S26-lidar used lidar scarp but **not** 3DEP 10 m DEM relay-zone persistence; no lane bridged geophysics edges with DEM scarps | +0.010–0.030 | High (conditional on tile coverage/access) |
| 5 | **Marussi gravity tensor × magnetic analytic-signal angular crossing** | B11, B18, B03, B09 | Minor eigenvalue of the horizontal Marussi gravity tensor crossed with the 3-D magnetic analytic-signal direction | Faults juxtapose density and magnetic contrasts simultaneously; the crossing is orientation-locked and scale-persistent | S13-PTHA summed tensors and cancelled intersections; no lane computed the **angular crossing** of the Marussi tensor with the analytic signal | +0.004–0.012 | Med |

## Why these are plausible — and what they do not establish

- The organizer task is mapping faults indicative of geothermal resources; the public catalogue is explicitly incomplete and
  the private test contains expert-identified faults outside it. Reproducing catalogued lines is not discovery.
- USGS GeoDAWN distinguishes magnetic measurements (subsurface structure/geology) from radiometric measurements (surface
  geology/soil). Combining independent physics (gravity, magnetic, radiometric, seismicity) is more robust than blending
  correlated bands.
- The organizer metric is a distance-weighted Tversky index (α=0.2 false-positive, β=0.8 false-negative, 300 m kernel),
  so coverage-vs-clutter trade-offs matter.
- **None of these is a performance projection.** A HOLDOUT-DTI or blind SGMC control is not a leaderboard score.

## Gate before any proposal can be tested

1. Restore and hash-check the complete pinned stack (done this session).
2. Use the shared cache, evaluator, and writer; predeclare the feature set, controls, fold plan, and stop rule.
3. Run each feature alone through the leakage canary (symmetric AUC ≤ 0.90) before fitting.
4. Check every registry raster's surface rank correlation before placement (stop on |ρ| > 0.90) and the complete registry
   on final dots (stop on >70% within 3 px).
5. Stop after 3 experiments or 2 hours. Report every HOLDOUT-DTI with evaluator version, withheld-positive count, and 95% CI.
6. Promotion to a real slot is a separate selector step; organizer-confirmed results require the submission receipt.

**Current decision:** S91-ALM is unique and downloadable; none of these proposals has been run.
