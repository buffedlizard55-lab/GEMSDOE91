# Priority GEMSDOE sites — executive review and submission decision

**Review date:** 2026-10-26 (UTC)  
**Decision:** **No new TIFF was generated in this review. No new TIFF is cleared to download or submit.** The assigned experimental lane is not specified, the input data/features are absent from this checkout, and no candidate has passed the requested holdout and registry gates. Do not spend a competition slot on a prior site artifact or on an unvalidated replacement.

**Source verification performed:** on 2026-10-26, GitHub's API was used to fetch public source HTML for the requested projects (not the DrivenData organizer). The current [GEMSDOE28 `index.html` snapshot](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/10c26af3dc4d45292189734b0b696c7afb24ffb1/index.html) includes a nine-site scorecard, explicitly says **“No row is ORGANIZER-CONFIRMED”**, and labels its historical claims “unverified owner report.” The current [GEMSDOE32 `docs/index.html` snapshot](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/7a97c5a88936a3fdb99d0358c3b85d739a714631/docs/index.html) instead calls 0.2778 “organizer-confirmed” while also calling it “owner-reported,” but provides no submission-page receipt in that content. This is an **evidence-label conflict**; this review uses **OWNER-REPORTED (UNVERIFIED)**, not ORGANIZER-CONFIRMED, unless an organizer receipt is produced. The current GEMSDOE32 page also presents a different new primary artifact and labels it “OK TO DOWNLOAD AND SUBMIT”; that is a page-owner assertion, not a clearance established by this review. No candidate from that page was downloaded or tested here. The GitHub-hosted project content is not itself an organizer receipt.

[Open the public-facing summary](priority-sites-executive-summary.html) · [Machine-readable run card](run-card-priority-sites-review.json) · [Current project front page](index.html) · [Standing project brief in README](../README.md#full-project-brief) · [Limitations and next steps](../LIMITATIONS_AND_NEXT_STEPS.md) · [Repository review evidence and historical R0 analysis](GEOTHERMAL_VENT_RESEARCH_S19.md)

## Executive answer

Within the nine sites named in the request, the highest listed value is **0.2778 OWNER-REPORTED (UNVERIFIED)** for GEMSDOE32's `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`. It is the best reported result among these sites, not a receipt-confirmed organizer score and not a recommendation to re-submit that file. The GEMSDOE28 cross-site scorecard calls the historical values “unverified owner report” and says no row is ORGANIZER-CONFIRMED; the current GEMSDOE32 page inconsistently labels 0.2778 “organizer-confirmed” while also saying “owner-reported.” Neither source snippet supplies a DrivenData receipt. Repository forensic notes describe a lineage in which a continuous H19-5 ridge surface was thinned to sparse dots, then catalogue-near dots were removed. That is a plausible explanation for why the reported value increased: the DTI-style objective rewards spatial coverage with a saturating distance kernel while still charging emitted prediction mass, so redundant nearby dots can hurt. This is a mechanism supported by prior repository analyses, not proof that this transformation caused an organizer score. See [the S19 synthesis, §3](GEOTHERMAL_VENT_RESEARCH_S19.md#3-forensic-analysis-why-gemsdoe32-scored-02778-how-gemsdoe-sites-compare-and-what-gemsdoe91s-live-scores-01367--01823-prove) and the source conflict above.

**Can we beat 0.2778?** It is possible in principle, but this checkout has no evidence that a new candidate would exceed it on the organizer's hidden test. The latest existing GEMSDOE91 run-card in this repository is S19-SVHF: **0.147791 HOLDOUT-DTI**, evaluator `gems57-pooled-hide-v2`, 60,988 withheld positives, 95% CI `[0.132771, 0.162342]`; this is an internal spatial holdout result, not a leaderboard score. It was below that run's recorded comparator and was marked negative. Existing runs cannot establish performance on a fresh hidden leaderboard, and comparing their holdout DTI directly with user-reported site scores is invalid.

The right next step is not to copy or relabel a high-score TIFF. It is to select a genuinely distinct geological mechanism, preregister it, reuse the shared feature stack/evaluator/writer, run the per-feature leakage canary and blocked holdout, compare the unplaced surface and final dots with the complete registry, and only then publish a clearly labeled research artifact. This review does not choose a weekly slot.

## Top reported entry by site

Every value in this table is labeled **OWNER-REPORTED (UNVERIFIED)**. The GEMSDOE28 source scorecard displays the same historical entries as “unverified owner report” (some rounded, e.g. 0.26 rather than 0.2600) and explicitly states no row is ORGANIZER-CONFIRMED. No submission-page receipt was available in this checkout to verify them. The original request supplied the identifiers and precision shown below. Do not treat these as a common benchmark: the values alone do not establish the organizer split, receipt, or exact scoring conditions.

| Site | Highest result listed in the request | Value and evidence class | Executive interpretation / caveat |
|---|---|---:|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | **0.2477 OWNER-REPORTED (UNVERIFIED)** | H19-5 sparse-dot lineage; the same request also lists a later 0.0859 result under a different hypothesis. The higher result is the site maximum supplied, not evidence the later method was worse on a matched evaluation. |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | **0.2600 OWNER-REPORTED (UNVERIFIED)** | Same named H19-5 ridge family, at a sparser dot spacing than the GEMSDOE24 entry. Historical repo forensics describe this as part of the H19-5 emission ladder. |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | **0.2449 OWNER-REPORTED (UNVERIFIED)** | A topographic gap-closure variant. The request also gives a 0.2190 hydrothermal-piedmont entry. No receipt or controlled ablation is supplied here. |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | **0.2710 OWNER-REPORTED (UNVERIFIED)** | Highest of four entries listed for this site; the other listed results range 0.2649–0.2708 OWNER-REPORTED (UNVERIFIED). |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | **0.2600 OWNER-REPORTED (UNVERIFIED)** | Off-catalogue Poisson-style emission result. Same reported value as GEMSDOE25's differently named candidate does **not** establish identical pixels or equal methodology. |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | `h27-4-solo-d28-20261004-8acb75e1-nan` | **0.2708 OWNER-REPORTED (UNVERIFIED)** | Same candidate identifier and value as the GEMSDOE28 `h27-4-r1-solo-d2-8` entry in the request. Likely a shared/re-published lineage, but exact identity requires byte/pixel hashes; do not count as independent evidence. |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778 OWNER-REPORTED (UNVERIFIED)** | The highest value among these nine sites in the supplied list. Repository evidence identifies the artifact as a sparse H19-5-family surface with catalogue-collar pruning; no organizer receipt is present in this checkout. |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | **0.2632 OWNER-REPORTED (UNVERIFIED)** | Analog tip/stepover hypothesis; value is lower than GEMSDOE32's reported result. This does not show the mechanism is scientifically inferior without a common holdout and matched emission budget. |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | **0.2750 OWNER-REPORTED (UNVERIFIED)** | Near the GEMSDOE32 reported value, and described in historical project notes as a different Andersonian/geothermal-prior approach. It supports testing distinct surfaces, but is not an independent verified score or proof of a vent/fault mechanism. |

**Within the request's nine entries, GEMSDOE32 is the clear reported leader.** It is not a validated submission choice. The highest reported entry listed is 0.2778; another prompt statement gives 0.3195 and a later current leaderboard figure of 0.4413. Those are different user-supplied time/context claims, not one coherent benchmark series. The repository records 0.4413 as PUBLIC-LEADERBOARD context in some prior notes but does not include a fresh organizer receipt for this session. Do not call any of these values HOLDOUT-DTI.

## What the data support, and what they do not

1. **Supported by pinned repository metadata:** the comparison inventory names raster artifacts for GEMSDOE24, 25, 27, 28, 30, 32, 33 and 36 and records hashes for those inventory files. Its declared scope is incomplete. GEMSDOE31 is not established as a separate inventory artifact in that list. The `registry/r0_verification.json` historical receipt records the GEMSDOE32 R0 zeros TIFF SHA-256 as `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`; the same historical evidence records 37,654 positive unit dots and exact identity with a 2 px catalogue-collar-pruned d2.8 ancestor. These are repository-recorded historical checks, not recomputed in the current checkout.
2. **Supported as a plausible scoring mechanism, not causal proof:** sparse, spaced dots can reduce redundant prediction mass because spatial truth credit saturates around nearby positives, and removing dots near already-mapped faults can reduce low-credit predictions. The site scores alone cannot isolate these effects; causal attribution requires same-surface, same-split ablations.
3. **Not supported:** claims that R0's 0.2778 is organizer-confirmed, that it is current rank-one, that any candidate has beaten it on the live hidden test, or that a fault proxy is direct evidence of geothermal vents. Competition mapping targets faults relevant to exploration; faults, geothermal systems, springs, and vents are related but non-identical targets.
4. **Fresh-checkout limitation:** the `data/` folder is absent and the Python environment initially lacks NumPy, Rasterio, SciPy, scikit-learn, and pytest. Registry manifests contain historical `local_present` flags; these are not evidence that bytes currently exist locally. Therefore no fresh holdout, feature canary, raster read/validation, or full-registry novelty check was run in this review.

## Candidate hypotheses to preregister before implementation

These are **not tested results** or score projections. A source/code search found no current implementation of Sentinel-1 InSAR time series, a multi-date thermal time series, absolute-DEM stream-network migration metrics, or time-dependent seismic catalog processing in `src/` or `scripts/`. Related ideas were proposed in earlier hypothesis documents (notably `docs/HYPOTHESES_S17_CGRD.md` and `docs/HYPOTHESES_S17.md`), but that does not make them implemented or validated. Ranked potential is qualitative and highly uncertain; without data and holdout results there is no defensible numeric DTI estimate. The shared lane rule still requires one explicitly assigned method paragraph. Root `docs/run-card.json` says `assigned: false`, so none is implemented or run here.

| Rank | Hypothesis | Specific layers and physical signature | Why it could find faults missing from the mapped catalogue | Difference from implemented code / overlap warning | Qualitative expected DTI potential / cost / source access |
|---:|---|---|---|---|---|
| 1 | **Interferometric strain transients at concealed fault zones (ISTF)** | Multi-temporal Sentinel-1 ascending/descending line-of-sight displacement, coherence and seasonal amplitude from NASA/JPL ARIA or ASF DAAC; measure persistent narrow strain gradients and migration/creep across basin margins, optionally aligned with static GeoDAWN gravity/magnetic context. | A buried or alluvium-covered fault can accommodate aseismic slip or fluid-pressure-related deformation without a clear 100 m DEM scarp or catalogue trace; time-domain deformation is an independent measurement rather than another static lineament score. | No InSAR time-series raster/ingestion code found in `src/` or `scripts/`; an earlier S17-CGRD proposal mentioned InSAR, but was not implemented in this repo. Must guard against atmospheric delay and non-fault hydrologic deformation. | **Highest potential, very uncertain; high cost. BLOCKED / not viable here.** Official source lead: [NASA ARIA](https://aria.jpl.nasa.gov/) / [ASF DAAC](https://asf.alaska.edu/). Sandbox outbound allowlist does not include NASA/ASF hosts; AOI coverage, download availability and license terms were **not checked**, so no validation or holdout is possible here. |
| 2 | **Piedmont drainage-network deflection and fan incision (PDFI)** | Absolute 1 m / 1/3-arc-second elevation from USGS 3DEP; channel-network curvature, tributary asymmetry, chi/knickpoint residuals, and fan-apex incision orientation. | Blind structures may deflect streams or partition fans before a fault trace is mapped; evaluating in cover-rich piedmont zones and outside catalogue buffers tests for buried fault continuation instead of just scarp proximity. | Drainage-χ was proposed in earlier repo hypotheses but no flow-routing/network implementation was found in `src/` or `scripts/`. Available competition B12 is detrended and is unsuitable by itself for full drainage routing. | **Medium-high potential, uncertain; high cost. BLOCKED / not viable here.** Official lead: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). Official footprint coverage and tile availability could not be checked from this sandbox; the source host is outside the network allowlist. |
| 3 | **Seasonal thermal-flow anomaly aligned with structure (STFA)** | Multi-date Landsat Collection 2 surface-temperature products (plus night/day and seasonal summaries), GeoDAWN static temperature and mapped fault orientations; target repeatable thermal gradients that persist across seasons and align with geophysical structures. | Persistent advective heat may mark fluid flow along an unmapped fault; the time dimension can reject transient surface heating that a single static temperature layer cannot distinguish. It is a geothermal-system proxy, not direct fault truth. | The repo includes static geotherm temperature and GDR spring/well geochemistry, but no multi-date Landsat/thermal time-series pipeline was found. Earlier static thermal priors do not equal a seasonal test. | **Medium potential, very uncertain; high cost. BLOCKED / not viable here.** Official lead: [USGS Landsat Collection 2](https://www.usgs.gov/landsat-missions/landsat-collection-2). Coverage, access/terms and data availability were not verified; no source download or holdout validation occurred. |
| 4 | **Time-dependent earthquake migration and focal-mechanism corridors (TEMF)** | USGS earthquake-catalog event times, hypocenters, magnitudes and available focal mechanisms; estimate time-varying event-rate gradients, swarm migration and nodal-plane orientation, conditional on the static GeoDAWN seismicity bands. | A concealed fault may host a migrating swarm or temporally clustered microseismicity not captured by a long-term density layer; time-order and orientation can distinguish fault-controlled sequences from isolated events. | The repository uses static competition seismicity-density bands, but no time-indexed catalog ingestion, declustering, or migration model was found. USGS catalog incompleteness and magnitude-of-completeness variation are major risks. | **Low-medium potential, uncertain; medium-high cost. BLOCKED / not viable here.** Official source lead: [USGS Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/search/). API/AOI availability and permitted access were not tested because the official host is not on the sandbox allowlist. |

### Top-candidate gate before any TIFF

ISTF is ranked first only as a scientific priority—not because its score or source coverage is known. The required free/official data lead is NASA/JPL ARIA or ASF DAAC Sentinel-1 displacement/coherence products. **Obtainability check:** this sandbox only permits outbound connections to GitHub/API, PyPI and npm hosts; NASA/ASF are not in that list. The repo also has no pinned InSAR stack. Thus the input cannot be obtained or spatially audited here and the candidate is **not viable or validated in this review**. Do not substitute a synthetic surface, a renamed historical raster, or an unverified third-party mirror.

If an authorized unrestricted run becomes available, first verify complete AOI coverage, time span, processing lineage, license and geocoding; then preregister one lane paragraph and rerun from the shared cache/evaluator/writer. Withhold whole fault segments plus buffer, derive all catalogue features from visible faults only, and test each feature alone with the leakage canary. Compare with the same-fold incumbent and report paired HOLDOUT-DTI with evaluator/version, positive count and 95% CI. Before placement require `|Spearman rho| <= 0.90` against every registry surface; after placement require no more than 70% of candidate dots within 3 px of any registry raster. Stop immediately on any breach. No weekly slot is selected by this workflow.

PDSC/source-depth tomography and tip-relay variants were not ranked as new candidates: the repo contains Euler/source-depth and continuous potential-field tomography (`src/gems91/eulr17.py`, `src/gems91/cgrd17.py`), and tip/relay approaches have prior implementations and submissions. Avoid repackaging them as novel without an explicit, code-audited distinct method.

## Current download / submission gate

- **A new TIFF generated by this review:** **No.** There is no file to download from this review.
- **OK to download:** **No current-review TIFF exists.** Earlier sessions' files in `docs/downloads/` are historical research artifacts, not a newly generated candidate.
- **OK to submit:** **NO.** There is no candidate with current-session validation, a positive comparable holdout, complete-scope uniqueness, and lane/selector authorization.
- **Weekly slot used:** 0 in this review.
- **Submission name / note:** none. Do not copy or rename a previous submission to create an apparent unique candidate.

The competition page's required-file note in the request says a single-band GeoTIFF or a ZIP containing one GeoTIFF, matching CRS, shape, and geotransform; predictions must remain within `[0, 1]`. A valid format is only a technical gate. The shared `scripts/submission_writer.py` and validator should be reused after a candidate is scientifically tested; do not work around the range error by blindly clipping or changing nodata values without revalidation.

## Sources and audit trail

### Repository / research records
- [Pinned comparison inventory](../registry/comparison_inventory.json) — records raster path, byte size, SHA-256 and source URL for an incomplete indexed fleet; does not contain score receipts.
- [R0 verification record](../registry/r0_verification.json) — historical hash and lineage verification for GEMSDOE32 R0; not re-run in this checkout.
- [S19-SVHF run card](run-card-S19-SVHF.json) — historical internal holdout and negative verdict; not a leaderboard receipt.
- [S19 geothermal/fleet synthesis](GEOTHERMAL_VENT_RESEARCH_S19.md) — prior analysis, with score provenance caveats.
- [Current project standing review and prompt](../README.md) — includes original supplied request, limitations and session status.
- [Competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [rules](https://www.drivendata.org/competitions/306/competition-doe-gems/) — supplied official review links; not freshly fetched in this sandbox.

### Score provenance
- The nine-site score values and candidate IDs above are transcribed from the user's message and cross-checked against the GEMSDOE28 source scorecard, which labels them **unverified owner report**. The owner pages were fetched through GitHub API; the static GitHub Pages hosts and DrivenData were not fetched directly.
- No DrivenData submission-page receipt or current authenticated leaderboard capture is included in this review. Therefore **ORGANIZER-CONFIRMED values: none**.
- Internal HOLDOUT-DTI is labeled separately and is not a projection, live score, or organizer confirmation.

## Three-pass verification log

**Pass 1 — implementation:** Created this detailed report, a plain-language Pages subpage, a machine-readable run card, a top-level front-door notice, and a current README status. The nine site maxima are labeled OWNER-REPORTED (UNVERIFIED), and the ranked hypothesis table separates proposal from measured evidence.

**Pass 2 — consistency and edge cases:** Found stale README text presenting S19 as the newest output and the ISO91 landing block as a current new artifact. Updated the README to label S19 historical and the Pages ISO91 block historical research-only. Added the current review notice above the older page content. A source-code search showed Euler/source-depth tomography and tip/relay methods already exist, so those were removed from the “new” candidates; the replacement time-series hypotheses require inaccessible external inputs and are explicitly marked blocked. GitHub API inspection also found conflicting owner/organizer score labels, now logged in `IRREGULARITIES.md`. Checked that priority-page relative links resolve and the embedded JSON exactly matches the standalone run card. `git diff --check` passes.

**Pass 3 — request audit:** Verified the summary covers all nine requested sites; provides at least three candidate hypotheses with layers/signature, missed-fault rationale, overlap caveats, costs and official-source leads; states why a new TIFF was not made; distinguishes OWNER-REPORTED (UNVERIFIED), HOLDOUT-DTI and ORGANIZER-CONFIRMED; includes submission-format/automated validation gates; and ends with a negative JSON run card. No claim of a newly verified official source, score receipt, holdout, registry pass, or TIFF validator is made. Outstanding gates are explicitly blockers rather than assumed to pass.

**Checks run in this checkout:** JSON parse and embedded/standalone card equality: PASS. Priority summary local-link check: PASS. Current home-page link to summary: PASS. `git diff --check`: PASS. Fresh GeoTIFF validation/model tests: NOT RUN (no new TIFF; Python scientific/geospatial dependencies absent; data directory absent).

## Run card

```json
{
  "hypothesis": "No experiment authorized or run: lane unassigned; top-ranked ISTF requires NASA/ASF source data unavailable in this sandbox and preregistration.",
  "mechanism": "Proposed, untested: multi-temporal Sentinel-1 LOS deformation/coherence may identify persistent strain gradients or transient creep across concealed basin-margin faults; no result claimed.",
  "named_non_fault_process_that_could_mimic_it": "Seasonal groundwater withdrawal/recharge deformation and tropospheric atmospheric delay can mimic fault-related InSAR strain; vegetation decorrelation is an additional measurement confounder.",
  "holdout_dti": {
    "label": "HOLDOUT-DTI",
    "evaluator_version": null,
    "value": null,
    "withheld_positives": null,
    "ci95": null,
    "status": "NOT RUN"
  },
  "correlation_overlap_vs_registry": {
    "status": "NOT RUN",
    "preplacement_max_abs_spearman": null,
    "final_dot_max_3px_overlap": null,
    "reason": "No candidate surface or final dots were generated; complete comparison registry is not present locally and its declared indexed scope is incomplete."
  },
  "raster_sha256": null,
  "validator_output": {
    "status": "NOT APPLICABLE — no TIFF generated",
    "no_nan_inside_footprint": null,
    "values_in_0_1": null,
    "crs_shape_transform_match": null
  },
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative"
}
```
