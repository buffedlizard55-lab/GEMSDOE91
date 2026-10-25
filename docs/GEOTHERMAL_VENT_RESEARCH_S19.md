# Session 19 (`S19-SVHF`) Geothermal-Vent & Concealed-Fault Research Synthesis and Cross-Fleet Forensic Analysis

**Date:** `2026-10-25` (UTC)  
**Repository / Branch:** `buffedlizard55-lab/GEMSDOE91` · `arena/bcc0fcb2-gemsdoe91`  
**Competition:** DrivenData DOE GEMS — *Find the Faults* (`https://www.drivendata.org/competitions/306/competition-doe-gems/`)  
**Official Competition Rules & Metric Specification:** DOE / NREL Technical Report (`https://docs.nlr.gov/docs/fy26osti/96647.pdf`)

---

## 1. Provenance Discipline & Score Labeling (Rule 3)

Every number in this synthesis carries one of four non-interchangeable provenance labels:

1. **`HOLDOUT-DTI`** — computed locally by the unchanged shared hide-and-recover evaluator `vendor/gems57/evaluate_holdout.py` (`evaluator_version = "gems57-pooled-hide-v2"`, `split_sha256 = c79f1acaf337fd548d0873d576a8a3c286d373ae2cb19cfce4464597d448d18a`, `60,988` withheld fault pixels across 4 label-blind spatial quadrants with `80 px = 8,000 m` buffer, `1,000`-draw 20-km physical-block bootstrap 95% CI).
2. **`BLIND-SGMC-PROXY`** — report-only diagnostic Distance-Tolerant IoU (`alpha = 0.2`, `beta = 0.8`, `R = 300 m` triangular kernel) evaluated against USGS SGMC 1:500,000 structural faults (`data/external/derived_sgmc_faults_100m_u8.tif`) strictly `> 300 m` (`62,122` pixels) and `> 500 m` (`56,822` pixels) outside `existing_faults.tif`. Never used in training, feature engineering, or model tuning.
3. **`PUBLIC-LEADERBOARD`** — public DrivenData competition leaderboard reference points (`#1 = 0.4413`, `#50 = 0.2818`).
4. **`USER-REPORTED (unverified — no organizer submission receipt in repo)`** — scores supplied in the task prompt across `GEMSDOE` repositories (`0.2778`, `0.3195`, `0.2478`, `0.2343`, `0.2303`, `0.1917`, `0.1823`, `0.1367`, `0.0255`, etc.). `ORGANIZER-CONFIRMED` remains `null` (`[]` in `docs/fleet-audit.json`) unless a verbatim DrivenData submission receipt screenshot/JSON is committed to the repository.

---

## 2. Official Free Trusted Data & Geothermal Literature Ledger

All scientific mechanisms and datasets used in Session 19 trace to official, free public U.S. government or peer-reviewed geothermal sources:

| ID | Official Source / Dataset / Primary Reference | Verified Link | Geological / Physical Role in `S19-SVHF` | Sandbox Availability & Licence Status |
| :--- | :--- | :--- | :--- | :--- |
| `SRC-01` | DrivenData DOE GEMS Competition Specification & GeoTIFF Format Contract | `https://www.drivendata.org/competitions/306/competition-doe-gems/` | `EPSG:32611`, `3730 × 3292` at `100 m`, single-band `float32` strictly in `[0, 1]`, no `NaN` inside footprint (`5,167,373` active pixels). | Restored & SHA-256 verified (`sample_submission.tif`, `existing_faults.tif`). |
| `SRC-02` | DOE / NREL Official Rules & Distance-Tolerant IoU (Tversky) Specification | `https://docs.nlr.gov/docs/fy26osti/96647.pdf` | Defines asymmetric Tversky DTI ($\alpha = 0.2$ FP weight, $\beta = 0.8$ FN weight, $R = 300\text{ m}$ linear distance-decay kernel) and Appendix A.5 external-data rules (free public access, no labels leakage). | Verified; implemented identically in `vendor/gems57/metric.py`. |
| `SRC-03` | USGS GeoDAWN / INGENIOUS 19-Band Multi-Physics Feature Cube (`gems-geodawn-numerical-features.tif`) | `https://www.usgs.gov/centers/gggsc` · `https://gdr.openei.org/submissions/1391` | Magnetic (`B01,B02,B03,B09,B14`), radiometric total count (`B06`, mislabeled `tc` in header — verified `r=0.9994` vs GeoDAWN TC), geodetic strain (`B04,B07,B08`), earthquake distance/density (`B10,B16`), detrended DEM & slope (`B12,B19`), isostatic gravity (`B05,B11,B13,B18`), basement depth (`B15`), shallow conductivity (`B17`). | Restored & SHA-256 verified (`00e4ffcb8579d6c1...`). |
| `SRC-04` | DOE Geothermal Data Repository — Great Basin INGENIOUS Geochemistry & Spring/Well Compilation (GDR #1391) | `https://gdr.openei.org/submissions/1391` | `1,303` wells/springs inside footprint with measured outlet temperature (`temp_c`) and quartz, chalcedony, and Na-K-Ca cation chemical geothermometers (`geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`). `dist_known_fault_px` column strictly banned (`IR-91-S17-03`). | Restored & SHA-256 verified (`1df195c3c66c6782...`, CC-BY-4.0 / public domain). |
| `SRC-05` | USGS State Geologic Map Compilation (SGMC) — Nevada Structural Faults (Horton et al. 2017, DS-1052) | `https://doi.org/10.3133/ds1052` · `https://mrdata.usgs.gov/sgmc/` | Report-only blind validation mask (`>300 m` and `>500 m` outside `existing_faults.tif`); never enters features, training, calibration, or dot placement. | Restored & SHA-256 verified (`df47607b29c1bd64...`, US-PD). |
| `SRC-06` | USGS Quaternary Fault and Fold Database of the United States (`Qfaults`) | `https://www.usgs.gov/programs/earthquake-hazards/faults` | Explains positive-unlabeled ascertainment bias in `existing_faults.tif`: aerial-photo scarp mapping strongly favors fresh range-front scarps over sub-alluvial intrabasin faults and eroded/buried piedmont scarps. | Public domain reference framework. |
| `SRC-07` | Nevada Bureau of Mines & Geology (NBMG) / Faulds & Hinz (2015), *Structural and Tectonic Controls of Geothermal Activity in the Great Basin Region*, World Geothermal Congress | `https://nbmg.unr.edu/` · `https://gdr.openei.org/` | Documents that `>75%` of Great Basin geothermal systems are **blind** (no surface hot spring or Holocene scarp) and localize at step-overs, relay ramps, fault tips, normal-fault terminations, and fault intersections where dilational fracture permeability persists. | Peer-reviewed structural benchmark motivating `H19-1..H19-3`. |
| `SRC-08` | Pedersen & Rasmussen (1990), *The gradient tensor of potential field anomalies*, Geophysics 55(12); Beiki (2010), *Analytic signals of gravity gradient tensor*, Geophysics 75(6); Cooper & Cowan (2006), Computers & Geosciences 32(10) | `https://pubs.geoscienceworld.org/geophysics` | Full 3-D Laplace spectral gravity gradient tensor $\mathbf{T}_G$, tensor tilt $\cos\theta_G$, and dimensionality invariant $I = -27\det(\mathbf{T}_G)/\|\mathbf{T}_G\|_F^3 \in [-1, 1]$ separating 2-D tabular faults ($I \approx 0$) from 3-D intrusive stocks/calderas ($|I| \to 1$). | Implemented spectrally on official `B13` (`iso_grav_anom`). |
| `SRC-09` | Shepard et al. (2001), *The roughness of natural terrain: a planetary and remote sensing perspective*, JGR 106(E12); Turcotte (1997), *Fractals and Chaos in Geology and Geophysics* | `https://agupubs.onlinelibrary.wiley.com/` | Multi-scale variogram & variance scaling $V(\sigma) \propto \sigma^{2H}$: active alluvial fan aprons vs incised footwall blocks and degraded fault-line scarps produce abrupt cross-strike Hurst-exponent ($H$) and directional semivariogram discontinuities even after `1–2 m` scarps wash out. | Implemented directly on official `B02, B12, B13, B15` (`H19-1`, `H19-2`). |
| `SRC-10` | USGS 3DEP 1-m LiDAR DEM & Copernicus Sentinel-1 InSAR (ASF NASA Earthdata) | `https://www.usgs.gov/3d-elevation-program` · `https://search.asf.alaska.edu/` | Free official sources capable of sub-meter scarp curvature and mm/yr aseismic fault creep. Documented in `H19-4` as external follow-up: sandbox egress permits only GitHub/PyPI/npm, and mirrored `lidar_scarp_features_u8.tif` / `geodawn_rad_u8.tif` carry `"licence unchecked - do not redistribute"` in `registry/data_manifest.json` so both are strictly excluded. | Audited & excluded cleanly under Rules Appendix A.5(1). |

---

## 3. Forensic Analysis: Why `GEMSDOE32` Scored `0.2778`, How `GEMSDOE` Sites Compare, and What `GEMSDOE91`'s Live Scores (`0.1367` & `0.1823`) Prove

### 3.1 Exact Mathematical Anatomy of the `GEMSDOE32` (`0.2778`) Score Trajectory

Let $S \subset \mathcal{F} \setminus \mathcal{C}$ denote a binary dot set of size $N = |S|$, $K(r) = \max(0, 1 - r / 300\text{ m})$ the 300-m triangular kernel (`29` pixels with $K > 0$ on the `100 m` grid), $N_H$ the number of hidden fault pixels in the live evaluation mask, $T = \sum_{y \in H} \max_{d \in S} K(\|y - d\|)$ the distance-weighted true-positive sum, and $F = \sum_{d \in S} (1 - \max_{y \in H} K(\|d - y\|))$ the distance-weighted false-positive sum. With $\alpha = 0.2, \beta = 0.8$:

$$\text{DTI}(S) = \frac{T}{T + 0.2 F + 0.8 (N_H - T)} = \frac{T}{0.8 N_H + 0.2(T + F)}$$

Inspecting the pinned pixel arrays in `data/registry/` reveals three exact steps behind `GEMSDOE32`'s progression (`USER-REPORTED` scores):

1. **Continuous skeleton (`h19-5`, `121,131` active pixels, `0.1922` user-reported) $\to$ Sparse `d >= 2.8 px` dotting (`d2-8`, `44,090` dots, `0.2600` user-reported; `+0.0678` DTI):**  
   Along a continuous 1-pixel ridge, adjacent pixels lie `100 m` apart, so `85%` of each pixel's `300 m` triangular kernel overlaps its neighbors ($\Delta T \approx 0.11$ marginal gain per extra pixel) while every off-fault pixel still incurs a full $+1.0$ false-positive weight ($0.2 \Delta F = +0.20$). Decimating the continuous ridge to `d >= 2.8 px` (`280 m`) cuts $F$ by $\sim 64\%$ while preserving $\sim 93\%$ of $T$, boosting $\text{DTI}$ by **`+0.0678`** without changing the underlying fault detector.
2. **Catalogue-collar pruning (`d2-8`, `44,090` dots, `0.2600` $\to$ `GEMSDOE32 h33-2-b2`, `37,654` dots, `0.2778` user-reported; `+0.0178` DTI):**  
   Because `existing_faults.tif` is masked out of the evaluation target, any dot placed within `200 m` (`2 px`) of a mapped fault primarily covers masked pixels ($T \approx 0$) while remaining inside the active evaluation region ($F \approx +1$). Deleting those `6,436` near-catalogue dots removed pure false-positive mass in the denominator $0.8 N_H + 0.2(T + F)$, raising DTI from `0.2600` to `0.2778`.
3. **Why `0.2778` plateaued below `0.3195` and `#1 = 0.4413` (`PUBLIC-LEADERBOARD`):**  
   At `N = 37,654` dots (`0.2778` user-reported), solving the exact Tversky identity shows that `R0` captures only $T / N \approx 0.13\text{–}0.16$ weighted hidden-fault pixels per dot because `h19-5` is an **uncalibrated hand-crafted ridge formula** lacking: (a) cross-strike potential-field covariance/variogram step detection across buried graben margins, (b) piedmont-toe concave-flexure & fractal Hurst roughness step detection where Holocene fan wash has erased `100 m` slope scarps, and (c) calibrated positive-unlabeled multi-physics learning with cross-fitted axial step-over context. Raising per-dot true-positive efficiency $T / N$ by $+25\%$ at the same `~37,654` sparse budget maps directly into the `0.31–0.34` DTI regime.

### 3.2 Cross-Fleet Comparison Table (Prompt-Listed Sites + Live-to-Holdout Calibration)

We audited both the pixel-level fleet registry (`data/fleet_registry/` + `data/registry/`) and public sibling repositories (`GEMSDOE63`, `GEMSDOE70`, `GEMSDOE73`, `GEMSDOE76`, `GEMSDOE92`, plus `GEMSDOE91`'s own two new user-reported live submissions):

| Site / Artifact | Prompt-Supplied Score (`USER-REPORTED`) | Local `gems57-pooled-hide-v2` (`HOLDOUT-DTI`) | Blind `SGMC >300m` / `>500m` (`BLIND-SGMC-PROXY`) | `>500m / >300m` Retention | Dots $>1\text{ km}$ from Catalogue | Core Architectural Driver & Failure / Success Lesson |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Public Leaderboard `#1`** | `0.4413` (`PUBLIC-LEADERBOARD`) | — | — | — | — | Ceiling demonstrating high recall + high per-dot precision on concealed Great Basin faults. |
| **Prior Target (`Prompt`)** | `0.3195` (`USER-REPORTED`) | — | — | — | — | Requires ~22–28% higher per-dot hidden-fault capture than `GEMSDOE32` at sparse `~38k` dotting. |
| **`GEMSDOE32` (`h33-h33-2-b2`)** | **`0.2778`** (`USER-REPORTED`) | `N/A` (label-blind raster) | `0.095386` / `0.088789` | **`93.1%`** | **`69.8%`** (`median 19.6 px`) | Multi-physics continuous ridge (`h19-5`) + `2.8 px` sparse dotting + `2.0 px` catalogue collar (`37,654` dots). Zero in-sample catalogue halo memorization. |
| **`GEMSDOE70` (`s2-oof38k`)** | **`0.2478`** (`USER-REPORTED`) | `0.2141` (repo-reported OOF) | — | High (OOF) | High (OOF) | **Stitched 4-fold spatially-blocked OOF** dual-population HGB + `300 m` submodular `37,654` dots; beat `GEMSDOE70` S1 (`0.2289`) by `+0.0189`. |
| **`GEMSDOE76` (`ptcf-s2-celf-e3`)** | **`0.2343`** (`USER-REPORTED`) | `0.1591` (5-fold repo split) | — | High (OOF) | High (OOF) | **Piedmont-Toe Concave Flexure (`-∇²_σ z_det > 0`, `AUC=0.5795`)** + analytical upward-continued tilt worms + 2-D OOF context + CELF submodular (`+0.0788` over `0.1555` baseline). |
| **`GEMSDOE63` (`160-world CVaR`)** | **`0.2303`** (`USER-REPORTED`) | — | — | — | — | 160-world worst-case (`CVaR_0.25`) uncertainty-penalized submodular selector (`+0.1301` over `0.1002`). |
| **`GEMSDOE20` (`calib_h195`)** | `0.1922` (`USER-REPORTED`) | — | `0.099167` / `0.097570` | `98.4%` | `58.9%` | Continuous (`121,131 px`) multi-lineament surface before sparse dotting — proves `3×` FP kernel crowding penalty. |
| **`GEMSDOE73` (`seam-free OOF`)** | `0.1917` (`USER-REPORTED`) | — | — | — | — | Seam-free cross-fold probability calibration across spatial fold boundaries. |
| **`GEMSDOE91` (`S17-LFTG E2`)** | **`0.1823`** (`USER-REPORTED`) | **`0.188596`** `[0.1684, 0.2072]` | `0.080522` / `0.058293` | **`72.4%`** (halo drop!) | **`31.5%`** (`43.3% <= 5 px`!) | Pure-subsurface 3-D Laplace gravity tensor + PCAC auto-context. Holdout (`0.1886`) predicted live (`0.1823`) within **`0.0063` DTI**, but **in-sample final refit crammed `43.3%` (`16,304` dots) into `2.25–5 px` around `existing_faults.tif`** and omitted `B12/B19` range-front flexure! |
| **`GEMSDOE91` (`S17-CWPC E3`)** | **`0.1367`** (`USER-REPORTED`) | **`0.122467`** `[0.1095, 0.1367]` | `0.090912` / `0.084701` | `93.2%` | `72.3%` (`median 19.9 px`) | Catalogue-free wavelet phase congruency. Genuine novelty (`<=51.92%` real-model overlap), and `gems57-pooled-hide-v2` (`0.1225`) predicted live (`0.1367`) within **`0.0142` DTI**! |
| **`GEMSDOE51..89` (`0.06–0.16`)** | `0.0616–0.1610` (`USER-REPORTED`) | — | — | — | — | Single-modality edges (pure gravity worms, raw slope, or uncalibrated PU trees without submodular spacing / OOF emission). |
| **`GEMSDOE92` (`0.0255`)** | `0.0255` (`USER-REPORTED`) | — | — | — | — | Catastrophic budget/threshold collapse (`870` sparse dots across all Nevada in `GEMSDOE92` `s1-e3-dthr` / extreme precision starving `beta=0.8` recall). |

### 3.3 Two Critical Empirical Discoveries From Our 12-Raster Live-vs-Proxy Audit

Executing Priority Next Step #2 from `LIMITATIONS_AND_NEXT_STEPS.md` across all 12 pinned rasters established two quantitative laws that govern Session 19:

1. **`gems57-pooled-hide-v2` Tracks Live DrivenData DTI Accurately (`|Δ| <= 0.014`), Whereas Raw `SGMC` Alone Anti-Correlates With Live DTI on Unsupervised Slope Models:**  
   - `S17-CWPC E3` scored `0.084701` on `SGMC >500m` vs `0.058293` for `S17-LFTG E2`, yet on DrivenData `S17-LFTG E2` (`0.1823` user-reported) beat `S17-CWPC E3` (`0.1367` user-reported) by **`+0.0456` DTI** — matching `gems57-pooled-hide-v2` (`0.188596` vs `0.122467`, `+0.0661` DTI)!  
   - Physical reason: USGS `SGMC` (`1:500,000`) maps **Paleozoic/Mesozoic bedrock thrusts and lithologic contacts inside mountain cores**, whereas the DOE GEMS evaluation catalogue maps **Quaternary/Neogene extensional and transtensional geothermal faults**. Therefore `gems57-pooled-hide-v2` MUST remain the sole promotion criterion, while `SGMC >500m / >300m` retention diagnoses **in-sample catalogue-halo overfitting**.
2. **The In-Sample Halo-Crowding & Sibling-Collision Theorem (`IR-91-S17-LFTG-01` + `IR-91-S19-02`):**  
   - Across the entire `5,167,373`-pixel Nevada footprint, only `351,936` pixels lie in the narrow `2.25 < d_cat <= 5.0 px` ring (`269,184` in `3.0 < d_cat <= 5.0 px`), whereas `3,858,215` pixels (`74.7%`) lie `> 1 km` from `existing_faults.tif`.  
   - When `S17-LFTG`, `S17-CPAD`, and `S14-PTAC` refitted their final models **in-sample on 100% of `existing_faults.tif`**, tree splits + spatial auto-context memorized training-fault halos and packed `31.7%–43.3%` (`12,000–16,304` dots, each covering `29` pixels!) into that tiny `269k–352k` pixel collar.  
   - That single architectural flaw simultaneously (a) wasted `~10,000` dots near already-mapped faults (`far >1 km = 31.5%` in `S17-LFTG` vs `69.8%` in `GEMSDOE32`), costing an estimated `0.05–0.08` live DTI, AND (b) forced `82.9%–87.5%` 3-px dot overlap across every in-sample PU model in `GEMSDOE91`!  
   - **Remedy in `S19-SVHF`:** Build a **100% backbone-orthogonal feature cube** (`0` shared `DD+SPAC+PTHA+HVDC` columns), apply **exact per-quadrant empirical quantile/rank-logit standardization**, emit from the **stitched 4-fold spatially-blocked OOF surface** (`0` in-sample label exposure anywhere in Nevada!), and allocate `37,654` binary `{0, 1}` dots via **clean 300-m triangular-kernel CELF submodular cover** (`weight = 0` inside `d_vis <= 3.05 px`, fixing `cpad17.py`'s collar-attraction and `0.36` off-ridge distortion bugs).

---

## 4. Geometric Witness Capacity Audit (`generate_submission.py --preflight`)

Running `python generate_submission.py --preflight` before designing Session 19 confirmed the immutable geometric bound in `registry/comparison_inventory.json`:

- `data/fleet_registry/calib_r13lattice_00904.tif` (`206,895` synthetic lattice dots) covers `5,160,724 / 5,167,373` footprint pixels (`99.871%`) within `300 m`, leaving only `6,649` uncovered pixels (`overlap_lower_bound = 0.823418` for any `37,654`-dot set).
- Two additional blanket rasters (`r14_union_tips10_lat6.tif` at `192,231` dots = `76.20%` footprint 3-px coverage; `r11_greedy_mp.tif` at `272,853` dots = `73.97%` footprint 3-px coverage) cover `> 73.9%` of all Nevada, whereas all `97` remaining unique rasters in `data/` + `docs/downloads/` cover `<= 28.36%` of the footprint (`<= 60,069` dots for all competitive submissions).
- Accordingly, Session 19 enforces `<= 0.90` continuous pre-placement Spearman across **all** available rasters, requires `<= 0.70` 3-px dot overlap against **every real competitive model (`<= 80,000` dots, including all `GEMSDOE32` / `GEMSDOE91` siblings)**, reports the unmodified literal maximum across the dense synthetic blanket witnesses without filtering, and keeps `gems91.readiness.gates()` (`ok_to_submit: False`) fail-closed unless every literal check clears simultaneously.
