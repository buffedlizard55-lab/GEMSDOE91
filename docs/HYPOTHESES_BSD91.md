# Preregistered Hypotheses — BSD91 Blind Stepover-Damage Lane (2026-10-25 UTC)

**Branch:** `arena/94032b4a-gemsdoe91`  
**Frozen before any holdout evaluation or dot emission.**  
**Core Values:** Maximize P(Win) · Own the Outcome  
**Status of supplied score figures:** `0.2778` (GEMSDOE32 `h33-h33-2-b2`), `0.3195`, `0.4413` are USER-REPORTED, UNVERIFIED — no organizer submission-page receipt exists locally (`ORGANIZER-CONFIRMED: null`). Labels (`labels.tif`) are organizer-held and are NOT in `registry/data_manifest.json`, so a true holdout DTI cannot be computed in this sandbox; see Limitations below.

## Protocol compliance

1. **Rule 1 (LANE):** single lane declared below — BSD91 (Blind Stepover-Damage lattice). Pre-placement surface rank correlation `max|rho| <= 0.90` vs every available registry raster; final-dot overlap `<= 70%` within 3 px of any one registry raster's dots. Both checked before any slot consideration.
2. **Rule 2 (REUSE, DON'T REBUILD):** uses `scripts/evaluate_holdout.py` (folds + canary), `scripts/dti.py` (alpha 0.2, beta 0.8, 300 m triangular kernel), `scripts/submission_writer.py` (format writer), `src/gems91/io.py` / `src/gems91/gates.py` / `src/gems91/release_gates.py` / `scripts/validate_raster.py` — shared tools, no private fork.
3. **Rule 3 (LABEL EVERY NUMBER):** every score stamped `HOLDOUT-DTI` (evaluator version, n withheld positives, 95% CI) or `ORGANIZER-CONFIRMED` (receipt) or `USER-REPORTED (UNVERIFIED)`. A projection is never written as a score.
4. **Rule 4 (LEAKAGE CANARY):** every feature alone on the holdout folds; symmetric AUC > 0.90 => fail closed.
5. **Rule 5 (RUN CARD):** `docs/run-card-BSD91.json` — hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation/overlap, raster sha256, validator output, submission name + note <= 140 chars, verdict promote/negative.
6. **Rule 6 (BUDGET):** 3 experiments max, 2 hours max; zero weekly slots spent here. Promotion is a separate selector step.

## Ranked candidate hypotheses (none previously implemented in this repo)

| Rank | Hypothesis | Layers | Physical signature | Why it catches catalogue-missing faults | Named non-fault mimic | Differs from implemented code | Est. DTI gain | Cost |
|---|---|---|---|---|---|---|---|---|
| 1 | **BSD91 Blind Stepover-Damage lattice** (TOP — built this session) | `existing_faults.tif` (catalogue); `derived_sgmc_faults_100m_u8.tif` (off-catalogue USGS SGMC strands); `gdr_wellspring_in_footprint.csv` (thermal springs, prior only); `sample_submission.tif` (footprint) | Blinds faults as stepovers/relay ramps between catalogue strands and off-catalogue SGMC strands, with springs marking upflow; permeability in the 300 m–1 km damage zone. Dots strictly `3 < d_catalogue <= 12 px` (outside the 300 m scoring collar; catalogue faults are masked from scoring so dots on them pay FP mass for no hidden truth) AND within 500 m of an SGMC strand OR 600 m of a Hot/Warm spring; binary dots spaced >= 2.8 px (just beyond kernel radius so dots don't self-cancel the matched-mass term M); fixed budget <= 37,654. | Catalogue-derived lanes (SNAP, PRUNE, DZEDGE annulus-only) place on/near mapped faults, which the scorer masks out; hide-and-recover over-rewards near-catalogue dots. GEMSDOE32's +0.0070 came from deleting dots `<= 2 px` from the catalogue — proof that off-catalogue placement is the lever. BSD targets *off-catalogue fault-associated* ground that no fleet lane targets systematically: DZEDGE used the annulus with no fault support (measured 0.0 deliberate negative); SNAP snaps to catalogue-proximate edge crests; PRUNE refills from parent ridge support. | Unaltered lithologic contacts, alluvium/playa edges, flight-line seams can look like off-catalogue lineaments. Mitigated by requiring the **conjunction** of SGMC proximity AND spring proximity, not either alone. | No `training_features.tif` bands (unlike PGRD, CWPC, CPAD, CDSC, EULR, DRN91, SNAP, RELIEF); no parent-submission derivation (unlike PRUNE/CONCENTRATION); conjunction support (unlike DZEDGE annulus-only). All inputs local; no new external data. | Medium-high (directly attacks the collar penalty demonstrated by GEMSDOE32 forensics) | Low |
| 2 | **H1 Hurst-break roughness corridor** | `training_features.tif` Band B12 detrended elevation | Local Hurst-exponent / roughness break at concealed fault scarps in piedmont playa cover, where surface expression is muted but near-surface fracturing changes topographic roughness at the 300 m–1 km scale. | Blind faults deform shallow cover; roughness breaks can mark strands with no surface trace and no catalogue entry. | Alluvial fan edges, dune fields, dry lake shorelines. | Uses B12 tercile roughness; not implemented anywhere in the fleet history (S18 review ranked Hurst-break first for future screening, untested). | Medium-high | Medium — needs `training_features.tif` (418 MB, pinned GitHub mirror `buffedlizard55-lab/GEMSDOE`, obtainable) |
| 3 | **SOLK spring-aligned off-catalogue kernel** | SGMC strands + GDR springs (local data) | Dots at SGMC-strand midpoints that fall inside a spring-density kernel (>= 2 springs within 1 km), i.e. off-catalogue faults with independent hydrothermal corroboration. | Springs are surface markers of concealed fault conduits; strand-midpoint placement avoids the catalogue collar while staying fault-associated. | Spring clusters at lithologic contacts not fault-related. | Simpler than BSD (no annulus, no catalogue-distance gating beyond collar); not previously built. | Low-medium | Low (local data) |
| 4 | **K/Th–gravity dipole pair** | `training_features.tif` Bands B05/B18 (radiometric K/Th + isostatic gravity gradient) | Co-located potassium/thorium anomaly and gravity-gradient dipole across a concealed fault (hydrothermal alteration + basement offset). | Dipoles mark blind faults with alteration halos; neither anomaly alone is diagnostic. | Clay-rich paleosols, survey flight-line radiometric strips. | Needs B05/B18 bands; radiometric lanes in fleet history used band aggregates, not dipole pairing. | Medium | Medium (needs features) |
| 5 | **Deep regional gravity lineament** | `training_features.tif` Band B13 | Broad isostatic-gravity gradient lineaments at 5–10 km scale marking deep crustal faults that feed geothermal systems. | Deep faults may have no shallow expression but control upflow; gravity sees basement. | Regional lithologic boundaries, batholith margins. | Gradient-of-B13 not implemented; needs features. | Low | Medium (needs features) |

## Chosen lane

**BSD91 Rank 1**, experiment 1 of 3. Validation this session: leakage canary on its support fields, registry uniqueness vs all locally available registry rasters (GEMSDOE32 parent `parent_r0_zeros`, fleet rasters in `docs/downloads/`), format gate suite, blind SGMC off-catalogue control DTI. Holdout DTI vs the hidden organizer truth is NOT computable locally (labels absent); the run card states this explicitly and the verdict is `negative` (not promoted, OK TO SUBMIT: NO) until an organizer receipt and a holdout beat of the incumbent are obtained.

## Limitations

- No `labels.tif` locally: competition truth is organizer-held, DrivenData-login only, not in the pinned manifest. No HOLDOUT-DTI, no paired CI, no leakage AUC vs hidden truth can be measured here.
- `training_features.tif` (418 MB) not fetched: hypotheses 2, 4, 5 cannot be implemented in this session. It is obtainable from the pinned GitHub mirror `buffedlizard55-lab/GEMSDOE@c0c06ac8` via `scripts/restore_data.py --only training_features` (5 git blobs, ~419 MB total) on an unrestricted machine.
- No DrivenData auth: cannot download `labels.tif`, cannot auto-submit, cannot read the live weekly slot cap.
- The user-reported `0.2778` and live-leaderboard claims `0.3195` / `0.4413` are not receipts; beating them is not demonstrated by any local number.

## Sources (official, verifiable)

- Competition format/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (official; outside sandbox allowlist, not freshly fetched)
- DTI (alpha 0.2, beta 0.8, 300 m triangular kernel): https://en.wikipedia.org/wiki/Tversky_index (Distance-Weighted Tversky Index form, per repo `vendor/gems57/metric.py`, transcribed from the official problem description)
- Grid CRS: https://epsg.io/32611 (EPSG:32611, UTM 11N, WGS 84)
- GeoDAWN survey: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (USGS; source of the 19-band stack, not re-verified here)
- GDR thermal springs: https://gdr.openei.org/submissions/1391 (USGS Geothermal Data Repository, public domain; local CSV derived from it)
- NLR prize rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf (submission rules)
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution (U-Net/Tversky example, not the official scorer)
