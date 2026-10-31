# S28-VFCD — ranked, previously untried geological hypotheses (2026-10-30)

Lane self-assignment (Rule 1): **S28-VFCD — Vent-Field-Conditioned Detector.**
The standing brief refers to "the single method paragraph below" but supplies none
(`registry/experiment_plan.json` records `lane: null`, IR-91-02). This file *is* this
session's declared method paragraph; drift checks run against the frozen registry on
both the surface (Spearman |rho| ≤ 0.90) and the final dots (≤ 70 % within 3 px of any
registry raster's dots — evaluated against all *method/submission* rasters; see the
run card for the dense-calibration-lattice irregularity IR-S28-01).

Every hypothesis names: the layer(s), the physical signature, why it should catch a
fault missing from the USGS/INGENIOUS catalogue (`data/official/existing_faults.tif`),
and how it differs from anything already implemented in this repo or scored by the
GEMSDOE fleet. Ranked by expected HOLDOUT-DTI improvement × implementation cost.

## H1 — Geothermometer-gated discharge-conduit detector (TOP CANDIDATE)

* **Layers:** pinned `data/external/gdr_wellspring_in_footprint.csv` (GDR well/spring
  temperature + quartz/chalcedony/cation geothermometer chemistry, 12,570 distinct
  cells, 928 Hot / 1,247 Warm, geothermometer T up to 262 °C); GeoDawn radiometrics
  `B03/B06/B02`; conductivity surfaces `B15/B17`; potential-field edges `B13/B14/B18`.
* **Signature:** (i) proximity to *high-enthalpy* discharge points (temp_c ≥ 80 °C or
  geothermometer ≥ 120 °C) — weighted exponential kernels at 12 px / 25 px; (ii)
  vent-to-vent straight-segment corridor density for high-T pairs within 40 px (a
  "string of pearls" along the concealed strand); (iii) corridor density restricted to
  > 8 px off-catalogue cells.
* **Why missing faults:** the INGENIOUS/USGS catalogue maps surface-rupturing faults.
  Blind faults have no mapped trace but still channel fluid: high-enthalpy discharge at
  the surface requires permeable fault damage zones tapping the brittle–ductive
  transition. Vent-aligned corridors off the catalogue are direct surface evidence of a
  concealed permeable structure.
* **How it differs here:** the GDR file was previously used only as a 1-km block prior
  to *reallocate R0's dots* (CONCENTRATION axis, MODEL −0.0056; IR-91-18) — never as
  detector features inside a trained model. No GEMSDOE fleet submission used
  geothermometer chemistry. Nothing else in `src/gems91/` reads the GDR file except
  `src/gems91/prior.py` (the block prior).
* **Named non-fault mimics:** (1) groundwater discharge focused on permeable ash-flow
  tuffs / carbonate contact karst with no fault control; (2) basin-margin cold springs
  where alluvial fans meet basin fill; (3) duplicate GDR well records at the same pad
  (de-duplicated here by pixel cell).
* **Expected improvement:** HIGH (new independent information; cheap).

## H2 — SGMC-off-catalogue concordance corridors

* **Layers:** pinned `data/external/derived_sgmc_faults_100m_u8.tif` (USGS state
  geologic-map faults, independent of the INGENIOUS catalogue) minus the catalogue
  dilated by 3 px; `B12/B19` topographic ridges; `B13/B14/B18` potential-field edges.
* **Signature:** cells within 2 px of an SGMC-mapped fault that is > 8 px from the
  catalogue AND supported by a geophysical edge — "USGS already mapped it, INGENIOUS
  did not".
* **Why missing faults:** the organizer's hidden truth is real faults omitted from the
  catalogue; USGS 1:250 k map faults absent from that catalogue are the highest-prior
  omissions by construction.
* **How it differs here:** SGMC has only ever been used as a *blind diagnostic* and as
  one raw emitter (`sgmc-off-catalogue-44k`, GEMSDOE29 → 0.0512 USER-REPORTED, no
  corroboration). It has never been a feature in a trained detector.
* **Named non-fault mimics:** 1:250 k generalization lines drawn beyond field
  verification; quarry/road lineaments digitized as faults.
* **Expected improvement:** MEDIUM (cheap; included as E-arm features, not support).

## H3 — Vent-anchored tip/relay connectors

* **Layers:** catalogue tip geometry (component end points of `existing_faults`), GDR
  high-T vents, `B12/B19` ridge grain.
* **Signature:** corridors from a mapped-fault tip to the nearest aligned high-T vent
  cluster, extended along local ridge grain beyond the 3 px collar.
* **Why missing faults:** slip dies out at mapped tips but the structure continues
  blind; geothermal systems localize at tip/relay damage zones.
* **How it differs here:** the GEMSDOE33 "analog-tip-stepover" (0.2632 USER-REPORTED)
  was a *family edit of R0's H19-5 support*; this is a de-novo connector detector with
  vent anchors, never implemented in this repo.
* **Named non-fault mimics:** alluvial fan apex alignments; drainage networks.
* **Expected improvement:** MEDIUM; cost MEDIUM (tip extraction). Preregistered as a
  follow-up lane if H1's holdout bar is not beaten — not run in this 3-experiment
  budget.

## H4 — Geothermometer-gated paired alteration halo (magnetic-destruction conduit)

* **Layers:** `B08` dilatation, `B09` magnetic density, `B06` radiometric TC, `B17`
  conductivity surface, GDR geothermometer T.
* **Signature:** linear magnetic-low / K-anomaly corridor whose two flanks are
  magnetically quiet (hydrothermal magnetite destruction), gated by high-T discharge
  within 25 px.
* **How it differs here:** PMDB (paired-flank magnetite-destruction bridge) exists in
  the S27-CVDC stack ungated; the geothermometer gate is the new element. Expected
  improvement MEDIUM-LOW; cost MEDIUM. Not run in this budget.

## H5 — USGS 3DEP 1 m lidar scarp persistence (BLOCKED — external data)

* **Layers:** USGS 3DEP QL1/QL2 lidar DEM for Nevada (free, official:
  https://apps.nationalmap.gov/lidarexplorer/ , https://rockyweb.usgs.gov ).
* **Signature:** sub-metre scarp persistence at 1 m resolution — blind-fault
  micro-topography invisible at the 100 m grid.
* **Status:** cannot be validated in this sandbox (outbound network restricted to
  github.com / pypi.org / npm). Named free official source above; requires an
  unrestricted host and ~100 GB staging. Declared NOT VIABLE for this session's
  budget; recorded as the top external-data follow-up.

## Ranking

| rank | hypothesis | expected HOLDOUT-DTI gain | cost | run in this budget |
|---|---|---|---|---|
| 1 | H1 geothermometer-gated discharge conduit | high | low | YES (E1–E3) |
| 2 | H2 SGMC-off-catalogue concordance | medium | low | YES (features in E2/E3) |
| 3 | H3 vent-anchored tip/relay connectors | medium | medium | no |
| 4 | H4 geothermometer-gated alteration halo | medium-low | medium | no |
| 5 | H5 3DEP 1 m lidar scarp persistence | high (if real) | high + blocked | no (IR: data host) |

The top candidate (H1, with H2 folded into the E2/E3 feature stacks) is validated on
the frozen spatially-blocked hide-and-recover holdout (`gems57-pooled-hide-v2`,
`label-blind-quadrants-v3-feature-buffered`) **before** any weekly submission slot is
spent. Per protocol Rule 6 this session never spends a slot; promotion is the separate
selector step.
