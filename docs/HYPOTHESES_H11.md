# Session 11 — ranked hypotheses and one preregistered experiment (H11-1)

Date: 2026-10-24 (UTC). Branch `arena/2774ed3d-gemsdoe91`.
Labels: **ORGANIZER-CONFIRMED** = read from an official DrivenData / NLR page this session. **HOLDOUT-DTI** = our emulation on withheld catalogue components with the shared template evaluator `gems57-pooled-hide-v2`. **REASONING** = derivation or prior, not measured. **CLAIM** = stated by a source we did not verify. No DTI gain is claimed for any candidate before its holdout run.

## 0. Parallel-run protocol: what could and could not be applied

- **Lane (protocol §1).** The brief refers to "the single method paragraph below", but no such paragraph is in this session's brief. The lane is therefore **unassigned**. The run is labelled `PROVISIONAL_RESEARCH_ONLY`, as CED91 was. This is an open irregularity (IR-91-S11-01).
- **Duplicate thresholds (protocol §1).** Rank correlation > 0.90 or > 70 % of dots within 3 px of one registry raster stops the run. Both are checked on the surface before placement and on the final dots.
- **Shared tools (protocol §2).** `evaluate_holdout` (`vendor/gems57`), `ced.place`, the spatial folds, the registry gate in `scripts/run_ced.py` and `submission_writer` are reused unmodified. The only new code is the label-blind feature module `src/gems91/h11.py` and the runner `scripts/run_h11.py`.
- **Budget (protocol §6).** One experiment this session (limit 3, 2 h). The runner writes a lock file, `docs/h11-experiment.json`, so the run cannot be repeated silently.
- **Registry scope (protocol §5).** The pinned registry (`registry/comparison_inventory.json`, 64 indexed files) is not the universal fleet registry. A `complete_universal_registry: true` claim cannot be made.

## 1. Official-source checks (fetched this session)

| Claim | Source | Status |
|---|---|---|
| Metric is distance-weighted Tversky, α = 0.2, β = 0.8, triangular kernel with R = 300 m (3 px) | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> | ORGANIZER-CONFIRMED (fetched) |
| Output: single-band float32 GeoTIFF, EPSG 32611, 100 m, values in [0, 1], null/NaN outside bounds | same page, "Submission format" | ORGANIZER-CONFIRMED |
| Test faults are expert-labelled new faults outside the USGS database; the final round rescoring uses an expanded label set | same page, "Competition structure" | ORGANIZER-CONFIRMED |
| Up to three submissions per week; one final submission per entity; generative-AI use must be stated in the narrative | NLR official rules, <https://docs.nlr.gov/docs/fy26osti/96647.pdf>, §3.2, §3.4 | ORGANIZER-CONFIRMED (fetched chunks 2–3) |
| Submission materials marked "public" become public; original work is warranted; third-party content must be licensed | same PDF, §A.4, §A.5 | ORGANIZER-CONFIRMED (fetched chunk 4) |
| Eligibility: an individual must be a U.S. citizen or permanent resident, and the registration statement is signed under penalty of perjury | same PDF, §1.3, §A.1 | ORGANIZER-CONFIRMED. Only the human user can attest. |
| Public leaderboard #1 0.4413 (xiaofanhu), #2 0.3916 (cfld__) | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> | ORGANIZER-CONFIRMED (fetched this session) |
| 0.3195 and 0.2778 are not on the public board as read | leaderboard page; IR-91-S10-05 | Irregularity, not a receipt |
| The 1-m 3DEP DEM is public domain and free | <https://www.usgs.gov/3d-elevation-program/about-3dep-products-services>; <https://www.usgs.gov/3d-elevation-program> | Official, found by search. **Not fetchable from this sandbox** (allowed hosts are GitHub, PyPI, npm). |

## 2. Five candidate hypotheses not yet tested in this repo

Ranking = expected DTI improvement × implementation cost. **No DTI improvement is estimated**, because none has been measured. Cost is the implementation effort in this repo.

| Rank | ID | Layers (organizer band name) | Physical signature targeted | Why it could find a fault missing from the catalogue | How it differs from what is already in the repo | Likely non-fault mimic | Cost | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | **H11-1** | band 12 `det_elev` only | Oriented coherence of the elevation gradient (structure-tensor anisotropy at 3 and 6 px) | A scarp is a coherent linear step in topography. Coherence separates it from an isotropic hill of the same steepness, so it can flag a trace whose surface expression is too weak for a catalogue entry (REASONING). The method follows structure-tensor coherence for linear discontinuities (Wu 2017, <http://cig.ustc.edu.cn/_upload/tpl/05/cd/1485/template1485/papers/wu2017DirectionalStructureTensorBasedCoherenceToDetectSeismicFaultsAndChannels.pdf>) and DEM lineament toolboxes (TecLines, <https://www.researchgate.net/publication/263367149_TecLines_A_MATLAB-Based_Toolbox_for_Tectonic_Lineament_Analysis_from_Satellite_Images_and_DEMs_Part_1_Line_Segment_Detection_and_Extraction>). | Band 12 is read in `build_relief.py` only as *zonal terciles*. Band 19 (slope) is used by `build_relief.py`. Neither uses an oriented tensor. Snap and CED use bands 3, 18, 2 and 5. | Drainage incision and bedrock ridge fabric aligned with regional structure; roads and canals; scarps narrower than 100 m are unresolved | Low | **Run now (experiment 1 of 3).** |
| 2 | H11-2 | bands 7 `geod_shearrate` and 8 `geod_dilaterate` | Shear-to-dilatation ratio ridge | Shear-dominant zones may host strike-slip faults | `build_strain_concentration.py` and `strain.py` already read bands 4, 7, 8. Overlap is high. | GPS interpolation artefacts (the field is smooth at the scale of the data) | Medium | Not run. Overlap with the strain lane is high. |
| 3 | H11-3 | band 16 `ieq_n100a15` and band 10 `deq_n100a15` | Anisotropy of the earthquake-density field | Microseismic alignments could reveal unmapped structures | `dd_vtc_pu.py` already reads bands 10 and 16. The 100-km smoothing removes 3 px detail (REASONING). | Catalogue-completeness gradients; aftershock clusters | Medium | Not run. High mimic risk and overlap. |
| 4 | H11-4 | band 15 `depth_to_base_surf` | Second-derivative (flexure-like) ridge of basin depth | Fault-bounded basin edges leave a curvature signature | H10-1 (basement step) was tested and is **negative** (`docs/HYPOTHESES_S10.md`). Curvature is a close variant. | Sediment-thickness changes that are not tectonic | Low | Not run. Close to a negative lane. |
| 5 | H11-5 | external: 1-m DEM from USGS 3DEP (free, public domain) | Scarp detection at 1 m (cross-profile offset, hillshade lineaments) | Scarps are the direct Quaternary-fault signal and are the strongest evidence available for unmapped faults | Not implemented. The pinned `ext_lidar_scarp_u8` is a derived external file (`registry/data_manifest.json`) whose provenance is not verified here. | Cultural features; alluvial fans; sub-metre noise | High | **Blocked.** The sandbox cannot reach usgs.gov. This is the most valuable single data gap and the first thing to request. |

## 3. H11-1 — preregistered method (fixed before the holdout run)

- **Input.** GeoDAWN band 12 (`det_elev`) only, nodata-filled with `ced.fill_input` (nearest-neighbour fill, median/IQR scaling, no labels).
- **Method.** Gradient Gaussian σ_g = 1.5 px. Structure-tensor integration σ_w ∈ {3, 6} px. Coherence = ((λ1 − λ2)/(λ1 + λ2))² ∈ [0, 1]. Surface = sqrt(pct(coh₃) · pct(coh₆)) · pct(|∇|), with percentiles over the footprint.
- **Placement.** `ced.place` (greedy, dots separated by more than 3 px, ascending index tie-break, budget = `ced.DOT_BUDGET` = 32,000, same as CED91). The final dots exclude mapped catalogue pixels, the same rule as CED91.
- **Arms.** `h11` (candidate), `gradient_control` (|∇| only, same placement; tests whether anisotropy adds anything beyond slope), `random_null` (seeded uniform random eligible pixels at equal per-fold mass). The S10 promotion rule requires the candidate to beat the random null.
- **Holdout.** Shared `spatial.folds` (whole-component hide-and-recover, 80 px buffer). Pooled DTI with α = 0.2, β = 0.8 and the 300 m triangular kernel. Paired physical-cluster bootstrap, 1000 draws, seed 520811.
- **Leakage canary.** Feature-alone AUROC against catalogue pixels for each feature. AUC > 0.90 means leakage until proven otherwise. The canary is a bound, not a proof of no leakage.
- **Registry.** Surface rank correlation ≤ 0.90 and final dot overlap ≤ 70 % within 3 px against all indexed registry rasters, checked before and after placement.
- **Decision rule.** Promote only if (a) the canary passes, (b) the registry gate passes on the pinned scope, (c) the candidate beats both controls with a 95 % CI above 0. Even then, promotion needs an assigned lane, a complete universal registry, a comparable prior holdout best and a separate selector. None of these exists in this session, so the verdict is **negative / research artifact** whatever the numbers show.

## 4. Irregularities raised by this section

- **IR-91-S11-01.** The brief has no assigned method paragraph. The lane is unassigned, so the parallel-run lane check cannot be applied as written.
- **IR-91-S11-02.** `docs/HYPOTHESES_S10.md` states that bands 8 and 17 are "not used anywhere in this repo". This is wrong: `strain.py` and `build_strain_concentration.py` read band 8, and `dd_vtc_pu.py` reads bands 8, 10, 15, 16, 17, 18. H10-2 and H10-3 are therefore not untested lanes, and the earlier ranking overstated them.
- **IR-91-S11-03.** Band 12 is read as terciles in `build_relief.py`. H11-1 is a different transform (oriented tensor), but it uses the same input. Its novelty claim is therefore about the transform, not the data.
- **IR-91-S11-04.** The 1-m DEM needed for H11-5 is public-domain at usgs.gov, but this sandbox cannot download it.
