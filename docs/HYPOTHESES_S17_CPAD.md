# Session 17 Preregistered Geological Hypotheses (`S17-CPAD`)

- **Frozen UTC:** `2026-10-25` (committed before any `S17` feature, model, or emitter code).
- **Assigned lane status:** Provisional local lane `S17-CPAD` (*Cover-Adaptive Potential-Phase, Accommodation-Saddle & Hydrothermal-Disequilibrium Dual-Specialist*); no external human multi-agent lane coordinator supplied an orthogonal lane token (`IR-S16-04`), so `assigned_lane` remains explicit and fail-closed in `src/gems91/readiness.py`.
- **Canonical evaluation benchmark (`PARALLEL-RUN PROTOCOL` Rule 2 & Rule 3):**
  - Unchanged shared evaluator `vendor/gems57/evaluate_holdout.py` (`VERSION = "gems57-pooled-hide-v2"`), paired with `vendor/gems57/spatial.py::folds(cat, fp, buffer_px=80)` (`4` contiguous UTM quadrants, `80 px = 8.0 km` spatial buffer, `0` shared train/truth connected components, `60,988` pooled withheld positive pixels = `29,319 + 12,596 + 9,473 + 9,600`, `1,000` paired 20 km physical-block bootstrap draws, `alpha = 0.2, beta = 0.8`, `R = 300 m = 3 px` triangular kernel).
  - Strictly label-blind global-footprint dot placement: `emit_global_dots(surface, visible_catalogue, footprint, budget=37654, collar_px=3.05, min_spacing_px=3.05)` receives **only** `surface`, `footprint`, and `visible_catalogue` — never `fold['region']`, `fold['truth']`, `fold['held_all']`, or `buffer_px` (resolving `IR-91-S17-01` discovered in legacy `scripts/run_s13_lane.py:87`).
  - Supplementary blind concealed-fault sanity benchmark: `BLIND-SGMC-CONTROL-DTI` (`62,122` off-catalogue USGS SGMC Quaternary/Cenozoic fault pixels at `> 500 m` from `existing_faults.tif`, never used in training or feature construction).
- **Pre-implementation forensic ground truth (`GEMSDOE32` & 92-repo fleet):**
  - Live snapshot audit (`2026-10-25T13:32:27Z`, `docs/fleet-audit.json`) across all `92` `buffedlizard55-lab/GEMSDOE*` repositories finds **`0` `ORGANIZER-CONFIRMED` receipts**.
  - `buffedlizard55-lab/GEMSDOE32@012e17b2a1` (`2026-10-25T09:56:58Z`) still publishes `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`sha256 c55bafc470054e82...`, `37,654` unit-amplitude dots, `d(catalogue) > 2 px`, `d_interdot > 3 px`) as **`UNSCORED`** (`projected 0.2747; NO ORGANISER SCORE EXISTS for this or any artifact in this repository`). User-reported `0.2778` and external `0.4413` / `0.3195` leaderboard figures remain unverified `CLAIM`s.
  - Because `S14-PTAC E2` (`0.267782 HOLDOUT-DTI` on legacy `gems91-hide-recover-v1.0` with `IR-91-S17-01` placement moat) had never been evaluated on `gems57-pooled-hide-v2`, Session 17 first evaluates the strongest permissible prior architecture (`INCUMBENT-PTAC-LB`) side-by-side on the identical `gems57-pooled-hide-v2` split alongside `CED91` (`0.089708 HOLDOUT-DTI`) and `S16-PGRD` (`0.069397 HOLDOUT-DTI`), and requires any promoted S17 arm to beat `max(INCUMBENT-PTAC-LB, CED91, S16-PGRD)`.

---

## Audit of Free Public Official External Data Sources & Viability Boundaries

Before selecting hypotheses, we audited candidate free, public-domain U.S. government / academic datasets for the Great Basin (`EPSG:32611`, `3730 x 3292` at `100 m` spacing) against both **competition rule compliance** (zero post-cut fault-trace leakage) and **sandbox execution viability** (network allowlist restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`):

| Source | Official Authority & URL | Licence / Rule Status | Sandbox Availability | Viability Verdict |
|---|---|---|---|---|
| **Official 19-band GEMS/GeoDAWN stack** (`gems-geodawn-numerical-features.tif`) | DrivenData / DOE GTO (`https://github.com/drivendataorg/gems-prize-reference-solution`) | Competition-provided (`SHA-256` pinned) | Restored & verified (`418.9 MB`) | **VIABLE (Primary)** |
| **DOE GDR Well & Spring Geothermometry** (`gdr_wellspring_in_footprint.csv`, `27,092` records) | DOE Geothermal Data Repository / INGENIOUS (`https://gdr.openei.org/submissions/1592`) | CC0 / U.S. Gov Public Domain; `dist_known_fault_px` column **banned** | Restored & verified (`2.49 MB`) | **VIABLE (Primary; strictly temperature & chemical geothermometers only)** |
| **USGS SGMC Concealed/Bedrock Faults** (`derived_sgmc_faults_100m_u8.tif`) | USGS Data Series 1052 (`https://pubs.usgs.gov/ds/1052/`) | Public Domain, **strictly banned as model input** (structural fault map leakage risk) | Restored & verified (`142 KB`) | **EVALUATION-ONLY (`BLIND-SGMC-CONTROL-DTI`; zero model access)** |
| **GeoDAWN Radiometrics K/Th/U (`geodawn_rad_u8.tif`) & USGS 3DEP 1 m LiDAR Scarps (`lidar_scarp_features_u8.tif`)** | USGS GeoDAWN (`https://www.sciencebase.gov`) / USGS 3DEP | Public Domain, but quantized external cache (`IR-91-26` licence-quarantine policy) | Restored in `data/external/` | **QUARANTINED FOR LIVE SUBMISSION (`H17-3` research-only)** |
| **NASA OPERA Sentinel-1 InSAR Surface Displacement / Coherence** | NASA ASF DAAC (`https://asf.earthdata.nasa.gov`) | Open NASA Earthdata | Blocked by sandbox network allowlist; not mirrored in pinned manifest | **NOT VIABLE IN SANDBOX (`H17-4`)** |
| **EarthScope / USArray 3-D Magnetotelluric Impedance & Phase Tensor** | IRIS / EarthScope SPUD (`https://ds.iris.edu/spud/emtf`) | Open NSF/USGS | Blocked by sandbox network allowlist; Band 17 (`cond_surf`) already captures shallow slice | **NOT VIABLE IN SANDBOX (`H17-5`)** |

---

## Ranked Novel Candidate Geological Hypotheses (`H17-1` .. `H17-5`)

### Rank 1 (SELECTED LANE) — `H17-1` (`S17-CPAD`): Cover-Adaptive Potential-Phase, Accommodation-Saddle & Hydrothermal-Disequilibrium Dual-Specialist
- **Layers & transforms used:**
  1. **Cooper–Cowan (2006) Normalized Potential-Field Edge Phase & Hydrothermal Magnetite-Destruction Poisson Deficit (`5` features, `100%` DEM-free):** Multi-scale directional gradients of `Band 13 (iso_grav_anom)` + `Band 11 (iso_grav_anom_vg)` + `Band 18 (iso_grav_anom_hg)` and `Band 02 (rtp)` + SI-corrected `Band 03 (tmi_hg / 200)` + `Band 09 (tmi_vg)` normalized by local 800 m RMS analytic amplitude (`cos(theta)`), strike-locked gravity–magnetic phase concordance, strike-normal second-derivative zero-crossing worms (`d_nn G ~ 0`), and **intrabasinal Poisson demagnetization deficit** (`cos(theta_grav) * max(0, G_600m(cos(theta_mag)) - cos(theta_mag))`).
  2. **Faulds & Hinz (2015) Structural Accommodation Saddles & Oblique Riedel Transtensional Kinematics (`6` features, `100%` DEM-free):** Principal Hessian hyperbolic saddle index `max(0, -k1*k2)/(k1^2 + k2^2)` on `Band 13` (`300 m`) and `Band 15 (depth_to_base_surf)` (`350 m` & `600 m`), multi-scale basement-thickness inflection worms, conjugate Walker Lane (`NW`) × Basin-and-Range (`NNE`) potential-field intersection mesh weighted by `Band 04 (geod_2ndinv)`, oblique WNW extension (`105 deg` E of N) decomposing `Band 08 (geod_dilaterate)` along NNE normal planes and `Band 07 (geod_shearrate)` along `330 deg` dextral Riedel planes, and `400 m` microseismic swarm-edge gradients on `Band 10`/`Band 16`.
  3. **Sibson (1996) Chemical Geothermometer Disequilibrium & Deconfounded Clay-Cap Baffles (`5` features: `3` strictly DEM-free + `2` cover-conditioned):** Local (`600 m` & `1.1 km`, strictly `< 1.2 km`) chemical-vs-outflow disequilibrium `max(0, max(T_quartz, T_chalcedony, T_cation) - max(T_measured, 15 C))` from `gdr_wellspring_in_footprint.csv` (`dist_known_fault_px` strictly banned), strike-projected disequilibrium conduits along subsurface `B13 + B02` strike, DEM-free `Band 17 (cond_surf)` quantile-residual lateral step gradients conditioned on `(Band 15, Band 06)`, playa-deconfounded lateral step gradients conditioned on `(Band 12, Band 15)`, and a smooth Concealed-Basin Cover Index (`Band 19`, `Band 12`, `Band 15`).
  4. **Exact Prior-Calibrated Subsurface-Transfer Dual-Specialist Architecture (resolving `IR-91-S15-05`, `IR-91-S15-06`, `IR-91-S15-07`, `IR-91-S17-01`):**
     - `85 / 109` local Stage-1 features are **bitwise invariant** to `Band 12` and `Band 19` (`STRICT_TOPO_FEATURE_NAMES` verified programmatically).
     - Every 2-quadrant pairwise Stage-1 model, 3-quadrant OOF Stage-1 model, and 4-quadrant full Stage-1 model is calibrated via exact Bayes reference-odds mapping (`c0 = 12.0` from training-domain `(pi_true, pi_sample)` only) **before** computing multi-scale `spac_coda` axial structural auto-context, eliminating the 2-vs-3-vs-4-quadrant prevalence drift that collapsed `S15-SCGF` (`IR-91-S15-06`) while retaining full dynamic range across `HistGradientBoostingClassifier` bins.
     - Both Stage-1 **and** Stage-2 maintain a dedicated **Pure-Subsurface Specialist** (`0` topographic features in Stage-1 and Stage-2) blended with the Full Specialist via a label-free Cover-Concealment Gate (`E2`) and submodular 300-m triangular-kernel emission (`E3`).
- **Physical signature targeted:** Blind geothermal upflow conduits, hydrothermally demagnetized intrabasinal fault cores, en-echelon relay ramps / accommodation-zone saddles (`Faulds & Hinz Settings #1, #3, #4`), and concealed growth faults buried beneath Quaternary playas and piedmont bajadas (`43%` of Nevada geothermal systems have no surface manifestations or scarps).
- **Why mapped faults miss it:** USGS Quaternary and INGENIOUS surface-trace compilations rely primarily on aerial/LiDAR geomorphic scarps and bedrock outcrop mapping; Holocene alluvial-fan aggradation, Lake Lahontan lacustrine silts, and smectite alteration caps erase surface topographic expression within `10^3–10^4` years while leaving sharp density inflections, magnetite-destruction troughs, hyperbolic basement saddles, lateral conductivity baffles, and high silica/cation geothermometer disequilibrium intact.
- **Named non-fault geological mimics:**
  1. Unfaulted intracaldera felsic tuffs and reversely magnetized Neogene volcanic flows (mimic magnetic lows / Poisson deficits without active fault permeability — rejected unless corroborated by gravity inflection phase, geodesic strain rate, and strike-coherent auto-context).
  2. Closed-basin evaporitic alkali playas (mimic high `Band 17` shallow conductivity — rejected by 2-D `(Band 15, Band 06)` / `(Band 12, Band 15)` quantile deconfounding and by taking the **lateral step gradient** rather than bulk basin conductivity).
  3. Buried paleochannels and pluton-margin hornfels contacts (mimic smooth basement depth curvature — rejected by hyperbolic saddle sign `-k1*k2 > 0` and regional `105 deg` transtensional slip/dilation alignment).
- **How it differs from repo methods:**
  - Unlike `CED91` and `S16-PGRD` (single-stage linear rules on gravity/magnetic gradients that scored `0.0897` and `0.0694 HOLDOUT-DTI`), `S17-CPAD` combines nonlinear interaction physics, chemical geothermometer disequilibrium (`T_chem - T_outflow`), hyperbolic accommodation saddles, and two-stage axial structural auto-context.
  - Unlike `S14-PTAC` (which relied heavily on `Band 19` topographic slope scarps and was never tested on label-blind `gems57-pooled-hide-v2` without `IR-91-S17-01`), `S17-CPAD` builds a strictly `B12/B19`-invariant Stage-1 + Stage-2 Pure-Subsurface Specialist gated by sedimentary cover concealment.
  - Unlike `S15-SCGF` (which leaked `Band 12`/`Band 19` into `PTHA` features inside its subsurface specialist, suffered `12x` prevalence-drift collapse across 2/3/4-quadrant auto-context splits, and overfit `15 km` regional coordinate bowls across quadrants), `S17-CPAD` eliminates all three structural failure modes simultaneously.
- **Expected DTI gain vs. engineering cost:** **Highest expected DTI gain (`+0.015` to `+0.045 HOLDOUT-DTI` over `INCUMBENT-PTAC-LB` and `> +0.10` over `CED91`/`S16-PGRD`) at moderate runtime (`~18–28 min` on 2 CPU cores, `< 25%` of the 2-hour cap).**

---

### Rank 2 — `H17-2`: Multi-Scale Anisotropic Radon / Beamlet Potential-Field Worm Graph
- **Layers & transforms used:** Upward-continued differences (`200 m -> 800 m -> 2,400 m`) of `Band 13 (iso_grav_anom)` and `Band 02 (rtp)` transformed via sliding `1.6 km` oriented Radon line integrals (`16` azimuths) to link fragmented potential-field "worms" across alluvial gaps via minimum-cost Dijkstra/geodesic path continuation, weighted by `Band 04` strain rate.
- **Physical signature targeted:** Deep (`1–4 km`) crustal-scale basement fault segments whose shallow expression is segmented into discontinuous steps beneath thick basin fill.
- **Why mapped faults miss it:** Discontinuous surface ruptures across step-overs appear unlinked in airphoto/DEM mapping even where a continuous basement master fault links them at depth.
- **Named non-fault geological mimic:** Regional Mesozoic thrust fronts, batholith margins, and linear basaltic dike swarms (produce long straight Radon lineaments with zero Quaternary slip).
- **How it differs from repo methods:** Replaces local pixelwise tree classifiers (`PTAC`/`SCGF`) and local Hessian ridges (`CED`/`PGRD`) with nonlocal Radon integral line-graph linking.
- **Expected DTI gain vs. cost:** Moderate expected gain (`+0.005` to `+0.015`), higher false-positive risk on pre-Cenozoic dikes/pluton edges, medium-high compute cost (`~40 min` for multi-scale sliding Radon transforms). Deferred behind `H17-1`.

---

### Rank 3 — `H17-3`: Radiometric Potassium-Metasomatism (`K/Th`) × 1 m 3DEP LiDAR Micro-Scarp Concordance
- **Layers & transforms used:** Ratio residual of potassium to thorium (`K / (Th + eps)`) from `data/external/geodawn_rad_u8.tif` paired with sub-meter topographic breakline density and openness from `data/external/lidar_scarp_features_u8.tif` and `Band 15` shallow cover gates.
- **Physical signature targeted:** Adularia–illite–sericite potassic alteration halos along degraded Holocene piedmont micro-scarps (`0.2–0.8 m` throw) invisible at `100 m` regional DEM resolution (`Band 12`/`Band 19`).
- **Why mapped faults miss it:** Regional `10–30 m` DEMs smooth sub-meter piedmont fault scarps below detection threshold in unmapped basins, and field mappers rarely pair gamma-ray spectrometry with subtle fan breaks.
- **Named non-fault geological mimic:** Potassic felsic ash-flow tuffs (rhyolite/ignimbrite) shedding into braided alluvial fan channels and Lake Lahontan wave-cut shorelines (`1,200–1,335 m` elevation benches).
- **How it differs from repo methods:** Introduces spectral K/Th geochemical alteration and 1 m LiDAR micro-geomorphology not present in the 19-band GEMS numerical stack (`S14-LSRG` tested LiDAR scarps alone on legacy folds without K/Th metasomatic coupling).
- **Expected DTI gain vs. cost:** Moderate gain on piedmont scarps, **blocked from live submission promotion** by `IR-91-26` (external quantized cache provenance not cleared for official competition submission without upstream raw reproduction). Deferred to research-only quarantine.

---

### Rank 4 — `H17-4`: Sentinel-1 InSAR Persistent-Scatterer Phase-Gradient Aquifer Baffles *(Not Viable in Sandbox)*
- **Layers & transforms used:** Multi-year NASA OPERA Sentinel-1 ascending/descending LOS velocity horizontal gradients (`\|\nabla v_{\text{LOS}}\|`) combined with `Band 17` conductivity steps and `Band 15` basin depth.
- **Physical signature targeted:** Sharp seasonal/secular pore-pressure & subsidence discontinuities (`2–10 mm/yr` step across `< 300 m`) where unmapped intrabasinal faults act as low-permeability clay-core cross-fault groundwater/geothermal baffles.
- **Why mapped faults miss it:** Zero cumulative topographic scarp is preserved on active agricultural/playa floors, yet modern radar interferometry resolves sharp differential compaction across fault-sealed compartments.
- **Named non-fault geological mimic:** Stratigraphic clay-lens pinchouts around municipal pumping cones and mine dewatering pits.
- **How it differs from repo methods:** Uses satellite radar phase discontinuities (`100 m` resolution) rather than coarse GPS station interpolation (`Bands 04/07/08` have `~15–30 km` station spacing).
- **Viability & rank rationale:** Scientifically high value, **not viable in this sandbox** (`asf.earthdata.nasa.gov` outside network allowlist and absent from `registry/data_manifest.json`).

---

### Rank 5 — `H17-5`: EarthScope 3-D Magnetotelluric Phase-Tensor Skew (`Phi_2`, `Beta`) Deep Conductive Roots *(Not Viable in Sandbox)*
- **Layers & transforms used:** Period-dependent (`10^0–10^3 s`) MT phase-tensor skew angle `|beta| > 3 deg` and strike-aligned induction arrows coupled to `Band 13` gravity gradients and `Band 10` deep seismicity (`> 5 km`).
- **Physical signature targeted:** Crustal-scale (`3–15 km` depth) anisotropic fluid/partial-melt ascent chimneys feeding blind Great Basin geothermal systems beneath resistive range blocks or conductive shallow smectite caps.
- **Why mapped faults miss it:** Deep ductile-to-brittle fluid roots often sit offset from mapped shallow listric range-front faults (`Band 17` only provides a single shallow conductivity slice).
- **Named non-fault geological mimic:** Paleozoic graphitic/sulfidic black shales (e.g., Roberts Mountains allochthon carbonaceous units) producing strong 3-D MT skew without active Quaternary faulting.
- **Viability & rank rationale:** **Not viable in this sandbox** (`ds.iris.edu` outside network allowlist; station spacing `~70 km` limits `300 m` DTI localization without dense array infill).

---

## Preregistered Experiment Plan Inside Selected Lane `H17-1` (`S17-CPAD`)

Strict budget: **at most `3` candidate model experiments (`E1`, `E2`, `E3`)** within `2` hours (`7,200 s`) wall-clock, evaluated alongside frozen reference baselines (`CED91`, `S16-PGRD`, and label-blind incumbent `INCUMBENT-PTAC-LB`) on the exact same `gems57-pooled-hide-v2` split (`60,988` withheld positives, `1,000` paired 20 km block bootstrap draws):

1. **Incumbent Baseline (`INCUMBENT-PTAC-LB`, 0 hypothesis budget — `LIMITATIONS_AND_NEXT_STEPS.md` Priority #2):**
   - Exact `S14-PTAC E2` feature set (`PTAC` + local `HVDC`/`PTHA`/`MHTR` + single-specialist `spac_coda` auto-context) re-trained and evaluated strictly on `vendor/gems57/spatial.py::folds(cat, fp, buffer_px=80)` with global-footprint blind placement (`emit_global_dots(..., budget=37654, collar_px=3.05, min_spacing_px=3.05)`), establishing the true apples-to-apples `gems57-pooled-hide-v2` benchmark for the repo's best prior architecture.
2. **Experiment 1 (`S17-CPAD E1` — `cpad17_e1_calib_dualspec_nms`):**
   - Adds the `16` new `CPAD` blind-geothermal features (`Cooper–Cowan` potential phase & Poisson demagnetization deficit, `Faulds–Hinz` hyperbolic accommodation saddles & `105 deg` Riedel transtensional shear-dilation, `Sibson` local `< 1.2 km` chemical geothermometer disequilibrium & deconfounded clay-cap baffles), restricts static context strictly to translation-invariant local features (`IR-91-S15-07`), enforces exact `85/109` `B12/B19`-invariant Stage-1 Pure-Subsurface Specialist (`IR-91-S15-05`), applies exact training-domain Bayes reference-odds calibration (`c0 = 12.0`) across all 2-quadrant pair, 3-quadrant OOF, and 4-quadrant full splits before extracting dual-specialist `spac_coda` auto-context (`IR-91-S15-06`), fits Stage-2 Full ensemble, and emits `37,654` global dots via label-blind greedy NMS (`collar_px=3.05`, `min_spacing_px=3.05`).
3. **Experiment 2 (`S17-CPAD E2` — `cpad17_e2_cover_gated_s2_nms`):**
   - Adds a dedicated **Stage-2 Pure-Subsurface Specialist** (trained strictly on non-topographic features + Pure-Subsurface `ac_sub_*` auto-context, `0` dependence on `Band 12` or `Band 19` in either Stage-1 or Stage-2!), blends Stage-2 Full and Stage-2 Subsurface via the continuous label-free **Sedimentary Cover-Concealment Gate** (`cpad_cover_concealment_prior`, shifting weight toward Pure-Subsurface in flat alluvial basins while preserving scarp resolution on range fronts), sharpens on-crest localization via multi-physics accommodation crest concordance, and emits `37,654` global dots via greedy NMS.
4. **Experiment 3 (`S17-CPAD E3` — `cpad17_e3_cover_gated_submod`):**
   - Takes the exact `E2` continuous probability surface (`0` retraining!) and replaces greedy peak-picking NMS with **lazy-greedy submodular 300-m triangular-kernel expected-DTI coverage allocation** (`_lazy_greedy_submodular_select` on `footprint & (edt(~visible) > 3.05)` with `min_spacing_px=3.05`), directly maximizing expected `300 m` triangular kernel coverage of hidden fault traces per emitted dot instead of clustering dots redundantly inside high-amplitude halos.

### Fail-Closed Gate Criteria (`src/gems91/readiness.py`)
- **Rule 4 Canary Gate:** Every `CPAD` feature and Stage-1/Stage-2 input feature tested alone on all `60,988` pooled withheld positives AND inside each of the 4 spatial quadrants must satisfy symmetric `AUC <= 0.90`.
- **Rule 1 Novelty Gate:** Pre-placement full-footprint Spearman `|rho| <= 0.90` AND final `3 px` dot overlap `<= 70%` across `registry/s17_comparison_inventory.json` (`95` verified rasters, `0` missing; `86` real submissions ordered before `9` synthetic calibration lattices). If `calib_r13lattice_00904.tif` triggers the mathematically unavoidable `>= 82.34%` synthetic lattice stop (`IR-S16-03`), record `DUPLICATE` faithfully, keep `verdict: "negative"`, `submission_ready: false`, `OK TO SUBMIT: NO`, and `slots_used: 0`.
- **Promotion Gate:** Even absent synthetic lattice obstruction, a candidate is eligible for human-selector consideration ONLY if its `gems57-pooled-hide-v2` `HOLDOUT-DTI` strictly exceeds `max(INCUMBENT-PTAC-LB, CED91, S16-PGRD)` with positive paired block-bootstrap evidence, and human weekly-slot selection remains separate (`Rule 6`).
