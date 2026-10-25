# Historical Session 15 Pre-Registered Hypotheses (`S15-HCPA`, 2026-10-25)

> **Current review supersedes this archive.** GEMSDOE32's `0.2778` is user-reported, not organizer-confirmed; no receipt is available. The prior experiment and data-presence statements below were not rerun in the current checkout. Official inputs are absent, preflight is blocked, and no historical TIFF is approved as a current candidate for download or submission. Qualitative expected gains are hypotheses, not scores. See [current review](REVIEW-ARENA-AE77BA5B-20261025.md).

**Status:** Historically pre-registered and frozen *prior* to the Session 15 holdout run and artifact build; not the current branch's experiment.
**Branch:** `arena/b580c734-gemsdoe91`
**Lane:** *Hydrothermal Convective Plume & Kinematic Dilatancy Architecture (`S15-HCPA`).*

---

## 0. Metric mechanism and the unverified `0.2778` claim

The original prompt supplied `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`. The linked [GEMSDOE32 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html), inspected on 2026-10-25, says “NO ORGANISER SCORE EXISTS,” marks the named H33 artifact unscored, and labels `0.2747` as a projection/model. No organizer receipt confirming `0.2778` was available. Treat that value—and the older fleet progression numbers in this section—as user-reported claims, not verified scores.

The official DTI uses a 300 m triangular kernel (`r = 3` pixels at 100 m) and `α = 0.2`, `β = 0.8`:

`DTI = T / (0.2 T + 0.2 (S − M) + 0.8 |G|)`

`T` is maximum kernel-weighted credit per truth pixel; `S` is prediction mass; `M` is the mass receiving proximity credit. When a truth pixel's maximum is already saturated, extra nearby mass may add no further `T` while still increasing the false-positive term. Thus sparse emission can improve DTI in some configurations. This is a plausible metric mechanism only; it does not establish what caused the reported `0.2778`, whether the number was received, or whether the raster would perform similarly under a properly controlled holdout.

A historical local file note describes the R0 raster as 37,654 unit-mass dots with a reported deletion of 2,545 near-catalogue dots. Those are raster geometry/lineage observations, not a score receipt. Any far-field fraction or correlation with the user-reported values is descriptive only and cannot establish a causal improvement. No projection, expected score, or claim of beating `0.2778` is made here.

The S15 physical hypotheses below are archived preregistration ideas. The current checkout has no official competition inputs, no validated current candidate, and no source-coverage or external-use clearance; its status is not changed by this historical file.
---

## 1. Five Candidate Geological Hypotheses

| Rank | ID | Layer(s) Involved | Physical Signature | Why It Catches *Uncatalogued* Faults | Non-Fault Mimic & Rejection | Difference vs Repo History | Expected DTI / Cost |
|---:|---|---|---|---|---|---|---|
| **1** | **H15-1 Hydrothermal Convective Plume & Basement Architecture (`HCPA`)** | `cond_surf` (Band 17), `depth_to_base_surf` (Band 15), `iso_grav_anom_hg` (Band 18), `gdr_wellspring_in_footprint.csv` | High subsurface electrical conductivity plume capped by clay, aligned with basement gradient $\nabla z_{base}$ and geothermometer reservoir heat flux ($T_{res} > 150^\circ\text{C}$) | Blind geothermal systems (Desert Peak, Tungsten Mountain) have NO surface scarps; they are expressed solely by subsurface saline fluid plumes, clay caps, and buried basement offsets | Conductive saline playas (dry lakes) without basement offsets $\rightarrow$ rejected by requiring cross-concordance with basement gravity gradient | No prior lane combined 3D conductivity depth with geothermometer heat flux and basement gradient vectors | **High** / Low |
| **2** | **H15-2 Tectonic Kinematic Dilatancy & Slip Tendency (`TKST`)** | `geod_dilaterate` (Band 8), `geod_shearrate` (Band 7), `geod_2ndinv` (Band 4), LiDAR strike (Band 11) | Normalized Coulomb slip tendency $T_s = \|\sin(2(\theta - \theta_{ext}))\|$ and dilation propensity $T_d = \sin^2(\theta - \theta_{ext})$ along fault strikes under WNW ($\sigma_3 \approx 105^\circ$) extension | Critically stressed faults in the Walker Lane / Basin and Range transition slip aseismically and remain open to fluid flow without forming large visible scarps | Regional diffuse strain without structural shear localization $\rightarrow$ gated by geodetic 2nd invariant shear gradients | S12 used scalar strain magnitude; TKST resolves kinematic tensor stress onto local strike | **High** / Low |
| **3** | **H15-3 Radiometric K-Metasomatism & Magnetite Leaching (`RTNL`)** | `geodawn_rad_u8.tif` ($K, Th, U, TC$), `tmi_vg` (Band 9) | Directional cross-strike potassium enrichment $\nabla_\perp (K / Th)$ coincident with negative magnetic vertical gradient ($tmi\_vg < 0$) | Hydrothermal alteration along active blind conduits metasomatically introduces adularia/illite ($K$) while destroying magnetite, leaving a distinct geochemical footprint in basin fill | Felsic plutons (high background $K$) $\rightarrow$ rejected by requiring negative magnetic susceptibility contrast and linear geometry | Prior lanes only used raw total count (TC) or simple log-ratios without directional derivative or magnetic destruction coupling | **Medium** / Low |
| **4** | **H15-4 Multiscale Topographic Concavity & Scarp Toe (`MTCS`)** | `det_elev` (Band 12), `det_elev_slope` (Band 19), `lidar_scarp_features_u8.tif` (`step_max`, `lapneg_max`, `coh100`) | Asymmetric slope-break with negative Laplacian crest and depositional toe concavity $\kappa$ persisting $>500$ m along strike | Sub-meter Holocene alluvial fan scarps degraded by erosion that were missed on 1:250k regional maps | Pluvial lake shoreline benches $\rightarrow$ rejected by requiring strike concordance with tectonic extension rather than elevation contours | Prior lidar models used raw slope deciles; MTCS isolates profile curvature asymmetry | **Medium** / Med |
| **5** | **H15-5 Submodular Winner-Geometry Emission (`SOFE`)** | Fused posterior of H15-1 + H15-2 + H15-3, `existing_faults.tif`, DTI greedy selector | Exact submodular DTI selection: $p_j \in \{0, 1\}$, $d_{min} = 3.16$ px spacing, $N = 37,654$ unit dots, $\ge 70\%$ far-field allocation | Matches the reported raster geometry of `h33-h33-2-b2` (its 0.2778 value is unverified) while testing a separate multi-sensor convective-plume and kinematic-dilatancy surface | Over-clustering in known fault halos $\rightarrow$ prevented by hard 25% halo cap and 75% far-field quota | Tests a DTI-motivated emission design; improvement is unverified | **High** / Low |

---

## 2. Experimental Plan (Budget: 3 Experiments)

- **Experiment 1 (E1 — Surface):** Train HistGradientBoosting ensemble combining H15-1 (HCPA convective plume features), H15-2 (TKST kinematic dilatancy), H15-3 (RTNL alteration), and base geophysical layers. Evaluate on 4-fold spatially-blocked holdout set (60,988 withheld positives, 1 km buffer). Compute single-feature leakage canaries (fail if AUC > 0.90).
- **Experiment 2 (E2 — Multiphysics Corroboration Gate):** Apply multi-family corroboration gate (hydrothermal plume $\times$ kinematic strain $\times$ structural scarp step). Score on holdout set.
- **Experiment 3 (E3 — Winner-Geometry Emission & S15 Candidate Generation):** Full-map submodular emission with winner geometry ($N = 37,654$ unit dots, $d_{min} = 3.16$ px, $\ge 70\%$ far-field). Re-validate from written bytes across all 5 validator suites. Run registry and sibling uniqueness checks. Produce validated `.tif`, `.zip`, JSON run card, and audit portal.

---

## 3. Historical data-source record — not current availability or authorization

The prior S15 lane reported the following inputs as pinned and present in its then-current environment. That historical claim is **not true for this checkout**: the current review found 0/15 manifest inputs present and preflight is blocked. Hashes and filenames below are provenance notes only; they do not establish current file presence, contest-use permission, or redistribution/sponsor-sharing rights. No data were restored from a mirror for this review.
1. `data/bridge/gems-geodawn-numerical-features.tif` (19 bands, 418 MB, SHA-256 `4371c82e3b8339b8...`)
2. `data/official/sample_submission.tif` (footprint, 1.6 MB, SHA-256 `2176d08e485aa2cd...`)
3. `data/official/existing_faults.tif` (catalogue, 425 KB, SHA-256 `7ba308ccdc4418b3...`)
4. `data/external/gdr_wellspring_in_footprint.csv` (27,092 records, 2.1 MB, SHA-256 `122718e65bdf55aa...`)
5. `data/external/lidar_scarp_features_u8.tif` (12 bands, 36.9 MB, SHA-256 `d580bb8bdcdb941e...`)
6. `data/external/geodawn_rad_u8.tif` (4 bands, 26.6 MB, SHA-256 `c22420f75999030d...`)
7. `data/external/derived_sgmc_faults_100m_u8.tif` (USGS SGMC control, 198 KB, SHA-256 `643cbe992ef4ba37...`)
