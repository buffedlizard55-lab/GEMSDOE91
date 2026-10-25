# S16-PGRD — preregistered magnetic–gravity residual lane

Recorded before feature construction or candidate placement, 2026-10-25.
Branch: `arena/400a3f1a-gemsdoe91`. **Provisional research lane, not an assigned competition lane:** the user message does not contain its promised single-method paragraph.

## Scope and prior work

Use only bands **B02 `rtp`** and **B13 `iso_grav_anom`** of the hash-pinned 19-band competition feature stack. Reuse the template's `vendor/gems57/evaluate_holdout.py`, `spatial.folds`, and `submission_writer.py`, plus the existing CED deterministic dot placer, canary, and exact registry instruments. Do not use a prior submission as a feature, starting raster, target, or placement mask. Reference submissions are read only by the novelty/forensic checks.

This follows the deferred `H14-4` pseudogravity idea in `HYPOTHESES_S14_HVDC.md`, but does **not** endorse its speculative numeric improvements or its claim of never having been tried across the fleet. A source search of this checkout found no implemented pseudogravity operator. CED compares gradient centroids; MTD/UCD use magnetic depth/continuation; S15 combines conductivity and other signals. None implements the local, band-matched gravity-on-pseudogravity residual below. Fleet-wide methodological novelty remains unverified.

## Ranked hypotheses (qualitative priority, not projected scores)

All four are variants within **one** magnetic–gravity transfer-residual lane. Only rank 1 is authorized in this run; other variants are untested deliverables, not a search space to tune after seeing the holdout.

| Rank | Hypothesis and layers | Physical signature and why it could find omitted faults | Named non-fault mimic | Difference from implemented code | Expected value / implementation cost |
|---|---|---|---|---|---|
| 1 | **PGRD: local pseudogravity regression discordance**; B02 + B13 | Band-limit pole-reduced magnetics, integrate once in wavenumber (`1/|k|`), fit a local gravity/pseudogravity transfer, then seek coherent residual-gradient edges persistent at two scales. A concealed altered contact may retain a density boundary while losing a proportional magnetic response, including beneath cover with no visible scarp. | Unaltered nonmagnetic granite–carbonate contact; remanent volcanic magnetization; flight-line seam | Tests a **failure of proportionality**, not CED's coincident edge-centroid alignment. Deferred conceptual precursor H14-4 is acknowledged. | Highest scientific priority here, uncertain DTI benefit; moderate CPU/memory, no new data |
| 2 | **Transfer-slope sign reversal**; B02 + B13 | Spatially persistent change in fitted signed gravity/pseudogravity coefficient along an otherwise continuous buried contact; potentially distinguishes alteration fronts from uniformly magnetized rock. | Reversed-polarity lava flow boundary | Spatial derivative of a local transfer coefficient, absent from existing lanes | Lower expected robustness because remanence is ambiguous; low incremental cost; **not run** |
| 3 | **Cross-scale transfer breakdown**; B02 + B13 | Compare residuals in disjoint wavelength bands and require a fine residual ridge within a broad gravity boundary. Could resolve shallow alteration over a deeper unmapped boundary. | Two unconnected lithological bodies at different depths | Local spectral transfer discrepancy, not UCD continuation-ratio depth proxy | Medium priority, lower localization certainty; moderate cost; **not run** |
| 4 | **Residual endpoint pairing**; B02 + B13 | Paired along-strike changes in residual-gradient coherence near the ends of a proportionality break could mark a short altered fault conduit rather than an entire rock-unit boundary. | Intrusive apophysis or survey seam ending | Topology of a transfer residual rather than prior-fault tips or S14 posterior auto-context | Lowest priority, more assumptions; higher cost; **not run** |

These are falsifiable exploration hypotheses, not evidence of geothermal vents, fluid temperature, permeability, or economically useful resources. Poisson-style proportionality assumes a common source with uniform density/magnetization and an appropriate pole reduction; heterogeneous geology can invalidate every assumption. A fault predictor is not a vent detector.

## Frozen E1 specification

- Candidate budget: **37,654** unit dots; deterministic row-major tie-breaking; separation strictly greater than **3 px**. This is a fixed comparison budget, not a universal DTI optimum.
- B02 and B13 are independently nearest-filled at invalid/sentinel cells and robustly standardized using the existing `ced.fill_input` helper. No catalogue enters feature construction. Bands are validated by their on-disk `band_name` tags.
- Reflect padding: 64 pixels. Gaussian bandpass: sigma 2 versus sigma 16 pixels. Apply `1/|k|` to B02, zero DC; apply the same bandpass without integration to B13. Units of the transformed fields are standardized proxies, **not physical density**.
- Local regression window sigma 25 px. Ridge floor: 5% of footprint median local pseudogravity variance. Compute residual gravity, residual edge strength at sigma 2 and 5, gravity edge strength at the same scales, residual structure-tensor coherence, and `1 - |local correlation|`.
- Ranking surface = geometric mean residual-edge ranks × geometric mean gravity-edge ranks × residual coherence × `(0.5 + 0.5 × discordance)` × input-support taper. The taper reaches one at 8 pixels from an invalid input or footprint boundary; no hidden-label geometry is used.
- Feature-alone canaries on **each fixed holdout quadrant**, including the final composite and every intermediate used by the surface. Symmetric AUC >0.90, undefined AUC, or nonfinite input blocks scientific evaluation.
- Surface uniqueness is checked before **any** placement. Read every frozen registry entry (including dense references and missing records); report missing files as UNVERIFIED, never PASS. Stop on the first measured duplicate. Full-resolution Spearman, no stride estimate.
- Whole intersecting 8-connected fault segments are hidden in every affected test quadrant. An 80 px training buffer surrounds the quadrant and held component tails. There is no catalogue-derived model feature and no supervised fit. Mask **visible faults only, pixel-exactly**; never delete a halo around hidden truth. Evaluation regions depend on the grid/footprint, not withheld labels.
- Same global-budget emission function in holdout and full inference: rank the full footprint, mask only currently visible faults, place the fixed budget, then score only the fixed held-out quadrant. Do not tell placement where the test quadrant or hidden segments are. No global-catalogue collar or truth-aware clipping is added to the holdout or final algorithm. The CED historical benchmark retains its originally published area-proportional quadrant quotas to reproduce that receipt, and is labelled accordingly.
- Controls: (a) gravity-persistence ranking, same budget and placement; (b) frozen CED91 surface at its historical 32,000-dot budget, recreated with the existing cached-feature builder. Controls are comparisons inside this one preregistered experiment, not additional hypothesis searches. Prior larger historical scores with different splits, halo deletion, or uncertain population are not interchangeable.
- Score with template pooled DTI: alpha 0.2, beta 0.8, triangular radius 300 m. Paired physical 20 km block bootstrap, 1,000 draws, fixed seed 160025; report positives, version, CI, and limitations. Reproducing CED is a benchmark integrity check, not a claim that CED is the repository's universal best.
- Write a fresh all-finite, one-band float32 TIFF and single-TIFF ZIP with the shared writer. Check SHA-256, internal ZIP member bytes, shape/CRS/transform, catalogue zeros, footprint zeros, and range on disk.
- Check final dots against the same frozen registry and stop on the first duplicate. Packaging/reporting of a negative result is allowed; no further model/emission experiment after a stop.

## Promotion and stop policy

**At most one candidate experiment is planned** (hard cap three / two hours); no live upload or weekly-slot selection. Promotion requires all shared readiness gates, a genuinely comparable best with paired positive CI, full registry evidence, an assigned lane, and a separately authenticated selector/weekly-cap receipt. Nothing in this run grants those permissions.

The pre-run registry feasibility audit already proves that a 37,654-dot result cannot satisfy the literal 70% gate against `calib_r13lattice_00904.tif`: 6,649 footprint cells are more than 3 px from that registry. Even placing one dot in every such cell forces at least `(37654-6649)/37654 = 0.8234184947` overlap. Spacing can only tighten that bound. This is **not** permission to erase the reference or place anti-registry noise. E1 is therefore a scientifically measured **negative research deliverable**, not a prospective weekly submission.

## Sources and obtainable data

- Official reference notebook: <https://github.com/drivendataorg/gems-prize-reference-solution>. Fetched at a recorded commit. It verifies a U-Net/Tversky-loss example and alpha/beta weights; it does **not** implement the organizer's distance-weighted scorer.
- Competition metric/format: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>. Official host outside this sandbox's allowlist; not freshly read. DTI arithmetic is the explicit user protocol and existing tested template, not a newly authenticated scorer.
- GeoDAWN source lead: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>. Official host not reachable under the configured allowlist. The local stack is verified against `registry/data_manifest.json`; a mirror hash establishes identity, not official endorsement or redistribution permission.
- Fatiando/Harmonica author's implementation of pole reduction and potential-field filters: <https://github.com/fatiando/harmonica/blob/main/src/harmonica/filters/_filters.py>. Author-maintained scientific software, **not a government source or geological proof**; commit and exact supporting lines stored separately.
- Deferred precursor: [`HYPOTHESES_S14_HVDC.md`](HYPOTHESES_S14_HVDC.md).

No candidate above needs new external data. Free official USGS 3DEP and NASA OPERA are useful future leads, but their retrieval endpoints are not available from this sandbox, so they are **not proposed as currently viable inputs**. Public GitHub fleet snapshots are learning/reference material only and never organizer-confirmed score receipts.
