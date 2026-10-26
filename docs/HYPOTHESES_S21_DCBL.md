# Preregistration S21-DCBL — Deep-Cover Basin Lineament (DCBL) lane, 5 ranked hypotheses — 2026-10-26

**Branch:** `arena/6b5a64ab-gemsdoe91`
**Preregistered UTC:** `2026-10-26T06:00:00Z` — written *before* any S21 holdout number or TIF was computed.
**Lane (single method paragraph, PARALLEL-RUN PROTOCOL Rule 1):**

> **Deep-Cover Basin Lineament (DCBL) lane:** Detect concealed intrabasinal normal faults buried under 0.3–2.5 km of Quaternary alluvium by (i) measuring the lateral continuity of *low-amplitude* isostatic-gravity lineaments via structure-tensor coherence of `iso_grav_anom` (Band 13) horizontal/vertical gradients (Bands 18/11/5), (ii) gating that coherence by `depth_to_base_surf` (Band 15) so only lineaments under thick cover count, and (iii) coupling them with `cond_surf` (Band 17) conductivity-gradient and `rtp` (Band 02) tilt-normalized magnetic edge evidence. Emission is greedy spaced dots (2.8 px min spacing, >3 px catalogue collar, 37,654 dots) from the cross-validated OOF surface. No catalogue geometry, R0 dots, or prior submission rasters are read during feature construction.

**Data budget:** 15 SHA-256-pinned inputs in `registry/data_manifest.json` only. No external download (3DEP, MT) required; proposal H17-5 remains blocked.

---

## 1. Five ranked hypotheses not yet tried in this repo

All were checked against `src/gems91/*.py` and `docs/HYPOTHESES_*.md` before preregistration. Existing lanes use curvature, wavelet, Euler, tensor, strain-swap, phase-congruency, Hurst/semivariogram, but **none** implements the exact transform below.

| Rank | Hypothesis & layers | Physical signature & operator | Why it catches catalogue-missing faults | Non-fault mimic & how it differs from repo code |
|---|---|---|---|---|
| **1 (selected)** | **H21-1 DCBL — Depth-gated gravity lineament coherence** — `B13 iso_grav_anom` + `B18/B11/B05 iso_grav_anom_*_gradient/slope` + `B15 depth_to_base_surf` + `B17 cond_surf` + `B02 rtp` | Structure tensor `J = Gσ[∇B13 ⊗ ∇B13]` with σ=3–5 px, coherence `C = (λ1-λ2)/(λ1+λ2)`, gradient magnitude `|∇B13|`, then **depth gate** `w = sigmoid((B15-350)/150)` and conductivity-gradient multiplier. Operator isolates *continuous* low-amplitude (0.5–2 mGal) gravity lineaments that persist >700 m under thick fill. | USGS/INGENIOUS catalogue maps surface scarps (`B12/B19`). Intrabasinal faults under 0.3–2.5 km fill have **no scarp** but still offset basement density by 0.15–0.3 g/cm³, producing subtle 0.5–2 mGal steps that are invisible without depth gating and line-coherence filtering. >35% of blind Great Basin systems are intrabasinal (Faulds & Hinz 2015). | **Mimic:** Buried paleochannels, basalt-filled depressions, or lithologic density contacts under cover. **Difference:** `pgrd.py` used Poisson regression residuals, `lftg17.py` used Laplace Γzz/θG, `cwpc17.py` used cross-wavelet — none gated by `B15` sigmoid or used structure-tensor coherence of `B13` gradients. |
| 2 | **H21-2 DGSS — Dilatational geodetic strain on subsurface strike** — `B07 geod_shearrate` + `B08 geod_dilaterate` + `B04 geod_2ndinv` + `B13/B02` structure-tensor strike | Project geodetic strain invariants onto local subsurface contact strike `θ = 0.5 atan2(2J12, J11-J22)` from `B13/B02` to form `τ = (B07 + μ·B08)·|cos(φ_strain - θ)|` with `B10/B16` swarm excess `log(1+B10)-0.85 log(1+B16)`. Targets critically stressed active blind faults in Walker Lane transtension. | Blind faults with no scarp still creep aseismically and generate microseismic swarms; surface-only strain maps miss them without subsurface strike coupling. | **Mimic:** GPS interpolation bullseyes at station sites. **Difference:** `strain.py` swapped R0 dots by strain; never projected onto `B13/B02` structure-tensor strike with swarm coupling. |
| 3 | **H21-3 MSCE — Magnetite-destruction conductivity dipole** — `B14 tmi` - `B01 mag_anom` + `B17 cond_surf` + `B06 tc` | Along-fault hydrothermal magnetite destruction (`B14_clean - B01`) produces *magnetic low* inside magnetic volcanic block, while clay cap produces `B17` high and `B06` K/Th depletion. Operator: signed odd-symmetric step `Δ = (B14_clean - B01) * ∇B17 / (|∇B17|+ε)` normalized by `B06` variance (intra-unit suppression). | Sealed blind conduits have clay caps with **no scarp** (B12≈0); magnetite low + conductivity high dipole is the only surface expression. Catalogue misses these because field mappers require scarp. | **Mimic:** Unfaulted hydrothermal alteration at intrusive margins. **Difference:** `ccr91.py` regressed `cond_surf` on `B15`; never built cross-field magnetic-low × conductivity-gradient dipole. |
| 4 | **H21-4 IU-RHME — Intra-unit normalized magnetic edge** — `B02 rtp` + `B06 tc` + `B17 cond_surf` + `B13 iso_grav_anom` | Normalize magnetic/gravity gradient magnitude by local 1-km variance of `B06` and `B17`: `E_norm = |∇B02| / (σ²(B06)+σ²(B17)+ε)` so edges *within* homogeneous lithology score higher than passive inter-unit contacts (high `B06`/`B17` variance). | Passive lithologic contacts produce strong multi-sensor steps without faulting; intra-unit faults offsetting a single tuff sheet generate weak but homogeneous-unit-confined edges that are systematically under-mapped. | **Mimic:** Intra-unit welding zonation. **Difference:** No prior lane normalized gradients by `B06`/`B17` local variance. |
| 5 | **H21-5 DE-HA — DEM Hurst anisotropy (fine-scale)** — `B12 det_elev` + `B19 det_elev_slope` only | Directional variogram Hurst exponent `H(φ)` at 100–400 m lags; anisotropy `A = (H_max - H_min)/H_mean`. Piedmont micro-scarps (<0.8 m throw) create directional Hurst break without long-wavelength topography. | Eroded Holocene scarps on alluvial fans (<1 m throw) are invisible at 100 m DEM but produce subtle Hurst anisotropy detectable at 100–300 m scales; field crews miss them due to vegetation/grading. | **Mimic:** Lahontan shorelines, fan lobes. **Difference:** `svhf19.py` used Hurst at 300–900 m with magnetic/gravity; this is DEM-only 100–400 m. |

**Ranking rationale (expected DTI gain vs cost):**
- H21-1 highest because 19-band competition stack already contains `B13/B15/B17/B02`; implementation is 2-D image filters (<1 min CPU); intrabasinal faults are the largest *catalogue-completeness gap* per SGMC control (`62k` off-catalogue fault pixels).
- H21-2 medium-high but needs swarm excess QC.
- H21-3 medium, needs flight-line destriping.
- H21-4/5 lower expected gain, included for completeness.

**External data viability:** All five use only `training_features` (pinned, `sha256 4371c82e...`, verified `400M` on disk). USGS 3DEP 1-m DEM (H17-5) not needed; proposal remains blocked per sandbox allowlist.

---

## 2. Why GEMSDOE32 0.2778 scored highest and whether we can beat it

**Forensics (owner-reported, not organizer-confirmed; see `docs/nine-site-audit-20261026.html`):**
- GEMSDOE32 `h33-h33-2-b2-zeros` (0.2778) is not a new detector: it is `h19-5` multi-physics ridge network (121,131 px) → `D2.8` thinning (44,090 dots, 0.2600) → `H27-4 solo` deletion of 3,891 dots at exactly 1 px from catalogue (0.2708) → deletion of 2,545 more dots at 2–2.8 px (0.2778), leaving **37,654 dots**.
- Geometry explains 100% of the gain: **dotting (+0.068)** is expected kernel-coverage economics (`k(d)=1-d/300m`, so spacing 2.8 px ≈ 280 m maximizes `T/M` while minimizing `FP_w = n-M`), and **pruning zero-credit collar dots** removes `FP_w` with `dT≈0` → DTI rises via denominator shrinkage `D = 0.2T +0.2(n-M)+0.8|G|`.
- **69% of its dots are >1 km from catalogue**, vs 31% for in-sample-refitted `S17-LFTG` (which collapsed to 43% ≤5 px halo crowding). Far-field bias is its real discovery trait; in-sample PU models crowd the 300–1,000 m halo.

**Can we beat 0.2778?** Yes in principle — the public leaderboard top is 0.4413 (historical note, not a receipt), implying hidden truth `|G|≈12,500 px` with ~40% R0 coverage; beating it needs ~62% more truth credit at same dot budget, i.e. a *better localizer*, not more pruning. Prior holdout-best `S14-PTAC` reached 0.267 HOLDOUT-DTI on hide-and-recover (comparable instrument), showing catalogue recovery can improve, but hide-and-recover does not track live scores (S20: Spearman 0.105). Our S19-SVHF stitched-OOF de-crowding lifted blind SGMC >500 m to 0.093 vs R0 0.088, proving far-field discovery is learnable. DCBL directly targets the intrabasinal blind fault gap that R0's far-field exploits, so it has a *mechanistic* path to beat R0 live — but it must be measured via organizer receipt, not projected.

---

## 3. Frozen 3-experiment plan (≤3 exps, ≤2 h, no slot spent without holdout win)

All on `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, 60,988 withheld positives, 80 px = 8 km buffer, 1,000×20 km block bootstrap, `split_sha256 c79f1acaf33...`) with report-only `SGMC>300m/500m` and leakage canaries (AUC>0.90 is stop).

- **E1 (DCBL-surface):** Depth-gated gravity lineament surface alone → OOF 37,654-dot emission. Tests whether `B13/B15/B17/B02` coherence without ML already beats R0's geometry.
- **E2 (DCBL-HGB):** HGB on 4 DCBL features + 2 base cover features (`B15`, `B13` magnitude) → OOF emission. Tests ML combination.
- **E3 (DCBL-Cal):** Prior-shift-calibrated (π0=0.022) dual-specialist (full vs B12/B19-free) with local auto-context ≤900 m, OOF stitched emission. Tests whether calibration + context bridges wash gaps.

Only the holdout-winning surface (if any beats `S14-PTAC 0.267782` and `S18-HGBR 0.200742` on same instrument with paired CI>0) is emitted full-map via `submission_writer.py` (all-finite zeros, no nodata, 37,654 dots, >3 px collar). Otherwise final emission is still written as *research artifact* with `verdict negative`.

**Gates:** format (float32, EPSG:32611, 3730×3292, transform, [0,1], no NaN), canary (max AUC ≤0.90), registry (surface |ρ|≤0.90 and final dots ≤70% within 3 px vs 64 frozen + downloads), holdout win vs comparable best with paired CI, selector approval (outside this runner).

No weekly slot is consumed by this preregistration.
