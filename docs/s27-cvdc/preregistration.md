# Session 27 (`S27-CVDC`) Preregistration — Rule-of-V Contour–Potential Discordance, Hydrothermal Magnetite-Destruction Baffle, Multi-Valley Knickzone Alignment & Stitched-OOF Uniqueness-Capped Submodular Emission

- **Date frozen (UTC):** `2026-10-29`
- **Branch:** `arena/2d335bdc-gemsdoe91`
- **Lane status:** Self-declared single coherent session lane executing (1) `LIMITATIONS_AND_NEXT_STEPS.md` S25-FABRIC Priority #1 (stitched-OOF far-field & competitive-uniqueness-capped emission geometry without in-sample catalogue refitting) and (2) `docs/s26/preregistration.md` deferred Ranks #1–#2 (`CVDC-PMDB` + `VCTK`).
- **Hard budget cap (Protocol Rule 6):** Maximum **`3` experiments (`e1`, `e2`, `e3`)** and `< 2 hours` wall-clock; **`0` weekly DrivenData submission slots** spent automatically.

---

## 1. Frozen Inputs, Provenance & Missing-Data Contract

1. **Admissible training inputs (SHA-256 verified via `registry/data_manifest.json`):**
   - `data/official/sample_submission.tif` (`EPSG:32611`, `3730 x 3292`, `100 m`, `5,167,373` finite footprint cells)
   - `data/official/existing_faults.tif` (`60,988` in-footprint positive catalogue pixels)
   - `data/bridge/gems-geodawn-numerical-features.tif` (`19` float32 bands; candidate features use only `B02, B03, B04, B05, B07, B08, B09, B11, B12, B13, B14, B15, B17, B18, B19`)
2. **Explicit exclusions (provenance & leakage safety):**
   - **`B06` (`tc`) excluded:** Label-blind audit (`IR-8E8-09`) established `r = 0.99699` with gamma-ray radiometric Total Count rather than magnetic tilt angle. True magnetic tilt is computed analytically from `B02/B03/B09`.
   - **`(B18, B11)` treated strictly as signed $(\partial_x B_{13}, \partial_y B_{13})$:** Label-blind gradient check (`docs/s27-cvdc/GEOTHERMAL_AND_FAULT_RESEARCH.md` §4) proved `corr(B18, dx B13) = 0.9481` and `corr(B11, dy B13) = 0.9380`. Vertical gravity curvature uses masked Laplacian $-\nabla_h^2 B_{13}$.
   - **`ext_lidar_scarp_u8` and `ext_geodawn_rad_u8` excluded:** Unresolved third-party rights (`IR-91-S19-01`).
   - **Zero fault coordinates in features:** Neither `existing_faults.tif` nor `fold["visible"]` enters any static or Stage-2 feature.
   - **Blind diagnostics (`derived_sgmc_faults_100m_u8.tif`, `registry/lfi_anchor_matches.json`) kept 100% post-hoc:** Never read during feature extraction, model fitting, experiment selection, or dot placement.
3. **NoData sentinel exclusion (`IR-8E8-02` safeguard):**
   - Cells with `~np.isfinite(x)` or `|x| >= 1e30` (`3,061` interior footprint cells) are excluded from every convolution/gradient via normalized masked Gaussian convolution (`cckm24._masked_blur`), and output feature supports are eroded beyond each operator's footprint (`GRAD_ERODE_PX = 3`, `CVDC_ERODE_PX = 16`, `VCTK_ERODE_PX = 16`) with `NaN` outside eroded support so no filled sentinel influences any finite value.

---

## 2. Frozen Feature Specification (`src/gems91/cvdc27.py`)

### 2.1 `base` Group (`6` features, `erode = 3 px`)
- `base_grad_b02`, `base_grad_b12`, `base_grad_b13`, `base_grad_b14`: `log1p(|grad|` of masked-smoothed `B02, B12, B13, B14` at `sigma = 2.0 px)`.
- `base_slope_b05`, `base_slope_b19`: `log1p(clip(B05, 0, None))` and `log1p(clip(B19, 0, None))` on eroded valid masks.

### 2.2 `cvdc` Group — Hypothesis Rank #1 (`CVDC-PMDB`, `18` features, `erode = 16 px`)
- **Rule-of-V Contour–Potential Strike Discordance (`5` features):**
  - Structure-tensor dominant gradient orientations $\theta_g, \theta_m, \theta_e$ of `B13` (gravity), `B02` (RTP magnetics), and `B12` (detrended elevation) at $\sigma \in \{2.0, 5.0\}\text{ px}$:
    - `cvdc_sin2_grav_elev_s2`, `cvdc_sin2_grav_elev_s5`: $\sin^2(\theta_g - \theta_e)\,\log(1 + |\nabla B_{13}|_\sigma |\nabla B_{12}|_\sigma)$
    - `cvdc_sin2_rtp_elev_s2`, `cvdc_sin2_rtp_elev_s5`: $\sin^2(\theta_m - \theta_e)\,\log(1 + |\nabla B_{02}|_\sigma |\nabla B_{12}|_\sigma)$
    - `cvdc_pot_align_discord`: $\cos^2(\theta_g - \theta_m)\,\sin^2(\theta_g - \theta_e)\,\log(1 + |\nabla B_{13}|_3 |\nabla B_{02}|_3)$
- **Subsurface Potential-Field Curvature, Analytic Tilt & Steger Crests (`7` features):**
  - `cvdc_grav_lap_abs_s2`, `cvdc_grav_lap_abs_s5`: $\log(1 + |\nabla_h^2 B_{13,\sigma}|)$ at $\sigma \in \{2.0, 5.0\}\text{ px}$
  - `cvdc_grav_crest_s2`, `cvdc_grav_crest_s4`: Positive principal negative Hessian ridge eigenvalue $\max(0, -\lambda_{\min}(H_\sigma(B_{05})))$ at $\sigma \in \{2.0, 4.0\}\text{ px}$
  - `cvdc_mag_tilt_abs`: $|\arctan(B_{09} / (B_{03}/100.0 + 10^{-3}))|$
  - `cvdc_mag_tilt_grad`: $|\nabla \arctan(B_{09} / (B_{03}/100.0 + 10^{-3}))|_{\sigma=2}$
  - `cvdc_mag_crest_s2`: $\max(0, -\lambda_{\min}(H_{\sigma=2}(\log(1 + B_{03}))))$
- **Hydrothermal Magnetite-Destruction Baffle, MT Residual & Transtensional Strain (`6` features):**
  - `pmdb_mag_trough_15px`: $\max(0,\; \overline{\log(1+B_{03})}_{\sigma=12} - \overline{\log(1+B_{03})}_{\sigma=2})$
  - `pmdb_baffle_grav_trough`: $\log(1 + B_{05}) \cdot \text{pmdb\_mag\_trough\_15px}$
  - `pmdb_cond_b15_resid`: `B17` minus global valid-footprint OLS linear fit on $[1,\; \log(1 + \max(0, B_{15}))]$ (evaluated inside each fold without labels; `B15/B17` are static unlabeled layers)
  - `pmdb_claycap_step_gate`: $\max(0, \text{pmdb\_cond\_b15\_resid}) \cdot \log(1 + 10\,B_{05}) \cdot (1 + \text{pmdb\_mag\_trough\_15px})$
  - `pmdb_transtension_index`: $\log(1 + \max(0, B_{07})) \cdot \max(0, B_{08}) / (B_{04} + 1.0)$
  - `pmdb_ns_ew_seam_guard`: $(|\partial_x B_{02}|_2 - |\partial_y B_{02}|_2) / (|\partial_x B_{02}|_2 + |\partial_y B_{02}|_2 + 10^{-6})$

### 2.3 `vctk` Group — Hypothesis Rank #2 (`VCTK`, `10` features, `erode = 16 px`)
- `vctk_valley_concav_s2`, `vctk_valley_concav_s4`: $\log(1 + \max(0, \nabla_\sigma^2 B_{12}))$ at $\sigma \in \{2.0, 4.0\}\text{ px}$
- `vctk_trans_slope_jump`: $\log(1 + |B_{19}(x + 4\hat{u}_e) - B_{19}(x - 4\hat{u}_e)|)$ along broad regional slope unit vector $\hat{u}_e = \nabla B_{12,\sigma=10}/|\nabla B_{12,\sigma=10}|$
- `vctk_thalweg_knick`: `vctk_valley_concav_s2 * log1p(B19) * (1.0 + vctk_trans_slope_jump)`
- `vctk_bilat_align_700m`, `vctk_bilat_align_1300m`: Bilateral cross-interfluve persistence $\min(M_{+L}, M_{-L})$ sampling `vctk_thalweg_knick` at offsets $\pm L \hat{t}_e$ ($\hat{t}_e \perp \hat{u}_e$) for $L \in \{7.0, 13.0\}\text{ px}$
- `vctk_slope_crest_s15`, `vctk_slope_crest_s35`: $\log(1 + \max(0, -\lambda_{\min}(H_\sigma(B_{19}))))$ at $\sigma \in \{1.5, 3.5\}\text{ px}$
- `vctk_scarp_prominence`: $B_{19} / (\overline{B_{19}}_{\sigma=12} + 0.25)$
- `vctk_cover_regime_b15`: $\log(1 + \max(0, B_{15,\sigma=4}))$

### 2.4 Stage-2 Nested Cross-Fitted Axial-Bridge OOF (`12` features per fold in `e2` & `e3`)
- Within each outer `v3` fold `f`, `fold["train"]` is partitioned into `3` spatially contiguous `60 px` (`6 km`) checkerboard/strip folds (`((y // 60) + (x // 60)) % 3`) to generate strictly out-of-sample inner Stage-1 predictions for both:
  1. **Full Stage-1 specialist (`34` static features)**, and
  2. **Pure-Subsurface Stage-1 specialist (`21` features strictly free of `B12` and `B19`: `base_grad_b02, base_grad_b13, base_grad_b14, base_slope_b05` + `17` `B12`-free / non-contour subsurface features or the `13` pure potential-field/MT/strain features)**. Specifically, the Pure-Subsurface specialist uses the **`17` strictly `B12/B19`-free features** (`base_grad_b02`, `base_grad_b13`, `base_grad_b14`, `base_slope_b05`, `cvdc_grav_lap_abs_s2`, `cvdc_grav_lap_abs_s5`, `cvdc_grav_crest_s2`, `cvdc_grav_crest_s4`, `cvdc_mag_tilt_abs`, `cvdc_mag_tilt_grad`, `cvdc_mag_crest_s2`, `pmdb_mag_trough_15px`, `pmdb_baffle_grav_trough`, `pmdb_cond_b15_resid`, `pmdb_claycap_step_gate`, `pmdb_transtension_index`, `pmdb_ns_ew_seam_guard` — verified bitwise `0.0` change under arbitrary perturbations of `B12` and `B19`!).
- On each Stage-1 probability map $P \in \{P_{\text{full}}, P_{\text{sub}}\}$, extract `6` directional axial-bridge features across `8` orientations ($0^\circ, 22.5^\circ, \dots, 157.5^\circ$):
  1. `s2_*_prob`: $P$
  2. `s2_*_axial_600m`: $\max_\theta \overline{P}_{\theta, L=11\text{px}}$
  3. `s2_*_aniso_600m`: $\max_\theta \overline{P}_{\theta, 11\text{px}} - \min_\theta \overline{P}_{\theta, 11\text{px}}$
  4. `s2_*_relay_900m`: $\max_\theta \min(\overline{P}_{+\theta, [3..9]\text{px}},\; \overline{P}_{-\theta, [3..9]\text{px}})$
  5. `s2_*_crest`: $\max(0, -\lambda_{\min}(H_{\sigma=1.8}(P)))$
  6. `s2_*_prom`: $P - \overline{P}_{\sigma=10}$
- Outer Stage-2 fits `HGB_full` (`34 + 12 = 46` features) and `HGB_sub` (`17 + 6 = 23` strictly `B12/B19`-free features) on `fold["train"]`, blending their predicted probabilities on `fold["region"]` as `0.78 * P2_full + 0.22 * P2_sub`.

---

## 3. Frozen Hyperparameters, Holdout Protocol & Three Experiments

- **Shared holdout instrument (`vendor/gems57` unmodified):**
  - Folds: `vendor/gems57/spatial.py::folds(catalogue, footprint, buffer_px=80)` (`label-blind-quadrants-v3-feature-buffered`, `60,988` withheld positives).
  - Evaluator: `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `alpha=0.2, beta=0.8, R=300 m`, `1,000`-draw paired `20 km` spatial-block bootstrap, `SEED = 20261029`).
  - Leakage canary (Protocol Rule 4): Every static feature and every Stage-2 OOF feature must achieve symmetric ROC AUC `max(AUC, 1 - AUC) <= 0.90` on every fold; any breach stops the lane immediately.
- **Frozen `HistGradientBoostingClassifier` parameters:**
  - `max_iter=220, learning_rate=0.055, max_leaf_nodes=31, min_samples_leaf=80, l2_regularization=2.0`, `NEG_PER_POS = 6`, bagged over `3` seeds (`20261029, 20261030, 20261031`) for outer Stage-1/Stage-2 and `1` seed (`20261029`) for inner Stage-1 OOF.
- **Total dot budget:** `BUDGET = 37,654` (`allocate(37_654, quadrant_areas)` in holdout; exact `37,654` on full footprint).
- **Matched `v3`-fold controls:**
  1. `control_s25_fabric_e2`: Incumbent `S25-FABRIC E2` (`0.147741` on `v3` folds; recomputed or verified identically on the exact same `v3` folds and budgets).
  2. `control_oof_base`: `6`-feature `base` 3-seed bagged OOF HGB + greedy NMS (`3.05 px` collar/spacing).
  3. `control_gravgrad`: Static `base_grad_b13` + greedy NMS (`3.05 px` collar/spacing).
- **Three Frozen Candidate Experiments (strictly `3` total):**
  - **`e1` (`cvdc_e1_stage1_nms`):** `34`-feature (`base + cvdc + vctk`) 3-seed bagged Stage-1 stitched OOF surface + `emit_dots_nms(collar_px=3.05, min_spacing_px=3.05)`. Pure test of new geology vs `control_s25_fabric_e2` and `control_oof_base`.
  - **`e2` (`cvdc_e2_stage2_submod`):** `Stage-2` (`0.78 * Full + 0.22 * PureSub`) stitched OOF surface + `emit_dots_celf_submodular(collar_px=3.05, min_spacing_px=3.05, uniqueness_cap=None)`. Tests nested Stage-2 axial trace bridging + exact `300 m` kernel submodular placement.
  - **`e3` (`cvdc_e3_stitched_uniq_submod`):** Same `Stage-2` stitched OOF surface + **far-field near-catalogue halo relief** (`d_vis` soft weight ramp $w_{\text{far}}(d) = 0.55 + 0.45\,\min(1, \max(0, (d - 3.05)/6.95))$ over `3.05–10.0 px`, `collar_px=3.05`) + **hard `<= 64%` 3-px dot-overlap uniqueness caps** across every competitive non-blanket reference raster (`<= 90,000` positive pixels across frozen registry + 9 focus leaders + `docs/downloads` + 108 LFI anchors).
- **Frozen Packaging & Selection Rule:**
  - **No in-sample full-catalogue refit (`IR-91-S17-LFTG-01` fix):** Final full-map packaging emits strictly from the **stitched 4-fold spatially-blocked OOF surface** (`oof_surface`) with `g.catalogue` collar (`> 3.05 px`), never refitting trees on `100%` of `existing_faults.tif`.
  - **Candidate selection across `{e1, e2, e3}`:** Among arms whose paired `95%` bootstrap CI lower bound vs `best_comparable_control` is `> 0`, select the highest-`HOLDOUT-DTI` arm whose packaged `37,654`-dot emission passes competitive non-blanket uniqueness (`<= 70%` 3-px overlap across all references with `<= 90,000` positive pixels and `|Spearman| <= 0.90` on both pre-placement surface and final dots); if none qualifies, select highest `HOLDOUT-DTI`.
  - **Fail-closed Promotion Gate (`verdict` & `ok_to_submit`):** `promote` (`ok_to_submit = True`) requires ALL of: (1) canary pass (`<= 0.90`), (2) paired `HOLDOUT-DTI` 95% CI `> 0` vs `best_comparable_control`, (3) validator pass (`[0, 1]`, finite, exact `EPSG:32611` grid, zero on-catalogue dots), AND (4) literal Rule 1 pass (`|Spearman| <= 0.90` and `<= 70%` 3-px dot overlap across **all** registry witnesses including dense calibration lattices). Because `calib_r13lattice_00904.tif` (`206,895` dots) forces `>= 82.341849%` literal 3-px overlap at `37,654` dots (`IR-8E8-01`) and selector review is separate, any literal lattice breach keeps `verdict = "negative"`, `ok_to_download = True` (`research only`), and `ok_to_submit = False` fail-closed.
