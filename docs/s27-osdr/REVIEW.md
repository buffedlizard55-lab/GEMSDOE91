# Session 27 (`S27-CVDC`) PhD Technical Review, Nine-Site Leaderboard Forensics & Verification Ledger

- **Date (UTC):** 2026-10-29
- **Branch:** `arena/7de7860e-gemsdoe91`
- **Preregistration (frozen prior to code/model execution):** `docs/s27-osdr/preregistration.md` (`sha256: df5f5e820fbd3d5265ebcbc888bddf20a17617b859900924cbc39c03f2f3b389`)
- **Generated Research GeoTIFF:** `docs/downloads/gems91-s27-cvdc-e2-37654dots-20261029T160258Z-7652cef9-zeros.tif` (`sha256: 28c610187313bf0493d50c4b56f6387fde5229688c7bed8498ea99a6c41515a0`, `140,275` bytes)
- **Single-TIFF ZIP:** `docs/downloads/gems91-s27-cvdc-e2-37654dots-20261029T160258Z-7652cef9-zeros.zip` (`sha256: 3f96194f69fc0195a11c3e5c385b60b57b710dc5ec2cd5c2a7ba41231f22b8cd`)
- **Organizer Score (`ORGANIZER-CONFIRMED`):** `None` (zero DrivenData portal receipts exist in-repo; `weekly_submission_slots_used = 0`)
- **Automated Verdict:** **`OK TO DOWNLOAD: YES` (research only; 18/18 format & `[0, 1]` checks PASS)** · **`OK TO SUBMIT: NO` (`verdict: "negative"`, 0 weekly slots spent)**

---

## 1. Executive Synthesis of Results

1. **New All-Time `v3`-Buffered Holdout Record in `GEMSDOE91`:** Across 3 preregistered experiments evaluated on the unchanged shared `vendor/gems57` template (`gems57-pooled-hide-v2`, `label-blind-quadrants-v3-feature-buffered`, 80 px whole-component & feature-context buffer, 60,988 withheld positives, exact 37,654 total area-allocated dots), **all three `S27-CVDC` experiments (`E1`, `E2`, `E3`) defeated both the 23-feature base OOF control (`0.125613`) and the reigning `v3` holdout incumbent `S25-FABRIC E2` (`0.146012` paired reproduction; `0.147741` published) with 95% paired spatial-block bootstrap CIs strictly above zero**:
   - **`E1` (`cvdc_e1_stage1_celf`):** `HOLDOUT-DTI = 0.157054` `[0.137985, 0.177503]` (`+0.011042` vs `S25-FABRIC E2`, 95% CI `[+0.003048, +0.019639]`).
   - **`E2` (`cvdc_e2_stage2_ac_celf` — Selected Winner):** **`HOLDOUT-DTI = 0.159482`** `[0.139292, 0.179660]` (**`+0.013470`** vs `S25-FABRIC E2`, 95% CI **`[+0.005260, +0.021892]`**; **`+0.033869`** vs `control_oof_base`).
   - **`E3` (`cvdc_e3_dual_cover_celf`):** `HOLDOUT-DTI = 0.157275` `[0.136937, 0.177639]` (`+0.011264` vs `S25-FABRIC E2`).
2. **Resolution of `S25-FABRIC`'s In-Sample Catalogue-Halo Bug:** By emitting the final 37,654 binary dots strictly from `E2`'s **stitched 4-fold `v3`-buffered OOF surface** (zero in-sample `g.catalogue` training) via 300 m submodular CELF (`uniqueness_cap = 0.64`), `S27-CVDC E2`:
   - Restored median catalogue distance from `S25-FABRIC`'s `5.83 px` (`75.87%` crammed in `(3, 10] px`) to **`19.80 px`** (`49.52%` at `>20 px`), matching `GEMSDOE32`'s natural off-catalogue distribution (`19.65 px` median, `49.20%` at `>20 px`) **without touching LFI or tuning catalogue-distance weights**.
   - Achieved **`#1` blind off-catalogue USGS SGMC recall (`0.112925` all, `0.105560` >500 m)** across all 15 evaluated rasters — outperforming `S25-FABRIC` (`0.079042`, >500 m `0.049414`), `GEMSDOE32` (`0.095386`), all 8 other focus leaders (`0.0934–0.1012`), and `GEMSDOE92 lbmc1` (`0.066984`).
   - Lifted unbiased refitted LFI `MODEL_PROJECTION_NOT_A_SCORE` from `S25-FABRIC`'s `0.07917` to **`0.18967`** (`ridge=1`) / **`0.18294`** (`ridge=10`).
3. **Competitive Uniqueness Verified Across 181 Sparse Fleet Rasters (and Literal Synthetic-Lattice Stop Disclosed):**
   - Pre-placement surface `max |rho| = 0.2067 <= 0.90` across all `211` SHA-verified rasters (`PASS`).
   - Final 37,654-dot 3-px Euclidean overlap: **`45.24% <= 70%`** across all 9 focus leaders (`PASS`), **`27.42% <= 70%`** vs `GEMSDOE92 lbmc1` (`PASS`), and **`60.69% <= 70%`** across all `181` competitive sparse (`<=90k` dots) rasters in the frozen+LFI+sibling fleet (`PASS`).
   - Literal unexempted overlap against the 206,895-dot synthetic 5-px calibration grid `calib_r13lattice_00904.tif` in `registry/comparison_inventory.json` is `99.97%` (mathematically unavoidable floor `>= 82.34%` at 37,654 dots because only `6,649` of `5,167,373` footprint cells lie `>3 px` from that lattice). Together with `lane = null` and Protocol Rule 6, `ok_to_submit` remains `false`.

---

## 2. Forensic Analysis of the Nine Focus Sites (`GEMSDOE24..36`) and `GEMSDOE92` (`0.2784`)

| Site | Best Claimed File | Dots | Claim (`USER-REPORTED`) | LFI `MODEL_PROJECTION_NOT_A_SCORE` (`r=1` / `r=10`) | Blind SGMC DTI (All / >500 m) | Max 3-px Overlap Within 9 Sites | `S27-CVDC` 3-px Overlap vs Site |
|---|---|---:|---:|---:|---:|---:|---:|
| `GEMSDOE32` | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 37,654 | `0.2778` | `0.27342` / `0.27261` | `0.095386` / `0.088516` | `100.00%` (`GEMSDOE24`) | `42.89%` (`UNIQUE`) |
| `GEMSDOE36` | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 38,854 | `0.2750` | `0.27082` / `0.27020` | `0.096770` / `0.089855` | `97.58%` (`GEMSDOE27`) | `43.05%` (`UNIQUE`) |
| `GEMSDOE28` | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 37,660 | `0.2710` | `0.26707` / `0.26791` | `0.093356` / `0.085861` | `100.00%` (`GEMSDOE24`) | `42.76%` (`UNIQUE`) |
| `GEMSDOE31` | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 40,199 | `0.2708` | `0.26842` / `0.26969` | `0.095295` / `0.087682` | `100.00%` (`GEMSDOE24`) | `43.27%` (`UNIQUE`) |
| `GEMSDOE33` | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 41,865 | `0.2632` | `0.26546` / `0.26731` | `0.095683` / `0.088038` | `99.71%` (`GEMSDOE27`) | `43.59%` (`UNIQUE`) |
| `GEMSDOE25` | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 44,090 | `0.2600` | `0.25993` / `0.26280` | `0.094174` / `0.086437` | `100.00%` (`GEMSDOE24`) | `43.33%` (`UNIQUE`) |
| `GEMSDOE30` | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 44,090 | `0.2600` | `0.25993` / `0.26280` | `0.094174` / `0.086437` | `100.00%` (`GEMSDOE24`) | `43.33%` (`UNIQUE`) |
| `GEMSDOE24` | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 60,069 | `0.2477` | `0.25005` / `0.25397` | `0.099911` / `0.091398` | `100.00%` (`GEMSDOE25`) | `44.87%` (`UNIQUE`) |
| `GEMSDOE27` | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 61,328 | `0.2449` | `0.24782` / `0.25176` | `0.101163` / `0.092048` | `98.02%` (`GEMSDOE24`) | `45.24%` (`UNIQUE`) |
| `GEMSDOE92` (context) | `gemsdoe92-lbmc1-35801dots-20261027-89a660f6-zeros.tif` | 35,801 | `0.2784` (`HOLDOUT-DTI: 0.0197`) | `0.25947` / `0.24874` (own `lbm_v1`: `0.3322`) | `0.066984` / `0.071334` | `56.60%` vs `GEMSDOE32` | `27.42%` (`UNIQUE`) |

### Key Mechanistic Findings
1. **Metric-Geometry Coupling (`alpha=0.2, beta=0.8`, 300 m kernel):** Discretizing continuous `H19-5` ridges (`0.1922`, 121k px) into `2.8 px`-spaced isolated `1.0` dots (`GEMSDOE25/30 = 0.2600`, 44,090 dots) preserves almost 100% of the 300 m triangular kernel's `0.8 * FN` recall envelope while slashing `0.2 * FP` volume by ~64%.
2. **Near-Catalogue Collar & Basin-Noise Pruning (`0.2600 -> 0.2778`):** `GEMSDOE32` (`h33-h33-2-b2`, 37,654 dots, `0.2778`) removed ~6,436 near-catalogue (`<=2 px`) and uncorroborated basin-floor dots from `d2.8`, tightening precision without losing range-front step-over coverage.
3. **Why `GEMSDOE92` (`lbmc1 = 0.2784`) Proves Both Submodular Feasibility and Goodhart Risk:** `lbmc1` proved a competitive-unique (`<=70%` overlap) 35,801-dot raster can slightly exceed `0.2778`, but optimizing directly on 123 leaderboard scores inflated its in-model projection to `0.3322` (`+0.0538` above live `0.2784`) while collapsing spatial holdout (`0.0197`) and blind SGMC (`0.0670`).
4. **Path Beyond `0.28` Toward Public `#1 = 0.4544`:** Combining external 1 m USGS 3DEP bare-earth LiDAR scarp curvature (`H27-4`, from official `1m_DEM_links.csv` on unrestricted network infrastructure) with `S27-CVDC`'s subsurface `CVDC + OSDR` potential-field corroboration and 300 m submodular CELF emission is the principled geophysical route to `0.35–0.45+`.

---

## 3. Ranked 5 Geological Hypotheses (`H27-1`..`H27-5`) & Step-by-Step DrivenData Submission Guide

| Rank & ID | Hypothesis & Exact Bands / Transform | Unmapped Mechanism vs Named Mimic | Status & Expected DTI Lift |
|---|---|---|---|
| **#1 · `H27-1`** (**IMPLEMENTED**) | **Rule-of-V Contour–Potential Discordance (`CVDC`) + Sign-Locked Odd-Symmetric Dip-Reversal (`OSDR`) + Multi-Valley Scarp Persistence (`MVSD`):** `B02` DEM contours vs `B11` Bouguer + `B13` THDR + `B18` RTP-mag tangents across 600–2,000 m; signed cross-contact steps across `B11, B12, B15, B17, B19, B06 (rad TC)`; `B15`-gated basin-floor veto | Dipping range-front / relay faults cut elevation contours across drainages while subsurface basement strike stays straight; vetoes flat-lying basalt mesa edges (`CVDC = 0`) and single-canyon talus chutes | **Implemented in `S27-CVDC`:** **`+0.013470` paired `v3` `HOLDOUT-DTI`** vs `S25-FABRIC` (`0.159482`); `#1` blind `SGMC` (`0.112925`) |
| **#2 · `H27-2`** (Unimplemented) | **Radon Slant-Stack Curvature Bifurcation (`RSCB`) for Horsetail Splays & Y-Junctions:** 12-azimuth $31\times 31$ sliding Radon transform on max-normalized `B02` scarp + `B13` THDR + `B18` RTP + `B11` horiz-grad (`R_2/R_1` bimodal peak separation $15^\circ\text{--}45^\circ$) | Catches distributed horse-tail tip splays & conjugate step-over Y-junctions (Faulds & Hinz, 2015) missed by single-azimuth structure tensors; vetoes dendritic alluvial-fan channels via `B11/B18` basement requirement | Low cost (`~25 min` CPU, in-stack); expected `+0.006` to `+0.014` `HOLDOUT-DTI` |
| **#3 · `H27-3`** (Unimplemented) | **Upslope Peclet Back-Projection (`APBP`) of Shallow Clay-Cap Outflow Plumes:** Advective upslope integration ($1\text{--}6\text{ km}$ along $+\nabla\text{B02}$) of `B15`-residualized `B17` shallow MT conductors + OpenEI GDR `#1391` thermal wells/springs to range-margin `B11` gravity steps | Catches blind range-margin feeder faults updip of laterally advected valley smectite clay-cap outflow tongues; `B15` residualization strips closed-basin playa evaporite brines | Low-medium cost (`~20 min` CPU, in-repo GDR `#1391`); expected `+0.005` to `+0.011` `HOLDOUT-DTI` |
| **#4 · `H27-4`** (External 1 m LiDAR) | **USGS 3DEP 1 m Bare-Earth LiDAR Scarp Profile-Curvature (`1m_DEM_links.csv`):** 1 m scarp height/throw & profile curvature ($\partial_{nn}^2 z$ over 5–25 m) + cross-drainage knickpoints aggregated to 100 m and gated by `H27-1` `CVDC + OSDR` | Resolves 1–4 m Holocene alluvial-apron scarps obliterated by 100 m Nyquist averaging; vetoes pluvial Lake Lahontan/Bonneville shorelines (strictly horizontal `dB02/ds = 0`, zero `B11` step) | Moderate cost (`2–4 h` outside sandbox); **highest live ceiling (`+0.04` to `+0.12+` toward `0.35–0.45+`)** |
| **#5 · `H27-5`** (External Seismicity) | **USGS ANSS ComCat Relocated Microseismic Lineament Projection (`1980–2026`):** 3-D RANSAC planar fits to `M >= 1.0`, `sigma_h <= 2 km` swarms projected updip at $55^\circ\text{--}65^\circ$ to `B02` surface & intersected with `B11/B13` steps | Illuminates aseismically creeping / blind critically stressed transfer zones lacking surface scarps; vetoes mine blasts (`depth = 0`, daytime cluster) & volcanic caldera swarms | Low-medium cost (`~45 min` outside sandbox); expected `+0.003` to `+0.009` `HOLDOUT-DTI` |

### DrivenData Upload Checklist (Only After Coordinator / Selector Approval)
1. **Current Gate:** `OK TO DOWNLOAD: YES` · `OK TO SUBMIT: NO` (`docs/s27-osdr/run-card.json` `verdict = "negative"`). Wait for human coordinator/selector review of `calib_r13lattice_00904.tif` policy and weekly slot allocation.
2. **Download & Checksum:** Download [`gems91-s27-cvdc-e2-37654dots-20261029T160258Z-7652cef9-zeros.tif`](../downloads/gems91-s27-cvdc-e2-37654dots-20261029T160258Z-7652cef9-zeros.tif) (`sha256: 28c610187313bf0493d50c4b56f6387fde5229688c7bed8498ea99a6c41515a0`) or [`.zip`](../downloads/gems91-s27-cvdc-e2-37654dots-20261029T160258Z-7652cef9-zeros.zip) (`sha256: 3f96194f69fc0195a11c3e5c385b60b57b710dc5ec2cd5c2a7ba41231f22b8cd`).
3. **Upload & Metadata:** Upload on `https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/` with name `gems91-s27-cvdc-e2-37654dots-20261029T160258Z-7652cef9-zeros` and `<=140`-char note (`91` chars): `S27 CVDC contour-potential discordance+OSDR spatial-OOF CELF 37654d; check run-card verdict`. Record the returned portal confirmation as `ORGANIZER-CONFIRMED`.

---

## 4. Flagged Irregularities & Environment Constraints

- **`IR-91-S12-04` (Verified Directly on GeoTIFF Header & Pixels in S27):** Embedded GDAL band description on Band 06 of `gems-geodawn-numerical-features.tif` states `'tc - Tilt angle or total curvature - magnetic field derivative for edge detection'`, whereas pixel values span `[2.953, 88.57]` (impossible for radians in `[-pi/2, pi/2]`) and correlate at `r = 0.99699` with GeoDAWN airborne radiometric Total Count (`TC`). `S27-CVDC` treats Band 06 strictly as radiometric `TC`.
- **Synthetic 5-px Calibration Lattice in Frozen Registry (`IR-91-S16-01` / `S25-TLF` Retraction):** `data/fleet_registry/calib_r13lattice_00904.tif` (206,895 dots) leaves only `6,649` footprint pixels `>3 px` from a lattice node, capping any literally `<70%`-overlapping submission at `<= 22,163` dots. We preserve the frozen 64-file `registry/comparison_inventory.json` untouched and report both competitive (`60.69% <= 70%` across 181 rasters) and literal (`99.97%`) checks transparently.
- **Sandbox Network Allowlist (`2026-10-29`):** Outbound connections in this sandbox are restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`. Live fetches to `www.drivendata.org`, `rockyweb.usgs.gov` (USGS 3DEP 1 m LiDAR), and `earthquake.usgs.gov` (ANSS ComCat) are blocked here and documented explicitly rather than simulated.
- **Host Hardware Ceiling:** `2` vCPUs, `3.8 GiB` RAM, `0 B` swap; mitigated via uncompressed `float32`/`float16` `np.memmap` streaming (`peakRSS <= 2.61 GiB` during nested 2-stage cross-fitting).
