# Repository review — active branch `arena/0a96aa96-gemsdoe91` (2026-10-25)

## Executive verdict

**No new raster was generated in this review.** Existing active candidate: CED91, `gems91-ced-v1-20261024-d35670b28c81.tif`; it is **OK TO DOWNLOAD: YES — research only** and **OK TO SUBMIT: NO**. The current run card says no method paragraph/lane was assigned. More decisively, final-dot comparison stopped at a registered raster with **99.9125%** of candidate dots within 3 pixels, exceeding the protocol's 70% duplicate threshold. The surface comparison passed within its indexed scope; that does not rescue a duplicate final placement.

The pinned input restore succeeded and the CED TIFF revalidated against the local sample and catalogue. That establishes file identity and format checks against locally restored references—not organizer acceptance, data-use rights, full registry novelty, or competition score. The training and feature files were fetched from immutable GitHub mirrors recorded in the repository manifest, not directly from the login-gated DrivenData data tab. Hash agreement verifies the mirror bytes against the repository's pins; it does **not** independently prove the original source or usage authorization.

## Evidence checked in this review

- Branch: `arena/0a96aa96-gemsdoe91`, initially clean at the inherited commit.
- `python scripts/restore_data.py`: all 15 manifest-listed inputs fetched/verified by SHA-256 and byte count. The working copy is in ignored `data/`; no competition-data binaries are proposed for Git.
- `python scripts/preflight.py`: local pinned references make the legacy PRUNE/MASS/SNAP/CONCENTRATION/RELIEF/TRACKB axes appear ready. This is only a file-presence/readiness report; it does not establish that a new method is assigned or promotable.
- `python scripts/verify_current_artifact.py --with-data`: **PASS** for the current CED artifact: one float32 band, 3730×3292, EPSG:32611, sample-matched transform, finite values, values in [0,1], zero outside footprint, zero mass on mapped catalogue, and valid single-TIFF ZIP. Actual raster SHA-256: `a29e79d400d0fb26ebcbc0be6b1dcf66b17dfedf9ded1ef8c9a53678c16553ee`.
- `python scripts/verify_evidence.py`: **PASS** for source/evidence consistency; it explicitly reports `geological_experiments_rerun: 0` and `submission_ready: false`.
- `python -m pytest -q`: **PASS**, 100% of the test progress completed, with one skip and rasterio deprecation warnings.
- Before this review's repair, `python scripts/check_artifact_policy.py` **FAILED**: three already-tracked historical S15 TIFF/ZIP files had no registry entries. They are now explicitly hash-pinned as `legacy_quarantined`; rerun the policy check to confirm.

## CED91 recorded result and uniqueness stop

The run card and `docs/ced-holdout.json` record **0.062153 HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, 60,988 withheld positives, 95% CI `[0.049910, 0.075115]`). The paired delta versus its magnetic-only control is **+0.010775 HOLDOUT-DTI** with 95% CI `[-0.004310, 0.026597]`; the interval includes zero, so the available paired evidence does not resolve an improvement over that control. This is a recorded local hide-and-recover result, not an organizer score. `ORGANIZER-CONFIRMED: null`.

Pre-placement surface novelty was checked against a frozen index of 64 rasters: maximum absolute rank correlation was `0.0242905` within that index. Final-dot comparison stopped after 27 of 64 entries when `calib_r13lattice_00904.tif` produced 99.9125% directed 3-pixel overlap. Remaining final comparisons were intentionally not run after the duplicate stop. The index and all public GEMSDOE sites are not proven complete; do not call this global novelty clearance.

The literal protocol therefore says stop: final overlap is >70%. Also, CED91's own run card has `lane.assigned=false`. No new experiment or TIF should be produced until a lane is assigned and a non-duplicate surface/placement can be tested under the shared holdout protocol. No weekly slot is shown as used; no organizer receipt exists.

## Three candidate hypotheses for a future authorized experiment

These are *candidate refinements*, not established novel methods. Code review found related feature families in this large repository and the supplied prompt lists many sibling projects. “Not found as this exact standalone test in the inspected local implementation” is not proof that another fleet repository has not tried it. Each candidate requires pre-placement surface uniqueness checks; any final dot overlap above 70% is an immediate stop. No DTI projection is assigned.

| Priority | Hypothesis and input layers | Physical signature / why it might find a catalogue-missing fault | Difference from current implementation and known overlap | Mimic; estimated implementation cost |
|---|---|---|---|---|
| 1 | **Cross-scale magnetic–gravity phase-lag coherence at basement contacts.** GeoDAWN stack bands: `rtp` (2), `tmi_vg` (9), `iso_grav_anom` (13), gravity vertical gradient (11), gravity horizontal gradient (18), and `depth_to_base_surf` (15). | Estimate direction and persistence of the displacement between magnetic and gravity edge phases, conditioned on cover thickness. A concealed fault may offset magnetic and density boundaries coherently even where the surface trace is absent from the catalogue. | CED91 uses two Gaussian scales, gradient-magnitude persistence/alignment and signed centroid displacement; it does not implement a cross-wavelet/phase-lag statistic. PTHA and Hessian methods are related, so this is a refinement with substantial overlap risk, not a wholly new geophysical family. | Intrusive/lithologic contact or flight-line levelling seam; medium cost (existing grid only), medium expected opportunity, unmeasured. |
| 2 | **Signed dilatation transition across a basement-edge normal.** GeoDAWN bands: `geod_dilaterate` (8), `geod_shearrate` (7), `geod_2ndinv` (4), gravity horizontal gradient (18), basement depth (15). | A local sign change or shear/dilatation contrast aligned with a buried basement step could mark a permeable fault zone beneath subdued topography. | Existing S15/HCPA, PTHA and strain modules already use geodetic-strain scalars and basement structure. The proposed test is an explicit signed cross-edge contrast, evaluated alone before fusion. The supplied stack contains scalar strain summaries, not a full tensor; do not claim a physically resolved principal-axis projection from these bands. | Broad tectonic strain gradient, interpolation artifact, or basin-edge lithology; low-to-medium cost, low-to-medium expected opportunity, unmeasured. |
| 3 | **Topographic expression as an observation-process control, not a positive fault prior.** GeoDAWN bands: detrended elevation (12), detrended-elevation slope (19), basement depth (15), paired with magnetic/gravity gradients (3, 9, 11, 18). | Test whether geophysical evidence predicts withheld fault segments specifically in deep-cover/low-relief domains where topographic fault visibility is poor; downweight exposed scarp signatures that merely reproduce mapped faults. | Current code has cover gates and many scarp/relief features; this candidate changes the estimand/control (cover-conditioned hide-and-recover) rather than simply adding another ridge feature. It must report the same fixed evaluator/split alongside stratified diagnostics. | Lithologic contacts or differential erosion can create the same cover/relief boundary; medium cost, diagnostic value higher than expected leaderboard gain, unmeasured. |

All three use bands in the locally restored 19-band feature stack and require no additional external data for a first experiment. Exact layer labels were read from the local GeoTIFF band descriptions; those labels are not a substitute for checking the official data documentation. No external-data-dependent idea is being presented as viable. Before implementation, compare each signature against all local modules and available fleet artifacts, preregister one assigned lane, and run the feature-alone leakage canary. The existing run is already stopped on final novelty and cannot be repurposed as a fresh candidate.

## Material repository issues and suggested fixes

1. **Landing-page/README drift:** the top README text still names another Arena branch, says pinned data are absent, and promotes a historical S15 run, while the active run card and `index.html` are CED91/S14-era. Replace the stale “current” section with the active-branch review and mark prior lane summaries explicitly historical. Keep the submission verdict conspicuous.
2. **Artifact policy drift:** the policy checker correctly found three tracked S15 TIFF/ZIP artifacts absent from its explicit inventory. This review registers the bytes as quarantined rather than weakening the policy. The repair must be validated by running the checker and CI tests.
3. **Data provenance:** `restore_data.py` downloads exact pinned files from GitHub project mirrors. Record that as byte integrity only; verify original competition provenance, license/eligibility and required acknowledgements against official DrivenData/DOE documents before any actual contest upload.
4. **Lane and promotion separation:** the local CED run card marks its lane unassigned, and the exact final placement is a duplicate. Do not use “build allowed” or a valid TIFF as a submission-ready gate. Selector and organizer receipt remain separate.
5. **Holdout scope:** CED91 uses the vendored shared `gems57` pooled evaluator. Confirm any future candidate uses the mandated hide-whole-segments-with-buffer split, visible-only catalogue features, exact visible-pixel masking and a selector matched to final emission. Feature-alone canaries must be measured for every input feature; a passing proxy canary is not proof of no leakage.
6. **Historical claims:** neither the site-reported 0.2778 nor any other reported leaderboard value is confirmed by an organizer receipt in this checkout. Keep HOLDOUT-DTI, projections, site claims and ORGANIZER-CONFIRMED results visibly distinct.

## Official review links

- [DrivenData competition overview and problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — official competition statement/metric reference; data tab is login-gated.
- [DrivenData competition data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — source of the submission template, catalogue and feature inputs; not directly accessed in this sandbox.
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — reference implementation.
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — official survey context; does not independently authenticate the GitHub mirror used here.
- [NLR rules/submission PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) and [DOE Geothermal Data Repository submission 1391](https://gdr.openei.org/submissions/1391).
- [EPSG:32611](https://epsg.io/32611) — CRS reference.

## Verification run card

The machine-readable card is [`run-card-REVIEW-0A96AA96.json`](run-card-REVIEW-0A96AA96.json). Verdict: **negative; no promotion; existing CED download is research-only; do not submit.**
