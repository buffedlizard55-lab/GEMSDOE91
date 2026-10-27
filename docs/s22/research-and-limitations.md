> **2026-10-27 correction — historical text below is superseded where it interprets S22 as a valid geological test.** The original implementation accepted 3,061 finite NoData cells inside the footprint in each of its two input bands. The historical HOLDOUT-DTI and canary arithmetic is retained for provenance only; it cannot validate or reject the intended mechanism. No corrected S22 experiment has been run. The literal 98.565889% duplicate stop remains in force. See the [current review](../review-8e8d86f2/REVIEW.md), [feature audit](../review-8e8d86f2/feature-audit.json), and [source-correction manifest](../review-8e8d86f2/source-correction.json).

# S22 scientific review, source ledger and limitations

Reviewed 2026-10-26. Statements below distinguish observed source text, measured local results, and hypotheses. This is not a claim of exhaustive literature coverage or organizer acceptance.

## What the competition actually measures

**Verified official source:** [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), both text chunks retrieved during S22. The target is geological faults indicative of geothermal resources, **not geothermal vents or confirmed productive reservoirs**. Experts supplied new faults outside the existing catalogue. The initial public/private split and subsequent expert-expanded final label set create distribution shift. A model recovering known mapped faults need not generalize to hidden, subtler new faults.

The source specifies `k(d)=max(1-d/300m,0)`, `TP=sum_truth max_prediction p*k`, `FP=sum_prediction p*(1-max_truth k)`, `FN=N_truth-TP`, and `DTI=TP/(TP+0.2 FP+0.8 FN+epsilon)`. Local arithmetic remains the shared template; its independent brute-force regression tests are in `tests/test_dti_official_formula.py` and `tests/test_metric.py`. The official reference U-Net notebook also uses alpha .2 / beta .8 for its training loss, but that loss is not the hidden competition scoring server. The freshly fetched official repository README and extracted notebook cells are under `evidence/s22/`, pinned by `official-reference-commit.txt`.

## Why the reported GEMSDOE32 result could be strong

The user reports **0.2778**, but no authenticated submission-page receipt tying it to a file SHA256 is available. Therefore this remains an **unverified historical claim**, not ORGANIZER-CONFIRMED and not HOLDOUT-DTI. The nine-site table ranks those claims only.

S22 re-downloaded the exact prompt-named leader rasters through immutable Git blobs and checked hashes. GEMSDOE32's raster contains 37,654 positive cells. Its sparse support is heavily shared with the other eight historical leaders; `nine-site-audit.json` provides every directed overlap and exact-support identity. GEMSDOE25 and GEMSDOE30 have equal support despite different file hashes. GEMSDOE36's named Anderson artifact must not be substituted with a differently named 40,199-dot ancestor (an error in the inherited S21 nine-site summary).

**Plausible mechanism, not established causation:** spaced dots can preserve distance-weighted coverage while removing redundant predictions; a known-fault collar can remove predictions that add little new-fault coverage. Whether any particular deleted dot helps depends on the hidden labels. Dot count alone cannot explain a leaderboard value, and the bytes do not prove that a named physics model produced those pixels.

For binary dots, let `T=TP`, `M=sum_dot max_truth k`, `N=number of dots`, and `G=number of truth pixels`. Then:

`DTI = T / [0.2*(T + N - M) + 0.8*G + epsilon]`.

**T is not generally M.** One reported score and a dot count cannot identify private truth prevalence, the exact extra true positives needed to beat a target, or a percentage attribution of score improvement to spacing versus pruning. Earlier repository statements asserting such quantities should be treated as model-dependent hypotheses, not verified facts. No hidden-label inversion was used in S22.

Can the reported GEMSDOE32 result be exceeded? It is possible in principle, but **S22 provides no evidence that this candidate does so**. OMTJ's HOLDOUT-DTI is reported with evaluator, positives and interval in `run-card.json`; it is not a leaderboard estimate. No calibrated estimate is published for any of the nine historical files or this new file. A model-based projection requires receipt-linked examples, independent validation, and uncertainty accounting for adaptive selection; these are absent.

## Geological reasoning and falsification

**Verified official context:** [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ), retrieved during S22. USGS distinguishes radiometrics (surface geology/soil) from magnetics (subsurface structure/geology). Area 2 flight lines are 400 m apart, with variable terrain clearance and separate acquisition blocks. Thus a 100 m raster does not imply independent 100 m geophysical resolving power. Flight-line leveling residuals and acquisition boundaries are concrete survey-related mimics of a texture boundary, in addition to unfaulted volcanic flows and intrusive contacts. USGS marks this release CC0.

**New testable hypothesis, not a literature-established detector:** fault displacement may juxtapose magnetic texture with different local signed third moments even when the first-moment edge is weak. OMTJ uses B14 TMI local skewness boundaries aligned with B13 gravity gradients. This differs from the already implemented second-moment semivariogram/sill and waveform/phase features. The prior-weight ranking was qualitative; no invented expected DTI gains were assigned. Four proposals and the fixed one-experiment plan appear in `preregistration.md`.

The tested result is negative. Its relatively low canary AUC is not proof of physical specificity; its poor hide-and-recover performance is evidence against using this simple operator alone. Do not tune its placement to evade the lattice or reinterpret the dense-reference failure as a pass. No further experiments ran after the literal overlap breach.

**Verified geothermal context:** [USGS Geothermal Resource Investigations Project](https://www.usgs.gov/centers/gmeg/science/geothermal-resource-investigations-project), overview retrieved during S22, describes groundwater circulation through hot rock and the importance of locating or engineering deep permeability. A magnetic contact does not establish heat, active permeability, fluid supply, or a vent. Future fault localization and geothermal favorability should be separate outputs rather than calling every predicted pixel a geothermal discovery.

## Official data / knowledge ledger

| Source and URL | What was actually verified in S22 | Availability, license, and possible use |
|---|---|---|
| [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Redirected to login via page retrieval | No authenticated official download or receipt session. Input bytes restored automatically from existing SHA-pinned team mirrors; provenance authentication remains separate. |
| [INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391), DOI 10.15121/1881483 | Public release page retrieved: geophysical maps, geodetics, seismicity, wells/springs, paleogeothermal features, faults, volcanics, 2 m temperature probes | Page explicitly CC BY 4.0, **not CC0**. Download links exposed; bulk files not fetched in S22. Fault datasets may duplicate catalogue truth and must be quarantined from holdout features. |
| [GDR paleogeothermal features](https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip) | Official release lists sinter/tufa and associated spring deposits | Potential independent fluid-history corroboration; not presently validated as a viable input. Deposits may be old/nonthermal, spatially biased, and aligned with mapped faults. |
| [GDR 2 m temperature probes](https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip) | Official release describes shallow temperature measurements | Potential thermal corroboration; sparse sampling and climate/soil effects require analysis. No fabricated coverage or expected gain. |
| [USGS GeoDAWN](https://doi.org/10.5066/P93LGLVQ) | Official page details acquisition, corrections, lidar coordination and CC0 | Native flight-height/line metadata could distinguish survey artifacts from geological texture. Only cached competition TMI/gravity used here. |
| [USGS geophysical maps](https://doi.org/10.5066/P9Z6SA1Z) | GDR 1391 links the official gravity/magnetics release | Metadata route verified, source files not acquired anew. No claim of new independent information beyond existing stack. |
| [Official reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution) | Current commit, README and notebook actually fetched using GitHub API | CPU path is supported. A GPU is not an absolute prerequisite for every approach; S22 ran on CPU. |
| [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | All seven extracted text chunks read | See rules notes below; this is source review, not legal/eligibility certification. |

The shell can access only allowlisted GitHub/PyPI/npm hosts. The page-reading tool can retrieve official text independently; **text retrieval does not mean the shell can download bulk rasters**. We did not claim an external-data hypothesis viable merely because its landing page exists.

## Rules and submission-format irregularities

- The problem page specifies a single float32 layer, EPSG:32611, 100 m resolution, matching bounds, [0,1] confidence; it says data outside bounds is null/NaN. The user's portal previously rejected out-of-range values. The existing shared writer emits all-finite zeros outside the sample footprint with `nodata=None`. This fixes numeric range defects locally but **does not prove organizer acceptance or resolve the page's null/NaN wording**. The new file has no negative sentinel, no NaN/Inf anywhere, and exact grid equality. Do not call that an authenticated official-format certification.
- Official Rules sections 3.2/3.4 specify three submissions per week, subject to website limits. **Current team quota remaining was not accessible**; zero slots used here.
- Sections 3.4–3.6 require one final selected submission across both rounds. A good public leaderboard result is not a guarantee of private/final placement.
- Section 3.2 permits generative AI with a narrative disclosure. `AI_USE.md` is updated for this work. Finalists need reproducible code and resource documentation. Registration, eligibility attestations, licenses and final selection cannot be inferred from a passing TIFF validator.
- Appendix A.1 contains generic Word/PDF narrative language while the submission-specific sections require a GeoTIFF; the prediction upload should follow the explicit GeoTIFF instructions. Do not replace the raster with this report.
- The official public leaderboard retrieved in S22 shows rank 1 `xiaofanhu` at **0.4437**. This is a dated **PUBLIC-LEADERBOARD OBSERVATION**, not an ORGANIZER-CONFIRMED submission-page receipt for our file. The prompt's 0.4413 and 0.3195 are not current top values in that observation. It must not be used to claim a calibrated target probability.

## Concrete next steps, in order

1. **Resolve registry feasibility before spending compute:** preserve the literal protocol until its coordinator supplies a versioned policy for calibration grids. Missing two frozen references and unindexed private submissions prevent universal clearance. No silent density exemptions.
2. Restore an incumbent's **fold-specific** predictions and fixed emission budgets, then rerun it alongside the next preregistered method on the same splits and paired spatial bootstrap. Historical best scalars are not a matched control. Holdout recovery must not mask hidden fault locations using the full catalogue.
3. Record authenticated submission receipts linked to exact raster SHA256s when available through an authorized channel. Keep organizer-confirmed outcomes distinct from community claims and public-leaderboard observations. Do not ask for passwords or paste tokens into this repo.
4. For a new independent scientific lane, verify and hash official high-resolution terrain or native survey QC data on an allowed ingest host; check extent, licensing, acquisition seams and catalogue independence. No promised score gain.
5. Maintain one renderer-owned current pointer and explicit archives. The scheduled feed refresh is a source inventory, not autonomous scoring/training or guaranteed fresh Pages content under legacy deployment.
