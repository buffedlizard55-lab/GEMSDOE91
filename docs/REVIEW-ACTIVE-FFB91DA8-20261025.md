# Active-checkout review — GEMSDOE91 (`arena/ffb91da8-gemsdoe91`)

**As of 2026-10-25 UTC.** This file records only checks made against this checkout; inherited branch records are cited as historical evidence, not represented as freshly rerun.

## Executive decision

**VERDICT: NEGATIVE / NO PROMOTION. No new TIFF was generated, no weekly submission slot was used, and no score was produced.** This is a deliberate protocol stop, not a claim that no viable geology exists. The parallel-run instruction says to use one assigned method paragraph, but the canonical `docs/run-card.json` says `lane.assigned: false`. The required competition rasters and feature cache are absent locally. Choosing a method from older parallel runs or changing an old raster would violate the stated lane and reuse rules and would not be a fresh validation.

**Download/submission status:** no artifact was created by this review. Prior download links elsewhere in the repository remain historical research artifacts. Do not submit one on the strength of this review. `OK TO SUBMIT: NO` for this review; there is no `OK TO DOWNLOAD` file newly produced.

## Pass 1 — inspect and establish ground truth

1. Confirmed the active branch is `arena/ffb91da8-gemsdoe91`; the worktree was initially clean.
2. Read the README and its preserved full project prompt, the canonical run card, prior active/repository reviews, data manifest and data-handling policy, shared holdout/writer sources, current portal pointer, candidate/hypothesis docs, and repository tests.
3. Executed `.venv/bin/python scripts/preflight.py`. It returned exit 1, `BUILD BLOCKED`, `0/2` minimum files verified, no ready axes. Specifically absent are `data/official/sample_submission.tif`, `data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif`, `existing_faults.tif`, and the numerical feature stack. The command refreshed `registry/preflight.json`; the JSON now records the observed absence rather than an older partial-state receipt.
4. The lane card remains unassigned. This is an independent blocker even if files are later restored.
5. Historical scores in the user prompt (including 0.2778, 0.3195, and 0.4413) were not authenticated by a submission receipt or freshly checked against the live organizer page in this pass. Treat them as **USER-REPORTED / UNVERIFIED**, not `ORGANIZER-CONFIRMED`. There is no organizer-confirmed score in this review.

## What the 0.2778 report can and cannot tell us

The user's GEMSDOE32 figure is unverified here, so its cause cannot be established from the score string or filename. A plausible metric mechanism is sparse-emission economics: under the repository's implemented distance-weighted Tversky formula, extra prediction mass that contributes little marginal truth coverage can worsen the denominator; removing redundant or catalogue-adjacent predictions can improve a score if useful coverage is retained. The 300 m triangular kernel also makes nearby predictions redundant in a saturating way. This is a hypothesis about the metric, **not a causal finding** about that artifact. A matched ablation on identical truth, evaluator, split, probability budget, and georeferencing is needed to attribute any gain.

The project's hide-and-recover target is withheld mapped catalogue faults. It is a proxy for catalogue-fault recovery, not direct evidence of blind-fault discovery or geothermal-vent detection. Beating the user-reported figure is possible in principle; this checkout has no fresh evidence that it can do so. Do not compare historical scores from different evaluator versions as if they shared one scale.

## Ranked candidate hypotheses — proposals only, not validated

The ordering is qualitative expected value versus implementation cost, conditional on data access. It is not a score projection. “Not found” means a targeted search of repository code/docs did not identify the exact method; it does not prove novelty across all external GEMSDOE projects. The broader repository has many related ridge, edge, scarp, relay, and thermal methods, so each must be checked against the complete registry and source tree before implementation.

| Rank | Candidate | Specific layers and physical signature | Why it may target a missed fault | Difference / overlap check | Named non-fault mimic | Expected benefit / cost / data gate |
|---|---|---|---|---|---|---|
| 1 | **Detrended-relief texture break (Hurst / spectral-slope contrast)** | Competition `det_elev` numerical band (B12), optionally the competition's 1 m DEM tiles; estimate local two-dimensional spectral slope / roughness on opposite sides of candidate lineaments, after removing broad relief. | Fracturing and differential erosion may alter surface texture across subtle, alluvium-obscured faults even where elevation gradient or a resolved scarp is weak. | The S18 repository review reports no Hurst/fractal spectral-slope implementation; current RELIEF/SNAP axes use relief classes/gradients. This is a potentially distinct transform, not a confirmed fleet-wide novelty claim. | Lithologic boundary between resistant and weak units; alluvial-fan or playa margin. | **Medium potential / low-to-medium cost.** The 100 m feature route needs the absent official feature stack. The finer route requires the login-gated competition `1m_DEM_links.csv`; this review did not verify access or obtain tiles. Do not treat it as ready. |
| 2 | **Unit-conditioned magnetic–gravity edge displacement** | GeoDAWN RTP/magnetic and isostatic-gravity layers (B02/B13 and their gradients) plus official geologic-unit polygons; signed edge displacement conditioned within units rather than global edge fusion. | A concealed fault may offset potential-field contacts within one mapped unit; conditioning could suppress ordinary unit boundaries that generate coincident edges. | The repo has global magnetic–gravity displacement (CED-family work), so the only potentially distinct part is within-unit conditioning plus unit/contact controls. Novelty is uncertain and must be confirmed in `src/`, hypotheses, and fleet registry. | Pluton margin or stratigraphic contact. | **Medium potential / medium-high cost.** Requires the official USGS State Geologic Map Compilation (SGMC). Official source lead: [USGS ScienceBase SGMC item](https://www.sciencebase.gov/catalog/item/6312f0f2d34e36012efa234a) and [ScienceBase DOI 10.5066/P1A3DQZK](https://doi.org/10.5066/P1A3DQZK). Retrieval, license, and footprint fit were **not checked** in this sandbox; not currently viable. |
| 3 | **Lineament-conditioned Landsat surface-temperature residual** | USGS Landsat Collection 2 Level-2 surface temperature; detrend by acquisition/time/topography, then test repeatable linear residuals aligned with structural corridors. | Shallow advective geothermal flow along an unmapped permeable fault could produce a thermal residual not visible in the fault catalogue. | Surface-temperature anomalies are distinct from GeoDAWN conductivity and well/chemistry proxies, but can be mistaken for those signals; no Landsat implementation was found in the inspected repo review. | Irrigation, evapotranspiration, albedo/aspect, or saline playa. | **Medium but highly uncertain / high cost.** Official source: [USGS Landsat Collection 2 Surface Temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature) and [Level-2 products](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products). This host/data access was not tested here; no data were downloaded, so not viable yet. |
| 4 | **Flightline-direction nuisance model with cross-sensor confirmation** | GeoDAWN RTP/TMI and radiometric channels plus official survey flight-line metadata; measure directional spectral peaks and whether candidate edges persist across independent channels and away from acquisition-line periodicity. | Its direct purpose is to reject survey seams that otherwise masquerade as blind faults, improving precision of structure evidence rather than adding a standalone fault predictor. | Existing repo work includes seam controls and multisensor fusion. The proposed distinction is an explicit, fold-safe flight-direction nuisance estimate; this is not asserted absent fleet-wide. | Levelling seam, flightline striping, or processing boundary. | **Low-to-medium potential / medium cost.** The GeoDAWN source is [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and); survey metadata and cached arrays are absent here. No additional external source is proposed, but data availability is not established. |

**Top candidate:** detrended-relief texture break, because it has an explicit repo-level novelty lead and may use an official competition band without sourcing a new dataset. It was **not validated**: no assigned lane, no sample grid/catalogue/feature cache, and no buildable holdout population. The requirement to validate a candidate against the current comparable holdout best before any slot is therefore unsatisfied; no slot may be considered.

## Pass 2 — review risks and assumptions

- **Lane ambiguity:** the user says “single method paragraph below,” but there is no unique authorized lane declaration; the canonical run card explicitly says unassigned. Do not infer assignment from the many prior method write-ups.
- **Input/provenance mismatch:** the checked-in `registry/preflight.json` had previously claimed only the parent raster was missing. A fresh preflight found both the template and parent absent, as well as all axis inputs. It has been refreshed to this environment's observed state. The data manifest's provenance/pin records are not evidence that files are currently local or that organizer terms authorize transfer.
- **No new validation:** with no local template/catalogue/features, there is no valid holdout reconstruction, per-feature canary, pre-placement surface correlation, final-dot overlap, or TIFF validator result. Existing receipts are not fresh results.
- **Novelty risk:** all four proposals may overlap external parallel projects, and two overlap existing local methods in part. “Untried” is a repository-scoped hypothesis based on a targeted search, not a claim across every linked site.
- **Metric interpretation:** the repo's `scripts/dti.py` documents its own derived implementation and explicitly says it has not been validated against the official scorer in this environment. Any internal DTI result must carry the evaluator version and is not an organizer score.
- **External-source obtainability:** public URLs are given for manual audit, but this environment did not fetch the USGS pages or datasets. No claim of current availability, licensing, or data footprint coverage is made.
- **Repository UX / current-feed irregularity:** the README preserves the user's full standing prompt, but it has accumulated historical branch summaries. The static portal previously opened with a banner linking to another branch's review and an OLC91 research download. I updated the banner and README pointer to this branch's review/run card and explicitly labelled page downloads historical research. The OLC91 page content and download remain historical and are not revalidated by this pass; the page's “current candidate” label should be reconciled in a future portal-data refresh.
- **Test/tooling:** pinned requirements were installed into ignored `.venv/` from PyPI; no repository dependency file was changed. Tests exercise software behavior, not missing-data science or organizer acceptance.

## Pass 3 — final verification and disposition

- Final serial `.venv/bin/python -m pytest -ra`: **PASS** (545 passed, 8 skipped, 58 warnings; skips require absent pinned inputs, warnings are Rasterio `Affine` pending-deprecation warnings). A first run concurrent with other verification returned three portal-test failures; the three targeted tests passed immediately afterward and a full serial rerun passed. Treat that initial nondeterminism as an unresolved test-harness irregularity, not as proof of a production bug or proof of its absence.
- `node tools/browser/smoke.cjs`: **PASS** after installing the locked browser dependencies and serving `docs/` locally; the smoke check reports no console/HTTP errors, no mobile overflow, and no axe violations on its 25-page sample. These are UI/download-delivery checks, not scientific or organizer validation.
- `.venv/bin/python scripts/verify_evidence.py`: **PASS** for its stated consistency-audit scope; it reports zero experiments rerun and `submission_ready: false`.
- `.venv/bin/python scripts/check_artifact_policy.py`: **PASS**, 87 registered prediction artifacts, no raw raster/archive tracked.
- Fresh `scripts/preflight.py`: **BUILD BLOCKED**, exit 1; no axis ready.
- No holdout, canary, registry comparison, candidate surface, writer, TIFF, or slot was run/created. No experimental time budget was consumed.
- The fresh review JSON card is `run-card-FFB91DA8-20261025.json`.

### Run card

```json
{
  "hypothesis": "Detrended-relief texture / local spectral-slope break across subtle structural lineaments; proposed, not tested.",
  "mechanism": "Contrast local roughness/spectral slope on opposing sides of candidate lineaments using official det_elev (B12); optional 1 m DEM route is blocked pending verified data access.",
  "named_non_fault_process_that_could_mimic_it": "Lithologic contact, alluvial-fan margin, or playa margin.",
  "holdout_dti": {
    "label": "HOLDOUT-DTI",
    "evaluator_version": null,
    "withheld_positives": null,
    "95_percent_CI": null,
    "status": "NOT RUN — unassigned lane and required rasters/cache absent"
  },
  "correlation_overlap_vs_registry": {
    "surface_rank_correlation": null,
    "final_dots_within_3px": null,
    "status": "NOT RUN — no candidate surface or dots"
  },
  "raster_sha256": null,
  "validator_output": {
    "no_NaN_inside_footprint": null,
    "values_in_0_1": null,
    "CRS_shape_transform_match": null,
    "status": "NOT APPLICABLE — no new raster"
  },
  "submission_name": null,
  "submission_note_max_140_characters": null,
  "verdict": "negative",
  "experiments_used": 0,
  "weekly_submission_slots_used": 0,
  "organizer_confirmed_score": null
}
```

## Official/manual-review links

- [DrivenData GEMS competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data tab (login gated)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN survey data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS SGMC ScienceBase item](https://www.sciencebase.gov/catalog/item/6312f0f2d34e36012efa234a)
- [USGS Landsat Collection 2 surface temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)
- [EPSG:32611](https://epsg.io/32611)

These links are pointers for independent review, not claims that this session fetched or verified each live page. **Next useful action:** resolve authorized lane assignment and permitted data placement; rerun preflight; then preregister and validate only the assigned candidate with the shared evaluator and writer. Do not alter the internal uniqueness thresholds or spend a weekly slot to satisfy an internal gate.
