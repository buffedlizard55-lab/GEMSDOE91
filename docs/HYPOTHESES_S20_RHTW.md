# Session 20 (`S20-RHTW`) Preregistered Geological Hypotheses & 3-Experiment Protocol

**Repository:** `buffedlizard55-lab/GEMSDOE91` · **Branch:** `arena/06420fd7-gemsdoe91`  
**Preregistration Timestamp (UTC):** `2026-10-26T00:50:00Z` (frozen **before** writing or fitting any `S20-RHTW` model)  
**Method Lane (`S20-RHTW`):** *Riesz-Harmonic Native Gravity-Magnetic Tensor Worm, Strike-Guided Hydrothermal Geothermometer Upflow & Pluvial-Decontaminated Dual-Specialist OOF Submodular Hierarchy*  
**Lane Assignment Status:** `lane.assigned = false` (no pasted method paragraph was supplied below Rule 1 in the prompt; autonomous research execution spends `0` weekly submission slots per Rule 6).

---

## 1. Ranked Shortlist of 5 Untried Candidate Geological Hypotheses (`H20-1` .. `H20-5`)

All 5 candidate hypotheses are ranked **prior to implementation** by expected Distance-Weighted Tversky Index (`DTI`) gain per unit of engineering & runtime cost under our sandbox constraints (`2` CPUs, `3.8 GiB` RAM, `<= 3` experiments, `<= 2 hours`).

| Rank | ID | Hypothesis Name | Target Layers (1-Based GDAL Bands & Verified Units) | Expected `HOLDOUT-DTI` Gain (`I2` `11,321` pos) | Impl. Cost | Selected in `S20-RHTW`? |
|---:|---|---|---|---|---|---|
| **1** | **`H20-1`** | **Riesz-Harmonic Native Gravity-Vector Marussi Tensor & Unit-Calibrated Verduzco Magnetic Tilt-Worm Concordance (`RHTW`)** | `B18` (`dG/dx` mGal/km), `B11` (`dG/dy` mGal/km), `B13` (`iso_grav_anom` mGal), `B15` (`depth_to_base_surf` m), `B02` (`rtp` nT), `B14` (`tmi` nT), `B03/200` (`tmi_hg` nT/m), `B09` (`tmi_vg` nT/m) | `+0.014` to `+0.024` | Low (`~25 s` FFT/Gaussian, `<600 MB` RAM) | **YES (`E1, E2, E3`)** |
| **2** | **`H20-2`** | **Strike-Guided Hydrothermal Geothermometer Disequilibrium & Transtensional Coulomb Conduit Inversion (`HSGD`)** | `gdr_wellspring_in_footprint.csv` (`row, col, temp_c, geothermquartz_c, geothermchalc_c, geothermcat_c`; `dist_known_fault_px` **banned**), `B17` (`cond_surf`), `B06` (`tc` nGy/h), `B04/B07/B08` (strain), `B10/B16` (seismicity) | `+0.004` to `+0.010` | Low (`~8 s`, `<250 MB` RAM) | **YES (`E2, E3`)** |
| **3** | **`H20-3`** | **Pluvial Paleoshoreline-Decontaminated Openness/Breakline Dual-Specialist Two-Stage OOF & `300 m` Submodular CELF (`PDOS`)** | `B12` (`det_elev`), `B19` (`det_elev_slope`), `B15` (`depth_to_base_surf`), `B18/B11` (normal gravity throw), `M_full` + `B12/B19`-blind `M_sub` OOF specialists | `+0.008` to `+0.015` | Medium (`~6 min` across 4 folds, `<850 MB` RAM) | **YES (`E1, E2, E3`)** |
| **4** | **`H20-4`** | **Fold-Safe Visible-Only Anisotropic Fracture-Mechanics Tip Wing-Crack & En-Echelon Relay Bridge Stress Prior (`FTRS`)** *(paired vs Desk-Scoped 1m/10m USGS 3DEP Fluvial $\chi/k_{sn}$)* | `visible` fault mask strictly inside each fold (`0` access to `truth`); desk-scoped external upgrade: USGS 3DEP 1/3 arc-sec & 1m LiDAR (`https://www.usgs.gov/3dep`, `CC0`) | `+0.008` to `+0.018` (`FTRS`) / `+0.015+` (`3DEP`) | Low (`FTRS`, `~10 s`/fold); External `3DEP` blocked by sandbox host allowlist | **`FTRS` in `E3`; `3DEP` documented** |
| **5** | **`H20-5`** | **3D Magnetotelluric (`MT`) Sub-Playa Conductive Clay-Cap Curtain & Sentinel-1 InSAR LOS Step (`MT-INSAR`)** | USGS Great Basin 3D MT resistivity cubes (`DOI: 10.5066/P9TWT2LU`, `CC0`) at `0.5, 1.5, 3.0, 5.0 km` + EarthScope ARIA InSAR LOS velocity | `+0.006` to `+0.014` | High (external `ScienceBase` / `ASF` hosts outside sandbox allowlist) | **Deferred (documented w/ DOIs)** |

---

### Detailed Specification of Each Hypothesis

#### `H20-1` (Rank 1): Riesz-Harmonic Native Gravity-Vector Marussi Tensor & Unit-Calibrated Verduzco Magnetic Tilt-Worm Concordance (`RHTW`)
- **Specific layers named:** `Band 18` (`iso_grav_anom_hg` = true native $\partial_x g$ in `mGal/km`), `Band 11` (`iso_grav_anom_vg` = true native $\partial_y g$ in `mGal/km`), `Band 13` (`iso_grav_anom`), `Band 15` (`depth_to_base_surf`), `Band 02` (`rtp`), `Band 14` (`tmi`), `Band 03` (`tmi_hg` converted via `/ 200.0` to `nT/m`), `Band 09` (`tmi_vg` in `nT/m`).
- **Physical signature & mathematical transform:**
  1. Reconstruct the exact 3D harmonic vertical gravity derivative $G_z(x,y; z)$ at upward-continuation heights $z \in \{0, 300, 900\}\text{ m}$ from the pre-resampled vector $(\text{B18}, \text{B11})$ via the 2D Riesz wavenumber transform:
     $$\widehat{G_z}(k_x, k_y; z) = \frac{-i k_x \widehat{\text{B18}}(k_x, k_y) - i k_y \widehat{\text{B11}}(k_x, k_y)}{\sqrt{k_x^2 + k_y^2}} e^{-z\sqrt{k_x^2 + k_y^2}}, \qquad \theta_G(z) = \arctan\!\left(\frac{G_z(z)}{\sqrt{G_x(z)^2 + G_y(z)^2 + \epsilon^2}}\right).$$
  2. Extract the **Horizontal Marussi Curvature Tensor** $M_G = \nabla_h (\text{B18}, \text{B11})$ principal ridge eigenvalue $\lambda_{\max}(M_G)$, multi-depth Cooper-Miller tilt-worm crest $|\nabla_h \theta_G(z)|$ (`cos(theta_G)` contact proximity), and **up-dip listric footwall migration** shifting deep (`900 m`) gravity contact phase up-dip by $\Delta x_{\text{px}} = \text{clip}(0.0055 \cdot \text{B15}, 0, 4.5)$ along $-\nabla_h \text{B15}$.
  3. Destripe E–W flight-line corrugation from `Band 02` (`rtp`), compute multi-depth RTP tilt-worm crests ($z \in \{150, 600\}\text{ m}$) plus unit-consistent Verduzco TMI tilt $\theta_M = \arctan(\text{B09} / (\text{B03}/200 + \epsilon))$ and its horizontal worm gradient $|\nabla_h \theta_M|$.
  4. Compute **2nd-order nematic strike-order concordance** $R_{\text{nem}} = \left|\sum_{p \in \{G, M, B\}} w_p e^{2i\psi_p}\right| / \sum_p w_p$ across Gravity Riesz-worm strike $\psi_G$, RTP worm strike $\psi_M$, and Basement-depth step strike $\psi_B$.
- **Why it catches faults missing from the USGS/INGENIOUS catalogue:** Sub-alluvial range-front splays, basin-interior horst/graben boundaries, and step-over transfer faults lack surface scarps (`Band 15 > 200 m`), so aerial-photo mapping missed them, yet their cumulative Cenozoic throw (`200–2,500 m`) creates sharp, strike-aligned density and susceptibility steps directly resolved by harmonic Riesz/Verduzco worms.
- **How it differs from repo implementations:** Eliminates both the `arctan(B11/|B18|)` gradient-azimuth bug (`IR-91-S13-01`) and `hgbr18.py`'s `B04/B05/B09` band-misidentification regression (`IR-91-S20-01`), reconstructing true harmonic $G_z$ from native pre-interpolated `(B18, B11)` for the first time in `GEMSDOE91`.
- **Named non-fault mimic:** Unfaulted Mesozoic granitoid pluton margins, Tertiary caldera ring dikes, and dipping volcanic-sedimentary unconformities.
- **External data obtainability:** Uses only pinned `gems-geodawn-numerical-features.tif` (`CC0 1.0` / `CC-BY-4.0`).

#### `H20-2` (Rank 2): Strike-Guided Hydrothermal Geothermometer Disequilibrium & Transtensional Coulomb Conduit Inversion (`HSGD`)
- **Specific layers named:** `data/external/gdr_wellspring_in_footprint.csv` (`27,092` wells/springs from DOE GDR 1391 `DOI: 10.15121/1881483`, reading strictly `row, col, temp_c, geothermquartz_c, geothermchalc_c, geothermcat_c`; `dist_known_fault_px` is **hard-blocked in code**), `Band 17` (`cond_surf`), `Band 06` (`tc` GeoDAWN radiometric Total Count), `Band 04` (`geod_2ndinv`), `Band 07` (`geod_shearrate`), `Band 08` (`geod_dilaterate`), `Band 10` (`deq_n100a15`), `Band 16` (`ieq_n100a15`).
- **Physical signature & mathematical transform:**
  1. Rasterize three label-blind hydrothermal source fields at `100 m`: excess outflow temperature $\Delta T_{\text{out}} = (T_{\text{meas}} - 16^\circ\text{C})_+$, silica/cation reservoir equilibration temperature $T_{\text{res}} = \max(T_{\text{qtz}}, T_{\text{chalc}}, T_{\text{cat}} - 25^\circ\text{C})$, and **chemical disequilibrium** $\Delta T_{\text{diseq}} = (T_{\text{res}} - T_{\text{meas}})_+$ (which peaks where deep `120–220 °C` fault-hosted fluids leak into cool shallow aquifers).
  2. Replace isotropic circular Gaussian smearing with **directional bank-of-strikes anisotropic diffusion** ($\sigma_\parallel = 14\text{ px}$, $\sigma_\perp = 3.5\text{ px}$ across 6 strike bins) steered along the local subsurface Riesz-gravity / RTP structural strike $\psi_{\text{struct}}$, and multiply by **transtensional Coulomb potency** ($z_+(\text{B07}) \cdot z_+(\max(\text{B08}, 0))$) and **`Band 17` (`cond_surf`) clay-cap lateral gradient**.
- **Why it catches faults missing from the USGS/INGENIOUS catalogue:** ~75% of Great Basin geothermal systems are blind and localize in dense, short-segment fault step-overs, terminations, and intersections that maintain open fracture permeability without generating tall surface scarps (Faulds & Hinz, 2015).
- **How it differs from repo implementations:** Prior sessions (`dd_vtc_pu.py`, `hgbr18.py`, `svhf19.py`) used isotropic Gaussian kernels around wells/springs, creating circular playa bullseyes (`GEMSDOE24 gvc1 = 0.0859`). `H20-2` projects geothermometer disequilibrium strictly along subsurface geophysical fault strikes and couples it to transtensional strain & clay-cap edges.
- **Named non-fault mimic:** Down-gradient lateral thermal outflow plumes in permeable Quaternary alluvial-fan paleochannels and high-salinity playa evaporite brines elevating `Na-K-Ca` cation ratios.
- **External data obtainability:** Already restored and SHA-256-pinned `gdr_wellspring_in_footprint.csv` (`https://gdr.openei.org/submissions/1391`, `CC-BY-4.0`).

#### `H20-3` (Rank 3): Pluvial Paleoshoreline-Decontaminated Openness/Breakline Dual-Specialist Two-Stage OOF & `300 m` Submodular CELF (`PDOS`)
- **Specific layers named:** `Band 12` (`det_elev`), `Band 19` (`det_elev_slope`), `Band 15` (`depth_to_base_surf`), `Band 18 & 11` (normal-projected subsurface gravity throw), `Band 06` (`tc`).
- **Physical signature & mathematical transform:**
  1. Compute multi-scale **Topographic Openness Differential** ($\Phi_+ - \Phi_-$ across 8 azimuths at radii $r \in \{3, 7, 14\}\text{ px}$; Yokoyama et al., 2002), **Local Relief Model breakline dipole** (Hesse, 2010), and **piedmont scarp flexure** (`slope step` at the `Band 15` bedrock-to-basin transition).
  2. **Pluvial Paleoshoreline Decontamination:** Compute unit scarp-normal vector $\hat{\mathbf{n}}_{\text{topo}} = \nabla_h \text{B12} / (|\nabla_h \text{B12}| + \epsilon)$ and measure cross-scarp subsurface gravity throw $|\mathbf{G}_h \cdot \hat{\mathbf{n}}_{\text{topo}}|$ plus `Band 15` normal basement gradient. Scarps sitting along closed basin-margin elevation bands with near-zero cross-scarp gravity/basement throw are flagged via `pluvial_shoreline_mimic_index` so `M_full` rejects Lake Lahontan (`~1,332 m`) & Lake Bonneville (`~1,552 m`) wave-cut benches!
  3. **Cross-Fitted Dual-Specialist Two-Stage Architecture (`M_full` + `Band 12/19`-Blind `M_sub`):**
     - `M_sub` uses **only subsurface/geophysical/hydrothermal features** (`0.0` bitwise dependence on `Band 12` and `Band 19`).
     - Stage-1 OOF posteriors feed a **12-azimuth Multi-Scale Oriented Line-Integral & Anisotropic Auto-Context** (`L = 900 m` and `1.7 km`) into Stage-2 OOF `HistGradientBoostingClassifier` specialists, pooled via **Asymmetric Cover-Gated Log-Odds Rescue**:
       $$\ell_{\text{pool}} = \ell_{\text{full}} + w_{\text{cover}}(\text{B15}, \text{B19}) \cdot \max\!\big(0,\, \ell_{\text{sub}}^{\text{aligned}} - \ell_{\text{full}}\big) + \alpha_{\text{worm}} C_{\text{worm}},$$
       and emitted at exact `N = 37,654` binary `{0, 1}` dots (`d_cat > 2.23 px` strict zero-dot collar) via **exact `300 m` triangular-kernel submodular expected-DTI CELF** from the **stitched 4-quadrant OOF surface** (`zero` in-sample memorization!).
- **Why it catches faults missing from the USGS/INGENIOUS catalogue:** Recovers both subtle degraded piedmont scarps (without triggering on pluvial shorelines) and completely flat buried intra-basin faults (via `M_sub` positive-part rescue), while packing dots at the exact `300 m` DW-Tversky kernel radius without hexagonal lattice artifacts.
- **Named non-fault mimic:** Pleistocene Lake Lahontan / Bonneville wave-cut benches, fluvial terrace risers, and longitudinal eolian sand dunes.

#### `H20-4` (Rank 4): Fold-Safe Visible-Only Anisotropic Fracture-Mechanics Tip Wing-Crack & En-Echelon Relay Bridge Stress Prior (`FTRS`) + Desk-Scoped USGS 3DEP 1m/10m Fluvial $\chi/k_{sn}$ Upgrade
- **Specific layers named:** Strictly `f["visible"]` inside each holdout fold (`existing_faults.tif` only on the final stitched OOF map; `f["truth"]` is **never** accessed), paired with local subsurface `RHTW` geophysical corroboration (`H20-1`). Desk-scoped external upgrade: seamless USGS 3DEP 1/3 arc-second (`~10 m`) & `1 m` LiDAR DEM (`https://www.usgs.gov/3dep`, `CC0 1.0`).
- **Physical signature & mathematical transform:** Extract skeleton endpoints and local tangent azimuth $\hat{\mathbf{t}}$ of `visible` fault segments (`>= 5 px` length), project **anisotropic Coulomb wing-crack / horse-tail tip lobes** (`300 m` to `2.2 km` ahead of fault tips within `±28°` opening cone) and **en-echelon relay-ramp step-over bridges** (between sub-parallel visible segments separated by `400 m–2.5 km`), strictly zeroed inside `d_vis <= 2.5 px` (`250 m` collar guard) and **gated multiplicatively by subsurface `M_sub` / `RHTW` geophysical support** so tip/relay lobes only fire where real geophysical continuation exists and `>= 58%` of dots remain in far-field (`>1 km`) basins!
- **Named non-fault mimic:** Erosional bedrock ridge spurs projecting beyond range-front fault terminations without subsurface fault continuation.

#### `H20-5` (Rank 5 — Desk-Scoped External Data Hypothesis): 3D Magnetotelluric (`MT`) Sub-Playa Conductive Clay-Cap Curtain & Sentinel-1 InSAR LOS Step
- **Specific layers named:** USGS Great Basin 3D MT Electrical Resistivity Models (`Peacock et al. 2020–2023`, `DOI: 10.5066/P9TWT2LU`, `CC0 1.0`) sliced at `0.5, 1.5, 3.0, 5.0 km` depth + EarthScope ARIA Sentinel-1 InSAR vertical/LOS velocity gradients (`CC-BY-4.0`).
- **Why deferred:** Outbound network access in this sandbox is restricted to `github.com`, `pypi.org`, and `registry.npmjs.org` (`www.sciencebase.gov` and `asf.alaska.edu` unreachable). Documented in `LIMITATIONS_AND_NEXT_STEPS.md` as Priority External Upgrade #2.

---

## 2. Preregistered 3-Experiment Budget & Frozen Selection Gate (Rules 1–6)

Strictly `3` experiments (`E1`, `E2`, `E3`) are preregistered against pinned incumbent `E0` (`OLC91/ISO91` baseline) and random floor `RND` on the unchanged shared evaluator `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`):

1. **`E1` (`RHTW + PDOS` Pure Geophysical + Geomorphic Dual-Specialist Two-Stage OOF + `300 m` Submodular CELF):**
   - `100%` catalogue-feature-free (`H20-1` + `H20-3`). Tests our unit-corrected Riesz-Harmonic gravity/magnetic worm + pluvial-decontaminated openness Dual-Specialist (`M_full` + `B12/19`-blind `M_sub` cover rescue) + 12-azimuth line-integral Stage-2 OOF GBDT.
2. **`E2` (`E1 + HSGD` Strike-Guided Hydrothermal Geothermometer & Transtensional Conduit):**
   - Still `100%` catalogue-feature-free (`H20-1` + `H20-2` + `H20-3`). Adds anisotropic strike-diffused GDR 1391 silica/cation geothermometer disequilibrium & outflow plumes gated by transtensional Coulomb strain and `B17` conductivity lateral steps.
3. **`E3` (`E2 + FTRS` Geophysically-Gated Fold-Safe Visible Tip/Relay Bridge Prior):**
   - Adds the geophysically-gated, fold-safe visible-only fracture-mechanics tip/stepover stress bridge (`>2.5 px` collar guard, bounded weight preserving far-field basin discovery).

### Evaluation & Promotion Rules (Frozen Before Any Fit)
- **Primary Holdout Instrument (`I2` — `vendor/gems57/holdout.py::buffered_component_draw(seed=20, hide_frac=0.20, buffer_px=3)`):** `11,321` withheld positive pixels across `606` buffered whole fault segments, `40 px` (`4 km`) LOQO training buffer, area-proportional `37,654` submodular CELF emission with `>2.23 px` strict collar, `1,000` paired `20 km` spatial-block bootstrap draws (`seed = 520810`). Comparable prior baseline: `E0 = 0.085260 HOLDOUT-DTI` (`[0.068962, 0.102856]`), `OLC91 E1 = 0.083186`, `ISO91 E1 = 0.068190`.
- **Secondary Diagnostic Holdout (`I1` — `gems91.isolated_holdout.isolated_component_draw(sep_px=5)`):** `11,911` withheld spatially isolated fault pixels (`>500 m` from any visible fault) to verify far-field isolated fault recovery (`comparable E0 = 0.093105`).
- **Blind Off-Catalogue Geological Control (`BLIND-SGMC-CONTROL`):** Evaluated at `>300 m`, `>500 m`, and `>1 km` from `existing_faults.tif` against `GEMSDOE32 R0` (`0.0888` at `>500 m`, `0.0829` at `>1 km`).
- **Rule 4 Single-Feature Canary Gate:** Every single static, hydrothermal, auto-context, and fold-safe visible tip/relay feature must achieve `symmetric_auc <= 0.90` (`max(AUC, 1 - AUC) <= 0.90`) both pooled and in every quadrant; any violation aborts immediately.
- **Rule 1 Uniqueness Gate:** Checked both **before placement** (`|Spearman rho| <= 0.90`) and **after placement** (`|Spearman rho| <= 0.90` and non-blanket `3-px` directed dot overlap `<= 0.70`) against every unique raster in `data/registry/`, `data/fleet_registry/`, `docs/downloads/`, and the 9 priority sites (`>110` unique rasters).
- **Winner Selection:** Select the arm among `{E1, E2, E3}` with the highest `I2 HOLDOUT-DTI` that passes Rule 4 (`canary <= 0.90`) and Rule 1 (`non-blanket overlap <= 0.70`, `|rho| <= 0.90`), emit its stitched 4-quadrant OOF full-map `-zeros.tif` + single-TIFF `-zeros.zip` via unchanged `vendor/gems57/submission_writer.py`, and report honest fail-closed `OK TO SUBMIT: NO` until separate human weekly-slot selector sign-off (Rule 6).
