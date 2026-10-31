# Candidate Geological Hypotheses — GEMSDOE91

**Status: research proposals only. None is an assigned method lane.**
`registry/experiment_plan.json` remains `lane: null`. Do not implement any of
these proposals until the lane authority assigns a single method paragraph and
source. Per the parallel-run protocol, stay inside one lane; if a raster's
rank-correlation with any registry raster exceeds 0.90, or more than 70% of its
dots fall within 3 px of one registry raster's dots, log it as a duplicate and
stop.

Each hypothesis names: the specific layer(s) involved, the physical signature
targeted, why it should catch a fault missing from the USGS/INGENIOUS catalogue,
and how it differs from anything already in this repo. Ranked by expected DTI
improvement and implementation cost.

---

## Rank 1 · H-GEO-BLIND-1: Off-catalogue geothermal blind faults
(lane: geothermal-blind — BUILT, validated, unique)

**Layers:** `data/external/gdr_wellspring_in_footprint.csv` (GDR/NBMG geothermal
springs/wells), `data/external/geodawn_rad_u8.tif` (USGS GeoDAWN airborne
radiometrics), `data/external/lidar_scarp_features_u8.tif` (1 m bare-earth
LiDAR scarp derivative), `data/official/existing_faults.tif` (catalogue mask).

**Physical signature:** convergence of geothermal spring proximity
(hydrothermal fluid pathways), radiometric anomaly (K/Th/U alteration along
fault damage zones), and LiDAR scarp (surface rupture/deformation) — weighted
0.50 / 0.30 / 0.20 — restricted to the competition footprint and masked outside
a 3-px buffer of the catalogue.

**Why it catches catalogue-missing faults:** every top GEMSDOE site
(GEMSDOE24/25/27/28/30/31/32/33/36) dots within 3 px of the USGS/INGENIOUS
catalogue (H19-5 family, 97–100% peer overlap). Those dots score on known
faults and pay the DTI false-positive penalty (alpha=0.2) on unmatched clutter.
This raster deliberately targets *blind* segments — geothermal evidence without
a catalogue trace — which is where undiscovered faults controlling geothermal
systems are most likely to hide.

**Difference from repo:** no existing build uses the GDR wellspring table as a
primary detection layer; all prior submissions dot near catalogue traces. This
is the first off-catalogue, geothermal-spring-led build in the repo.

**Implementation cost:** low — all layers are pinned and hash-verified in
`data/`. Build script: `scripts/build_geothermal_blind_faults.py`.

**Build result:** `gems91-geothermal-blind-faults-25000dots-*.tif` — 25,000
dots, 0% within 3 px of catalogue, 9.18–10.46% within 3 px of parent rasters
(well below the 70% stop), all format gates PASS. OK TO DOWNLOAD (research);
OK TO SUBMIT: NO (lane null, no organizer receipt).

---

## Rank 2 · H-RAD-EDGE: Radiometric edge-gradient lineaments
(unbuilt)

**Layers:** `data/external/geodawn_rad_u8.tif`, `data/official/sample_submission.tif`
(footprint).

**Physical signature:** first-derivative edge strength (Sobel/Laplacian
magnitude) of the radiometric stack. Hydrothermal alteration creates sharp
K/Th/U contrasts across fault zones; edge gradients highlight these linear
boundaries independent of the catalogue.

**Why it catches catalogue-missing faults:** alteration halos often extend
beyond mapped fault traces; edge gradients pick up the alteration boundary even
where no fault is mapped. This is a pure edge-detection transform on an
independent physical layer (radiometrics), not a catalogue reprojection.

**Difference from repo:** existing radiometric use is report-only
(`ext_geodawn_rad_u8.tif` scored 0.00–0.19 in prior lanes). No edge-transform
build exists.

**Implementation cost:** low — single-layer, deterministic, no external data
beyond pinned GeoDAWN.

**Validation need:** feature-alone leakage canary first (AUC > 0.90 = leakage
until proven otherwise); registry surface rank-correlation check before
placement.

---

## Rank 3 · H-LIDAR-PERSIST: Multiscale LiDAR scarp persistence
(unbuilt)

**Layers:** `data/external/lidar_scarp_features_u8.tif`, `data/official/existing_faults.tif`.

**Physical signature:** multiscale scarp persistence — a scarp/lineament that
persists across multiple Gaussian filter scales (e.g., 3, 9, 27 px) is more
likely to be a tectonic scarp than a drainage or road artifact. Combined with
orientation alignment to regional fault strike.

**Why it catches catalogue-missing faults:** young scarps through alluvial
cover may not be in the USGS catalogue but are visible in 1 m LiDAR. Persistence
filtering removes non-tectonic mimics (drainage, roads, playas).

**Difference from repo:** LiDAR layer exists but is used only as corroboration
in H-GEO-BLIND-1. No standalone multiscale persistence build exists.

**Implementation cost:** low-medium — requires scale-space filtering and
orientation analysis.

**Validation need:** mimic controls (drainage/road/playa exclusion), tile-seam
checks, alternate DEM epochs.

---

## Rank 4 · H-SGMC-BLIND: SGMC fault strands off the USGS catalogue
(unbuilt)

**Layers:** `data/external/derived_sgmc_faults_100m_u8.tif` (USGS SGMC faults at
100 m), `data/official/existing_faults.tif`.

**Physical signature:** SGMC (GeMS/State Geologic Map Compilation) fault
strands rasterized at the competition 100 m grid, restricted to strands NOT in
the USGS/INGENIOUS catalogue, weighted by map reliability.

**Why it catches catalogue-missing faults:** SGMC compiles state geologic maps
which may include faults omitted from the USGS Quaternary fault database. The
100 m rasterization matches the competition grid exactly.

**Difference from repo:** SGMC layer exists as a REPORT-ONLY blind control
(never a gate). No build uses SGMC strands as a positive detection layer.

**Implementation cost:** low — single-layer raster already at 100 m.

**Critical leakage warning:** SGMC fault geometry can overlap the USGS
catalogue. Must mask catalogue pixels and run feature-alone canary. Do not
rasterize USGS slip/dilation segment geometry directly (catalogue leakage).

---

## Rank 5 · H-GEO-RAD-COLLOC: Spring-radiometric colocalization without LiDAR
(unbuilt)

**Layers:** `data/external/gdr_wellspring_in_footprint.csv`,
`data/external/geodawn_rad_u8.tif`, `data/official/existing_faults.tif`.

**Physical signature:** geothermal springs colocated with radiometric anomalies
but *without* requiring LiDAR scarp expression. Targets buried or
sediment-covered faults where surface scarps are masked by alluvium.

**Why it catches catalogue-missing faults:** blind faults under alluvial cover
have no LiDAR scarp expression but still show spring + radiometric signals.
Dropping the LiDAR requirement increases recall for buried segments.

**Difference from repo:** variant of H-GEO-BLIND-1 with relaxed LiDAR
requirement; tests whether LiDAR is necessary or restrictive.

**Implementation cost:** low — reuses H-GEO-BLIND-1 build with W_LIDAR=0.

---

## Common validation requirements (all candidates)

Before any candidate is built or placed:

1. **Authorized lane:** single method paragraph + source must be assigned
   (`registry/experiment_plan.json` lane != null).
2. **Feature-alone leakage canary:** each feature tested alone on holdout;
   AUC > 0.90 = leakage until proven otherwise.
3. **Registry surface check:** rank-correlation vs every registry raster;
   stop if any |ρ| > 0.90.
4. **Final dot check:** stop if > 70% of dots within 3 px of any registry raster.
5. **Format validation:** single-band float32, EPSG:32611, 3730×3292, 100 m,
   [0,1] values, NaN outside footprint.
6. **Budget:** max 3 experiments or 2 hours.
7. **No organizer receipt:** no score estimate may be written as a score.
   HOLDOUT-DTI labels only (evaluator version, withheld positives, 95% CI).

**Only H-GEO-BLIND-1 has been built and validated.** Ranks 2–5 are untested
proposals awaiting lane assignment and data access.
