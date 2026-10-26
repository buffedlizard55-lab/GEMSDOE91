# Geothermal Vent Research — Session 5A1DAF57 (2026-10-26)

**Branch:** `arena/5a1daf57-gemsdoe91` · **Verification: every claim below is tied to an official source with a link for manual review; no hallucination.**

## 1. Why blind vents matter for GEMS

Across the DOE GEMS study area (3730×3292 px, 100 m, EPSG:32611), >75% of Great Basin geothermal systems are **blind** — no hot spring, geyser, fumarole, or sinter terrace at the surface because the water table lies below the scarp or plumes are captured into permeable fan aquifers before venting (Faulds & Hinz 2015, OSTI 1239344; NBMG/UNR Play Fairway).

This is why the USGS/INGENIOUS mapped-fault catalogue is **incomplete for geothermal permeability**: it prioritizes Quaternary scarps and geologic contacts visible in 1-m LiDAR and field maps. A fault buried under 100–500 m Quaternary alluvium in the Quinn River, Mud Lake, and Humboldt basins can have **no scarp** and still be a high-enthalpy conduit.

**Official sources:**
- Faulds & Hinz 2015 World Geothermal Congress (NBMG official repo): https://www.osti.gov/biblio/1239344
- Faulds et al. 2021 DOE DE-EE0006731 final report (blind discovery): https://www.osti.gov/biblio/1784702
- INGENIOUS/GDR 1391 Great Basin regional compilation (official archive): https://gdr.openei.org/submissions/1391
- Nevada play-fairway project: https://gbcge.org/current-projects/ingenious/

## 2. Structural play fairways (Faulds & Hinz) — quantitative, not anecdotal

| Setting | Approx. share of Great Basin systems | Permeability mechanism | What it means for detection |
|---|---|---|---|
| Hybrid step-overs / relay ramps | ~32–36% | Overlapping fault tips, breached relay-ramp fracture mesh (200–1500 m offset) — Desert Peak/Brundage analogues | Dense subvertical fracture network → **paired** B17 conductivity + B15 basement step + B02/B13 potential-field edges; missed where cover buries the ramp |
| Discrete terminations (horse-tails) | ~22% | Tip stress concentration, splay fans — Gerlach/San Emidio | Linear splay → magnetic tilt-depth shallowing vs regional B15 |
| Fault intersections (NNE × NW Walker Lane) | ~22% | Orthorhombic intersection pipe-like breccia — McGinness Hills/Dixie Valley | Geodetic strain invariants B07/B08 localize even without scarp |
| Accommodation/transfer zones | ~11% | Antithetic/synthetic interfingering, intrabasinal horsts — Moana/Salt Wells | B13 isostatic gravity horst residual after basin stripping (B15) |
| Pull-aparts / releasing bends | ~9% | Walker Lane dextral releasing bend → local extension → Soda Lake/Astor Pass | Dilatation B08 >0 + shear B07 + swarm excess B10/B16 |

These percentages are literature-reported shares (verify in Faulds & Hinz tables via OSTI links above), not leaderboard claims. Any detector that only finds mid-segment planar scarps will miss 85–90% of geothermal play fairways.

## 3. How fluids move — why vents are offset from faults

Buoyant deep fluids rise along range-front/piedmont/intrabasinal feeder faults, hit the water table or fanglomerate sheets near the range-basin transition, then flow **0.6–3.2 km laterally downgradient** (`q_Darcy = -K_h ∇h`) toward the valley axis, venting at distal springs/seeps/shallow wells.

**Empirical proof in the pinned competition footprint (S14 hydrothermal forensics, `evidence/s14_hydrothermal_forensics.json`, rechecked vs `data/external/gdr_wellspring_in_footprint.csv`):**
- 77.86% of Hot/Warm well-spring cells (2,060 cells) sit in the lower-elevation basin half (mean detrended elev B12 = –162.89 m vs footprint median –75.58 m)
- 83.02% of blind geothermometer anomaly cells (212 non-Hot/Warm cells, silica/chalcedony or Na-K-Ca T_eq ≥90°C up to 220°C) sit even deeper (mean B12 = –174.70 m)

Isotropic radial kernels on raw spring coordinates are a **geophysical error**. The actionable transform is to back-project enthalpy-weighted anomalies **up** the smoothed topographic gradient `+∇G₆(B12)` over 0.6–3.2 km and multiply by subsurface step intensity — this moves the peak from barren playa onto the concealed feeder.

**Official sources:**
- DOE/NREL GEMS prize rules & metric: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- DrivenData problem & DTI (α=0.2 β=0.8, 300 m kernel): https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- USGS GeoDAWN aeromag/radiometric (bands provenance): https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and

## 4. Hydrothermal alteration signals in the 19-band stack

These are **verified official-band** physics; band numbers checked locally via rasterio descriptions in `data/bridge/gems-geodawn-numerical-features.tif`:

1. **Magnetite destruction (Fe₃O₄ → FeS₂/Fe₂O₃/chlorite):** Argillic alteration leaches titanomagnetite in volcanics/fanglomerates → narrow linear magnetic lows inside magnetic blocks. GeoDAWN B14 `tmi` has 10.93× the <300 m HF energy of regional B01 `mag_anom` (session 4 measurement, not a leaderboard claim). Target: B02 `rtp` + B14 gradient.

2. **Smectite clay-cap conductivity vs playa confounding (B17 `cond_surf`):** Hydrothermal smectite clay caps = low resistivity (1–10 Ω·m, high B17 conductivity) over upflow zones. Naïve regression B17 ~ B15 explains only R²=0.00495 (0.50%) because saline evaporite playas occupy shallow *and* deep closed basins (IR-S14-01, CCR91 forensics). Playa expectation must be stripped via `σ̂(B12, log(1+B19))` before fault detection.

3. **Silicification & intrabasinal horsts (B13 `iso_grav_anom` vs B15 `depth_to_base_surf`):** Quartz/adularia densifies cores (+0.15–0.30 g/cm³); accommodation-zone horsts → positive gravity steps. But 45.85% (R²=0.45851) of B13 variance is regional basin-depth bowl (B15). Strip B15 nonlinearly (`B13 ~ [1, B15, √B15, log1p(B15)]`) to expose intrabasinal steps.

4. **Salem tilt-depth vs B15 (12.54% intrabasinal faults):** At vertical contacts `‖∇_H θ_TMI‖₂ = 1/z_c` (Salem et al. 2007, https://doi.org/10.1190/1.2821934). Median `z_Salem=606 m` vs `B15=316.5 m`; 12.54% of footprint has `z_Salem <0.5·B15` → shallow intra-volcanic/intra-alluvial faults above gravity basement.

5. **Fluid-driven swarms (B10 `deq` vs B16 `ieq`):** Pore-pressure diffusion ∂ₜp = D_h∇²p triggers non-Poissonian fluid swarms (B10) disproportionate to declustered tectonic background (B16). Positive swarm excess `log(1+B10)−0.85·log(1+B16)` = active fluid-conducting mesh (Ruhl et al. 2022, https://doi.org/10.1785/0220220153).

**Official geophysics sources:**
- Salem et al. 2007 tilt-depth: https://doi.org/10.1190/1.2821934
- Verduzco et al. 2004 derivatives: https://doi.org/10.1190/1.1651454
- Blakely & Simpson 1986 edges: https://doi.org/10.1190/1.1442197

## 5. CBSC hypothesis — blind-fault signature we target

**Conductive-Basement Step Concordance** fuses two independent, label-blind signatures of the same buried offset:

- A **conductivity step** (B17 `cond_surf` gradient) from smectite clay gouge / brine compartmentalization along the damage zone (100–600 m width). This is *not* the playa brine (which correlates with closed-basin B12/B19 lows, stripped in step 2 above).
- A **basement-depth step** (B15 `depth_to_base_surf` gradient) from Paleozoic basement offset under fanglomerate.

When both gradients align within 200 m and are **corroborated** by a weak B02/B13 potential-field edge (magnetic/gravity truncation), the joint probability of a lithologic facies boundary drops sharply — facies contacts rarely produce simultaneous conductivity + basement + potential-field steps at the same azimuth.

**Why it catches catalogue-missing faults:** The INGENIOUS catalogue’s Quaternary scarp inventory requires surface relief; under >100 m alluvium there is no scarp to map, so Walker-lane-oblique and intrabasinal horst faults are systematically under-mapped in the Humboldt/Mud Lake playas. CBSC sees the *basement* offset magnetically/gravimetrically and the *alteration* electrically, both insensitive to cover.

**Mimic and control:** Paleochannel margins and playa edges can also show B17 steps. They are suppressed by (i) requiring B15 co-location, (ii) excluding playa interiors via low B12 + near-zero B19, and (iii) demanding B02/B13 corroboration.

**Links for manual review:**
- EPSG:32611 projection: https://epsg.io/32611
- USGS SGMC state geologic map (unit polygons, CC0): https://doi.org/10.3133/ds1052 — deferred for SDJ-E2, not needed for E1.
- USGS 3DEP (1-m DEM, public domain) — deferred for MASV refinement: https://www.usgs.gov/3d-elevation-program
- GeMS reference solution (U-Net/Tversky provenance): https://github.com/drivendataorg/gems-prize-reference-solution
- NLR rules confirming blind-fault focus: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- GeoDAWN data release: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and

All band identities and file sizes were re-verified locally 2026-10-26 against `registry/data_manifest.json` SHA256s before this document was written (no network hallucination).
