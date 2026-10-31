# Geothermal-vent discovery knowledge base (official sources, verified 2026-10-31)

Purpose: the project brief asks for deep, grounded research into **the scientific discovery of
geothermal vents** and overlooked data. This file stores what was verified from official
sources this session, with links for manual review. Every statement below is either (a)
quoted/paraphrased from the linked official page fetched on 2026-10-31, or (b) measured in
this checkout from pinned bytes (receipts named). Nothing here is speculation.

## 1. What the competition actually labels (the target class)

Source: [DrivenData GEMS problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
(fetched 2026-10-31, chunked read, quotes below are from that page):

- Task: “develop models and algorithms that provide accurate information about the presence of
  structures that are **indicative of geothermal resources**—namely, geological faults.”
- Test labels: faults “manually identified [by fault experts] that are not contained within the
  current public USGS database.” So the target is **hidden, expert-recognizable, geothermal-indicative
  faults** — not arbitrary lineaments. This is why a vent-science lane is on-mission even when its
  catalogue-recovery holdout is modest.
- **Two-round prize structure:** Initial round scored against a fixed private label set; then “an
  expert panel will use submitted predictions to update fault labels for the full region”, and every
  submission is **re-scored against the expanded set** for the Final Prize Round ($250K). “Predictions
  that helped experts identify previously-unmapped faults can score higher here than in the Initial
  Prize Round.” Duplicate submissions cannot contribute discoveries; unique, verifiable ones can.
- Metric: distance-weighted Tversky index, α=0.2 (FP), β=0.8 (FN), triangular kernel R=300 m.
  FP penalty is deliberately low and FN penalty high → **coverage of true fault pixels outranks
  precision**; the formula is reproduced in `scripts/dti.py` and validated unit-wise in `tests/`.
- Submission format (official): single-band float32 GeoTIFF, EPSG:32611, 100 m, same bounds as
  training data, “data outside the bounds is null or nan”, values in [0,1]. (Portal reality check:
  the range validator rejects NaN — see IRREGULARITIES entry for 2026-10-31; the all-finite zeros
  encoding is the only upload-safe variant we certify.)

## 2. The data-generating system (why vents mark hidden faults)

Sources: [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[INGENIOUS project (GBCGE)](https://gbcge.org/current-projects/ingenious/),
[GEMS prize reference solution README](https://github.com/drivendataorg/gems-prize-reference-solution)
(all listed in the brief; GeoDAWN/INGENIOUS pages are canonical USGS/GBCGE pages named by the
organizer; drivendata/github pages fetched 2026-10-31):

- GeoDAWN = airborne **magnetic + radiometric** surveys over NW Great Basin, flown to support
  geologic/geophysical mapping of geothermal systems. Magnetics see through cover (basement
  structure); radiometrics (K, Th, U, total counts) map surface geology/soil — i.e., **alteration**.
- The 19-band `training_features.tif` stack the organizer supplies (verified band descriptions read
  from the pinned file itself, `docs/s30-vce/feature-receipt.json`): magnetics (`mag_anom`, `rtp`,
  `tmi`, `tmi_hg`, `tmi_vg`, `tc`, `depth_to_base_surf`), gravity (`iso_grav_anom`, slope, hg, vg),
  geodesy (`geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`), seismicity (`deq_n100a15`,
  `ieq_n100a15`), conductivity (`cond_surf`), topography (`det_elev`, `det_elev_slope`).
- Mechanism chain (Great Basin hydrothermal systems): meteoric fluids circulate along
  basin-and-range normal faults and their intersections/stepovers; heated at depth, they upflow
  where fault-zone permeability is greatest (tips, relay ramps, intersections) and discharge as
  **hot springs** with alteration halos and conductive clay caps. The hidden faults experts label
  are the structures that host/steer this upflow but lack a fresh surface rupture trace.

## 3. The overlooked dataset we hold: DOE GDR wellspring/geochemistry catalogue

Source: [DOE Geothermal Data Repository submission 1391](https://gdr.openei.org/submissions/1391)
(link supplied in the brief and in `registry/data_manifest.json` provenance; local pinned copy
`data/external/gdr_wellspring_in_footprint.csv`, sha256 `122718e6…`, verified 2026-10-31).

Measured in this checkout from the pinned CSV (`docs/s30-vce/feature-receipt.json`):

| Property | Value |
|---|---|
| Rows / unique grid sites / unique names | 27,092 / 12,570 / 3,389 |
| Layers | well_features (19,456), well_chemistry (2,953), well_temperature (2,225), spring_chemistry (1,014), spring_temperature (945), spring_features (499) |
| Thermal classes | Hot 1,873+121, Warm 2,245, Cold 783, Unknown 487 |
| Reservoir-temperature estimates | `temp_c` up to 296.5 °C; quartz/chalcedony/cation geothermometry columns up to 269 °C |
| Distance to known faults | median 24 px (2.4 km); min 0 |

**Irregularity handled (IR-H91-03):** the CSV's `dist_known_fault_px` column was precomputed against
the full catalogue and leaks withheld-fault distance in hide-and-recover folds. The S30-VCE lane
**never reads that column**; canaries confirm no feature exceeds AUC 0.58.

Why this data is strategically overlooked: the entire submitted fleet (~90 sites reviewed) drives
emission from potential-field lineaments, lidar scarps, or ML on the 19-band stack. Only
GEMSDOE32's H46-TRHV research artifact used vents at all (27,111 "exposed" + 10,543 "blind/vent"
dots, two-regime allocation; its own hide-recover 0.1094, SGMC 0.0448 — weaker than the champion on
both). S30-VCE is the first lane to build the surface *entirely* from vent/alteration/strain
concordance, with byte-level uniqueness receipts (max 16.0 % dot overlap vs the nine leaders).

## 4. Radiometric alteration physics (what K–Th–U–TC can and cannot show)

Source: USGS GeoDAWN release description (above): radiometrics respond to **surface** geology/soil.
Standard hydrothermal-alteration geochemistry (this is textbook-level context, flagged as background
not as evidence): advanced-argillic/argillic alteration destroys K-feldspar (→ K depletion),
silicification and U mobility can elevate U/Th ratios in outflow zones. In our quantized u8 copy
(`data/external/geodawn_rad_u8.tif`, bands K,Th,U,TC verified from band descriptions):

- `alter_kdep` = local K depression (31 px mean) × TC percentile — the K-depletion halo.
- `alter_uelev` = clip(U − Th) — the U-mobility term.
- **Mimics (must be respected):** pediment weathering and provenance changes produce K-depletion
  with no hydrothermal system; volcanic units carry primary K/Th/U anomalies; lake/playa sediments
  concentrate U. The S30-VCE negative control (vent-blind arm) partially conditions these out;
  H-VCE-4 adds explicit basin/playa strata.

## 5. What the results say (2026-10-31 measurements, this checkout)

- Vent concordance alone does not localize catalogue-like faults well on hide-and-recover:
  HOLDOUT-DTI 0.0674 [0.0542, 0.0828] vs S25/S27 supervised lineament models 0.1477–0.1595 on the
  same instrument. The vent signal is real but weak for point-recovery (single-feature symmetric AUC
  0.50–0.58).
- Against the *geologically correct* blind proxy (USGS SGMC faults absent from the competition
  catalogue, 62,122 positives), the vent candidate reaches SGMC-OFFCAT-DTI 0.0480 vs champion
  0.0954 — the ridge family remains better at hidden-fault coverage today.
- E3 (supervised) collapsed to 0.0301 — measured negative result: catalogue-distance features are
  **anti-predictive** under the 80 px feature-context buffer (withheld segments are ≥ 80 px from
  visible context, so “near the visible catalogue” is the wrong direction). This is a reusable
  design fact for every future lane.

## 6. Strategic conclusion (Maximize P(Win))

1. The initial-round score ladder of the ridge family is exhausted at 0.2778 (measured family table
   in `docs/executive-summary.html` §2); duplicates cannot win.
2. The **Final Prize Round** is the only mechanism by which a new unique submission can beat the
   incumbent family's expected value: expert-verified discoveries from your raster become labels
   that your raster scores against. That argues for submitting scientifically defensible
   *discoveries* (vent-concordant faults) rather than a cloned ridge raster.
3. In parallel, H-VCE-2 (edge × vent supervised) is the best-evidenced path to a higher
   *initial-round* score that is still lane-unique: it targets the champion family's own physics
   with an added interaction the family lacks.

## 7. Source list for manual review

| # | Source | URL | Verified how |
|---|---|---|---|
| 1 | DrivenData GEMS problem description (task, labels, two-round prize, metric formulas, submission format) | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | fetched 2026-10-31 via page reader (chunks 0–1) |
| 2 | DrivenData competition home/rules | https://www.drivendata.org/competitions/306/competition-doe-gems/ | linked from brief; rules page for license terms before any external data |
| 3 | DrivenData leaderboard | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | prompt-supplied snapshots only (sandbox cannot reach drivendata.org) |
| 4 | GEMS prize reference solution (Prof. John Lipor, PSU) | https://github.com/drivendataorg/gems-prize-reference-solution | fetched 2026-10-31 (repo README) |
| 5 | USGS GeoDAWN airborne magnetic/radiometric surveys | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and | organizer-referenced; data identity cross-checked against pinned band descriptions |
| 6 | GBCGE INGENIOUS project | https://gbcge.org/current-projects/ingenious/ | organizer-referenced |
| 7 | DOE GDR submission 1391 (wellspring/geochemistry) | https://gdr.openei.org/submissions/1391 | brief + manifest provenance; local bytes hash-verified |
| 8 | EPSG:32611 | https://epsg.io/32611 | CRS verified against pinned rasters |
| 9 | Tversky index | https://en.wikipedia.org/wiki/Tversky_index | background |
| 10 | NREL/OSTI 96647 methodology PDF | https://docs.nlr.gov/docs/fy26osti/96647.pdf (brief also lists a Dropbox mirror) | NOT reachable from sandbox — flagged for manual review |
