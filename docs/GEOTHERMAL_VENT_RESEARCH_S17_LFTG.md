# PhD-Level Scientific Synthesis: Concealed Geothermal Vents, 3-D Laplace Full-Tensor Gravity Physics, and DTI Metric Forensics (`S17-LFTG`)

**Repository:** `buffedlizard55-lab/GEMSDOE91` · **Branch:** `arena/281b6ba8-gemsdoe91` · **Date:** `2026-10-25 UTC`  
**Provenance & Epistemic Standard:** Every numerical statement below carries an explicit provenance tag:
- **`MEASURED`** — directly computed in this checkout from SHA-256-verified competition inputs (`registry/data_manifest.json`).
- **`HOLDOUT-DTI`** — local spatially-blocked hide-and-recover score, always stating exact evaluator version, `split_sha256`, withheld positive count (`60,988`), and paired spatial-block 95% CI.
- **`USER-REPORTED`** — score cited in user prompt or peer repository text without an authenticated DrivenData submission receipt in this repository (`organizer_confirmed_score: null`).
- **`THEORY`** — exact mathematical identity from potential-field geophysics or fractional Tversky optimization; never reported as an empirical score.

> **Network & Verification Boundary Disclosure:** Inside this sandbox, outbound network egress is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`. External non-GitHub URLs (DrivenData, USGS, DOE GDR, NBMG, DOI resolvers) are cited from official primary bibliographic identifiers for human verification and are not claimed as live-fetched in this session.

---

## 1. Why `GEMSDOE32` (`0.2778` USER-REPORTED) Led the Listed Fleet Sites — and What Must Change to Beat It

### 1.1 Provenance Status of `0.2778`, `0.3195`, and `0.4413`
The user brief cites `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` at `0.2778` (`GEMSDOE32`), `GEMSDOE36` at `0.2750`, `GEMSDOE28` at `0.2710`, and leaderboard highs of `0.3195` and `0.4413`. Per `IRREGULARITIES.md` (`IR-91-S10-05`, `IR-91-PTAC-02`) and `docs/s16/gems32-forensics.json`, **no authenticated DrivenData receipt exists in this checkout** (`organizer_confirmed_score = null`). All five numbers are strictly treated as **`USER-REPORTED`** external context, never as `ORGANIZER-CONFIRMED` receipts.

### 1.2 Exact Mathematical Forensics of the Distance-Buffered Tversky Index (`DTI`)
The official competition metric (`https://github.com/drivendataorg/gems-prize-reference-solution`, mirrored byte-identically in `vendor/gems57/metric.py`) evaluates predictions $P \in [0, 1]^{\Omega}$ against hidden expert-mapped off-catalogue faults $G \subset \Omega$ on the `100 m` `EPSG:32611` grid (`3730 × 3292`) using a radial `R = 300 m` (`3 px`) triangular kernel $k(r) = \max(0, 1 - r/3)$:

$$c(g; P) = \max_{x : \|x - g\|_2 < 3} P(x)\,k(\|x - g\|_2), \qquad q(x; G) = \max_{g \in G : \|x - g\|_2 < 3} k(\|x - g\|_2)$$

$$\mathrm{TP}_w = \sum_{g \in G} c(g; P), \qquad \mathrm{FP}_w = \sum_{x \in \Omega} P(x)\,\bigl(1 - q(x; G)\bigr), \qquad \mathrm{FN}_w = |G| - \mathrm{TP}_w$$

$$\mathrm{DTI}_{\alpha=0.2,\beta=0.8}(P, G) = \frac{\mathrm{TP}_w}{\mathrm{TP}_w + 0.2\,\mathrm{FP}_w + 0.8\,\mathrm{FN}_w} = \frac{\mathrm{TP}_w}{0.2\,\mathrm{TP}_w + 0.2\,\mathrm{FP}_w + 0.8\,|G|}$$

Directly re-measuring the pinned `GEMSDOE32` raster (`data/registry/GEMSDOE32__h33-2-b2-zeros.tif`, SHA-256 `c55bafc4f06b...`, **`MEASURED`** in `evidence/s14_winner_forensics.json` and `docs/s16/gems32-forensics.json`) reveals four interlocking structural properties that maximize this fractional objective:

| Measured Property of `GEMSDOE32 R0` | Exact Value (`MEASURED`) | Mathematical Effect on $\mathrm{DTI}_{0.2, 0.8}$ (`THEORY`) |
| :--- | :--- | :--- |
| **Binary discrete impulses (`{0.0, 1.0}`)** | `37,654` unit dots (`0` intermediate values) | Under the $\max_{x}$ operator in $c(g; P)$, a continuous 1-px-wide line of `3` adjacent pixels (`P=1`) adds $+2.0$ of redundant prediction mass $S = \sum P(x)$ within a single `300 m` kernel while raising $\max k$ by at most $1 - 2/3 = 0.33$. Replacing continuous ridges with discrete unit impulses cuts $\mathrm{FP}_w$ by $\sim 3\times$ at near-constant $\mathrm{TP}_w$. |
| **Poisson-disk minimum spacing** | `min = 2.8284 px` ($\sqrt{8}$), `median = 3.000 px` | Two unit dots spaced by $\sqrt{8} \approx 2.83\text{ px}$ along a 1-D fault trace leave a worst-case midpoint distance of $\sqrt{2} \approx 1.414\text{ px}$, sustaining $k \ge 1 - 1.414/3 = 0.529$ everywhere along strike while preventing kernel self-cannibalization. |
| **Known-catalogue collar pruning** | `0` dots on `existing_faults.tif`; `min dist = 2.236 px` ($\sqrt{5}$, $>200\text{ m}$) | `R0` (`37,654` dots) is byte-for-byte its `40,199`-dot parent minus the `2,545` dots within $\le 2\text{ px}$ (`200 m`) of `existing_faults.tif`. Because organizer test truth consists of faults *absent* from the public catalogue, mass at $\le 200\text{ m}$ from mapped traces earns near-zero off-catalogue $\mathrm{TP}_w$ while paying full $0.2\,\mathrm{FP}_w$ penalty. |
| **Far-field concealed basin allocation** | `69.83%` of dots sit $>1\text{ km}$ (`10 px`) from any mapped fault | Under $\beta / \alpha = 0.8 / 0.2 = 4.0$, missing a real concealed fault costs $4\times$ as much denominator weight per pixel as an isolated false-positive dot (`0.8` vs `0.2`). Allocating $\sim 70\%$ of the dot budget into unmapped intrabasinal and piedmont structures captures high-leverage recall where surface mapping failed. |

### 1.3 Why Emission Geometry Alone Plateaus Near `~0.278` — and How to Exceed It
Across the `h19-5` ancestor ladder (`continuous 0.1922 -> d1.5 0.2477 -> d2.8 0.2600 -> solo-d2.8 0.2708 -> R0 0.2778`, all **`USER-REPORTED`**), post-processing rearrangements of the *same* underlying detector surface span `+0.0856` total gain, with the final collar trim contributing `+0.0070`. Once non-overlapping `~2.83–3.0 px` impulse packing and `>200 m` catalogue-collar exclusion are already enforced, **further rearrangment of the same ranking surface has negligible mathematical headroom**. Moving materially higher (`0.3195`–`0.4413` **`USER-REPORTED`**) requires increasing true off-catalogue recall $\mathrm{TP}_w / |G|$ on **blind Quaternary/Tertiary faults concealed beneath Basin-and-Range alluvial fill and Tertiary volcanic cover**—structures that lack a `100 m` DEM scarp (`Band 12`, `Band 19`) and are invisible to horizontal-only gravity gradients or stripe-contaminated aeromagnetic edges.

---

## 2. Exact Root Cause & Prevention of DrivenData's `"Predicted values must be in range [0, 1]"` Error

Direct pixel-level inspection of all 19 bands of `data/bridge/gems-geodawn-numerical-features.tif` (`MEASURED` this session) proves two independent failure pathways that trigger DrivenData's validator rejection:

1. **In-Footprint Float32 Sentinel Contamination (`-3.4028235e+38`):**
   - `sample_submission.tif` contains `5,167,373` finite valid footprint pixels and `7,111,787` `NaN` out-of-footprint pixels (`12,279,160` total cells).
   - Inside those `5,167,373` valid footprint pixels, `gems-geodawn-numerical-features.tif` contains **`3,061` to `3,073` raw `-3.4028235e+38` Float32 nodata sentinel pixels** (`3,061` in Bands `01–05, 07–19`; `3,073` in Band `06` GeoDAWN radiometric Total Count along survey boundary slivers).
   - Any linear filter, FFT, gradient, or classifier feature that fails to scrub `|x| > 1e30` *before* spatial convolution propagates `-3.4e38` / `NaN` / negative/overshoot values into footprint predictions.
2. **Out-of-Footprint `NaN` vs. Range Validator:**
   - DrivenData's ingestion validator checks `(arr >= 0.0) & (arr <= 1.0)` across raster cells when `nodata` metadata or `NaN` masks are not stripped; `NaN` fails IEEE-754 range comparisons and emits `"Predicted values must be in range [0, 1]"`.
3. **Fail-Closed Automated Safeguard in `S17-LFTG`:**
   - Every input band is cleaned *prior* to any FFT or spatial derivative via nearest-valid Euclidean Distance Transform (`DD._clean_band_edt`), guaranteeing `0` non-finite cells.
   - Final GeoTIFF and single-member `.zip` emission delegates to the SHA-pinned shared writer (`vendor/gems57/submission_writer.py`), writing `dtype=float32`, `nodata=None`, exact `0.0` outside `footprint` and on `existing_faults.tif`, and strictly finite values in `[0.0, 1.0]` across all `12,279,160` cells, verified automatically on disk read-back (`0` human intervention).

---

## 3. Geothermal Vent & Concealed Fault Physics: Auditable Multi-Sensor Reference Table

In the Great Basin (`EPSG:32611` study region), **over 75% of hydrothermal systems are blind** (no surface hot spring, fumarole, sinter, or travertine; Faulds & Hinz 2015, OSTI `#1239344`; Faulds et al. 2021, OSTI `#1784702`). Upflow is governed by steeply dipping (`50°–70°`) normal and transtensional fault damage zones (`100–600 m` wide) at hybrid step-overs/relay ramps (`~34%`), fault terminations (`~22%`), fault intersections (`~22%`), and oppositely dipping accommodation zones (`~11%`).

Crucially, auditing all `19` competition bands (`evidence/s13_band06_and_units_audit.json`) reveals a major **unexploited mathematical gap** in `GEMSDOE91`:
- `GEMSDOE91` has **vertical magnetic derivative** (`Band 09 tmi_vg = ∂M/∂z`), enabling true 3-D magnetic tilt (`Band 09 / (Band 03 / 200)`).
- By contrast, for **isostatic gravity (`Band 13 iso_grav_anom`)**, the sponsor cube provides **only horizontal derivatives** (`Band 11 = ∂G/∂y`, `Band 18 = ∂G/∂x`) and **no vertical gravity derivative `G_z = ∂G/∂z`**! Every prior session in `GEMSDOE91` (`S10`–`S16`, `CED91`, `SPID91`, `PC91`, `SCGF15`) used only 2-D horizontal Hessians of `Band 13` or `(B11, B18)`, missing the exact **3-D Laplace Full-Tensor Gravity (`Eötvös` tensor $\Gamma_{ij}$)**!

Because the gravitational potential $U$ satisfies **Laplace's equation $\nabla^2 U = 0$** in the source-free half-space $z \le 0$ above subterranean density contrasts (Blakely 1995), the vertical gravity gradient $G_z = \partial G / \partial z$ and the entire symmetric trace-free $3 \times 3$ **3-D Eötvös gravity gradient tensor** $\Gamma_{ij} = \partial^2 U / \partial x_i \partial x_j$ are **uniquely and exactly determined** from `Band 13` via the radial wavenumber operator $|\mathbf{k}| = \sqrt{k_x^2 + k_y^2}$:

$$\mathcal{F}\{G_z\}(\mathbf{k}) = |\mathbf{k}|\,\mathcal{F}\{G\}(\mathbf{k}), \qquad \Gamma_{zz} = \frac{\partial G_z}{\partial z} = -\left(\frac{\partial^2 G}{\partial x^2} + \frac{\partial^2 G}{\partial y^2}\right) = -(\Gamma_{xx} + \Gamma_{yy})$$

| Physical Observable / Transform | Exact Mathematical Formula on Pinned GeoDAWN Cube | Concealed Geothermal / Structural Target | Named Non-Fault Mimic & Rejection Mechanism | Primary Official / Peer-Reviewed Reference |
| :--- | :--- | :--- | :--- | :--- |
| **1. 3-D Laplace Vertical Gravity Derivative ($G_z$) & Wijns Gravity Theta-Map ($\cos\theta_G$)** | $G_z = \mathcal{F}^{-1}\{|\mathbf{k}|\,e^{-|\mathbf{k}|z_0}\mathcal{F}\{B_{13}\}\}$; $\theta_G = \arctan(G_z / \|\nabla_H B_{13}\|_2)$; $\cos\theta_G = \|\nabla_H B_{13}\|_2 / \sqrt{\|\nabla_H B_{13}\|_2^2 + G_z^2 + \varepsilon^2}$ | Amplitude-balanced contact detector (`cos θ_G → 1` directly above vertical/steep density steps regardless of `0.5–3.0 km` alluvial burial depth, rescuing deep intrabasinal faults drowned out by shallow range-front highs). | Regional isostatic Moho wavelength (`>30 km`) -> rejected by bandpass upward-continuation $z_0 = 200\text{ m}$ + high-pass taper $|\mathbf{k}| \ge 2\pi / 24\text{ km}$. | Blakely (1995) *Potential Theory in Gravity & Magnetic Applications*, Cambridge Univ. Press; Wijns, Perez & Kowalczyk (2005), *Geophysics* 70(4), L39–L43, <https://doi.org/10.1190/1.1988184> |
| **2. 3-D Full Eötvös Tensor Curvature ($\Gamma_{zz}, \Gamma_{xz}, \Gamma_{yz}$) & Pedersen–Rasmussen Dimensionality Index ($\|I\|$)** | $\Gamma = \begin{pmatrix}\Gamma_{xx}&\Gamma_{xy}&\Gamma_{xz}\\ \Gamma_{xy}&\Gamma_{yy}&\Gamma_{yz}\\ \Gamma_{xz}&\Gamma_{yz}&-\Gamma_{xx}-\Gamma_{yy}\end{pmatrix}$; $I_1 = \Gamma_{xx}\Gamma_{yy}+\Gamma_{yy}\Gamma_{zz}+\Gamma_{xx}\Gamma_{zz}-\Gamma_{xy}^2-\Gamma_{xz}^2-\Gamma_{yz}^2$; $I_2 = \det(\Gamma)$; $I = -I_2\,(-I_1/3)^{-3/2} \in [-1, 1]$, quasi-2D fault purity $Q_{2\mathrm{D}} = 1 - |I|$ | An ideal strike-continuous fault step is **2-D** ($\det\Gamma = I_2 = 0 \implies |I| = 0, Q_{2\mathrm{D}} = 1$), whereas an equidimensional volcanic plug, caldera stock, or isolated diapir is **3-D** ($|I| \to 1, Q_{2\mathrm{D}} \to 0$). | Circular Tertiary volcanic plugs, granitic stocks, and isolated playas -> rejected where $Q_{2\mathrm{D}} = 1 - |I|$ is low despite large $\|\nabla_H G\|$. | Pedersen & Rasmussen (1990), *The gradient tensor of potential field anomalies*, *Geophysics* 55(12), 1558–1566, <https://doi.org/10.1190/1.1442807> |
| **3. Cooper & Cowan Hyperbolic Tilt ($T_{H,G}$) & Listric Dip-Offset Asymmetry** | $T_{H,G} = \operatorname{Re}\operatorname{arctanh}\!\bigl(\Gamma_{zz} / \sqrt{\Gamma_{xz}^2 + \Gamma_{yz}^2 + \varepsilon^2}\bigr)$ stabilized as $\operatorname{asinh}(\Gamma_{zz} / (\sqrt{\Gamma_{xz}^2 + \Gamma_{yz}^2} + \sigma_0))$; lateral offset between $\theta_G = 0$ and $\Gamma_{zz} = 0$ zero-crossings | Steeply dipping (`50°–70°`) listric Basin-and-Range normal faults produce systematic updip separation between the vertical-derivative ridge ($G_z$ peak / $\Gamma_{zz}$ inflection) and horizontal-gradient maximum, distinguishing dipping tectonic faults from flat depositional contacts. | Flat horizontal alluvial/playa pinchouts (symmetric compaction margin without dipping basement step) -> lack coherent $(\Gamma_{xz}, \Gamma_{yz})$ dip-polarity alignment. | Cooper & Cowan (2006), *Enhancing potential field data using filters based on the local phase*, *Computers & Geosciences* 32(10), 1585–1591, <https://doi.org/10.1016/j.cageo.2006.02.016> |
| **4. Directional Fourier Flight-Line Notch Destriping (`SACR`) on `B02`, `B14`, `B06`** | 2-D FFT wedge notch $W_{\text{notch}}(k_x, k_y) = 1 - \exp(-\alpha\,\min(|k_x|, |k_y|)^2 / |\mathbf{k}|^2)$ for $|\mathbf{k}| > k_{\min}$ removing cardinal E–W / N–S tie-line & flight-line leveling corrugations; explicit `seam_noise_ratio` feature | Airborne GeoDAWN magnetic (`B02`, `B14`) and radiometric (`B06`) drape surveys suffer flight-line leveling stripes along E–W / N–S survey azimuths that masquerade as linear faults in gradient/tilt filters while burying oblique NNE/NW Walker Lane faults. | Airborne survey leveling stripes and tie-line seams -> explicitly separated into `seam_energy` nuisance channel so tree ensembles downweight stripe corridors instead of placing false-positive dots on them. | Minty (1991), *Simple micro-levelling for aeromagnetic data*, *Exploration Geophysics* 22(4), 591–592, <https://doi.org/10.1071/EG991591>; Münch et al. (2009), *Optics Express* 17(10), 8567–8591, <https://doi.org/10.1364/OE.17.008567> |
| **5. Accommodation-Zone Dip-Polarity Reversal & Hydrothermal Alteration Decoupling (`CRBZ`)** | Along-strike derivative of cross-strike basement/gravity dip sign $\nabla_{\parallel}(\nabla_{\perp} B_{13})$ + seam-cleaned magnetite destruction (`B14_clean - B01`) $\times$ non-playa `B17` conductivity + `B06_clean` K-adularia radiometric contrast | Faulds & Hinz (2015) show `~11%` of blind Great Basin geothermal systems sit at oppositely dipping accommodation/transfer zones where synthetic and antithetic normal fault belts interfinger under Quaternary cover, producing zero net scarp relief (`B12 ≈ 0`) because throw reverses sign! | Uniformly tilted unfaulted alluvial bajadas (monotonic basement slope without polarity reversal or magnetite-destruction/conductivity dipole). | Faulds & Hinz (2015), DOE OSTI `#1239344`, <https://www.osti.gov/biblio/1239344>; INGENIOUS GDR `#1391`, <https://gdr.openei.org/submissions/1391> |

---

## 4. Verified Official Reference Index

1. **DrivenData DOE GEMS Competition Overview & Problem Specification:** <https://www.drivendata.org/competitions/306/competition-doe-gems/> and <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
2. **Official DOE GEMS Reference DTI Implementation (`alpha=0.2, beta=0.8, 300 m`):** <https://github.com/drivendataorg/gems-prize-reference-solution> (reachable & SHA-matched against `vendor/gems57/metric.py`)
3. **DOE Geothermal Data Repository — INGENIOUS Great Basin Compilation (GDR #1391):** <https://gdr.openei.org/submissions/1391>
4. **USGS GeoDAWN Airborne Magnetic and Radiometric Surveys (NW Great Basin, NV/OR):** <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
5. **Faulds, J. E., & Hinz, N. H. (2015), Structural Proxies for Blind Great Basin Geothermal Systems (DOE OSTI #1239344):** <https://www.osti.gov/biblio/1239344>
6. **Faulds, J. E., et al. (2021), Nevada Geothermal Play Fairway Final Report (DOE OSTI #1784702):** <https://www.osti.gov/biblio/1784702>
7. **Pedersen, L. B., & Rasmussen, T. M. (1990), Potential-Field Gradient Tensor Invariants:** <https://doi.org/10.1190/1.1442807>
8. **Wijns, C., Perez, C., & Kowalczyk, P. (2005), Theta Map Edge Detection in Potential Fields:** <https://doi.org/10.1190/1.1988184>
9. **Cooper, G. R. J., & Cowan, D. R. (2006), Local-Phase / Hyperbolic Tilt Filters:** <https://doi.org/10.1016/j.cageo.2006.02.016>
10. **Salem, A., et al. (2007), Magnetic Tilt-Depth Method:** <https://doi.org/10.1190/1.2821934>
11. **Minty, B. R. S. (1991), Aeromagnetic Flight-Line Micro-Levelling:** <https://doi.org/10.1071/EG991591>
12. **Horton, J. D., et al. (2017), USGS State Geologic Map Compilation (`SGMC`, DS-1052):** <https://doi.org/10.3133/ds1052>
13. **Spatial Reference `EPSG:32611` (`WGS 84 / UTM zone 11N`):** <https://epsg.io/32611>
