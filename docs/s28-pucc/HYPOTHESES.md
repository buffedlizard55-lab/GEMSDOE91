# S28-PUCC candidate geological hypotheses (generated 2026-10-31, before implementation)

Competition target: faults in the GeoDAWN region (NW Nevada) missing from the
USGS Quaternary/INGENIOUS catalogue; metric DTI (α=0.2 FP, β=0.8 FN, 300 m
triangular kernel) — recall-heavy. Every number below is a hypothesis, not a
measurement; measurements land in run-card.json.

## Ranked slate (by expected DTI improvement vs implementation cost)

### H28-1 — SGMC-off-catalogue corridor consensus (rank 1; expected gain: high; cost: low)
* **Layers:** `external/derived_sgmc_faults_100m_u8.tif` (USGS State Geologic Map
  Compilation faults, public domain, pinned) minus a 2 px collar of
  `official/existing_faults.tif`; GeoDAWN TMI (B14) and isostatic-gravity (B18)
  horizontal-gradient crest fields.
* **Physical signature:** a fault trace that exists in a state geologic-map
  compilation but not in the Quaternary catalogue is the *empirical distribution
  of catalogue omission* — young-looking but unlisted. The detector targets the
  geophysical edge (magnetic/gravity gradient) that the map trace rides on.
* **Why it catches hidden faults:** the test set is faults experts found that the
  catalogue missed; SGMC-minus-catalogue is the largest legal, free, official
  inventory of "real faults the Quaternary catalogue does not list". Hidden
  expert traces should concentrate where unlisted faults already cluster.
* **How it differs from this repo's attempts:** S27-OSDR used zero external fault
  inventories (pure GeoDAWN physics); S25-FABRIC used grain texture; the
  CONCENTRATION axis used GDR only as a block prior. No prior lane emitted along
  strictly-off-catalogue SGMC corridors.
* **Named mimic:** misregistered/obsolete map contacts carried in SGMC; quarry
  roads and canals mimicking linears.
* **External source (verified obtainable):** already pinned — USGS SGMC-derived
  raster in `registry/data_manifest.json` (`sgmc_faults_control`), origin USGS
  ScienceBase state geologic map compilations (public domain).

### H28-2 — GDR vent-chain corridor extension (rank 2; expected gain: medium; cost: low)
* **Layers:** `external/gdr_wellspring_in_footprint.csv` (Hot/Warm cells,
  12,570 de-duplicated cells) + TMI/grav edge field (B14/B18).
* **Physical signature:** geothermal upflow is structurally controlled; chains of
  hot springs/wells mark permeable fault damage zones, including faults with no
  surface rupture. Corridor = `exp(-d/12 px)` vent prior × edge co-location.
* **Why hidden:** a fault can be missed by surface mapping yet still vent;
  vent-chain corridors extend the mapped vent trend along strike onto the hidden
  strand. Directly serves the "geothermal vents" discovery goal.
* **Difference:** GEMSDOE36 `kpl36-exp3` used GDR vents as a two-regime mixture
  (0.1647); GEMSDOE27 `h29-hydrothermal-piedmont` used a hydrothermal prior
  (0.2190). Neither used vent-chain × edge-concordance corridor crests inside a
  consensus emission with catalogue flank removal.
* **Named mimic:** alluvial discharge fans and artesian seeps aligned along
  lithologic contacts, not faults.

### H28-3 — OSDR sign-locked dip reversal as a consensus vote (rank 3; expected gain: medium; cost: low)
* **Layers:** B11/B13/B14/B15/B17/B06 via the reused
  `compute_osdr_sub_backbone_fp` (38-feature cached stack).
* **Physical signature:** opposite flanks of a buried fault scarp produce
  antisymmetric (odd-step) response in potential-field and conductivity fields.
* **Why hidden:** buried/covered faults show dip reversal without the topographic
  expression that got faults catalogued.
* **Difference:** S27-OSDR used OSDR inside a 38-feature supervised pool with
  auto-context; this lane uses the pure label-free backbone as one vote in a
  corridor consensus and never trains on it.
* **Named mimic:** unfaulted dipping ash-flow tuff contacts; GeoDAWN flight-line
  seams (both documented in `cvdc_osdr27.py`).

### H28-4 — Seismicity-gated tip-relay corridors (rank 4; deferred)
* **Layers:** B10/B16 earthquake-density + catalogue tip geometry (fold-visible).
* **Signature:** background seismicity clusters at extensional relay ramps between
  catalogued segment tips; the connecting strand is usually unmapped.
* **Why hidden:** relay ramps are systematically under-mapped; experts filling the
  map gap would strike exactly there.
* **Difference:** `h33d-analog-tip-stepover` (0.2632) placed tip dots on the
  family base field; `s33-seisdil` (0.0963) used seismicity dilatation. A
  seismicity-*gated* tip corridor with fold-visible tips is new here.
* **Deferred reason:** needs fold-visible tip extraction (catalogue-derived;
  implementation cost medium). Pre-register for S29 if PUCC underperforms.
* **Named mimic:** quarry blasts / reservoir-induced seismicity clusters.

### H28-5 — Buried basement-step concordance (rank 5; deferred)
* **Layers:** B15 depth-to-conductive-base × B13/B18 gravity-gradient concordance
  under high cover (`mvsd_cover_index`).
* **Signature:** persistent basement offset beneath alluvium with no surface
  expression.
* **Why hidden:** buried faults are invisible to surface mapping.
* **Difference:** GEMSDOE40 `h8-euler-lineament-depthcluster` (0.0355–0.0984) and
  S16 basement steps used single fields; concordance-of-two beneath a cover gate
  is new but overlaps existing basement work enough that cost > gain.
* **Named mimic:** lithologic basement contacts, intrusion margins.

## Decision
Implement H28-1 as the PUCC consensus lane (H28-1/2/3 + lidar crest) per
`preregistration.md`. Validate on the spatially-blocked v3 hide-and-recover
holdout before any submission-slot consideration. H28-4/H28-5 are pre-registered
for a follow-up lane and are **not** implemented here (budget Rule 6).
