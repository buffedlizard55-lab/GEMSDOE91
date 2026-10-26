# Nine-site evidence audit and no-run decision — 2026-10-26

**Branch:** `arena/af73263f-gemsdoe91`

**Decision:** **NO NEW TIFF. `OK TO DOWNLOAD: NO NEW TIFF FROM THIS REVIEW`. `OK TO SUBMIT: NO`.**

**Experiments:** 0. **Slots used:** 0. **Organizer-confirmed score:** none.

This is a read-only audit of the supplied GEMSDOE24/25/27/28/30/31/32/33/36 sites and the active GEMSDOE91 checkout. It is not a scientific experiment, a slot choice, a leaderboard refresh, or a TIFF validation. The interactive nine-site summary is [`nine-site-audit-20261026.html`](nine-site-audit-20261026.html); the source-of-truth claim register is [`research/nine-site-audit-20261026.json`](research/nine-site-audit-20261026.json); the no-run card is [`run-card-SITE-AUDIT-20261026.json`](run-card-SITE-AUDIT-20261026.json).

## Executive decision

The highest value in the user's supplied nine-site list is GEMSDOE32's `h33-h33-2-b2` at **0.2778**. It is a **USER/OWNER-REPORTED, UNVERIFIED** claim in this audit, not `ORGANIZER-CONFIRMED`: the current GEMSDOE32 score ledger describes owner-recorded submissions but says no organizer receipt binds the bytes to those rows, and its current submissions manifest has `receipt: null` for the TIFF. A contradictory line on the same owner site calls the number an “organizer-confirmed owner report”; that wording does not replace the missing receipt.

**There is no file I can recommend or approve to submit.** The nine values are historical reports, not a controlled comparison or a verified ranking of exact TIFF-to-receipt pairs. The GEMSDOE91 lane is still `null`, the pinned sample/parent/features are missing under `data/`, and the shared preflight blocks every build axis. No experiment, leakage canary, pre-placement registry check, final-dot novelty check, or new-raster validator ran. The previous ISO91 download remains a prior research file with a negative verdict; it is not a new output from this review.

## Evidence boundary and site-by-site executive summary

All nine repositories were read at pinned GitHub commits, not through a mutable Pages deployment. The exact commit SHAs and file-level links are in the JSON register. Scores below are the highest rows in the supplied shortlist, **not necessarily the best-ever entry at each site**. No organizer receipt was retrieved or verified in this pass.

| Site | Highest supplied entry | Supplied score | Method / evidence interpretation |
|---|---|---:|---|
| **GEMSDOE24** | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | **0.2477** | H19-5 multi-physics ridge surface thinned at d=1.5, reported as 60,069 pixels. The repository's submission metadata has `live_dti: null` and `score_evidence: null` and describes it as unscored. The score is a user/owner claim, not a receipt. The current site's GVC1/RSHG1 values are internal HOLDOUT-DTI results on a different evaluator, not competition scores; both are marked DO NOT SUBMIT. |
| **GEMSDOE25** | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | **0.2600** | The H19-5 ridge surface thinned to 44,090 dots at roughly 2.8-pixel spacing. GEMSDOE25's current registry labels the D2.8 file withdrawn/duplicate and identifies it as byte-identical to a listed file. No official score receipt was found. Its current H66 research screens do not yield a promoted/slot-approved file. |
| **GEMSDOE27** | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | **0.2449** | T-v2 gap-closure additions to the D1.5 base: 61,328 dots = 60,069 + 1,259. GEMSDOE28's owner-maintained registry labels the score support `task_statement_only`; its local A/B note reports a negative increment relative to the D1.5 claim, not an independent organizer comparison. A separate H27-8 registry row is explicitly unscored; modelled values are projections, not scores. |
| **GEMSDOE28** | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | **0.2710** | H36-1 rung-3.0/r1 blind allocation; owner materials list 37,660 pixels. The score registry warns that these are owner-reported public-leaderboard values, not receipts. The current safety notice says no file is approved; H36-1/H38-1 are historical research. |
| **GEMSDOE30** | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | **0.2600** | A 44,090-dot D2.8-style sparse/off-catalogue emission. GEMSDOE31's pinned user-score registry says its dot set is identical to GEMSDOE25 D2.8, so the two rows are not independent evidence. The current GEMSDOE30 pointer is a separate research lane and requires a complete parallel registry before any slot choice. |
| **GEMSDOE31** | `h27-4-solo-d28-20261004-8acb75e1-nan` | **0.2708** | H27-4 solo D2.8: 40,199 pixels after removing the 3,891-pixel ring within 1 px/100 m of the mapped catalogue. GEMSDOE31's own manifest calls this a historical reference-only re-emission, pixel-identical to GEMSDOE28 H27-4; it is not a unique current candidate. The score is unverified. |
| **GEMSDOE32** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778** | The owner-maintained construction is a sparse H19-5 ridge family followed by D2.8 thinning and catalogue-flank pruning; the reported final raster has 37,654 dots and deletes 2,545 more dots within 2 px/200 m of the H27-4 solo parent. The exact geometry claim is from owner-maintained forensics; it is not a fresh reproduction here. The reported score lacks a receipt binding it to the raster in the current manifest. |
| **GEMSDOE33** | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | **0.2632** | Owner ledger describes a 41,865-pixel analog tip/stepover addition, 33,670 pixels shared with an r1 base plus 8,195 tip/stepover pixels. Its score feed explicitly says the values are reports, not verified file/score pairs, and that no DrivenData receipt or authenticated account session is available. The current-run card is a preflight-negative review; it did not establish a new organizer result. |
| **GEMSDOE36** | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | **0.2750** | The supplied label calls this an Anderson-geothermal PINN emission with 38,854 dots. GEMSDOE32's pinned forensics describe it as a strict superset of all 37,654 B2 dots plus 1,200 extras; that is a geometry comparison, not proof of an independent detector effect. GEMSDOE36's current review calls the score a supplied owner claim and says no new TIFF was generated. |

### What the `0.2778` result may mean — and what it does not prove

The most defensible explanation is **metric-aware thinning and catalogue-flank exclusion**, not a demonstrated breakthrough in independent geology. The owner sites describe a nested lineage: dense H19-5 ridge → D2.8 sparse dots → H27-4 “solo” pruning → H33-2-B2 deleting another catalogue-near ring. Under a distance-tolerant score with a 300 m kernel, nearby emitted cells can have overlapping/redundant credit; an emitted cell with little credit can still add false-positive mass. If known mapped-fault pixels are excluded from the evaluation, removing predictions close to those masked faults can improve the score while retaining more distant coverage.

That is a **plausible mechanism**, not a causal estimate for the claimed 0.2778. The exact competition score has no verified receipt-to-file association in the audited records, the relevant leaderboard labels are owner-maintained, and the nested variants are not an independently randomized experiment. The “zero-credit” wording in some owner forensics assumes the hidden evaluation's exact mask/truth relationship; it is not independently measured here. The score also does not prove geothermal-vent discovery or that the same pruning generalizes to hidden faults.

**Could an original candidate beat 0.2778?** In principle, yes. **Evidence that this checkout can do so now:** none. A prior GEMSDOE91 review records 0.4413 as a public-leaderboard observation on 2026-10-25, while 0.3195 appears in an older 2026-10-03 owner snapshot and in the supplied prompt. This audit did not refresh the official leaderboard; therefore neither is labelled “current” here. Both are public-leaderboard context, not a score receipt for any listed TIFF.

## Current owner-site research files are not a submission recommendation

“Live candidate” below means an available research file or active run-card in a pinned owner-repository snapshot, **not** a confirmed current competition submission. The table is deliberately conservative and does not nominate a slot.

### Existing GEMSDOE91 files in this checkout (historical / separate-branch artifacts)

`docs/current-run.json` still points at the negative ISO91 file from 2026-10-25. These four files are available in the current checkout/site, but none was generated by this review, newly revalidated here as a candidate, or approved for upload. Their holdout measures are not leaderboard scores and cannot establish an `ORGANIZER-CONFIRMED` ranking.

| Existing file | HOLDOUT-DTI (evaluator, withheld positives, 95% CI) | Evidence/status |
|---|---|---|
| ISO91 E1 — [`run-card-ISO91.json`](run-card-ISO91.json) | 0.081253 (`gems57-pooled-hide-v2`, 11,911, `[0.063850, 0.099617]`) | Earlier negative session; failed G1/G2/G4. Its extended sibling sweep records 70.109% literal 3-px overlap with a registry raster, exceeding the stop rule. Old format-valid research download only; not this review's file. |
| S19-SVHF E3 — [`run-card-S19-SVHF.json`](run-card-S19-SVHF.json) | 0.147791 (`gems57-pooled-hide-v2`, 60,988, `[0.132771, 0.162342]`) | Earlier parallel run; `submission_ready=false`, `selector_approval=false`; literal overlap 99.8513% with the synthetic-lattice witness. Not a slot candidate. |
| S18-HGBR E1 — [`run-card-S18-HGBR.json`](run-card-S18-HGBR.json) | 0.200742 (`gems57-pooled-hide-v2`, 60,988, `[0.180482, 0.221419]`) | Separate parallel run; despite its card's internal `verdict: promote`, literal overlap is 99.843% with the synthetic-lattice witness and `live_slot_decision` says `DO_NOT_SPEND_WEEKLY_SLOT_AUTOMATICALLY`. This audit does not endorse/select it. |
| S18-UNIQUE — [`run-card-S18-UNIQUE.json`](run-card-S18-UNIQUE.json) | **NOT RUN** | Format/demo checks only; holdout not measured, leakage canary pending and full-raster uniqueness pending. Not eligible for selection. |

The highest *listed* local HOLDOUT-DTI among those four is S18-HGBR's 0.200742, but it is not a competition score, is blocked by the literal duplicate rule, and is not comparable to the nine-site owner reports. **The file to submit from this review remains none.**

### Related owner repositories (pinned snapshots)


| Site | Latest research status visible in the pinned snapshot |
|---|---|
| GEMSDOE24 | H24-GVC1 and H24-RSHG1 are HOLDOUT-DTI research results. For GVC1: **0.148763 HOLDOUT-DTI**, `gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.134135, 0.163703]`; 76.82% of final dots fall within 3 px of a registry raster, so DO_NOT_SUBMIT. RSHG1: **0.128994 HOLDOUT-DTI**, same evaluator and withheld count, 95% CI `[0.115783, 0.143050]`; its page also says DO_NOT_SUBMIT. These are not leaderboard scores and are not directly comparable to `gems57-pooled-hide-v2` without a matched rerun. |
| GEMSDOE25 | H66-1 screen passed but fresh-draw confirmation failed; H66-2 passed a screen but was unconfirmed at the experiment cap. Its current page says research/testing only, not a slot-approved submission. |
| GEMSDOE27 | The pinned registry lists an H27-8 all-increments artifact as unscored. Any modelled 0.2484/0.2781 figures are explicitly projections, not scores. |
| GEMSDOE28 | Current safety notice: no file currently approved. H36-1/H38-1 are historical research artifacts; some older page projections are not scores. |
| GEMSDOE30 | Current-run pointer is MSDB-1v2 research; its own note requires a complete parallel registry before any slot decision. The latest LSM attempt is explicitly stopped as a duplicate. |
| GEMSDOE31 | The H27-4 file is a historical copied geometry, not a unique current candidate. Local delivery checks establish local file properties only, not organizer acceptance. |
| GEMSDOE32 | Current site includes a separate GEO-CONDUIT artifact, but its current strict-review notice says DO NOT SUBMIT and reports a 99.67% duplicate overlap with a synthetic lattice. An older “OK TO DOWNLOAD AND SUBMIT” callout conflicts with that notice; the conflict is not approval. The fetched snapshot does not provide a complete shared-evaluator card for that file, so no numerical holdout claim is used here. |
| GEMSDOE33 | The current-run card is a preflight-negative analog-transfer review; the older A33-L1 file is a research download, not a competition score or slot approval. The card does not provide a comparable new holdout value with the required evaluator metadata. |
| GEMSDOE36 | The 2026-10-26 review says no new TIFF was generated; old downloads are research-only. |

These current-file statuses vary in evaluator, holdout, registry completeness, and age. They cannot be ranked as a single live competition leaderboard. The “best file to submit” field in the machine card is therefore **null**.

## Ranked hypotheses — proposals, not results

Ranking is **qualitative conditional expected DTI upside relative to implementation/data cost, with a tractability penalty**; it is not a numeric score forecast. No numerical improvement is projected. These ideas are distinct from each other; some are already documented as untested ideas in GEMSDOE91, so they are **not claimed novel across the repo or the wider GEMSDOE fleet**.

| Rank | Geological hypothesis and layers/data source | Physical mechanism and why it could find uncatalogued faults | Code difference / named non-fault mimic | Qualitative expected DTI upside, cost, data status |
|---:|---|---|---|---|
| **1** | **Dipping-contact waveform matched-filter bank** — competition bands B02 RTP magnetics, B13 isostatic gravity, B14 TMI, with B15 depth-to-basement as a scale/context layer. Local prior proposal: [`HYPOTHESES_S17.md`](HYPOTHESES_S17.md), H17-2. | A buried fault that offsets a magnetic/density contact can preserve an asymmetric step waveform below alluvial cover even where the surface has no mapped scarp. Fit signed 2-D forward templates over strike/dip/source-depth and require consistent geometry across more than one physical field; this targets contact displacement, not just high gradients. | Existing lanes use gradient, curvature, tensor, wavelet, Euler, and source-depth summaries; no exact forward waveform bank was found in the implementation search. **Mimic:** an unfaulted dipping stratigraphic contact, dyke, or pluton margin can have similar profiles; require cross-field and held-out-contact controls. | **Expected upside: medium, unquantified; relative priority highest because the official competition bands are the intended inputs. Cost: high compute/implementation.** Competition raster/cache is absent here and the official data tab is login-gated. Previously proposed but not run; not new fleet-wide novelty. |
| **2** | **Repeatable same-age alluvial-fan displacement** — B12/B19 for regional context plus official USGS 3DEP 1 m bare-earth DEM tiles; optional map-unit age context from the USGS GeMS/SGMC release, excluding all mapped fault geometries. | A concealed/uncatalogued fault may produce the same signed vertical step or warped tread across multiple adjacent fan surfaces of comparable age. Requiring along-strike persistence across separate fan surfaces can separate tectonic displacement from a single depositional edge. | Existing DEM scarp/Hurst/knickpoint families do not implement a cross-fan, same-age surface-offset consistency statistic. **Mimic:** fan-lobe boundaries, debris-flow levees, terrace risers, drainage incision, roads, or grading. | **Expected upside: potentially high if coverage is complementary, unquantified; rank lowered by tractability. Cost: very high data-preparation/coverage cost.** 3DEP and SGMC are official source leads linked below; exact tile coverage, schema, rights for derived data, and footprint overlap were not verified. **Not viable until those checks/access are completed.** |
| **3** | **Focal-mechanism orientation coherence with geodetic strain** — B07/B08 strain, B10/B16 seismicity summaries, B02/B13 structural context, plus USGS ComCat focal-mechanism/moment-tensor products where available. | Spatially coherent focal-mechanism rotations or nodal-plane alignments with the principal strain axes may reveal active concealed structures that are not expressed as surface topography. This is a test of active fault kinematics, not a point-density prior. | Existing code uses summary seismicity and geodetic strain, but no per-event focal-mechanism orientation field was found. **Mimic:** volcanic/aftershock swarms, sparse station coverage, and mechanism uncertainty can create apparent clusters or rotations. | **Expected upside: low-to-medium and uncertain, unquantified because event coverage is unknown. Cost: high external-data and QC cost.** USGS ComCat is an official source lead; focal-mechanism coverage is event-dependent, no raw catalog is local, and coverage was not queried. **Not viable now.** |

**Top candidate test status:** H17-2 is the qualitative top candidate, but it was **not tested**. The absent lane paragraph prevents selecting it as the method for this checkout; missing `data/` prevents building or validating it. No selector/slot decision was made. This is an explicit blocker, not a positive or negative scientific result.

## Three-pass review record

### Pass 1 — checkout and evidence inventory

- Re-read the standing brief in `README.md`; checked the fixed branch, experiment plan, manifests, evaluator/writer/readiness modules, current site sources, and historical run cards.
- Confirmed `registry/experiment_plan.json` has `lane: null`; `data/` is absent.
- `scripts/restore_data.py --check`: 15 pinned input files failed verification. No mirror data were restored; authorization/reuse concerns remain unresolved.
- `scripts/preflight.py --json`: **BUILD BLOCKED, 0/2 required inputs verified**; all six build axes blocked. `generate_submission.py --preflight`: assignment absent and capacity witness unavailable; 0 experiments and no candidate.
- Pinned the nine sibling source repositories to the commits listed in [`research/nine-site-audit-20261026.json`](research/nine-site-audit-20261026.json). No mutable Pages page was treated as an exact receipt.

### Pass 2 — claim and irregularity review

- Compared the nine supplied top values with the pinned owner registries and current cards; retained the original score values only as USER/OWNER-REPORTED claims.
- Checked the most important duplication relationships: GEMSDOE25 D2.8 is marked withdrawn/duplicate; GEMSDOE30's D2.8 dot pattern is reported identical to GEMSDOE25; GEMSDOE31 H27-4 is a historical copy of GEMSDOE28; GEMSDOE36 is reported as GEMSDOE32 B2 plus 1,200 dots.
- Treated the GEMSDOE32 0.2778 conflict as unresolved because its site has a “confirmed owner report” label but the same snapshot's ledger disclaims receipt-to-byte linkage and its file manifest has `receipt: null`.
- Kept 0.3195 and 0.4413 separate. The last stored public snapshot in this checkout is dated 2026-10-25; no live refresh was performed on 2026-10-26.
- Searched the local implementation and hypothesis records before listing alternatives. Related implementations exist; hypotheses are not claimed novel beyond the inspected scope. No experiment was launched.

### Pass 3 — documentation and regression checks

- Added this dated review, a commit-pinned JSON audit register, a no-run JSON card, a data-driven executive HTML page, and regression tests. Updated README with this operative brief; the root page now routes to the no-run audit, while the generated portal/index and submission guide prominently mark the earlier ISO91 file as historical research only.
- Recreated the pinned Python environment in ignored `.venv/` from `requirements.txt`; no environment files are tracked.
- Full repository tests: **see final verification entry below**. The expected preflight failure remains a blocker, not a test failure.
- No candidate raster was created, so format validation, leakage canaries, pre-placement rank correlation, final-dot overlap, HOLDOUT-DTI, and a TIFF SHA-256 are correctly `NOT RUN`/null. Null is not a pass.

## Official/manual-review source links

These links are supplied for manual review; this 2026-10-26 pass did not fetch the DrivenData, USGS, DOE, Landsat, or ComCat pages. Prior local review [`REVIEW-ACTIVE-E649E460-20261025.md`](REVIEW-ACTIVE-E649E460-20261025.md) contains a dated 2026-10-25 official-source audit and a public leaderboard observation of 0.4413. An official page can change; the observation is not a live value.

- [DrivenData DOE GEMS problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData data portal (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official GEMS reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS 3D Elevation Program](https://www.usgs.gov/3d-elevation-program)
- [USGS GeMS/SGMC 2026 release](https://www.usgs.gov/data/geologic-map-schema-gems-version-state-geologic-map-compilation-sgmc-geodatabase-conterminous) · [DOI 10.5066/P1A3DQZK](https://doi.org/10.5066/P1A3DQZK)
- [USGS ComCat earthquake catalog](https://earthquake.usgs.gov/data/comcat/)
- [USGS Landsat Collection 2 surface temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)
- [DOE/NLR competition report](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

## Remaining blockers / next actions

1. Supply or authenticate the one assigned method paragraph for this branch; do not infer it from historical experiments.
2. Resolve data-use authorization and restore the exact pinned inputs through the approved path; do not treat a GitHub mirror hash as a distribution licence.
3. Make the shared evaluator, template, and writer available and verify their pinned versions; fix shared-tool defects once, not in a private fork.
4. Only after assignment and inputs exist, run the highest-ranked pre-registered candidate with visible-fault-only features, whole-segment buffered holdout, feature-alone leakage canaries, and pre-placement novelty. Stop on the specified >0.90 correlation or >70% 3-px overlap.
5. Test the exact final dots against the complete registry, report HOLDOUT-DTI with evaluator/version/withheld count/95% CI, and generate a new TIFF only after all gates pass.
6. Keep selector/weekly-slot decision separate. A “download” badge is not submission approval; no file is approved here.

## Final verification (2026-10-26)

- Full suite: **PASS — 652 passed, 9 skipped**. There were 87 Rasterio `Affine` pending-deprecation warnings; no failures. This includes `tests/test_site_audit.py` and `tests/test_submission_portal.py`.
- Portal and local links: **PASS** — local target/fragment checks for the nine-site HTML, root landing page, current portal and submission guide.
- Render reproducibility: **PASS** — audit, ISO91 source-page and front-door renderers were run twice; SHA-256 snapshots of the root, sources, generated portal pages, audit page and current-run pointer were unchanged.
- Artifact policy: **PASS — 95 explicitly registered prediction artifacts; no raw raster/archive tracked.** No new TIFF was generated.
- Python compile check: **PASS** (`compileall` for `src`, `scripts`, and `tests`); both new JSON cards parse successfully.
- `git diff --check`: **PASS**.
- The scientific preflight remains **BLOCKED** as reported above. These documentation/regression checks are not experiment authorization or submission approval.

## Run card

See the machine-readable no-run card at [`run-card-SITE-AUDIT-20261026.json`](run-card-SITE-AUDIT-20261026.json). This was not an experiment: all scientific and artifact outputs are null or `NOT_RUN`, no submission name/note is offered, and the verdict is negative/blocked.
