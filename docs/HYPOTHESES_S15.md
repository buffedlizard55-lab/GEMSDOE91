# Session 15 Pre-Registered Hypotheses (`S15-HCPA`, 2026-10-25)

**Status:** Pre-registered and frozen *prior* to running any Session 15 holdout score or emitting any candidate GeoTIFF.
**Branch:** `arena/b580c734-gemsdoe91`
**Lane:** *Hydrothermal Convective Plume & Kinematic Dilatancy Architecture (`S15-HCPA`).*

---

## 0. Forensic Analysis: Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` Scored 0.2778 and How to Beat It

### A. Mathematical Metric Dynamics (DTI Emission Economics)
The DrivenData GEMS competition evaluates predictions using the Discrete Tversky Index with a 300 m triangular decay kernel ($r = 3$ pixels at 100 m cell size) and parameters $\alpha = 0.2, \beta = 0.8$:
$$\text{DTI} = \frac{T}{\alpha T + \alpha(S - M) + \beta |G|} = \frac{T}{0.2 T + 0.2(S - M) + 0.8 |G|}$$
where:
- $|G|$ is the constant number of ground truth fault pixels (e.g. 60,988 withheld positives).
- $S = \sum_j p_j$ is the total mass emitted.
- $T = \sum_{i \in G} \max_j (p_j \cdot K(d(i, j)))$ is the kernel coverage credit.
- $M = \sum_j p_j \cdot \max_{i \in G} K(d(i, j))$ is the mass credited to ground truth.

Crucially, because $T$ computes the **pointwise maximum** ($\max_j$) over all emitted dots rather than a sum, once a true fault pixel is covered by a unit dot ($p_j = 1.0$), any second dot placed within 300 m yields **zero additional credit** ($\Delta T \approx 0$). However, every additional redundant dot adds directly to total emitted mass $S$. In false positive or misaligned areas ($M = 0$), each extra dot adds $\alpha \cdot 1.0 = 0.2$ directly into the denominator!

Consequently, contiguous line predictions or clustered dot clouds waste mass:
- A continuous line places dots at 1.0 px (100 m) spacing, consuming $3\times$ more mass than spaced dots for nearly identical $T$.
- Thinning along lineaments to dots spaced at $\ge 2.8$ to $3.16$ px ($\approx 300$ m) cuts mass $S$ by $3.3\times$ while preserving $T$.
- This explains the empirical climb of the GEMSDOE fleet:
  - 123k solid dots (spacing 1.0 px): scores 0.1855 – 0.1922.
  - 60k thinned dots (spacing 2.2 px): score jumped to 0.2477.
  - 44k thinned dots (spacing 3.16 px): score jumped to 0.2600.
  - 40k thinned dots (spacing 3.0 px): score jumped to 0.2708.
  - 37,654 dots at 3.16 px spacing (`h33-h33-2-b2`): **0.2778**.

### B. Far-Field Blind Fault Targeting
In Basin and Range extensional tectonics, mapped faults in the USGS Quaternary Fault and Fold Database are concentrated along mountain fronts where bedrock or alluvial scarps are exposed. The competition test set targets **undiscovered/blind faults** that host hydrothermal geothermal circulation. Emitting dots in the immediate halo of known faults ($\le 10$ px / $\le 1$ km) yields a high local holdout score (when withholding known fault segments), but fails on the true competition test set because the known fault halo is already thoroughly explored.
- The 0.2778 winner placed **69.8% of its dots in the far-field** (> 10 px / > 1 km from catalogue), with 0 dots on catalogue.
- Spearman correlation with organizer scores: `frac_dots_gt10px_of_catalogue` $\rho = +0.857$, `median_nn_spacing_px` $\rho = +0.898$, `n_dots` $\rho = -1.000$.

### C. How to Score Higher Than 0.2778 Toward 0.3195 and 0.4413
At 37,654 dots, 0.2778 corresponds to an average credit per dot of $T / S \approx 0.139$.
To reach 0.3195 requires $T / S \approx 0.160$. To reach the leaderboard record 0.4413 requires $T / S \approx 0.220$.
Because emission geometry is already near-optimal (37,654 dots at 3.16 px spacing), **beating 0.2778 requires a significantly more accurate geological probability surface in the far-field basins and pediments**.
Specifically, Session 15 addresses the blind geothermal discovery problem directly using physical tracers of hydrothermal circulation and crustal strain.

---

## 1. Five Candidate Geological Hypotheses

| Rank | ID | Layer(s) Involved | Physical Signature | Why It Catches *Uncatalogued* Faults | Non-Fault Mimic & Rejection | Difference vs Repo History | Expected DTI / Cost |
|---:|---|---|---|---|---|---|---|
| **1** | **H15-1 Hydrothermal Convective Plume & Basement Architecture (`HCPA`)** | `cond_surf` (Band 17), `depth_to_base_surf` (Band 15), `iso_grav_anom_hg` (Band 18), `gdr_wellspring_in_footprint.csv` | High subsurface electrical conductivity plume capped by clay, aligned with basement gradient $\nabla z_{base}$ and geothermometer reservoir heat flux ($T_{res} > 150^\circ\text{C}$) | Blind geothermal systems (Desert Peak, Tungsten Mountain) have NO surface scarps; they are expressed solely by subsurface saline fluid plumes, clay caps, and buried basement offsets | Conductive saline playas (dry lakes) without basement offsets $\rightarrow$ rejected by requiring cross-concordance with basement gravity gradient | No prior lane combined 3D conductivity depth with geothermometer heat flux and basement gradient vectors | **High** / Low |
| **2** | **H15-2 Tectonic Kinematic Dilatancy & Slip Tendency (`TKST`)** | `geod_dilaterate` (Band 8), `geod_shearrate` (Band 7), `geod_2ndinv` (Band 4), LiDAR strike (Band 11) | Normalized Coulomb slip tendency $T_s = \|\sin(2(\theta - \theta_{ext}))\|$ and dilation propensity $T_d = \sin^2(\theta - \theta_{ext})$ along fault strikes under WNW ($\sigma_3 \approx 105^\circ$) extension | Critically stressed faults in the Walker Lane / Basin and Range transition slip aseismically and remain open to fluid flow without forming large visible scarps | Regional diffuse strain without structural shear localization $\rightarrow$ gated by geodetic 2nd invariant shear gradients | S12 used scalar strain magnitude; TKST resolves kinematic tensor stress onto local strike | **High** / Low |
| **3** | **H15-3 Radiometric K-Metasomatism & Magnetite Leaching (`RTNL`)** | `geodawn_rad_u8.tif` ($K, Th, U, TC$), `tmi_vg` (Band 9) | Directional cross-strike potassium enrichment $\nabla_\perp (K / Th)$ coincident with negative magnetic vertical gradient ($tmi\_vg < 0$) | Hydrothermal alteration along active blind conduits metasomatically introduces adularia/illite ($K$) while destroying magnetite, leaving a distinct geochemical footprint in basin fill | Felsic plutons (high background $K$) $\rightarrow$ rejected by requiring negative magnetic susceptibility contrast and linear geometry | Prior lanes only used raw total count (TC) or simple log-ratios without directional derivative or magnetic destruction coupling | **Medium** / Low |
| **4** | **H15-4 Multiscale Topographic Concavity & Scarp Toe (`MTCS`)** | `det_elev` (Band 12), `det_elev_slope` (Band 19), `lidar_scarp_features_u8.tif` (`step_max`, `lapneg_max`, `coh100`) | Asymmetric slope-break with negative Laplacian crest and depositional toe concavity $\kappa$ persisting $>500$ m along strike | Sub-meter Holocene alluvial fan scarps degraded by erosion that were missed on 1:250k regional maps | Pluvial lake shoreline benches $\rightarrow$ rejected by requiring strike concordance with tectonic extension rather than elevation contours | Prior lidar models used raw slope deciles; MTCS isolates profile curvature asymmetry | **Medium** / Med |
| **5** | **H15-5 Submodular Winner-Geometry Emission (`SOFE`)** | Fused posterior of H15-1 + H15-2 + H15-3, `existing_faults.tif`, DTI greedy selector | Exact submodular DTI selection: $p_j \in \{0, 1\}$, $d_{min} = 3.16$ px spacing, $N = 37,654$ unit dots, $\ge 70\%$ far-field allocation | Matches the empirical geometry of `h33-h33-2-b2` (0.2778) while placing dots according to our superior multi-sensor convective plume and kinematic dilatancy surface | Over-clustering in known fault halos $\rightarrow$ prevented by hard 25% halo cap and 75% far-field quota | Fixes the DTI emission economics fleet-wide | **High** / Low |

---

## 2. Experimental Plan (Budget: 3 Experiments)

- **Experiment 1 (E1 — Surface):** Train HistGradientBoosting ensemble combining H15-1 (HCPA convective plume features), H15-2 (TKST kinematic dilatancy), H15-3 (RTNL alteration), and base geophysical layers. Evaluate on 4-fold spatially-blocked holdout set (60,988 withheld positives, 1 km buffer). Compute single-feature leakage canaries (fail if AUC > 0.90).
- **Experiment 2 (E2 — Multiphysics Corroboration Gate):** Apply multi-family corroboration gate (hydrothermal plume $\times$ kinematic strain $\times$ structural scarp step). Score on holdout set.
- **Experiment 3 (E3 — Winner-Geometry Emission & S15 Candidate Generation):** Full-map submodular emission with winner geometry ($N = 37,654$ unit dots, $d_{min} = 3.16$ px, $\ge 70\%$ far-field). Re-validate from written bytes across all 5 validator suites. Run registry and sibling uniqueness checks. Produce validated `.tif`, `.zip`, JSON run card, and audit portal.

---

## 3. Data Sources & Verification (Zero External Downloads Needed)
All required data inputs are already pinned, verified, and present in `data/`:
1. `data/bridge/gems-geodawn-numerical-features.tif` (19 bands, 418 MB, SHA-256 `4371c82e3b8339b8...`)
2. `data/official/sample_submission.tif` (footprint, 1.6 MB, SHA-256 `2176d08e485aa2cd...`)
3. `data/official/existing_faults.tif` (catalogue, 425 KB, SHA-256 `7ba308ccdc4418b3...`)
4. `data/external/gdr_wellspring_in_footprint.csv` (27,092 records, 2.1 MB, SHA-256 `122718e65bdf55aa...`)
5. `data/external/lidar_scarp_features_u8.tif` (12 bands, 36.9 MB, SHA-256 `d580bb8bdcdb941e...`)
6. `data/external/geodawn_rad_u8.tif` (4 bands, 26.6 MB, SHA-256 `c22420f75999030d...`)
7. `data/external/derived_sgmc_faults_100m_u8.tif` (USGS SGMC control, 198 KB, SHA-256 `643cbe992ef4ba37...`)
