# Official sources verified in Session 22 (2026-10-26 UTC)

Every statement below was read from the cited page on 2026-10-26 with the Arena `fetch_page` / `web_search` tools. They return **text pages only**; no binary data were downloaded from any of these hosts. Quotations are short and exact; anything else is paraphrase and says so. Machine-readable receipts: `docs/s22/official-sources.json`.

> **How to use this file.** If a claim in the README, a run card or an earlier session's note conflicts with a row here, the row here wins (it carries a URL you can open). Anything *not* in this table is unverified.

## A. Scoring and labels (DrivenData, DOE GEMS Prize Challenge)

| # | What was verified | Exact wording (≤ 25 words) / paraphrase | URL |
|---|---|---|---|
| A1 | Metric definition | "distance-weighted Tversky index"; α = 0.2 on false positives, β = 0.8 on false negatives; triangular kernel, range R = 300 m (3 px). | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> |
| A2 | Component formulas (paraphrase) | `TP_w = Σ_g max_x p(x)k(d)`; `FP_w = Σ_x p(x)[1 − max_g k]` over pixels with p > 0; `FN_w = Σ_g[1 − max_x p(x)k]`; `DTI = TP_w/(TP_w + αFP_w + βFN_w + ε)`. Worked example `3.00/(3.00 + 0.2·1.89 + 0.8·2.00) = 0.60`. | same page |
| A3 | Submission format | Same CRS (EPSG:32611) and 100 m resolution as the training data, same bounds, "data outside the bounds is null or nan", single `float32` layer with values in [0, 1]. | same page |
| A4 | **Known faults are masked** | "Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation, so they do not count towards penalty terms." Re-evaluation masks them too. | [forum 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) (DrivenData staff `chrisk-dd`, 2026-09-16) |
| A5 | **Definition of a "new fault"** | "any fault pixel not already captured by USGS/INGENIOUS" and "can include newly mapped geometry of an existing fault system". | [forum 11536](https://community.drivendata.org/t/where-do-you-draw-the-line/11536) (2026-09-23) |
| A6 | **Aggregation** | Public score "computed by pooling over all pixels in the public subset and computing a single Tversky index"; chunking not disclosed; private score computed the same way; final re-evaluation on the entire GeoDAWN area. | [forum 11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550) (2026-10-01) |
| A7 | Test-fault provenance is secret | Organizers are "not sharing details about the data sources, fault types, or coverage behind the test faults". Phase 2 test set is "updated by expert review of all Phase 1 submissions". | [forum 11527](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527) (2026-09-23) |
| A8 | Which submissions are scored | Reviewers "may look at all submissions at their discretion. Only the selected final submissions are [used] for scoring." | [forum 11579](https://community.drivendata.org/t/phase-2-expert-review-and-phase-1-submissions/11579) (2026-10-26) |
| A9 | Submission limit | Rules say three per week; "The competition website limit prevails, despite the parenthetical." | [forum 11553](https://community.drivendata.org/t/submission-amount-question/11553) (2026-10-05) |
| A10 | Meaning of the earthquake bands | `deq_n100a15` / `ieq_n100a15` "are the INGENIOUS earthquake rate density layers that have been clipped to the GeoDAWN area and re-gridded to 100m". | [forum 11557](https://community.drivendata.org/t/units-and-very-large-values-in-deq-n100a15-and-meaning-of-ieq-n100a15/11557) (2026-10-07) |
| A11 | Public leaderboard snapshot | #1 **0.4437**, #2 0.3916, #3 0.3904, #5 0.3553, #10 0.3379, #24 0.3169, #50 0.2826. (The prompt's 0.4413 and 0.3195 are earlier snapshots.) | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> |

## B. Official Rules (U.S. DOE / NLR, September 2026)

URL: <https://docs.nlr.gov/docs/fy26osti/96647.pdf> (sections cited in brackets).

| # | Requirement | Notes for this project |
|---|---|---|
| B1 [§3.2] | "single GeoTIFF with a single raster layer at 100-meter resolution" for "the entirety of the GeoDAWN study area"; at most three submissions per week (website limit prevails, A9). | Our files are single-band float32, 3730 × 3292, EPSG:32611, validated by code. |
| B2 [§3.2] | Use of generative AI is allowed but "you must indicate in the narrative … the extent … and how you used it". | **This repository is written largely by AI agents.** Any final narrative must say so (see `AI_USE.md`). |
| B3 [§3.4, §3.5, §3.6.2] | One final submission across both rounds, chosen "without knowledge of your scores on the private test set … to discourage overfitting to the public test set". | Public-leaderboard probing is permitted but its gains may not transfer; every projection here is labelled as such. |
| B4 [§3.5] | Finalists must deliver "complete code assets and documentation" able to "sufficiently reproduce the winning results and generate predictions on new data samples". | A hand-placed or leaderboard-reverse-engineered raster cannot satisfy this; the pipeline in `scripts/` and `src/gems91/` is the reproducibility evidence. |
| B5 [§1.3, A.3] | Eligibility, team and single-entity rules apply. | ~150 live scores in ~4 weeks (≈ 5 per day) are hard to reconcile with three submissions per week for **one** entity. **Flag for the account holder to confirm compliance**; nothing here asserts a violation. |

## C. Data and geology sources used or checked

| # | Source | What it is | URL | Reachable from the sandbox? |
|---|---|---|---|---|
| C1 | DrivenData reference solution | U-Net (Monte-Carlo CV) on the provided stack, Tversky loss; GPU or CPU | <https://github.com/drivendataorg/gems-prize-reference-solution> | yes (GitHub) |
| C2 | INGENIOUS dataset (GDR #1391) | training labels, earthquake rate-density layers | <https://gdr.openei.org/submissions/1391> | **no** (`curl` HTTP 000) |
| C3 | GeoDAWN airborne magnetics/radiometrics (USGS) | `https://doi.org/10.5066/P93LGLVQ`; ScienceBase item `657e1d85d34e23d3533209f7` | <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> | **no** |
| C4 | USGS 3DEP 1 m DEM (The National Map) | free, public domain; 1 m products staged as 10,000 × 10,000 m tiles | <https://apps.nationalmap.gov/downloader/> | **no** |
| C5 | USGS 3DEP point clouds on AWS Open Data | EPT, `s3://usgs-lidar-public`, no account needed | <https://registry.opendata.aws/usgs-lidar/> | **no** |
| C6 | Faulds & Varga (1998) | accommodation and transfer zones, GSA Special Paper 323, pp. 1–45 | <https://doi.org/10.1130/SPE323> | page only |
| C7 | Faulds & Hinz (2015) | 426 Great Basin geothermal systems, ~39% blind, step-overs ~32%, terminations ~25%, eight favourable settings (World Geothermal Congress 2015) | <https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11100.pdf> | page only |
| C8 | Dixie Valley high-resolution aeromagnetic survey (USGS) | 200 m line spacing; buried intra-basin faults identified from narrow horizontal-gradient ridges | <https://www.usgs.gov/publications/preliminary-results-a-high-resolution-aeromagnetic-survey-identify-buried-faults-dixie> | page only |

**Direct reachability test (this session, `curl --max-time 10`)**: `apps.nationalmap.gov`, `prd-tnm.s3.amazonaws.com`, `usgs-lidar-public.s3.amazonaws.com`, `earthquake.usgs.gov`, `sciencebase.gov`, `gdr.openei.org`, `drivendata.org`, `community.drivendata.org` all returned HTTP 000. The sandbox allow-list is GitHub, PyPI and npm only.

## D. What these facts changed

1. A4 + A5 explain the **collar effect**: pixels on the catalogue are excluded, and a new fault is by definition *not* a catalogue pixel, so a dot 1–2 px beside a mapped trace is almost always an unmatched false positive. See `docs/s22/r0-decomposition.json`.
2. A6 + B3 mean the public board measures only a hidden subset; a gain found by fitting the public score need not transfer to the private set or to the Phase 2 area.
3. A10 kills the seismicity-residual hypothesis before any compute (the layers are smoothed rate densities).
4. A7 + A8 + B4 mean the Phase 2 score depends on expert review of geologically credible predictions; a raster that only games the metric earns no Phase 2 credit.
5. A11 shows the user-reported best (0.2778) sits just below rank 50 and that the leaders (0.33 – 0.44) are well beyond what the sandbox-accessible 100 m stack has reached.
