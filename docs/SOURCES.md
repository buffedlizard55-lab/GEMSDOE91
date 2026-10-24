# Source audit — GEMSDOE91

Checked on **2026-10-24 UTC**. This register distinguishes facts verified from an official source from claims copied from project sites. A link being listed is not proof that a statement on another site is correct.

## Official competition sources

| Source | What was checked | Result and limits |
|---|---|---|
| [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Fetched directly on 2026-10-24 | The task is to predict geological faults indicative of geothermal resources, including faults absent from the public catalogue. The page defines the distance-weighted Tversky index: for each truth pixel, TP credit uses the maximum predicted probability times triangular-kernel weight within radius; false-positive mass is weighted by one minus the maximum kernel weight to truth; false negatives are the truth pixels' remaining uncovered mass. The DTI is TP divided by TP + alpha·FP + beta·FN + epsilon; alpha=0.2, beta=0.8, with a linear 300 m triangular kernel. Submission requirements: one float32 layer; predictions in [0,1]; EPSG:32611; 100 m resolution; same bounds; outside-bounds cells null/NaN. It lists the provided feature families and says training labels are available in vector and raster formats. |
| [DrivenData About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/) | Fetched directly on 2026-10-24 | Describes GeoDAWN magnetic/radiometric data, coordinated airborne lidar, the nature of faults, and why faults can be geothermal-fluid pathways. This supports geological motivation only; it does not establish that any candidate raster will score well. |
| [Official GEMS Prize Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Fetched directly on 2026-10-24; document title: *Geologic Enhanced Mapping System (GEMS) Prize Official Rules*, September 2026 | Sections 3.2–3.5 state the submission cap (up to three per week, subject to the competition website), that one final submission is selected across both prize phases, and that submissions are automatically scored against newly created fault labels. Section 3.2 also requires a narrative disclosure describing generative-AI use where applicable and states that entrants remain responsible for accuracy and authorship representations. The rules require finalists to provide reproducible code assets and documentation and set final content due by 5 p.m. ET on the submission-deadline date. The rules direct entrants to the website for current dates and platform limits; the exact current deadline was not verified in this review. |
| [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Fetched directly on 2026-10-24 | The page displayed **0.4413** at rank 1 at the time of this check. Label: PUBLIC-LEADERBOARD OBSERVATION only; neither HOLDOUT-DTI nor ORGANIZER-CONFIRMED for GEMSDOE91, and not private-test performance. Recheck the live page before any decision. |
| [DrivenData data/download page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Fetched directly on 2026-10-24 | Redirected to the DrivenData login page. No credentials were supplied or used. The page is therefore not accessible from this checkout. The problem description and rules say the training features and labels are supplied to registered competitors; the exact files are not present in this checkout. |
| [DrivenData reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution) | Fetched directly on 2026-10-24 | The repository page lists a reference notebook and environment files. The checkout does not contain `evaluate_holdout.py` or `submission_writer.py`; this repository page does not list those files either. This is not evidence that no separate shared template exists elsewhere; no path to one was supplied. |

## Official geological and geospatial sources

| Source | What was checked | Result and limits |
|---|---|---|
| [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Official link and metadata result checked; direct page fetch timed out in this session. The DrivenData problem/About pages independently describe the GeoDAWN inputs. | Used only as provenance for GeoDAWN magnetic/radiometric survey data. This audit does not certify a local GeoDAWN raster, band order, licence for a mirrored file, or feature value. |
| [USGS publication: Stress concentrations at structural discontinuities in active fault zones](https://pubs.usgs.gov/publication/70196066) | Fetched directly on 2026-10-24 | The abstract discusses fault terminations, step-overs, intersections, bends, and other interactions as structural discontinuities associated with fluid flow, including in geothermal systems. It motivates a testable hypothesis; it is not evidence that a proposed predictor works in the competition region. |
| [USGS publication: Blind geothermal system in Southern Gabbs Valley](https://pubs.usgs.gov/publication/70201803) | Fetched directly on 2026-10-24 | The abstract reports a blind geothermal system associated with fault intersections and a displacement-transfer zone, with gravity, magnetic, and magnetotelluric evidence. It motivates multi-scale, multi-physics hypotheses; it does not validate any candidate. |
| [EPSG registry entry 32611](https://epsg.io/32611) | Fetched directly on 2026-10-24 | Identifies EPSG:32611 as WGS 84 / UTM zone 11N, in metres. The organizer page remains authoritative for the competition's required projection. |
| [INGENIOUS project page](https://gbcge.org/current-projects/ingenious/) | Link recorded; not independently fetched in this audit | Included as a project source lead only. No claim about its current contents or licensing is made here. |

## GEMSDOE32 comparison source

| Source | What was checked | Result and limits |
|---|---|---|
| [Current GEMSDOE32 project page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | Fetched directly on 2026-10-24 | It presents a downloadable candidate and explicitly states that **no organizer score exists for artifacts in that repository**. The current page's displayed owner-best and public-leaderboard snapshot do not substantiate the user-supplied `0.2778` for `h33-h33-2-b2`. Treat that number as an unverified site/user claim unless an organizer receipt is produced. |
| [Pinned GEMSDOE32 source snapshot](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/078f3cea1bc75d15beb81b095ab488a912327a5d/docs/index.html) | Fetched directly on 2026-10-24 | The same page snapshot includes the explicit no-organizer-score disclaimer and describes its holdout/model results as proxies or models. Those local results are not organizer scores. |

## Local metric implementation audit

The official problem description specifies per-truth-pixel maximum prediction-weighted kernel credit. `scripts/dti.py` uses a maximum operation for its true-positive term; `src/gems91/metric.py` sums every nearby prediction contribution. These local implementations therefore disagree. Neither is the required shared `evaluate_holdout.py`; no output from either is accepted as HOLDOUT-DTI in this review. The discrepancy is documented in `IRREGULARITIES.md` and `docs/REVIEW-20261024.md`; it was not patched in a private substitute.

## Evidence rules used in this repository

- **HOLDOUT-DTI** is reserved for a run of the specified evaluator and must name its version, withheld-positive count, and 95% confidence interval.
- **ORGANIZER-CONFIRMED** is reserved for an exact result copied from an organizer submission-page receipt. A public leaderboard observation is recorded separately and must not be presented as a GEMSDOE91 receipt.
- Legacy `CLAIM`, `MODEL`, and `PROXY` entries in historical files are not converted into either evidence class. They are not evidence that a new candidate beats a compliant holdout baseline.
- Current source links are provided for manual review. No automated competition login, upload, or credential handling is performed.
