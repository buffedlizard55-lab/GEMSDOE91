# Current repository review — `arena/ae77ba5b-gemsdoe91` (2026-10-25)

## Executive decision

**No new GeoTIFF was generated. No candidate was selected or tested, no experiment lane was assigned, and no submission slot was used.** The official competition inputs and cached feature stack are absent from this checkout, so a real spatially blocked holdout, a final-grid build, a new-file novelty scan, and an on-disk validator run cannot be performed here. No synthetic or re-encoded historical TIFF is offered as a substitute.

- **OK TO DOWNLOAD (current review): NO** — there is no new candidate file. Existing TIFFs in the repository are historical artifacts, not this review's output.
- **OK TO SUBMIT: NO** — no new surface, spatial holdout, feature canary, registry check, or final-file validation was completed.
- **Slots used:** 0. **Experiments run:** 0. **ORGANIZER-CONFIRMED score:** none.
- **Preflight:** `BUILD BLOCKED`; 15/15 manifest inputs are absent locally and every implemented axis is blocked. The official data page redirected to login in the prior review; no challenge data were downloaded or restored from an unapproved mirror.

See the [current status page](current-review.html), [executive summary / future upload guide](executive-summary-current-review.html), and [machine-readable review card](run-card-REVIEW-AE77BA5B.json).

## 1. GEMSDOE32 `0.2778` claim: what the evidence supports

The `0.2778` value remains a **user-reported claim**, not an organizer-confirmed score in the evidence available to this checkout. On 2026-10-25 the linked [GEMSDOE32 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) said **“NO ORGANISER SCORE EXISTS”** for its artifacts, marked the named `h33-h33-2-b2` file `UNSCORED`, and labelled `0.2747` as a projection/model. No submission-page receipt connecting the named TIFF to `0.2778` was available. The public DrivenData leaderboard snapshot showed `0.4413` at rank 1, but that page is not a receipt for the GEMSDOE32 TIFF or for GEMSDOE91.

Several older repository documents call `0.2778` “ORGANIZER-CONFIRMED” or say that the TIFF “scored” it. Those statements conflict with the inspected GEMSDOE32 page and are not supported by a receipt. They must be read as superseded historical claims; this review corrects the most prominent occurrences and the active portal. A copied organizer receipt would be required to change the evidence class.

### Plausible metric mechanism — not a causal explanation of `0.2778`

The official [problem description and DTI definition](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) give a 300 m triangular kernel, `α=0.2`, and `β=0.8`. The repository's tested algebra is equivalent to the official weighted TP/FP/FN form:

`DTI = T / (0.2 T + 0.2 (S − M) + 0.8 |G|)`

Here `T` is the sum of per-truth-pixel *maximum* kernel-weighted credit, `S` is total prediction mass, and `M` is prediction mass credited by proximity to truth. Consequently, an added prediction that does not increase any truth pixel's maximum credit can add false-positive mass without improving `T`; sparse emission can therefore improve the metric in some configurations. The [byte-level lineage notes](parent-forensics.json) also describe the GEMSDOE32 raster as a 37,654-dot subset that deleted 2,545 dots within 200 m of the existing-fault mask.

Those facts do **not** show that thinning or collar deletion caused the claimed `0.2778`: there is no verified score receipt and no controlled, organizer-scored density-only comparison. The mechanism is plausible; its causal contribution to the reported value is unknown. No projection is presented as a score here.

### Highest recorded local result is a different evidence class

The highest recorded local result in this checkout is **`0.267782 HOLDOUT-DTI`**, evaluator `gems91-hide-recover-v1.0`, 60,988 withheld positives, 95% CI `[0.253687, 0.281135]`, in [`docs/run-card-S14-PTAC.json`](run-card-S14-PTAC.json). This is a spatial hide-and-recover result, not a competition score. Its literal final-dot gate stopped promotion: **99.852%** directed overlap within 3 px against `calib_r13lattice_00904.tif`. It is not a candidate to copy, re-encode, or upload.

## 2. Repository and fleet novelty review

A targeted text scan covered repository source, documentation, static pages, registry metadata, and source lists, followed by a keyword scan of the 92 rows in `docs/fleet-audit.json` (snapshot timestamp `2026-10-24T07:25:26Z`). The fleet snapshot itself says `complete_universal_registry: false`; private, unindexed, future, and unrepresented files remain outside its scope. This is a bounded novelty review, not universal uniqueness clearance.

Findings that change the ranking:

- **Already documented and therefore not counted as a genuinely new hypothesis family:** ASTER TIR/SWIR alteration is named as future lead `H14-4` in `LIMITATIONS.md`; USGS heat-flow residual plus 3-D MT is already hypothesis `H12-5` in `docs/HYPOTHESES_S12.md`. Neither lead is implemented as a current experiment here.
- **Human-readable repository-source/documentation scan:** no ECOSTRESS, NURE-HSSR stream-sediment/water, or stable-isotope/tritium feature references were found; existing GDR well/spring temperature and geothermometry remain related groundwater evidence. A case-insensitive search did flag short `NURE`/`HSSR` substrings in base64-encoded TIFF payloads embedded in archived JavaScript download bundles. The substrings were inside the payload fields, and decoding those bundle payloads found no literal ASCII tokens; these are encoding coincidences, not semantic dataset-use references. This is not universal novelty clearance: the fleet inventory is only 92 rows and private/unindexed material is not covered. The isotope proposal is a distinct measurement family, not a claim that groundwater evidence itself is new.
- **The 2017 USGS ASTER categorical alteration map is an untested product, but it is not ranked as a “new family.”** The broad ASTER family was already mentioned in `LIMITATIONS.md`. Its official southwest raster has a broad nominal bbox that overlaps the region, but exact valid-cell overlap with the challenge footprint, class coverage, and positional accuracy have not been checked. Metadata describes a categorical 30 m map, no formal positional/attribute accuracy assessment, DN 48 as no-data, and DNs 49–50 as potentially unreliable SWIR classifications. It is not a continuous spectral measurement.
- **Lithology/SGMC-derived methods were not promoted as novel.** Lithology-conditioned conductivity/radiometric residuals and multiple-depth MT are already covered in BHAR/H91 and related lanes. The 2026 GeMS/SGMC release was not added as a “new” method merely because its product is newer.

### Ranked, untested hypotheses

These are qualitative priors for *research usefulness*, not numerical DTI forecasts. The ordering balances plausible holdout signal against ingestion/analysis cost; all three have low or moderate confidence until local coverage, eligibility, leakage canaries, and spatial holdout results are measured. **None is selected for an experiment in this checkout.**

| Rank | Hypothesis and relevant layers | Physical signature and off-catalogue rationale | Difference from repository methods | Named non-fault mimics / controls | Qualitative holdout upside and cost |
|---|---|---|---|---|---|
| **1** | **Recharge/age-adjusted groundwater isotope residuals.** Great Basin groundwater geochemical database (sample/site tables; stable-isotope and tritium fields only where present and quality-qualified), plus elevation/aquifer context. Deduplicate against existing GDR samples before use. | A fault-controlled connection between recharge, basin aquifers, and concealed discharge may produce coherent isotope/residence-time departures from local elevation and aquifer baselines. A spatially continuous, fold-safe residual could point to hidden hydraulic compartments or conduits rather than to mapped fault proximity. | The repository uses point well/spring temperature and chemical geothermometry; the scanned code/docs/fleet did not identify stable-isotope/tritium predictors. This is a distinct measurement family, but it must be shown not to duplicate GDR observations. | **Mimics:** paleowater, high-elevation recharge, carbonate versus basin-fill aquifers, sample-location error, and seasonal or mixed-water sampling. **Controls:** stratify by aquifer/recharge context; preserve location uncertainty and source IDs; do not use fault-distance fields. | **Potential: moderate; confidence: low. Cost: medium–high** (relational joins, duplicate/sample provenance, geospatial uncertainty and sparse-field handling). Exact target-footprint sample count, field coverage, and challenge-use terms are unknown. |
| **2** | **Drainage-conditioned NURE-HSSR multi-element anomalies.** USGS NURE-HSSR water and sediment/soil sample records, their element/detection-limit/method metadata, catchments, and geology for within-unit background controls. | A multi-element water/sediment anomaly consistent across sample media and hydrologically connected upstream areas could indicate water-rock interaction or altered source rocks above a concealed structure; the anomaly would be routed to its contributing catchment, not smeared isotropically from every sample. | No NURE-HSSR or stream-sediment feature was found in the repository/fleet snapshot. Existing GDR geothermometry is a different, geothermal-well/spring observation family. | **Mimics:** uranium/mineralized lithology (the NURE program's original purpose), mining/anthropogenic contamination, laboratory/batch effects, drainage mixing, and incomplete survey coverage. **Controls:** harmonize methods and detection limits first; stratify by survey quadrangle/lithology; keep water and sediment evidence separate until agreement is tested. | **Potential: moderate; confidence: low. Cost: high.** The official USGS pages list 335,547 water and 397,625 sediment records nationally, not in the challenge footprint. The underlying program is incomplete and heterogeneous; Nevada counts and challenge-use terms are unverified. |
| **3** | **Quality-screened ECOSTRESS repeat-scene thermal residuals.** NASA ECOSTRESS L2T LSTE v003 land-surface temperature/emissivity, cloud and quality masks, acquisition times, plus terrain/land-cover context. | A spatially coherent thermal residual that persists across independent, quality-screened acquisitions after local, seasonal, emissivity, elevation, and observation-time adjustment could be a surface expression of shallow hydrothermal circulation near an unmapped fault. Require repeatability; a single hot pixel is not the signature. | No ECOSTRESS, multi-date TIR, or time-series surface-temperature feature was found in the scanned repository/fleet text. Existing well/spring temperatures are point samples, not satellite surface observations. | **Mimics:** cloud contamination, ISS view/solar-array obstruction, evapotranspiration/irrigation, soil moisture, bare-rock emissivity, slope/aspect, and changing overpass time. **Controls:** use product QC/cloud/obstruction fields; compare only time/season-matched scenes; require multi-scene persistence and negative controls. | **Potential: low–moderate; confidence: low. Cost: high.** The product is 70 m and active, but observation timing is variable, historical gaps are documented, and exact challenge-footprint scene counts are unknown. |

The ordering is a qualitative risk-adjusted priority, not an optimized numerical ranking: isotope/residence-time evidence is first because it offers a direct subsurface hydrology mechanism with potentially fewer legacy survey-method confounders, but its sample fields, precision, and coverage are unknown. NURE is second because water/sediment anomalies could offer a spatially independent catchment signal, while incomplete quadrangle coverage and cross-lab heterogeneity raise cost and false-positive risk. ECOSTRESS is third because repeatable thermal residuals are physically plausible but surface temperature has strong seasonal, emissivity, vegetation, cloud, view-angle, and overpass confounders. This ordering may change after local coverage is measured; no numeric DTI delta is assigned.

Source quality is a gating issue, not a footnote. USGS NURE-HSSR metadata reports that the 1975–1980 survey did not complete all quadrangles, involved multiple laboratories/methods, and had systematic reformatting errors. The NBMG database page itself cautions that locations can be off by kilometres and that accuracy is not guaranteed. ECOSTRESS is NASA-led data with generally open use unless a product-specific restriction applies, but the competition's separate external-data/sponsor-sharing condition still requires confirmation. None of these records currently establishes contest-use clearance or target coverage.

## 3. Why no candidate was validated

The local competition inputs are missing. The current `scripts/preflight.py` run reported missing `sample_submission` and `parent_r0_nan`, with every implemented axis blocked; the data directory contains none of the 15 manifest-listed files. `registry/data_manifest.json` now records the current 0/15 observation as false while retaining the 2026-10-23 presence/hash notes under date-qualified historical fields. The official DrivenData data page redirected to login in the prior review. Repository policy in [`docs/DATA.md`](DATA.md) forbids treating a public mirror as authorization to use or redistribute competition inputs.

Therefore this review did **not**:

- fetch or license-check candidate datasets for challenge use;
- count isotope, NURE, ECOSTRESS, or ASTER observations/cells inside the exact challenge footprint;
- generate a prediction surface or a TIFF/ZIP;
- run a leakage canary, spatial holdout, pre-placement surface-correlation check, final-dot comparison, or raster validator;
- assign a lane, recommend a weekly slot, or claim a submission score.

The next valid research step is conditional, not a slot choice: first verify source availability, exact footprint coverage, data provenance/licensing and sponsor-sharing compatibility; then preregister **one** method lane and use the shared `scripts/evaluate_holdout.py` and `scripts/submission_writer.py`. Hold out whole fault components with the prescribed buffer, derive catalogue features from visible faults only, mask visible pixels exactly, use pooled DTI with `α=0.2`, `β=0.8`, and the 300 m triangular kernel, run each feature alone as a leakage canary, and compare both the pre-placement surface and final dots against the available registry. A correlation over `0.90` or directed final-dot overlap over `70%` is a duplicate stop. A spatial holdout is not a leaderboard prediction; any future score must carry evaluator version, withheld-positive count and 95% CI, or an organizer receipt.

## 4. Three review passes and verification

1. **Evidence and score discipline:** rechecked the official DTI/problem page, GEMSDOE32 page, leaderboard snapshot, local run cards, and prior-forensics references. Corrected the `0.2778` evidence class and separated metric mechanism from causal claims.
2. **Method and novelty review:** searched repository source/docs and the 92-row fleet snapshot; compared candidate ideas with existing GDR geothermometry, heat-flow/MT (`H12-5`), ASTER (`H14-4`), lidar, radiometric, lithology, and plume methods. Excluded already-documented families from the new ranking and recorded incomplete-registry limits.
3. **Data, artifact, and delivery review:** confirmed local preflight is blocked, did not generate a raster, created a fail-closed review card/site guide, and ran the unit suite after installing the repository-pinned requirements in an ignored local virtual environment: **390 passed, 8 skipped, 30 warnings**. No scientific experiment or file validator was run because no new raster exists.

## 5. Official and primary sources

- [DrivenData #306 problem, DTI definition, target and file format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [GEMSDOE32 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) — owner-published evidence; says no organizer score exists for its artifacts.
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — page snapshot is not a receipt for this raster.
- [DOE/NLR competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Official DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — login-gated in the prior review.
- [Great Basin Groundwater Geochemical Database (NBMG/UNR)](https://nbmg.unr.edu/geothermal/GeochemDatabase.html) and [USGS Professional Paper 1409-C](https://www.usgs.gov/publications/geochemistry-and-isotope-hydrology-representative-aquifers-great-basin-region-nevada)
- [USGS NURE-HSSR water](https://mrdata.usgs.gov/nure/water/), [sediment](https://mrdata.usgs.gov/nure/sediment/), and [metadata/quality history](https://mrdata.usgs.gov/metadata/nurehssr.html)
- [NASA ECOSTRESS L2T LSTE v003 catalog record](https://www.earthdata.nasa.gov/data/catalog/lpcloud-eco-l2t-lste-003) and [NASA data-use guidance](https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance)
- [USGS ASTER alteration map release](https://www.usgs.gov/data/digital-maps-hydrothermal-alteration-type-key-mineral-groups-and-green-vegetation-western) — previously named family; not counted as a new hypothesis here.
- [USGS Great Basin heat-flow release](https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa) — related to already-documented `H12-5`, not counted as new.

---

**Final verdict: negative for promotion, not for science.** The strongest result of this review is a corrected evidence record and a bounded shortlist. The requested unique GeoTIFF remains unbuilt and unvalidated until authorized inputs and complete evaluation gates are available.