# Session 17 Pre-Registration — Euler Deconvolution Source-Geometry Fusion (`S17-EULR`)

**Frozen prior to any Session 17 feature build, model fit, holdout evaluation, or GeoTIFF emission.**
**Date:** 2026-10-25 UTC · **Branch:** `arena/597b6f3f-gemsdoe91`
**Shared tools reused (Protocol Rule 2, no private fork):** `scripts/evaluate_holdout.py`
(folds, canary, pooled DTI, SGMC control, registry gates), `scripts/dti.py`,
`scripts/submission_writer.py`, cached builders `gems91.dd_vtc_pu` (49 static),
`gems91.mhtr_coda` (16 S11 + corridor emitter), `gems91.ptha` (20 PTHA + OOF learner +
crest + Dinkelbach emitters), S13 tile/paired-bootstrap helpers in
`scripts/run_s13_lane.py`, readiness policy `gems91.readiness`.
**Comparable holdout bar:** `0.267782 HOLDOUT-DTI` (95% CI [0.253687, 0.281135],
`gems91-hide-recover-v1.0`, 60,988 withheld, split `0f874367…`, S14-PTAC E2,
`docs/run-card-S14-PTAC.json`); next `0.244601` (S13-PTHA E3). S15-SCGF E2 scored
`0.240633` on the same instrument and is a labelled negative.
**Budget (Rule 6):** ≤3 experiments (E1/E2/E3 below), ≤7,200 s of experiment time
(first OOF fit → last holdout score). Feature-cache builds, canaries, registry
checks, writing and validation are engineering prerequisites, timed and reported
separately. Zero weekly DrivenData slots are spent; promotion is a separate
selector step this session cannot perform (no assigned lane paragraph, no
authenticated weekly-cap receipt).

---

## 0. Why `h33-h33-2-b2` (0.2778 CLAIM) led the fleet — and what beating it requires

### 0.1 Evidence labels (Rule 3)
- `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, and every other
  fleet number in the brief (`docs/reported-results.csv`), is
  **CLAIM — USER-REPORTED, NOT ORGANIZER-CONFIRMED**. GEMSDOE32's own page states
  no organizer score exists in that repository (pinned audit
  `docs/s16/gems32-forensics.json`). No submission-page receipt for any fleet
  file exists in this checkout.
- Public leaderboard high **`0.4413` (xiaofanhu, 30 submissions)** was read
  directly from the organizer leaderboard page on 2026-10-25
  (<https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>,
  fetched this session; #2 `0.3916`). This is an **ORGANIZER-PAGE-READ** of the
  public board, not a receipt for any fleet file. The brief's `0.3195` is stale
  (it would rank below #20 on the same read).
- Official metric/format were re-read this session from the organizer problem
  page (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>):
  distance-weighted Tversky, α=0.2, β=0.8, triangular kernel R=300 m,
  max-kernel TPw/FPw/FNw; single-layer float32 GeoTIFF, EPSG:32611, 100 m,
  values in [0,1], null/NaN outside bounds. `scripts/dti.py` implements exactly
  this algebra: `DTI = T / (0.2T + 0.2(S−M) + 0.8|G|)`.

### 0.2 Byte-verified mechanism (reproduced this session from pinned rasters)
All 15 `registry/data_manifest.json` inputs were restored and SHA-256-verified
this session (`scripts/restore_data.py`, all `ok`). On those bytes:
`h33-h33-2-b2-zeros` (37,654 binary dots) is **exactly**
`solo-d2.8 (40,199 dots) minus dots with catalogue distance ≤2 px` — 0 added,
2,545 removed (recomputed 2026-10-25; matches `docs/s16/gems32-forensics.json`).
Median nearest-neighbour spacing 3.0 px (min 2.828), 69.8% of dots >10 px from
the catalogue, zero mass on catalogue pixels. The claimed-score chain is an
**emission** progression on one detector surface (H19-5 solid 121k px 0.1922 →
thin 1.5 px 0.2477 → thin 2.8 px 0.2600 → solo 0.2708 → B2 prune 0.2778; all
CLAIM). Mechanism: TPw takes a **max** over predictions within 300 m of each
truth pixel, so redundant neighbouring mass adds ≈0 credit but still pays
α(S−M); thinning and deleting near-catalogue dots (masked truth can pay
nothing there) raise credit-per-dot until the marginal dot reaches break-even
≈ α·DTI. **Conclusion (MODEL judgement):** 0.2778 is surface-limited, not
packing-limited. Emission tweaks on the same surface are exhausted (an
independent surface, GEMSDOE36 Anderson PINN at 38,854 dots, plateaued at the
same ~0.275 CLAIM). Beating 0.2778 — let alone the verified public 0.4413 —
requires a **better ranking** that credits genuinely concealed faults the
exposed-scarp lineage misses. Whether any candidate here beats 0.2778 live is
unknowable without an organizer receipt; this session tests ranking quality on
the shared holdout only and never writes a projection as a score.

### 0.3 Holdout limitation (stated, not hidden)
Hide-and-recover withholds *mapped* faults, which are biased toward exposed
scarps; hidden test faults were expert-labelled as *new* faults and may be
blind (organizer problem page, §Datasets/Labels). HOLDOUT-DTI therefore
measures catalogue-style recovery, an imperfect proxy for blind-fault
discovery. The blind off-catalogue USGS SGMC control
(`EH.score_off_catalogue_sgmc`, >3 px from catalogue) is reported alongside as
a second, independent-geology check. Prior sessions measured holdout↔live
rank correlation as weak/negative on small samples (`evidence/s14_winner_forensics.json`,
ρ=−0.75, n=7) — another reason no live score is forecast here.

---

## 1. Five ranked candidate hypotheses not yet tried in this repo

Novelty basis: grep over `src/gems91/*.py`, `scripts/*.py`, `docs/HYPOTHESES*.md`
on 2026-10-25 (Euler/Parker/forward-template/χ/flow-accumulation/hypocenter:
zero implementations; Euler explicitly recorded “absent in repo” in
`docs/HYPOTHESES_S16PC.md` §1). Expected gains are **MODEL judgements for
ranking only — never scores**. Cost assumes the pinned 19-band stack already
restored; no hypothesis below except #4/#5 needs new data.

| Rank | ID & layers | Physical signature / transform | Why it catches catalogue-*missing* faults | Named non-fault mimic + rejection | Difference vs everything implemented here | Expected ΔHOLDOUT-DTI (MODEL) / cost / viability |
|---:|---|---|---|---|---|---|
| **1 (RUN)** | **H17-1 Euler source-geometry fusion.** B14 `tmi` + B09 `tmi_vg` (magnetic), B13 `iso_grav_anom` (gravity, FFT Gz), B15 `depth_to_base_surf` (agreement only) | Windowed Euler deconvolution (Thompson 1982; Reid et al. 1990): per 11×11 px window solve `(x−x0)Fx+(y−y0)Fy+(ζ−ζ0)Fζ=N(B−F)` for source offset/depth/background at structural indices N∈{0,1}; rasterize accepted-solution density, mean depth, depth uncertainty. Correct SI ⇒ tight clusters; wrong SI ⇒ scatter. | Buried basement contacts under basin fill have weak *amplitude* but coherent gradient *ratios* over a window; Euler position/depth depend on ratios, complementing this repo's amplitude-scaled tilt/Frangi/worm/phase detectors. Lateral (strike-slip) contacts also cluster without normal-throw polarity — targeting the persistent SW/Walker-Lane fold weakness (S14 SW 0.1826 vs NE 0.3365) that normal-concordance features penalize. | Unfaulted lithologic contacts (indistinguishable by Euler alone — supervised fusion with step/strain features must separate); isolated volcanic plugs (N≈3 point sources scatter at N=0/1, low joint mag×grav density); flight-line seams (depth≈0, rejected by depth/B15-agreement features). | No Euler solver exists in repo code. SPI/Salem (S12/S15) estimate pointwise wavenumber/depth from tilt; Euler jointly inverts windowed gradients for 3-D position + depth + background with formal uncertainty and SI-clustering diagnostics — a different estimator with different failure modes. Fleet Euler lanes emitted raw solutions standalone (USER-REPORTED 0.0355–0.0984); H17-1 instead fuses Euler *statistics* as supervised features atop the proven S13 stack + Dinkelbach emission, tested by single-change ablation. Fleet-wide fusion novelty is UNVERIFIED. | Low–medium positive if real (MODEL +0.000 to +0.020 vs matched ablation; falsification equally likely given fleet standalone weakness) / **medium** (one new module, convolution-form solver) / **viable now, licence-clean** (official stack only) |
| 2 | **H17-2 Dipping-contact waveform matched-filter bank.** B02 `rtp`, B14, B13 | Correlate observed anomaly profiles with analytic dipping-contact forward waveforms over depth×dip×strike templates; feature = best normalized correlation + winning depth/dip. | A faulted contact has a characteristic asymmetric step-waveform even at low amplitude; template *shape* matching rejects symmetric dyke/plug anomalies that edge magnitude accepts. | Dipping unfaulted stratigraphic contacts (same waveform family; needs strain/step-polarity fusion). | ASC91 matched *level steps* in smoothed fields; no code forward-models potential-field contact waveforms. | Medium (MODEL) / **high** (template bank × 3 fields on 12.3M px; CPU-heavy) / viable but deferred on cost |
| 3 | **H17-3 Parker–Oldenburg basement-stripping residual.** B13 + B15 | FFT forward-model gravity of the B15 basement interface (Parker series, assumed density contrast), residual = observed − forward; fault blocks inside basement remain as residual steps after basin-fill effect removal. | Intrabasement faults that do not offset the modelled basement surface still step density *within* basement; stripping removes the dominant basin signal that masks them. | Wrong density contrast / B15 model error creates correlated residuals (mimic: B15 interpolation artefacts). | BHAR `G_intra` is a *polynomial regression* of B13 on B15 transforms (verified in `bhar_s12.py`), not an interface-relief FFT forward model. No Parker code exists (grep = 0). | Low–medium (MODEL) / medium / viable; deferred (contrast ambiguity, B15 is itself gravity-informed → circularity risk needs care) |
| 4 | **H17-4 Fluvial χ / divide-asymmetry.** Absolute DEM (not B12) | Flow routing, channel steepness/χ imbalance across divides, knickpoint alignment (Willett-style divide migration metrics). | Young blind faults perturb drainage/divides before a scarp is mappable. | Lithologic knickpoints, Lahontan shoreline benches. | No flow-routing code exists (grep = 0). **BLOCKED HERE — not proposed as viable this session:** B12 is *detrended* elevation (regional trend removed), unsuitable alone for flow routing. Required free official source: USGS 3DEP DEMs via The National Map (`https://apps.nationalmap.gov/tnmaccess/`, public domain) / competition `1m_DEM_links.csv`. Obtainability checked 2026-10-25 from bash: `apps.nationalmap.gov`, `usgs.gov` unreachable (curl exit 35, HTTP 000; only github/pypi/npm egress). Deferred to an unrestricted host with hash-pinned tiles. | High ceiling (MODEL) / high I/O / **non-viable in sandbox** |
| 5 | **H17-5 Relocated-hypocenter planar lineations.** USGS ComCat/FDSN hypocenters (not B10/B16 grids) | 3-D RANSAC/DBSCAN planar clusters of relocated microseismicity projected to 100 m traces. | Blind seismogenic faults image directly at depth, invisible to 15-km-smoothed B10/B16 density bands. | Quarry blasts, geothermal injection swarms (time/depth filters). | No hypocenter code exists. **BLOCKED HERE:** free official source USGS FDSN (`https://earthquake.usgs.gov/fdsnws/event/1/`, public domain) checked 2026-10-25 from bash: unreachable (curl exit 35). Also needs careful leakage design (catalogue-independent). Deferred. | High ceiling (MODEL) / medium / **non-viable in sandbox** |

Only H17-1 is authorized this session (single lane `S17-EULR`, `assigned: false`
— the brief promises a “single method paragraph” it does not contain; lane
self-declared and frozen here before any fit, as in S13–S16).

## 2. Frozen S17-EULR method

### 2.1 Inputs (hash-pinned, restored & verified 2026-10-25)
`training_features` 19-band stack (sha256 `4371c82e…`, 418,912,844 B),
`existing_faults` (`7ba308cc…`, labels/exclusion only for Euler),
`sample_submission` (`2176d08e…`, grid/footprint only — see IR-S17-01),
`gdr_wellspring_in_footprint.csv` (via shared static builder only),
SGMC control raster, R0 zeros (parent-diff/registry only, never a feature).
Grid verified from bytes: 3730×3292, EPSG:32611, transform
(100, 0, 243350, 0, −100, 4508550); footprint 5,167,373 px; catalogue 60,988 px.
No prior submission raster is a feature, starting point, or placement mask.

### 2.2 Derivative QA (measured this session, label-blind, before freezing operators)
Interior 768×768 crop (all-valid, y0=228, x0=379), centre-half statistics:
- FFT `dz(B14)`/px vs `B09×100`: **r=+0.98919, slope 0.96981** ⇒ B09 is the TMI
  vertical derivative in nT/m (confirms S12/S13 audits). Magnetic `Fζ = B09×100`
  (per-px, depth-positive `+|k|` convention).
- FFT `dz(B13)` vs B11: **r=−0.15406**; `dy(B13)` vs B11 **r=+0.93895**,
  `dx(B13)` vs B18 **r=+0.95673** ⇒ (B11,B18) are signed *horizontal* gradient
  components, **not** vertical/magnitude as tags state (confirms
  `evidence/s13_band06_and_units_audit.json`). Gravity `Gζ` is therefore
  computed by FFT `|k|` from B13; B11/B18 are not used as Euler derivatives.
- Feature-band valid pixels inside footprint: 5,164,312/5,167,373 (99.941%);
  3,061 sentinel px (nodata −3.4028235e38) are EDT-filled for filtering but
  excluded from Euler acceptance (≥8 px clearance, §2.3).

### 2.3 Euler solver (new `src/gems91/eulr17.py`, test-first)
Coordinates in pixels, ζ = depth (down +), observation ζ=0, source depth d>0.
Per window (W=11 px, centred (xc,yc), local offsets u,v):
solve least-squares `A·(du,dv,d[,B])ᵀ = b`, `A=[Fx, Fy, Fζ, N]`,
`b = u·Fx + v·Fy + N·F` (N=0 drops B). Normal-equation sums are computed by
box-filtering absolute-coordinate fields then transforming to window-centred
form; the fast solver must match a brute-force per-window solver on test grids
(`tests/test_eulr17.py`) before any real-data use, and must recover known
(x0,y0,d) on an Euler-homogeneous synthetic field (solver-algebra test, not a
geological claim).
- Magnetic: F=B14, Fx/Fy = Gaussian derivatives (σ=1.2 px, per-px) of EDT-filled
  B14, Fζ = Gaussian-smoothed (σ=1.2) `B09×100`, F smoothed σ=1.2. N∈{0,1}.
- Gravity: F=B13, Fx/Fy = Gaussian derivatives (σ=1.5 px), Fζ = FFT `|k|`/px of
  EDT-filled B13 (reflect-pad 64) then Gaussian σ=1.5, F smoothed σ=1.5. N∈{0,1}.
- Acceptance (all label-free, frozen): centre ≥8 px from any invalid/outside px
  (per-field valid mask); window-mean amplitude `√(Fx²+Fy²+Fζ²)` ≥ 40th
  percentile over accepted centres; depth d∈[0.5, 25] px; |du|,|dv|≤8 px;
  relative depth uncertainty `√cov_dd / d ≤ 0.20` (cov = s²(AᵀA)⁻¹).
- Rasterization: bin accepted sources at rounded (xc+du, yc+dv); per combo
  `dens = log1p(G_{σ=2}(count))`, `depth = G_{σ=3}(Σd)/G_{σ=3}(count)`
  (undefined→footprint-median fill), `unc` likewise for relative uncertainty.
  `joint_dens = ½(dens_mag0 + dens_grav1)`; `mag0_b15_agree = −|100·depth_mag0 − B15|/1000`
  clipped [−5,0] (B15 assumed metres per tag/value range: median 316, p99 3416 —
  assumption recorded; tree splits do not require exact units).
  All 14 columns robust-z (median/MAD, clip ±8), finite everywhere on footprint.
  Names: `s17_eulr_{mag0,mag1,grav0,grav1}_{dens,depth,unc}`,
  `s17_eulr_joint_dens`, `s17_eulr_mag0_b15_agree`. Euler uses **no catalogue**
  in construction ⇒ identical features in holdout and full inference (no
  fold-rebuild leakage path).

### 2.4 Learner, emitter, experiments (single-change ablation)
Feature blocks: static cols `range(34)+[44..48]` (39, exactly as S13/S14 —
including their known omission of cols 34–43, preserved for comparability),
S11 16, PTHA 20 (E1) vs PTHA20+EULR14=34 (E2/E3 base). Euler columns carry
`s17_` names absent from `ptha.TOPO_FEATURE_NAMES` ⇒ included in the shared
learner's subsurface branch (correct: magnetic/gravity/depth only; the shared
topo list's known incompleteness, IR-91-S15-05, is preserved unchanged for
comparability and reported, not silently “fixed”).
Learner: unchanged `PTHA.fit_and_predict_ptha_oof_fold` per fold
(visible faults only, fold exclude = region|withheld|buffer).
Emitters: unchanged `MC.mhtr_corridor_submodular_emit` (E1/E2: γ=1.20,
mhtr_weight=0.48, piedmont 0.24, spacing 2.45, 48,000 area quotas via S13
eligible logic, collar >3 px from *visible* faults) and
`PTHA.dinkelbach_fold_independent_emit` (E3: target 48,000, spacing 2.50).
Crest/piedmont: unchanged S13 surfaces from original PTHA/S11 blocks.
- **E1 (ablation control):** S13 recipe (75 feats), corridor emit. Validates the
  instrument in this checkout and supplies paired tiles. (S13 E2-corridor
  reference: 0.198407; S13 E3-Dinkelbach: 0.244601 — different emitter, cited
  for orientation only.)
- **E2 (H17-1 test):** E1 + 14 Euler cols (89 feats), identical seeds
  (1700+20·idx+fold pattern per experiment index as frozen in runner),
  learner, emitter, quotas. **Paired E2−E1 (5 km tiles, 400 draws) is the
  primary scientific readout.** Falsifier: paired CI includes ≤0 ⇒ Euler
  block adds no holdout ranking value in this fusion; lane recorded negative.
- **E3 (emission):** Dinkelbach emit on the better of {E1,E2} OOF surfaces
  (frozen rule: higher pooled HOLDOUT-DTI; ≥ picks E2, mirroring S13).
Winner for full-map = max HOLDOUT-DTI among {E1,E2,E3} (S13 rule). Full fit on
complete catalogue (seed 1791), full emit: Dinkelbach 44,000 @2.50 if E3 wins
else corridor 48,000 @2.45 (S13 rule), eligible = footprint & ¬catalogue &
d_cat>3 px. No post-hoc variants; a canary/duplicate stop ends experiments.

### 2.5 Scoring, canary, uniqueness, writing (shared, fail-closed)
- Folds: `EH.build_segment_buffered_folds(bridge_px=3, buffer_px=10)`; assert
  split SHA `0f874367d8d34964c9b8802d3d67d348f68ade1f9fbc4301bffc5eafcb524db8`
  and 60,988 withheld. Score: `EH.score_pooled_holdout(..., n_boot=200,
  mask_buffer_predictions=True)` as primary **HOLDOUT-DTI
  (`gems91-hide-recover-v1.0`)** for comparability with S13–S15 cards, plus
  `False` (`v1.1-nohalo`) receipt; on eligible-restricted fold dots the two
  must agree in pooled value (asserted; IR-S17-02). Visible faults masked
  pixel-exactly by the evaluator; no halo deletion in placement.
- Canary (Rule 4) **before any fit**: `EH.run_leakage_canary` on all 89
  candidate columns (39+16+20+14), subsample_step=4; any symmetric AUC>0.90,
  nonfinite, or undefined stops the run. Passing is not proof of no leakage.
- Uniqueness (Rule 1): registry = hash-distinct same-grid `*.tif` in
  `data/fleet_registry` (restored subset of frozen `registry/comparison_inventory.json`;
  2 GEOD rows lack blobs/files → UNVERIFIED, counted not_checked) +
  `data/registry` + `docs/downloads`, excluding own `gems91-s17-eulr-` prefix.
  No lattice exemption. Pre-placement surface check per experiment
  (`check_registry_surface_uniqueness`, stride 20; duplicate ⇒ stop) and final
  surface+dots check (`check_registry_uniqueness`, stride 5; directed ≤3 px
  overlap ≤0.70, |ρ|≤0.90). The S16 capacity bound (lattice covers 99.8713% of
  footprint within 3 px; ≥82.34% forced overlap at 37,654 dots,
  `docs/s16/registry-feasibility.json`) means the literal gate is expected to
  fail at 44–48k budgets; it will be reported, never waived or gamed.
- SGMC blind control: `EH.score_off_catalogue_sgmc` (report-only).
- Writing: `SW.write_validated_submission_bundle` → all-finite `-zeros.tif`
  primary (nodata=None, every cell in [0,1] — the portal
  “Predicted values must be in range [0, 1]” failure mode), NaN companion,
  single-TIFF ZIP, browser bundle; triple validators must PASS or no bundle.
  Independent re-read verification + `gems91.readiness.gates` determine the
  public verdict. Expected verdict regardless of holdout outcome:
  **OK TO DOWNLOAD: YES — RESEARCH · OK TO SUBMIT: NO** (unassigned lane, no
  selector/weekly-cap receipt, literal registry gate; plus promotion would
  additionally require beating 0.267782 with paired evidence vs S14-PTAC,
  which this single-stage design does not even attempt to pair against —
  point comparison only, stated as such).

## 3. Irregularities flagged for review (found this session)
- **IR-S17-01:** pinned `sample_submission.tif` bytes are binary {0,1} with
  1.0 *exactly on the 60,988 catalogue pixels* (verified identical masks),
  whereas the organizer page describes the sample as predicting “total fault
  absence”. The mirror file is therefore a catalogue-as-example raster, not
  the described absence sample. Impact: none on grid/footprint use (CRS/shape/
  transform/finite-footprint verified); sample *values* must never be used as
  a prediction or label source. Flagged, not silently corrected.
- **IR-S17-02:** shared `score_pooled_holdout` default changed across sessions
  (S16 flipped `mask_buffer_predictions` default to False/v1.1). S13–S15 v1.0
  cards predate the flip. S17 passes the argument explicitly (both versions
  reported) instead of editing the shared evaluator.
- **IR-S17-03:** frozen registry restore is incomplete: 2/64 rows (retracted
  GEOD twins) have no `git_blob` and no local file ⇒ `restore_registry.py`
  fails closed. S17 restores/verifies the 62 blob rows by the same pins and
  records the 2 as not_checked; the frozen inventory is not edited.
- Band-tag defects B06 (radiometric TC mislabelled as tilt) and B11/B18
  (horizontal components mislabelled) were previously audited
  (`evidence/s13_band06_and_units_audit.json`) and independently reproduced
  in §2.2; tags are never trusted over bytes.

## 4. Sources for manual review (official first)
- Competition problem/metric/format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (fetched 2026-10-25)
- Public leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (fetched 2026-10-25; #1 0.4413)
- Reference solution (U-Net/Tversky-loss example; not the distance-weighted scorer): https://github.com/drivendataorg/gems-prize-reference-solution (README fetched 2026-10-25 via GitHub API)
- GeoDAWN surveys (USGS): https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (bash-unreachable here; manual-review link)
- INGENIOUS: https://gbcge.org/current-projects/ingenious/ · EPSG:32611: https://epsg.io/32611 · Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- Euler deconvolution: Thompson (1982), *Geophysics* 47; Reid et al. (1990),
  “Magnetic interpretation in three dimensions using Euler deconvolution”,
  *Geophysics* 55, 80–91, DOI 10.1190/1.1442774; Reid & Thurston (2014) on SI
  errors/uses/abuses (window/SI caution followed in §2.3 acceptance gates).
- Blind-system structural settings: Faulds & Hinz (2015), World Geothermal
  Congress (step-overs ~32%, terminations ~25%, intersections ~22% of ~250
  categorized Great Basin systems; up to ~75% of resource blind) — context for
  why catalogue-missing faults matter; fault predictions here are **not**
  confirmed geothermal vents, temperatures, or resources.
- Blocked-data sources (free/official, obtainability checked §1): USGS National
  Map TNM Access https://apps.nationalmap.gov/tnmaccess/ ; USGS FDSN
  https://earthquake.usgs.gov/fdsnws/event/1/ ; GDR submission 1391
  https://gdr.openei.org/submissions/1391 (already pinned locally as CSV).
