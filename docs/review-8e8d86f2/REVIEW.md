# Current review — 27 October 2026

## Executive verdict

**NO NEW TIFF / NOT OK TO SUBMIT.** No geological experiment or competition
upload was run in this review. The supplied protocol lacks the promised single
method paragraph, and the frozen 37,654-dot plan is impossible under its literal
registry rule: **at least 82.341849%** of any such dots lie within three pixels
of one pinned 206,895-dot reference, exceeding 70%. This necessary geometric
bound is not a score and cannot certify a smaller raster. Do not shrink the
budget or omit dense references just to evade it. [Reproducible preflight](experiment-preflight.json).

The [historical S22 OMTJ TIFF](../downloads/gems91-s22-omtj-e1-20261026-a99b8923f0-zeros.tif)
is downloadable **for research only**, not a new candidate. Its last local
validator checked one float32 band, EPSG:32611, the pinned grid, all pixels
finite in [0,1], zero on the catalogue and zeros outside the footprint. That
is a format check, not organizer acceptance. Its final dots hit a **98.565889%**
lattice overlap. Its inputs are scientifically compromised: [fresh mask
inspection](feature-audit.json) finds 3,061 finite declared-NoData cells **inside**
the sample footprint in each of bands 13 and 14; the historical magnetic scale
was `2.01829445877272e35`. The archived S22 calculation is **HOLDOUT-DTI
0.066223 [0.048015, 0.086803]**, `gems57-pooled-hide-v2`, 60,988 withheld
positives; it is retained as arithmetic evidence only, **invalid as a test of
the intended feature**. The old canary results share the same inputs and do not
clear corrected features. No corrected geological rerun was performed.

The historical S18 “unique” raster is likewise **NOT OK TO SUBMIT**: a direct
re-check finds 19,921 / 20,000 = **99.605%** of its dots within 3 px of the
pinned lattice, a duplicate. Its older card checked only two references.
[Witness and identities](s18-witness.json). Neither identical SHA nor a
capacity bound is a full uniqueness certificate. Frozen S22 receipts are not
rewritten; the corrected code and archived original hashes are recorded in
[source-correction.json](source-correction.json).

## Concurrent S23 result merged during this review

Main advanced while this work was underway; the separately run S23-TILTA study
and its TIFF were retained, but **they were not produced by this review**. Its
[recorded HOLDOUT-DTI](../s23/holdout.json) was **0.014803 [0.011131,
0.018893]**, `gems57-pooled-hide-v2`, 60,988 withheld positives. That is not a
leaderboard score. The recorded comparison with S22 is not a matched paired
comparison: the budgets differ and S22's inputs are contaminated. Independent
[byte-level checking](s23-witness.json) finds **19,979 / 20,000 = 99.895%**
overlap with the same pinned lattice, a literal **DUPLICATE STOP**. A
competitive-only uniqueness pass does not override this rule.

S23 described band 06 (`tc`) as magnetic tilt based on embedded metadata. A
label-blind diagnostic against a hash-pinned, grid-matched community mirror of
a radiometric image instead found **r = 0.996990** with its `TC` band, sampled
every tenth of 5,164,300 jointly valid pixels. That strongly suggests a
total-count radiometric channel rather than validating magnetic tilt; it does
not independently authenticate the mirror's organizer provenance or licence.
Band 18 contains signed values and correlates **r = 0.947178** with a gravity
x-derivative; its description as an unsigned horizontal-gradient magnitude is
not established. [Method and hashes](s23-band-semantics.json).
[Coverage inspection](s23-input-audit.json) finds 3,073 and 3,061 in-footprint
NoData cells in bands 06 and 18 respectively. Unlike S22, S23 converted them
to missing and nearest-neighbor filled them; the scientific validity of that
imputation has not been demonstrated. The reported holdout therefore does not
validate the advertised tilt mechanism. The S23 runner now blocks implicit
reruns; the original source and immutable receipts remain archived.
[Corrected S23 research page](../s23/executive-summary.html).

## Nine historical leaders — claims, files and geometric evidence

These are the exact historical files associated with the user's stated claims,
not proof they were the highest official results. The claims are **UNVERIFIED
USER-REPORTED**, not `ORGANIZER-CONFIRMED`, and are not calibrated estimates.
Estimated organizer score and receipt-linked score are **unavailable** for all
nine. [Frozen audit and all 72 directed comparisons](../s22/nine-site-audit.json)
used immutable Git blob snapshots on 26 October; [refreshed source
inventory](focus-inventory.json) was obtained on 27 October. Current GitHub
main may have moved since the raster audit. The separately merged
`evidence/nine-site-leader-check.json` used a Chebyshev square rather than the
shared Euclidean 3-px gate (for example, GEMSDOE36's peer maximum was 98.26%
there versus 97.58% here). Both still exceed 70%; their exact percentages are
not interchangeable. The diagnostic source was corrected and archived without
rewriting that receipt. Each row's witness is the greatest
measured directed overlap against one of the other eight, not universal registry
coverage. All nine fail the literal >70% duplicate stop among those peers.

| Site / immutable source | Actual historical TIFF | USER-REPORTED claim | Defensible estimate | Unique among the nine? | SHA-256 |
|---|---|---:|---|---|---|
| [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/8b00ee91b9d6d7ef0e3762eb7bc0c92bee0928d1/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 | unavailable | No — 100.00% vs GEMSDOE24 | `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` |
| [GEMSDOE36](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/6dae4545076c4e5fc2be1cf348fe740ba9508a1d/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | unavailable | No — 97.58% vs GEMSDOE27 | `e15891020b9c57056ac7fa874a5e506fbd6ed9314a4ea8e73af0753887a3708a` |
| [GEMSDOE28](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/12ec4fea4c97a7887a7ca8a06f9bd94c7609ea07/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 | unavailable | No — 100.00% vs GEMSDOE24 | `5556aa1438fd67376b60d5ffc99228ec09dcc11a8408298a743ccb88d6163641` |
| [GEMSDOE31](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/225b22f9569b16a91e3b2ff1e873d92d36783410/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 | unavailable | No — 100.00% vs GEMSDOE24 | `07b6db440535404bb41ec8ddc797713e200d308e3da35937393efde5eb84bc40` |
| [GEMSDOE33](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/adf1f45ae0030de5e63d07655eaeb1a0ea4d96f3/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | unavailable | No — 99.71% vs GEMSDOE27 | `87f857d505e23247e991ccfab2cbe9f49a04df4f9c8028dce7ea261554690757` |
| [GEMSDOE25](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/fac6dbe5852baa0f0125d00ecc5cb1c16872741a/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 | unavailable | No — 100.00% vs GEMSDOE24 | `91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8` |
| [GEMSDOE30](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/35ce8911e2c3287eed973eacd12c252e8cb3f34c/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | unavailable | No — 100.00% vs GEMSDOE24 | `8cf893ead5667df21d3288a9968c35fd5385c425b029d82ee71d311715b129fd` |
| [GEMSDOE24](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/fb9e230bc09c55b96e142c69691f0cf403d69006/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | unavailable | No — 100.00% vs GEMSDOE25 | `68d0e2e4fcc594f9a23f56c44b885fee733d026d39be55e18ad2a07289525310` |
| [GEMSDOE27](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/cf8b4c201f2cc2ef649b6ca7cd32f235c2f6743a/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 | unavailable | No — 98.02% vs GEMSDOE24 | `33003374335d84bf885f2d8f5e9dd4c57044c8ec58fa6a0d7fa581e8bc41c11d` |

GEMSDOE25 and GEMSDOE30 have **identical positive support**, although their
file bytes and hashes differ. Several files use NaN outside the footprint;
that distinction does not make their in-footprint positive supports unique.
Peer overlap is directional and includes within-three-pixel proximity, not
necessarily exact-pixel equality.

## Why the reported GEMSDOE32 0.2778 might be high

The reported 0.2778 is not linked here to an authenticated organizer receipt.
The measured 37,654-dot support is heavily shared with the earlier family; a
potential explanation is that sparse, spaced placement can retain near-fault
coverage while reducing redundant false positives. Pruning near known faults
may also change that trade-off. **Neither the file bytes nor one unverified
score prove which action caused a performance difference.** Known-fault pixels
are masked exactly; nearby pixels are not automatically exempt ([DrivenData
staff clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4)).

The [official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
defines a 300 m triangular distance kernel, α=0.2 and β=0.8. [DrivenData
staff](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2)
state that public and private subsets are pooled before computing one Tversky
index. For binary predictions, truth-side credit `T` and summed prediction-side
credit `M` are generally different, so one score plus the number of dots does
not identify hidden truth prevalence or an exact pruning effect. The official
public leaderboard was observed at **0.4544 for rank 1 on 2026-10-27**
([dated observation](official-observation.json), [current leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/));
that is not a file-specific receipt and can become stale.

## Geological next steps and trusted data

[Four ranked, not-yet-run hypotheses](HYPOTHESES.md) specify layer signatures,
cost, rationale, named non-fault mimics and differences from inspected code.
They include cross-contact magnetic kurtosis, oriented terrain granulometry,
cross-spectral phase lag, and a conditional USGS 3DEP test. None was assigned
or tested here; novelty is limited to the inspected repository, not a claim of
worldwide novelty. The target is **faults**, not proof of a geothermal vent,
permeability, temperature or a productive reservoir.

- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI `10.5066/P93LGLVQ`, is CC0 and identifies survey flight lines, variable terrain clearance and acquisition blocks. Survey seams and volcanic or intrusive contacts are potential mimics.
- [INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391), DOI `10.15121/1881483`, is CC BY 4.0; it describes geophysics, geology, wells, springs and thermal observations. Fault/catalogue-related layers must be treated as leakage risks.
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services) offers unrestricted DEM/lidar products; local coverage, tiles and quality have **not** been verified or downloaded here.
- [USGS Landsat surface temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature) is freely available; surface heat can reflect weather, water, season or land cover rather than geothermal upflow.
- [USGS SGMC](https://www.usgs.gov/data/geologic-map-schema-gems-version-state-geologic-map-compilation-sgmc-geodatabase-conterminous) is CC0 but has mixed map scales and unreconciled boundaries. Mapped fault layers risk label leakage.
- [Southern Gabbs Valley USGS case study](https://www.usgs.gov/publications/discovery-a-blind-geothermal-system-southern-gabbs-valley-western-nevada-through) illustrates blind geothermal discovery from multiple data types, not validation of our proposed transforms.
- The [official data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) required login in this review. Inputs were restored from SHA-pinned **community mirrors**, not authenticated organizer downloads; integrity is not origin authentication. No external dataset was used in a model; a radiometric community mirror was read locally for the band diagnostic only, with origin and licence unverified and no redistribution.

## Range error and future submission process

The shared local writer's all-finite representation avoids out-of-range finite
sentinels in the output and the historical S22 file passed automated numeric and
grid checks. It does **not** prove that the earlier organizer rejection is
solved: the official text says null/NaN outside bounds, while our research TIFF
uses zero outside and `nodata=None`. The precise server behavior and a receipt
are not available. Never copy an input band's sentinel to the prediction.

For a **future** file only: (1) obtain an explicit assigned lane and a plan
consistent with the unchanged literal rules, with honest pinned input masks and
source licenses; (2) pass each-feature leakage canaries, whole-segment buffered
holdouts with catalogue features built from visible faults only, and surface /
final-dot checks against the full available registry; (3) use the shared writer
and shared evaluator, compare a same-fold same-budget incumbent with paired
uncertainty, and require independent separate slot selection; (4) check the
current allowed submission count in the authenticated official page. The
[rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) mention three per week,
but [staff clarify the website limit prevails](https://community.drivendata.org/t/submission-amount-question/11553/2).
Only then choose the approved TIFF or its single-TIFF ZIP on the [official
submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/),
confirm SHA, name and ≤140-character note, and save the submission ID, timestamp,
result and uploaded hash. Only an actual authenticated receipt merits
`ORGANIZER-CONFIRMED`; a public leaderboard or repo page does not.

## Reproduction and review

```bash
python -m pip install -r requirements.txt
python scripts/restore_data.py --only sample_submission,existing_faults,training_features,parent_r0_zeros
python scripts/restore_registry.py --available-only
python scripts/audit_feature_nodata.py --output work/feature-audit.json  # exits 1: expected
python scripts/audit_registry_witness.py docs/downloads/gems91-S18-UNIQUE-curvtilt-20000dots-20261026T213155Z-29db2405.tif --output work/s18-witness.json  # exits 1: duplicate
python scripts/experiment_preflight.py --output work/preflight.json  # exits 1: blocked
python generate_submission.py --with-data  # validates historical bytes, never promotes
python scripts/verify_s22.py --with-data
python scripts/check_artifact_policy.py
python scripts/render_portal.py
python -m pytest -q
```

Restored feature stack and fleet registry are ignored data and must be fetched
again in a clean clone. Two of 64 frozen registry items remained unavailable;
no universal registry clearance, submission receipt, remaining quota, matched
incumbent rerun or live competition submission is claimed. A separate
[current run card](run-card.json) records nulls for unmeasured new-candidate
fields. Review passes: **1 — input and novelty/provenance; 2 — scientific and
official-source claims; 3 — portal, automated tests and consistency.** Test
results and residual issues are documented in the final run card.
