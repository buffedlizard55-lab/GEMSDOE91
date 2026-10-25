# Preregistered Hypotheses — Session 18 (`S18-HGBR`)

- **Frozen Before Holdout Evaluation:** `2026-10-25T20:05:00Z`
- **Repository / Branch:** `buffedlizard55-lab/GEMSDOE91` (`arena/bba4efce-gemsdoe91`)
- **Lane Identifier:** `S18-HGBR` (Multi-Scale Anisotropic Hurst-Exponent / Variogram-Slope Break, Potential-Field Curvature-Bridge & Rank-Aligned Dual-Specialist Auto-Context)
- **Primary Evaluator:** `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `split_sha256 = c79f1acaf337fd548d0873d576a8a3c286d373ae2cb19cfce4464597d448d18a`, `60,988` withheld positive pixels across 4 label-blind spatial quadrants with `80 px` / `8.0 km` exclusion buffer, `1,000` paired `20 km x 20 km` spatial-cluster bootstrap draws, `alpha = 0.2`, `beta = 0.8`, `R = 300 m` triangular kernel).
- **Untouched Blind Off-Catalogue Controls:** USGS SGMC Great Basin concealed & structural faults (`data/external/derived_sgmc_faults_100m_u8.tif`) evaluated strictly outside `existing_faults.tif` at `> 300 m` (`62,122` pixels), `> 500 m` (`56,822` pixels, registration-offset free), and `> 1 km` (`48,389` pixels).
- **Experiment Budget (`Rule 6`):** At most `3` preregistered experiments (`hgbr_e1`, `hgbr_e2`, `hgbr_e3`) within the `2`-hour wall-clock budget; `slots_used = 0` (no live DrivenData submission slot spent automatically).

---

## 1. Forensic Motivation from Live Leaderboard & 22-Raster Fleet Calibration

New user-reported live DrivenData scores (`2026-10-25`) provide decisive empirical feedback on Session 17:
- `GEMSDOE91` `gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros`: **`0.1823` `USER-REPORTED`** (`0.188596 HOLDOUT-DTI` on `gems57-pooled-hide-v2`) — **new all-time live best in `GEMSDOE91`**, beating `S17-CWPC` (`0.1367` `USER-REPORTED`, `0.122467 HOLDOUT-DTI`) by **`+0.0456` (`+33.4%`)** and `S13-PTHA` (`0.1325` `USER-REPORTED`, `0.179206 HOLDOUT-DTI`) by **`+0.0498` (`+37.6%`)**.
- Across all `22` scored fleet rasters on disk (`data/fleet_registry/` + `docs/downloads/`), evaluating exact `vendor/gems57/metric.py::dti_exact` against `existing_faults.tif` and untouched off-catalogue USGS SGMC faults reveals a **Two-Factor Live DTI Law**:
  1. **Localizer Precision (`gems57-pooled-hide-v2`):** `S17-LFTG` (`0.1886 HOLDOUT-DTI`) beat `S17-CWPC` (`0.1225 HOLDOUT-DTI`) by `+0.0661` on label-blind holdout and `+0.0456` on the live leaderboard despite placing only `31.5%` (`11,871`) of its dots at `d(existing_faults) > 1 km`.
  2. **Far-Field Off-Catalogue Allocation (`FF > 1 km` & `SGMC > 1 km`):** Every binary ~37.6k–40.2k dot submission scoring `>= 0.2376` on the live leaderboard (`GEMSDOE32 R0` `0.2778`, `GEMSDOE36` `0.2750`, `GEMSDOE28` `0.2710`, `GEMSDOE28 solo` `0.2708`, `GEMSDOE49` `0.2376`) places **`65.4%–69.8%`** of its dots at `d(existing_faults) > 1 km` and achieves **`SGMC > 1 km >= 0.0805`**. By contrast, `S17-LFTG` (`FF > 1 km = 31.5%`, `SGMC > 1 km = 0.0399`) and `S17-CPAD` (`FF > 1 km = 43.9%`, `SGMC > 1 km = 0.0513`) refit their final 4-quadrant full-map models **in-sample** on `100%` of `existing_faults.tif` (`IR-91-S17-LFTG-01`), causing tree ensembles to memorize catalogued faults and trap `56.1%–68.5%` of all `37,654` dots inside the `305 m–1,000 m` auto-context halo around already-known faults.

Furthermore, `LIMITATIONS_AND_NEXT_STEPS.md` identified three concrete technical bottlenecks to resolve in Session 18:
1. **Priority #1 (`docs/REVIEW-S18-20261025.md` H1):** Implement **Multi-Scale Anisotropic Hurst-Exponent / Variogram-Slope Break & Cross-Scale Roughness Step (`S18-HGBR`)** to detect fractal cataclastic damage zones and buried piedmont fault-line scarps where first-order gradients are smoothed by diffusive sheetwash or deep cover.
2. **Priority #2 (`IR-91-S17-01`):** Eliminate cross-split Stage-1 tail-variance drift between 2-quadrant pairwise models (`pair_ab`) and 3-quadrant OOF models (`oof_q`) by applying **per-quadrant empirical quantile / rank-Beta alignment** before computing `spac_coda` spatial auto-context.
3. **Priority #3 (`IR-91-S17-02` & `IR-91-S17-LFTG-01`):** Replace arithmetic specialist blending with **Cover-Conditioned Log-Odds Specialist Pooling + Hurst-Tensor-Phase Crest Sharpening**, and emit the full-map `37,654`-dot raster from the **stitched 4-fold Out-of-Fold (`OOF`) Stage-1 + Stage-2 surface** with visible-catalogue halo de-crowding (zero in-sample memorization of `existing_faults.tif`).

---

## 2. Five Novel Candidate Geological Hypotheses (`H18-1` – `H18-5`)

### H18-1 (`S18-HGBR` — Top Candidate Implemented in Session 18): Multi-Scale Anisotropic Hurst-Exponent / Variogram-Slope Break & Cross-Scale Roughness Step
- **Specific Layers Involved:**
  - Subsurface (100% `Band 12` / `Band 19` free): `Band 13` (`iso_grav_anom`), `Band 2` (`rtp`), `Band 15` (`depth_to_base_surf`), `Band 17` (`cond_surf`), `Band 4` (`th`), `Band 5` (`k`).
  - Surface scarp branch (isolated in `STRICT_TOPO_FEATURE_NAMES`, excluded from Pure-Subsurface Specialist): `Band 12` (`det_elev`), `Band 19` (`det_elev_slope`).
- **Physical Signature Targeted:**
  - Intact crystalline/sedimentary blocks and diffusive alluvial fans exhibit smooth self-affine scaling with high local Hurst exponent $H(x) \approx 0.75\text{--}0.95$ ($S_2(\tau) = \langle |\Delta_\tau^2 F|^2 \rangle^{1/2} \propto \tau^H$). Brittle fault damage zones (`200 m–800 m` wide breccia, Riedel shear lenses, and anastomosing fracture corridors) inject high-wavenumber variance across lags $\tau \in \{100, 200, 400, 800\}\text{ m}$, producing a sharp **local Hurst-exponent deficit** ($1 - H(x)$) and strong **strike-versus-dip Hurst anisotropy** ($H_{\parallel}(\psi) - H_{\perp}(\psi) > 0$: smooth and persistent along fault strike $\hat{s}$, rough and step-discontinuous across fault normal $\hat{n}$).
  - On degraded Quaternary piedmont scarps (`Band 12`), fine-scale diffusive sheetwash smooths the `100–200 m` scarp face ($H^{\text{fine}} \to 0.85$) while the `400–800 m` vertical throw step remains sharp ($H^{\text{coarse}} \to 0.35$), creating a positive **cross-scale Hurst break** $\Delta H_{\text{elev}} = H^{\text{fine}} - H^{\text{coarse}}$.
- **Why It Catches Unmapped/Concealed Faults Rather Than Catalogued Ones:**
  - The USGS/INGENIOUS `existing_faults.tif` catalogue was compiled primarily from aerial-photo scarp mapping and high-amplitude first-derivative lineaments. Concealed Basin-and-Range faults beneath `100–500 m` of pediment veneer and distributed intra-basin accommodation zones lack a single knife-edge first-derivative cliff, but their `200–800 m` cataclastic damage halo and hydrothermal magnetite-destruction / illite-alteration fracture network produce a coherent multi-scale variogram-slope break across gravity (`Band 13`), destriped RTP magnetics (`Band 2`), basement depth (`Band 15`), and K/Th radiometrics (`Band 5 / Band 4`).
- **How It Differs from Existing Repo Implementations:**
  - Every prior module (`dd_vtc_pu`, `mhtr_coda`, `spac_coda`, `ptha`, `hvdc`, `scgf15`, `pgrd`, `cpad17`, `lftg17`, `cwpc17`, `cgrd17`, `cdsc17`, `eulr17`) computes single-scale or ratio-of-derivative amplitude/phase operators (Sobel gradients, Frangi Hessians, Cooper–Cowan $\theta$, Laplace $G_{zz}$, Riesz wavelets, Euler deconvolution). None computes the **log-log variogram / second-order structure-function scaling exponent $H(x)$**, **directional Hurst anisotropy $H_{\parallel} - H_{\perp}$**, or **cross-scale fine-minus-coarse Hurst break $\Delta H$**.
- **Named Non-Fault Mimic & Suppression:**
  - *Mimic:* Isotropic volcanic talus aprons, caldera ring rubble, and cardinal `N-S` / `E-W` airborne survey seam noise (`Band 2`, `Band 6`, `Band 14`), which lower isotropic $H(x)$.
  - *Suppression:* Cardinal flight-line spectral notch destriping is applied before variogram computation, and isotropic rough terrain is rejected by requiring positive directional Hurst anisotropy $H_{\parallel}(\psi) - H_{\perp}(\psi) > 0$ aligned with the 3-D Laplace gravity / magnetic strike $\psi$.
- **Official Literature & Free Data Sources:**
  - Mandelbrot (1985), *Self-affine fractals and fractal dimension*, Physica Scripta 32(4):257–260: https://doi.org/10.1088/0031-8949/32/4/001
  - Savage & Brodsky (2011), *Collateral damage: Evolution with displacement of fracture distribution and secondary fault strands in fault damage zones*, JGR Solid Earth 116(B3): https://doi.org/10.1029/2010JB007665
  - Official competition 19-band GeoDAWN stack (`data/bridge/gems-geodawn-numerical-features.tif`, USGS ScienceBase: https://doi.org/10.5066/P9XBBBUU).

### H18-2: Potential-Field Curvature-Bridge & Up-Dip Listric Fault-Trace Migration
- **Specific Layers Involved:** `Band 13` (`iso_grav_anom`), `Band 15` (`depth_to_base_surf`), `Band 2` (`rtp`), `Band 4` (`th`), `Band 5` (`k`) — 100% `Band 12` / `Band 19` free.
- **Physical Signature Targeted:**
  - Normal faults in the Great Basin dip $45^\circ\text{--}60^\circ$ basinward (often listric into mid-crustal detachments). Consequently, the maximum horizontal gravity gradient and 600-m upward-continued Wijns $\cos\theta_{600\text{m}}$ crest are systematically displaced $d_{\text{shift}} = z_{\text{base}} \cot\delta \approx 200\text{--}700\text{ m}$ into the hanging wall relative to the sub-alluvial fault trace. By computing the vector offset between shallow (`200 m`) and deep (`600 m`) Laplace gravity edge phases scaled by local `Band 15` (`depth_to_base_surf`), we migrate the deep potential-field inflection **up-dip** back to the true sub-crop trace, and combine it with K/Th (`Band 5 / Band 4`) radiometric metasomatic leakage along the footwall damage zone.
- **Why It Catches Unmapped/Concealed Faults Rather Than Catalogued Ones:**
  - Deeply buried basin-interior faults (`Band 15 > 400 m`) fail the competition's strict `R = 300 m` triangular evaluation kernel when dots are placed directly on the uncorrected hanging-wall gravity gradient maximum (`300–600 m` down-dip of the true trace). Up-dip migration restores the trace within `< 200 m` of the true fault sub-crop.
- **How It Differs from Existing Repo Implementations:**
  - `lftg17.py` (`lftg17_listric_dip_asymmetry`) measured scalar shallow-minus-deep $\cos\theta$ difference at the same pixel $(y, x)$ without migrating the deep field spatially up-dip along the local dip-azimuth vector $\hat{n}_{\text{updip}}$ or coupling it with `Band 5 / Band 4` K/Th adularia-illite alteration steps.
- **Named Non-Fault Mimic & Suppression:**
  - *Mimic:* Sloping granitic pluton margins and tilted depositional pinch-outs.
  - *Suppression:* Gated by Pedersen–Rasmussen quasi-2D gravity tensor purity $Q_{\text{2D}} = 1 - |I|$ and anisotropic Hurst damage deficit.
- **Official Literature & Free Data Sources:**
  - Grauch & Hudson (2007), *Aeromagnetic anomalies over faulted strata*, Leading Edge 26(11): https://doi.org/10.1190/1.2805760

### H18-3: Geodetic-Seismic Kostrov Strain Partitioning & Dilatational Coulomb Focusing
- **Specific Layers Involved:** `Band 7` (`geod_shearrate`), `Band 8` (`geod_dilaterate`), `Band 10` (`deq_n100a15`), `Band 16` (`ieq_n100a15`), `Band 13` (`iso_grav_anom`), `Band 9` (`gdr_vital_signs`), `data/external/gdr_wellspring_in_footprint.csv` — 100% `Band 12` / `Band 19` free.
- **Physical Signature Targeted:**
  - Active blind geothermal faults occur at the brittle transition between locked, high-shear-strain crustal blocks (`Band 7`, `Band 8`) and dilatational microseismic fracture swarms (`Band 10`, `Band 16`) accompanied by elevated chemical geothermometer disequilibrium ($\Delta T_{\text{Na-K-Ca}} - T_{\text{chalcedony}}$ from GDR well/spring chemistry). Combining the Kostrov seismic-to-geodetic coupling deficiency with local gravity-tensor strike $\psi_G$ and Hurst damage anisotropy isolates permeable transtensional fault tips.
- **Why It Catches Unmapped/Concealed Faults Rather Than Catalogued Ones:**
  - Over 75% of discovered and undiscovered Great Basin hydrothermal systems (e.g., Brady's, Desert Peak, McGinness Hills) lie in step-overs and accommodation zones where surface scarps break down into dense, unmapped minor fault meshes that release strain via microseismic swarms and fluid upwelling rather than single large surface-rupturing scarps.
- **How It Differs from Existing Repo Implementations:**
  - Resolves `IR-91-S14-01` (`Band 10` sign-inversion bug in legacy `ptha.py`) and couples Kostrov strain-rate partitioning directly with multi-scale Hurst damage anisotropy (`hgbr18_grav_rtp_hurst_sync`) and chemical geothermometer disequilibrium (`hgbr18_geotherm_hurst_conduit`).
- **Named Non-Fault Mimic & Suppression:**
  - *Mimic:* Broad regional GPS interpolation lobes (`> 25 km`) and mining-blast clusters.
  - *Suppression:* Restricted to local (`<= 800 m`) Hurst-anisotropic structural corridors with quasi-2D gravity tensor purity.
- **Official Literature & Free Data Sources:**
  - Faulds & Hinz (2015), *Structural settings of geothermal systems in the Great Basin*, World Geothermal Congress: https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11067.pdf
  - DOE Geothermal Data Repository (GDR) INGENIOUS Collection: https://gdr.openei.org/submissions/1590

### H18-4: Bi-Harmonic Thin-Plate Flexural Curvature & Differential Compaction Hinge
- **Specific Layers Involved:** `Band 15` (`depth_to_base_surf`), `Band 13` (`iso_grav_anom`), `Band 17` (`cond_surf`).
- **Physical Signature Targeted:**
  - Differential compaction of Neogene basin fill over buried basement fault scarps bends hanging-wall strata into a thin-plate flexural monocline whose fourth-order biharmonic operator $\nabla^4 z_{\text{base}}$ peaks along the buried fault hinge.
- **Why It Catches Unmapped/Concealed Faults:** Detects zero-scarp differential-compaction faults across flat playa floors.
- **How It Differs from Existing Repo Implementations:** Fourth-order biharmonic flexural operator vs second-order Hessian/Laplacian in `spac_coda` / `cgrd17`.
- **Named Non-Fault Mimic & Suppression:** Differential compaction over buried paleochannels; suppressed by gravity-magnetic strike concordance.

### H18-5: Multi-Azimuth Radon-Transform Lineament Persistence across Radiometric Ratio Channels
- **Specific Layers Involved:** `Band 3` (`u`), `Band 4` (`th`), `Band 5` (`k`), `Band 6` (`tc`).
- **Physical Signature Targeted:**
  - Sliding-window (`1.6 km`) localized Radon line-integral variance across ternary radioelement ratios (`K/Th`, `U/Th`, `U/K`) to trace leached fault-zone oxidation/reduction boundaries across pediment fans.
- **Why It Catches Unmapped/Concealed Faults:** Captures subtle geochemical alteration halos where mechanical throw is `< 1 m`.
- **How It Differs from Existing Repo Implementations:** Localized Radon line-integral projection across ternary radiometric ratios vs point gradients.
- **Named Non-Fault Mimic & Suppression:** Stratigraphic ash-flow tuff contacts; suppressed by requiring cross-cutting discordance with topographic contours.

---

## 3. Candidate Ranking by Expected DTI Gain vs Implementation Cost

| Rank | Hypothesis ID | Physical Mechanism | Primary Layers | Expected `HOLDOUT-DTI` Gain | Expected Live / Blind SGMC Gain | Implementation Cost | Session 18 Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **H18-1 + H18-2 + H18-3 (`S18-HGBR`)** | Multi-Scale Anisotropic Hurst-Exponent Break + Up-Dip Listric Migration + Geotherm-Strain Partitioning + Rank-Aligned Auto-Context + OOF Full-Map Emission | `B02, B04, B05, B07–B10, B12, B13, B15–B17, B19` + GDR CSV | **`+0.003` to `+0.008`** over `INCUMBENT-PTAC-LB` (`0.1942`) and beating `S17-CPAD E1` (`0.1982`) | **`+0.025` to `+0.040`** on Blind SGMC `> 500 m` / `> 1 km` via OOF full-map emission (`IR-91-S17-LFTG-01` fix) | Medium (`16` features in `src/gems91/hgbr18.py`, `< 450 MB` RAM) | **Selected & Implemented (`hgbr_e1`, `hgbr_e2`, `hgbr_e3`)** |
| **2** | **H18-4** | Bi-Harmonic Thin-Plate Flexural Curvature | `B13, B15, B17` | `+0.001` to `+0.003` | `+0.005` | Medium (sensitive to 4th-derivative grid noise) | Deferred to Session 19 |
| **3** | **H18-5** | Localized Radon Ternary Radiometric Lineaments | `B03, B04, B05, B06` | `+0.001` to `+0.002` | `+0.004` | High (sliding Radon transform compute cost) | Deferred to Session 19 |

---

## 4. Exact Preregistered Specification of `S18-HGBR` (`src/gems91/hgbr18.py`)

### 4.1 16 Novel Label-Blind `S18-HGBR` Features (`HGBR_FEATURE_NAMES`)
All 16 features are strictly local (`<= 1.2 km`), translation-invariant (zero coordinate polynomials or `> 2.5 km` regional bowls, `IR-91-S15-07`), and 100% independent of `existing_faults.tif` and any prior submission raster:
- **Cols `0..13` (14 features — 100% `Band 12` / `Band 19` free, included in both Full and Pure-Subsurface Specialists):**
  0. `hgbr18_grav_hurst_deficit`: Local multi-scale variogram-slope deficit $1 - H_{\text{grav}}(x)$ across $\tau \in \{100, 200, 400, 800\}\text{ m}$ on `Band 13` (`iso_grav_anom`).
  1. `hgbr18_rtp_hurst_deficit`: Local multi-scale variogram-slope deficit $1 - H_{\text{rtp}}(x)$ across $\tau \in \{100, 200, 400, 800\}\text{ m}$ on flight-line-destriped `Band 2` (`rtp`).
  2. `hgbr18_grav_hurst_anisotropy`: Directional Hurst-scaling anisotropy $H_{\parallel}(\psi_G) - H_{\perp}(\psi_G)$ on `Band 13` (`iso_grav_anom`).
  3. `hgbr18_rtp_hurst_anisotropy`: Directional Hurst-scaling anisotropy $H_{\parallel}(\psi_M) - H_{\perp}(\psi_M)$ on destriped `Band 2` (`rtp`).
  4. `hgbr18_grav_rtp_hurst_sync`: Multi-physics fractal-damage synchronization $\sqrt{\max(0, z(1-H_{\text{grav}})\cdot z(1-H_{\text{rtp}}))}\cdot \cos^2(\psi_G - \psi_M)$.
  5. `hgbr18_basement_hurst_step`: Local Hurst-scaling deficit on $\log(1 + \text{Band 15})$ weighted by Laplace gravity 2D purity $Q_{\text{2D}}$.
  6. `hgbr18_tensor_theta_hurst_crest`: Concordance of 3-D Laplace gravity $\cos\theta_{200\text{m}}$, Cooper–Cowan phase $\theta_{\text{grav}}$, and directional Hurst anisotropy $H_{\parallel} - H_{\perp}$.
  7. `hgbr18_cond_hurst_baffle`: `Band 15`-deconfounded $\log(1 + \text{Band 17 cond\_surf})$ cross-strike variogram break (zero DEM/playa dependence).
  8. `hgbr18_radiometric_k_th_fault_leak`: Destriped potassium-to-thorium ratio (`Band 5 / (Band 4 + eps)`) cross-strike step concordant with `hgbr18_rtp_hurst_deficit`.
  9. `hgbr18_strain_potency_partition`: Sign-corrected seismic activity (`Band 10 + Band 16`) vs geodetic strain rate (`hypot(Band 7, Band 8)`) partition index gated by gravity Hurst anisotropy.
  10. `hgbr18_transtensional_coulomb_focus`: Dilatational shear rate coupling (`Band 7 * Band 8`) projected along gravity strike $\psi_G$ and Hurst deficit.
  11. `hgbr18_updip_listric_trace_shift`: Up-dip listric fault-trace migration shifting 600-m gravity edge phase along the shallow-to-deep dip vector scaled by `Band 15` basement depth.
  12. `hgbr18_geotherm_hurst_conduit`: GDR chemical geothermometer disequilibrium (`Band 9` + `gdr_wellspring_in_footprint.csv` $\Delta T_{\text{diseq}}$, strictly excluding `dist_known_fault_px`) coupled with `hgbr18_grav_rtp_hurst_sync`.
  13. `hgbr18_tri_modal_concealed_ridge`: Pure-subsurface tri-modal ridge index combining Laplace gravity $G_{zz}$ zero-crossing worm, destriped RTP tilt-phase crest, and anisotropic Hurst damage break.
- **Cols `14..15` (2 features — topographic scarp scaling features registered in `STRICT_TOPO_FEATURE_NAMES`, used ONLY in the Full Specialist and excluded from the Pure-Subsurface Specialist, `IR-91-S15-05`):**
  14. `hgbr18_elev_hurst_break`: Cross-scale topographic Hurst-exponent break $H_{\text{elev}}^{\text{fine}}(100\text{--}200\text{ m}) - H_{\text{elev}}^{\text{coarse}}(400\text{--}800\text{ m})$ on `Band 12` (`det_elev`).
  15. `hgbr18_slope_variogram_step`: Directional cross-strike vs along-strike variogram step on `Band 19` (`det_elev_slope`).

### 4.2 Three Preregistered Holdout Experiments (`Rule 6`: `<= 3` Runs)
All three arms are evaluated on the unchanged `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` buffer, `37,654` global binary dots, `collar_px = 3.05`, `min_spacing_px = 3.05`):
1. **`hgbr_e1` (Rank-Aligned Full Multi-Physics Hierarchy + Hurst-Tensor Crest Pool -> Global Greedy NMS):**
   - Stage-1 + Stage-2 Full Specialist (`144` local static features = `STATIC_LOCAL 39 + S11 16 + S12 20 + PTHA 20 + HVDC 17 + CPAD 16 + HGBR 16`, plus `20` per-quadrant rank-aligned Stage-1 Full & Pure-Subsurface `spac_coda` auto-context features = `164` features).
   - Fixes `IR-91-S17-01` via per-quadrant quantile-to-reference-Beta alignment (`align_stage1_quadrant_quantiles`) before computing `spac_coda` auto-context, and pools Stage-1 + Stage-2 in log-odds space (`w_s2 = 0.66`) with bounded Hurst-Tensor-Phase crest sharpening (`emit_global_dots_nms`).
2. **`hgbr_e2` (Cover-Conditioned Dual-Specialist Log-Odds Pool with Pure-Subsurface Boost -> Global Greedy NMS):**
   - Combines the `164`-feature Full Specialist with the `124`-feature strictly DEM-free Pure-Subsurface Specialist (`0.0` `Band 12` / `Band 19` dependence in features, structure tensors, hard-negative mining, and auto-context) via cover-adaptive log-odds pooling (`w_sub in [0.22, 0.58]` controlled by `cpad_cover_concealment_prior`) + Hurst-Tensor-Phase crest sharpening (`IR-91-S17-02`), emitted via `emit_global_dots_nms`.
3. **`hgbr_e3` (Cover-Conditioned Dual-Specialist Surface -> Submodular 300-m Triangular-Kernel Emitter):**
   - Evaluates the lazy-greedy submodular 300-m triangular-kernel selector (`emit_global_dots_submodular`) on the `hgbr_e2` dual-specialist surface.

### 4.3 Full-Map Emission Protocol (`IR-91-S17-LFTG-01` Fix)
To prevent the in-sample full-map catalogue memorization halo that degraded `S17-LFTG` (`FF > 1 km = 31.5%`) and `S17-CPAD` (`FF > 1 km = 43.9%`), the winning holdout arm's full-map submission raster (`37,654` binary `{0.0, 1.0}` dots) is emitted from the **4-fold Out-of-Fold (`OOF`) stitched Stage-1 + Stage-2 surface** (where every quadrant $q \in \{0, 1, 2, 3\}$ is predicted strictly out-of-sample by models trained on the other 3 quadrants $m \ne q$) with a `4 px` cosine cross-quadrant seam feather and visible-catalogue halo de-crowding (`d(existing_faults) <= 9.0 px` smooth attenuation).
