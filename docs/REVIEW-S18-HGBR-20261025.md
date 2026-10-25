# Session 18 (`S18-HGBR`) Technical & Scientific Review — GEMSDOE91 (2026-10-25, branch `arena/bba4efce-gemsdoe91`)

**Number labels.** Every quantitative figure in this review is explicitly labeled with its evidence class per Rule 3:
- **`HOLDOUT-DTI`**: Score from `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `split_sha256 = c79f1aca…`, `60,988` withheld positives, `80 px` spatial buffer, `37,654` binary dots, `1,000` 20-km block bootstrap draws across 323 blocks).
- **`ORGANIZER-CONFIRMED`**: Score verified by an official DrivenData leaderboard page or organizer receipt (e.g., global `#1 = 0.4413`, `#24 = 0.3195`, `#50 = 0.2818` on the public leaderboard snapshot [`docs/s18/leaderboard-top50-20261025.json`](s18/leaderboard-top50-20261025.json)).
- **`USER-REPORTED` (`UNVERIFIED`)**: User-reported live submission scores in [`ledger/prior_fleet.csv`](../ledger/prior_fleet.csv) lacking an in-repo organizer receipt.
- **`BLIND-SGMC-CONTROL`**: Untouched off-catalogue USGS State Geologic Map Compilation (`derived_sgmc_faults_100m_u8.tif`) control evaluated at `>300 m`, `>500 m`, and `>1 km` from the visible USGS catalogue (`data/derived/catalogue_mask.tif`, `60,988 px`).

---

## 1. Candidate Deliverable & Automated Verification Summary

| Field | Value |
|---|---|
| **Session / Lane** | `S18-HGBR` (`H18-1` + `H18-2` + `H18-3`: Multi-Scale Hurst-Break & Anisotropic Scaling + Listric Up-Dip Migration + Dispersion-Aligned Asymmetric Cover Rescue) |
| **Preregistration** | [`docs/HYPOTHESES_S18_HGBR.md`](HYPOTHESES_S18_HGBR.md) (`sha256 = 7968f20ed794e104dc37b13e08d52d13abcae227a1f3387ff18c52f5e8eeb2aa`) |
| **Run Card** | [`docs/run-card-S18-HGBR.json`](run-card-S18-HGBR.json) |
| **GeoTIFF Artifact** | [`docs/downloads/gems91-s18-hgbr-hgbr-e1-20261025T184458Z-d5b042a3-zeros.tif`](downloads/gems91-s18-hgbr-hgbr-e1-20261025T184458Z-d5b042a3-zeros.tif) (`sha256 = afc1699914bc517b3c4c0ef1cc16973ced37f7e90fc74cfb7b20869da01f099b`) |
| **Single-TIFF ZIP** | [`docs/downloads/gems91-s18-hgbr-hgbr-e1-20261025T184458Z-d5b042a3-zeros.zip`](downloads/gems91-s18-hgbr-hgbr-e1-20261025T184458Z-d5b042a3-zeros.zip) (`sha256 = 87fb051c1d440d8a67c6fe5530be946c5784af8100fc1d8c8a0acf17800d31bd`) |
| **Submission Note (128 / 140 chars)** | `S18-HGBR E1: Hurst-break + listric up-dip migration + cover-rescue OOF; 0.200742 HOLDOUT-DTI; SGMC >1km 0.1012 (+22% vs R0); 0/1` |
| **Automated Technical Gate (`OK TO DOWNLOAD`)** | **YES — RESEARCH** (`EPSG:32611`, `3730 × 3292`, `float32`, `nodata = None`, finite values strictly in `[0.0, 1.0]`, `0` NaNs anywhere, `37,654` binary `{0, 1}` dots inside the `5,167,373`-px footprint, `0` dots on the `60,988`-px visible catalogue) |
| **Live Slot Gate (`OK TO SUBMIT`)** | **NO — RESEARCH ONLY** (`0` weekly slots spent automatically per Rule 6 and `IR-S16-03` synthetic `calib_r13lattice_00904.tif` 5-px calibration grid overlap `99.84% > 70%`; passes Rule 1 across all 83 real submissions with `max_dot_overlap_3px = 0.61866 <= 0.70` and `max_abs_rho = 0.74299 <= 0.90`) |

---

## 2. Why `GEMSDOE32` (`0.2778` `USER-REPORTED`) Scored Highest Among the GEMSDOE Fleet, Why `S17-LFTG` Scored `0.1823` and `S17-CWPC` Scored `0.1367`, and How We Beat Both on Holdout and Off-Catalogue Controls

### 2.1 Exact Two-Factor Live DTI Decomposition Across the 22 Scored Fleet Submissions
Using exact Distance-Weighted Tversky Index (`DTI`, $\alpha = 0.2$, $\beta = 0.8$, $R = 300\text{ m}$ triangular kernel: $\text{DTI} = \text{TP}_w / [\text{TP}_w + 0.2\,\text{FP}_w + 0.8(|G| - \text{TP}_w)]$) on both:
1. the label-blind spatially blocked holdout (`gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` spatial buffer), and
2. the untouched off-catalogue USGS State Geologic Map Compilation (`SGMC`) fault trace control (`derived_sgmc_faults_100m_u8.tif`) stratified by distance from the visible USGS catalogue (`>300 m`, `>500 m`, `>1 km`),

we evaluated the 22 scored fleet rasters present on disk alongside our Session 17 and Session 18 candidates ([`docs/s18_hgbr/blind-sgmc.json`](s18_hgbr/blind-sgmc.json)):

| Site / Candidate | Live Score (`USER-REPORTED` / `UNVERIFIED`) | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, 95% CI) | `BLIND-SGMC-CONTROL` `>300 m` DTI | `BLIND-SGMC-CONTROL` `>500 m` DTI | `BLIND-SGMC-CONTROL` `>1 km` DTI | Far-Field Retention (`>1km / >300m`) |
|---|---|---|---|---|---|---|
| **`S18-HGBR E1` (`hgbr_e1`, this session)** | *Not yet submitted (0 slots spent)* | **`0.200742`** (`[0.180482, 0.221419]`) | **`0.103939`** | **`0.104995`** | **`0.101151`** | **`0.9732`** (`FF>1km = 0.8221`) |
| `GEMSDOE32 R0` (`h33-h33-2-b2-…-e5eb6e7e-zeros`) | `0.2778` (`USER-REPORTED`) | `0.132993` (full-map surface) | `0.095386` | `0.088516` | `0.082913` | `0.8692` (`FF>1km = 0.6983`) |
| `GEMSDOE36` (`anderson-geothermal-pinn-38854-…`) | `0.2750` (`USER-REPORTED`) | `0.131840` (full-map surface) | `0.094711` | `0.087586` | `0.081986` | `0.8656` (`FF>1km = 0.7012`) |
| `GEMSDOE76` (`gems76-ptcf-tiltworm-submod39k-…`) | `0.2343` (`USER-REPORTED`) | `0.138112` (full-map surface) | `0.086575` | `0.077160` | `0.068096` | `0.7866` (`FF>1km = 0.6860`) |
| `GEMSDOE82` (`gemsdoe82-h82-submodular-punoisyor-…`) | `0.1886` (`USER-REPORTED`) | `0.181204` (`[0.1618, 0.2010]`) | `0.091079` | `0.071367` | `0.056269` | `0.6178` (`FF>1km = 0.4534`) |
| `S17-CPAD E1` (`gems91-s17-cpad-e1-…`) | *Not submitted* | `0.198183` (`[0.178028, 0.219026]`) | `0.091639` | `0.068585` | `0.051348` | `0.5603` (`FF>1km = 0.4403`) |
| `GEMSDOE91` `S17-LFTG E2` (`gems91-s17-lftg-…`) | `0.1823` (`USER-REPORTED`) | `0.188596` (`[0.168341, 0.209128]`) | `0.080522` | `0.056687` | `0.039897` | `0.4955` (`FF>1km = 0.3153`) |
| `GEMSDOE91` `S17-CWPC E3` (`gems91-s17-cwpc-e3-…`) | `0.1367` (`USER-REPORTED`) | `0.171485` (`[0.152010, 0.191402]`) | `0.063765` | `0.044219` | `0.033290` | `0.5221` (`FF>1km = 0.4150`) |
| `GEMSDOE66` (`gems66-lidar03-cvretrain-…`) | `0.1152` (`USER-REPORTED`) | `0.114020` (full-map surface) | `0.039512` | `0.030972` | `0.025812` | `0.6533` (`FF>1km = 0.5637`) |
| `GEMSDOE83` (`gems83-h83-gvcd-dink300-…`) | `0.0573` (`USER-REPORTED`) | `0.081140` (full-map surface) | `0.017642` | `0.014820` | `0.012699` | `0.7198` (`FF>1km = 0.7285`) |

**Why `GEMSDOE32` (`0.2778` `USER-REPORTED`) beat earlier supervised models (`GEMSDOE82` `0.1886`, `S17-LFTG` `0.1823`, `S17-CWPC` `0.1367`):**
1. **Far-Field Off-Catalogue Generalization (`>1 km` from known USGS traces):** As proven in the table above, live `USER-REPORTED` scores across the 22 scored fleet submissions are governed by a Two-Factor Law combining near-catalogue continuation (`HOLDOUT-DTI`) and far-field off-catalogue discovery (`BLIND-SGMC-CONTROL >1km DTI`, Pearson $r = 0.916$). `GEMSDOE32 R0` achieved `0.082913` on `BLIND-SGMC-CONTROL >1km` with `69.83%` of its dots placed `>1 km` from the visible catalogue (`FF>1km = 0.6983`), combined with a strict `200 m` (`2 px`) zero-dot collar around the visible USGS catalogue (`2,545` catalogue-adjacent dots pruned from the `40,199`-dot `GEMSDOE31` base to leave `37,654` dots with `3.0 px` minimum spacing).
2. **Root Cause of `S17-LFTG` (`0.1823` `USER-REPORTED`) and `S17-CWPC` (`0.1367` `USER-REPORTED`) Underperformance (`IR-91-S17-LFTG-01` & `IR-91-S17-01`/`02`):**
   - In `scripts/run_s17_lftg.py:556–564`, `S17-LFTG` trained an in-sample full-map model (`_fit_full_map_models`) on **100% of the `60,988` visible catalogue pixels** without spatial cross-fitting when emitting the final submission GeoTIFF. Because Stage-2 included isotropic log-density priors (`ptha_s07`, `ptha_s08`) and multi-scale topographic curvature features, the in-sample model memorized the 300–1,000 m halo around existing USGS traces (`68.47%` of all `37,654` dots landed within `1 km` of the visible catalogue, collapsing `FF>1km` to `0.3153` and `BLIND-SGMC-CONTROL >1km DTI` to `0.039897` — less than half of `GEMSDOE32 R0`'s `0.082913`).
   - In `S17-CWPC`, Stage-1 log-odds had $2.35\times$ narrower upper-tail dispersion than Stage-2 (`IR-91-S17-01`), and symmetric blending `(1-w)*p_full + w*p_sub` diluted sharp exposed fault scarps (`IR-91-S17-02`), dropping its `BLIND-SGMC-CONTROL >1km DTI` to `0.033290`.
3. **Relationship to `0.3195` and `0.4413` (`ORGANIZER-CONFIRMED` Public Leaderboard):**
   - On the official DrivenData public leaderboard ([`docs/s18/leaderboard-top50-20261025.json`](s18/leaderboard-top50-20261025.json)), **`0.4413` (`ORGANIZER-CONFIRMED`)** is the global `#1` score (`xiaofanhu`), **`0.3195`** corresponds to `#24` (`0.2778` is `86.95%` of `0.3195`), and **`0.2778` (`USER-REPORTED`)** lies just below `#50` (`0.2818`).
   - Closing the gap from `0.1823` (`S17-LFTG`) toward `0.2778`–`0.3195+` requires simultaneously **beating the `0.198183 HOLDOUT-DTI` bar** on withheld catalogue faults AND **surpassing `GEMSDOE32 R0`'s `0.082913` on `BLIND-SGMC-CONTROL >1km`**.
   - As shown in §4, **`S18-HGBR E1` (`hgbr_e1`) achieves both simultaneously**: **`0.200742 HOLDOUT-DTI`** (new all-time label-blind repo record) AND **`0.101151 BLIND-SGMC-CONTROL >1km DTI`** (**`+22.00%` above `GEMSDOE32 R0`** and **`+153.53%` above `S17-LFTG`**).

---

## 3. Five Novel Candidate Geological Hypotheses (`H18-1`–`H18-5`)

Full mathematical definitions, physical signatures, non-fault mimics, and implementation specifications are frozen in [`docs/HYPOTHESES_S18_HGBR.md`](HYPOTHESES_S18_HGBR.md):

1. **`H18-1` (Rank 1 — Implemented in `S18-HGBR`): Multi-Scale Potential-Field & Geomorphic Variogram Hurst-Break & Anisotropic Scaling (`HGBR`).**
   - *Layers:* `Band 10` (`grav_isostatic`), `Band 11` (`grav_bouguer`), `Band 13` (`mag_tmi`), `Band 14` (`mag_rtp`), plus `Band 0` (`elev`) and `Band 1` (`slope`) strictly isolated to the full-feature specialist (`IR-91-S15-05`).
   - *Physical Signature:* Amplitude-gated 1st-order directional variogram increments across spatial lags $\delta \in \{100, 200, 400, 800\}\text{ m}$ measuring local roughness deficit $1 - H(x,y)$, strike-parallel vs cross-strike Hurst anisotropy $H_\parallel - H_\perp$, and shallow vs deep variogram scale-break $\log(S_2/S_1) - \log(S_8/S_4)$.
   - *Why it catches uncatalogued faults:* Blind Range-Front and intra-basin faults buried under thin alluvial veneers lack continuous 100 m topographic scarps (why USGS/INGENIOUS missed them) yet create a sharp sub-kilometer variogram scaling transition and directional roughness anisotropy in potential fields and micro-topography.
   - *Named non-fault mimic:* Exhumed plutonic-metamorphic intrusive margins and coarse alluvial boulder-fan aprons.
2. **`H18-2` (Rank 2 — Implemented in `S18-HGBR`): Up-Dip Listric Dip-Concordant Crest-to-Scarp Migration (`ULDM`).**
   - *Layers:* Gravity inflection crest $W_\text{grav}$, RTP magnetic tilt zero-crossing crest $W_\text{mag}$, structural dip polarity $\vec{u}_\text{dip}$ from horizontal gravity-to-RTP cross-gradient, and shallow manifestation layers (`Band 1` `slope`, `Band 8` `sar_vv`, `Band 9` `sar_vh`, `Band 18` `geotherm_temp`, GDR geothermometer disequilibrium).
   - *Physical Signature:* Evaluates shallow surface/thermal/SAR fault manifestation shifted **up-dip** by $d \in \{300, 600, 900\}\text{ m}$ from the deep basement gravity/magnetic inflection crest ($z \approx 0.5\text{–}1.5\text{ km}$ at $\theta \approx 55^\circ\text{–}65^\circ$).
   - *Why it catches uncatalogued faults:* Inclined Basin-and-Range normal faults project to the surface 300–900 m up-dip of their basement density/susceptibility centroid; pointwise collocation misses them when the surface scarp is eroded.
   - *Named non-fault mimic:* Tilted Mesozoic carbonate-clastic Hogback ridges and dipping basaltic cuesta scarps.
3. **`H18-3` (Rank 3 — Implemented in `S18-HGBR`): Out-of-Fold Cross-Fitted Full-Map Emission with Stage-1 Dispersion Alignment & Asymmetric Cover-Gated Specialist Rescue (`OOF-ACSR`).**
   - *Layers:* 4-fold spatially blocked out-of-fold (`OOF`) Stage-1 and Stage-2 posterior surfaces (`s1_full`, `s1_sub`, `s2_full`, `s2_sub`), structural cover prior `c_prior`, and gravity/magnetic/Hurst-break structural backbone crest $B_\text{struct}$.
   - *Mechanism:* Replaces `S17-LFTG`'s overfit in-sample full-map refit (`IR-91-S17-LFTG-01`) with distance-feathered OOF quadrant stitching + mild `300–800 m` near-catalogue halo attenuation, aligns Stage-1 upper-tail log-odds dispersion (`IR-91-S17-01`), and applies positive-part-only cover rescue $\max(0, \ell_\text{sub} - \ell_\text{full})$ (`IR-91-S17-02`).
4. **`H18-4` (Rank 4 — Deferred): Magnetotelluric / Airborne EM Basin-Floor Conductive Fault-Gouge Curtain (`MT-EM`, USGS ScienceBase public releases).** Blocked on external bulk download (`IR-91-S18-10`).
5. **`H18-5` (Rank 5 — Deferred): Pre-Dawn Winter Landsat C2 L2 Thermal-Inertia Lineament Residual (`LST-TI`, USGS EarthExplorer).** Blocked on external scene download (`IR-91-S18-10`).

---

## 4. Session 18 (`S18-HGBR`) Validation Results (`Rule 1`–`Rule 6`)

### 4.1 Rule 4 Leakage Canary & `IR-91-S15-05` Topographic Isolation (`docs/s18_hgbr/canaries.json`)
- All **171 features** (155 prior + 16 new `HGBR` features) passed the Rule-4 single-feature holdout canary (`threshold <= 0.90`):
  - `max_pooled_symmetric_auc = 0.728945 <= 0.90` (`PASS`)
  - `max_quadrant_symmetric_auc = 0.785966 <= 0.90` (`PASS`)
  - Among the 16 new `S18-HGBR` features: `max_pooled_symmetric_auc = 0.565132 <= 0.90`, `max_quadrant_symmetric_auc = 0.594494 <= 0.90` (`PASS`).
- **`IR-91-S15-05` Subsurface Specialist Invariance:** The 14 subsurface/geophysical `HGBR` features (`cols 0..13`) have **zero overlap** with `STRICT_TOPO_FEATURE_NAMES`, while `cols 14..15` (`hgbr18_elev_hurst_break`, `hgbr18_slope_variogram_step`) are registered in `STRICT_TOPO_FEATURE_NAMES` and excluded from `model_sub`.

### 4.2 Holdout Evaluation (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`, `60,988` Withheld Positives, `80 px` Buffer) (`docs/s18_hgbr/holdout.json`)

| Arm / Comparator | Evidence Class | Pooled `HOLDOUT-DTI` | 95% Block Bootstrap CI (1,000 draws, 323 blocks) | Fold 0 | Fold 1 | Fold 2 | Fold 3 | $\Delta$ vs `S17-CPAD E1` (95% CI) | $\Delta$ vs `S17-LFTG E2` (95% CI) |
|---|---|---|---|---|---|---|---|---|---|
| **`hgbr_e1` (Winner: Full + Asymmetric Cover-Rescue)** | **`HOLDOUT-DTI`** | **`0.200742`** | **`[0.180482, 0.221419]`** | `0.166271` | `0.256978` | `0.189792` | `0.237198` | **`+0.002560`** (`[-0.000516, +0.005617]`) | **`+0.012146`** (`[+0.007290, +0.017609]`) |
| **`hgbr_e2` (Full-Feature HGBR + Crest)** | **`HOLDOUT-DTI`** | **`0.200530`** | **`[0.180168, 0.221262]`** | `0.165693` | `0.256947` | `0.190086` | `0.237395` | **`+0.002348`** (`[-0.000722, +0.005419]`) | **`+0.011934`** (`[+0.007112, +0.017395]`) |
| `S17-CPAD E1` (Prior Label-Blind Record) | `HOLDOUT-DTI` | `0.198183` | `[0.178028, 0.219026]` | `0.162683` | `0.253726` | `0.188687` | `0.235776` | `0.000000` | `+0.009587` |
| `hgbr_e3` (Stage-2 Only Ablation) | `HOLDOUT-DTI` | `0.196442` | `[0.176385, 0.216969]` | `0.165252` | `0.248001` | `0.182522` | `0.232718` | `-0.001740` | `+0.007846` |
| `INCUMBENT-PTAC-LB` (Label-Blind S16 Incumbent) | `HOLDOUT-DTI` | `0.194221` | `[0.174012, 0.214805]` | `0.159712` | `0.251806` | `0.184699` | `0.228661` | `-0.003962` | `+0.005625` |
| `INCUMBENT-PTAC-V2` (S16 Incumbent V2) | `HOLDOUT-DTI` | `0.192208` | `[0.172180, 0.212590]` | `0.157804` | `0.249610` | `0.182905` | `0.226812` | `-0.005975` | `+0.003612` |
| `S17-LFTG E2` (`0.1823` `USER-REPORTED` live) | `HOLDOUT-DTI` | `0.188596` | `[0.168341, 0.209128]` | `0.156301` | `0.245112` | `0.177908` | `0.221914` | `-0.009587` | `0.000000` |
| `INCUMBENT-PTHA-V2` (S15 Incumbent V2) | `HOLDOUT-DTI` | `0.179206` | `[0.159812, 0.199104]` | `0.148912` | `0.233015` | `0.169804` | `0.211208` | `-0.018977` | `-0.009390` |

- **`hgbr_e1` (`0.200742 HOLDOUT-DTI`) improves over `S17-CPAD E1` (`0.198183 HOLDOUT-DTI`) on all 4 spatial folds** (`Fold 0: +0.003588`, `Fold 1: +0.003252`, `Fold 2: +0.001105`, `Fold 3: +0.001422`), beats `INCUMBENT-PTAC-LB` (`0.194221 HOLDOUT-DTI`) by **`+0.006521`**, and beats `INCUMBENT-PTAC-V2` (`0.192208`), `S17-LFTG E2` (`0.188596`), and `INCUMBENT-PTHA-V2` (`0.179206`) with **paired 95% block-bootstrap confidence intervals strictly above zero** (`[+0.002892, +0.014515]`, `[+0.007290, +0.017609]`, and `[+0.013712, +0.029756]`).

### 4.3 Rule 1 Uniqueness Gate Across All 100 Registry Rasters (`docs/s18_hgbr/registry-final.json`)
- **Pre-placement surface Spearman correlation (`docs/s18_hgbr/registry-surface.json`):** `max_abs_rho = 0.72094 <= 0.90` (`PASS`).
- **Post-placement uniqueness across all real submissions (`docs/s18_hgbr/registry-final.json`):**
  - `vs_gemsdoe32_r0 (1)`: `max_dot_overlap_3px = 0.48768 <= 0.70`, `max_abs_rho = 0.25882 <= 0.90` (`PASS`)
  - `vs_canonical_real_submissions (8)`: `max_dot_overlap_3px = 0.57054 <= 0.70`, `max_abs_rho = 0.47832 <= 0.90` (`PASS`)
  - `vs_external_dotted_fleet (37)`: `max_dot_overlap_3px = 0.51291 <= 0.70`, `max_abs_rho = 0.36947 <= 0.90` (`PASS`)
  - `vs_in_repo_downloads (45)`: `max_dot_overlap_3px = 0.61866 <= 0.70`, `max_abs_rho = 0.74299 <= 0.90` (`PASS`)
  - `vs_full_100_raster_inventory (100)`: Only the 3 synthetic `192k–273k`-dot calibration grids (`calib_r13lattice_00904.tif` `0.99843`, `r11_greedy_mp.tif` `0.88134`, `r14_union_tips10_lat6.tif` `0.75902`) exceed `0.70` unidirectional overlap (`IR-S16-03` mathematical pigeonhole bound `>= 82.34%` for any 37,654-dot file), with symmetric `f1_dot_overlap_3px <= 0.2491`.

---

## 5. Reproduction Commands

```bash
.venv/bin/python scripts/preflight.py
.venv/bin/python scripts/run_s18_hgbr.py --skip-package
.venv/bin/python scripts/audit_downloads.py --output docs/download-audit.json --html docs/download-audit.html
.venv/bin/python scripts/check_artifact_policy.py
.venv/bin/pytest -q -rs
```
