# Session H92 Pre-Registered Hypotheses — Cover-Gated Transfer Faults (CGTF)

**Branch:** `arena/b7908996-gemsdoe91`  
**Lane (self-declared; no external selector paragraph supplied — `IR-91-S12-01`):** Cover-Gated Transfer Faults — blind intrabasinal horsts, transtensional pull-aparts and shallow volcanic faults under Quaternary cover, isolated by per-fold Bouguer/compaction stripping and conductivity conditioning, emitted at winner economics (37,654 dots, 70% far-field, 3.16 px spacing).  
**Preregistration timestamp:** 2026-10-25T02:30:00Z — frozen BEFORE any H92 holdout score or GeoTIFF emission.  
**Inputs:** ONLY `registry/data_manifest.json` pinned official files — `sample_submission.tif`, `existing_faults.tif`, `gems-geodawn-numerical-features.tif` (19 bands), `gdr_wellspring_in_footprint.csv` (prior only), `derived_sgmc_faults_100m_u8.tif` (REPORT-ONLY control). No `ext_lidar_scarp_u8.tif`, no `ext_geodawn_rad_u8.tif` (licence-unchecked `IR-91-26`); no parent raster read as prior.

---

## 0. Why did `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` score 0.2778? (Measured answer, same as S14)

Measured 2026-10-24 in this sandbox with shared evaluator `gems91-hide-recover-v1.0` on sha256-pinned rasters (`registry/data_manifest.json`, `evidence/s14_winner_forensics.json`):

| Raster | CLAIM organizer | dots | median spacing | % >10 px from catalogue | HOLDOUT v1.1 | SGMC |
|---|---|---:|---:|---:|---:|---:|
| h16-1 | 0.1855 | 123,939 | 1.00 px | 59.2% | 0.1622 | 0.1113 |
| h19-5 | 0.1922 | 121,131 | 1.00 px | 58.9% | 0.1617 | 0.0992 |
| h19-5 d1.5 | 0.2477 | 60,069 | 2.24 px | 59.3% | 0.1672 | 0.0999 |
| h19-5 d2.8 | 0.2600 | 44,090 | 3.16 px | 59.6% | 0.1573 | 0.0942 |
| solo d2.8 | 0.2708 | 40,199 | 3.00 px | 65.4% | 0.0478 | 0.0953 |
| **R0 h33-2-b2** | **0.2778** | **37,654** | **3.16 px** | **69.8%** | 0.0066 | 0.0954 |

Spearman vs CLAIM: `n_dots ρ=-1.000 (p<0.001)`, spacing `ρ=+0.898`, far-field share `ρ=+0.857`. **Metric economics:** DTI denominator is `0.2*(S-M)+0.2*T+0.8*|G|` with triangular kernel R=300 m (3 px). Once a truth pixel is covered at k≈1, extra dots on same line add ≈0 to T but +0.2 to denominator. Thinning a continuous line to ≈3 px spacing keeps T, cuts S by 3.3×. **Far-field:** hidden test faults are by construction >300 m from catalogue; R0 spends 69.8% of dots >1 km away — highest of fleet. **Precision gate:** h19-5 required multi-family agreement before mass. All three are additive.

**Can we beat 0.2778?** Yes — R0 is a thinned subset of h19-5's hand threshold surface, so it cannot recover faults that h19-5 missed. A better surface at identical emission economics (37,654 far-field dots) leaves headroom. Leaderboard 0.4413 CLAIM proves hidden truth is recoverable. No organizer receipt exists for 0.2778/0.4413 in this sandbox (verified in `GEMSDOE32/docs/index.html` snapshot: "NO ORGANISER SCORE EXISTS").

---

## 1. Five ranked candidate hypotheses (all 100% official GeoDAWN, no external data)

Ranked by expected HOLDOUT-DTI lift ÷ implementation cost. All label-free (no `existing_faults.tif` except final 3 px collar). All testable without new data (all 19 bands already pinned).

| Rank | ID | Specific Layer(s) (official band names) | Physical Signature & Exact Transform | Why it catches *uncatalogued* faults (not USGS/INGENIOUS) | Named non-fault mimic → rejection | Differentiation vs every prior GEMS* lane in this repo | Expected HOLDOUT-DTI gain / Cost |
|---|---|---|---|---|---|---|---|
| **1** | **H92-1 Cover-Stripped Intrabasinal Horsts** | `B13 iso_grav_anom`, `B15 depth_to_base_surf`, `B17 cond_surf`, `B12 det_elev`, `B11 iso_grav_anom_hg`, `B18 iso_grav_anom_hg`, `B05 iso_grav_anom_slope` | **Per-fold Bouguer/compaction stripping:** `G_intra = B13 − ĝ(B15)` where `ĝ` is least-squares quadratic `a0+a1·B15+a2·B15²` fitted ONLY on visible-faults training domain per fold (label-free band relation, never touches withheld truth geometry). `G_intra_grad = ‖∇G_intra‖₂`, `G_intra_svd = B13_svd − ĝ_svd`. **Cover-conditioned conductivity residual:** `C_res = B17 − ĉ(B15,B12)` where `ĉ` is bilinear `b0+b1·B15+b2·B12+b3·B15·B12` per fold. `C_res_grad = ‖∇C_res‖₂`, `C_res_DoG = G₃(C_res)−G₁₂(C_res)` (300 m–1.2 km clay-cap band-pass). `R²(B13~B15)=0.4664` measured 2026-10-24; stripping cuts σ(B13) 10.21→7.46 mGal, revealing horst steps buried under 200–1200 m Lahontan/Humboldt alluvium. Combine via `w_cover·(z(G_intra_grad)·z(C_res_grad))⁰·⁵` where `w_cover = σₖ((B15−220)/45)` gates to thick cover. | USGS Qfaults maps Quaternary scarps; intrabasinal horsts under thick alluvium have zero surface scarp and −35 mGal basin-bowl mask that previous models never stripped. | **Playa saline brines & broad lacustrine clays:** flat `G_intra≈0` and `C_res_DoG≈0` (removed by DoG); require coincident `G_intra_grad` AND `C_res_grad` lineament (product, not sum) | First lane to do **fold-safe per-fold Bouguer stripping** (S12 fitted globally, leaking via band covariance; S11/S13 never stripped). S14 used lidar/rad, not this. | **High / Low** (3 bands, CPU, verified `R²`) — validated in E1 |
| 2 | **H92-2 Transtensional Kinematic Corridor** | `B04 geod_2ndinv`, `B07 geod_shearrate`, `B08 geod_dilaterate`, `B10 deq_n100a15`, `B16 ieq_n100a15`, `B13` | **Kinematic vorticity:** `Wk = B07/√(B07²+4·B08²)` (−1..1: 0=pure extension, ±1=pure strike-slip, 0.4–0.75=transtension). **Dilatation sign & gradient:** `sgn(B08)`, `‖∇B08‖₂`. **Swarm index:** `S_swarm = ln(1+B10)−k·ln(1+B16)` where `k` from `log B16~log B10` regression per fold. **Brittle-transtension joint:** `z(Wk)·z(S_swarm)·z(G_intra_grad)` | Walker Lane & Humboldt Structural Zone pull-aparts have minimal vertical throw (no Qfaults scarp) but intense shear + fluid-driven swarms; host >75% of Basin's blind geothermal systems (Faulds & Hinz 2015). | **Diffuse caldera ring faults & quarry blasts:** no elongated Frangi linearity; blasts lack `B07` shear | First to compute `Wk` from Kreemer & Hammond (2007) and swarm index correctly (S12 had `B10` outlier skew bug `IR-91-S12-03` with max 4.96e6) | **Medium / Low** — validated in E2 |
| 3 | **H92-3 Shallow Magnetic Residual Intravascanic Faults** | `B01 mag_anom`, `B14 tmi`, `B03 tmi_hg`, `B09 tmi_vg`, `B02 rtp`, `B06 tc` | **Shallow GeoDAWN residual:** `ΔT_shallow = B14 − β̂·B01` (β̂ per fold). **Analytic signal:** `A_T = √((B03/200)²+B09²)` (exact SI, `B03/200.024` vs `B09 nT/m`, `r=0.999991` verified), `RTP analytic A_R = ‖∇B02‖₂`. **Tilt:** `θ_T=atan2(B09,B03/200)`, `k_SPI=‖∇θ_T‖₂ ∝1/z_mag`. **Remanence contrast:** `z(A_T)−z(A_R)`. `SPI` enrichment +2.3× on blind SGMC faults (S12 finding). | Reversed-polarity Neogene volcanic plateaus: RTP shifts anomalies; intrabasinal faults under 10–50 m basalt have zero topo but shallow `ΔT` lineament | **Equidimensional plugs/necks:** Frangi vesselness `V_σ→0` (λ₂/λ₁≈1); flow lobes lack `±600 m` basement dipole step | First to use **dimensionally-exact** `B03/200` analytic signal (S12 discovery `IR-91-S12-01` fixes 100× tilt bug); S14 skipped | **Medium / Low** |
| 4 | **H92-4 Multi-Scale Curvature & Openness Scarp** | `B12 det_elev`, `B19 det_elev_slope` | **LRM:** `LRM₁km = B12−G₁₀(B12)`, `LRM₃₀₀m = B12−G₃(B12)`. **Structure tensor:** `κ₁,κ₂ = eig(G₂.₅(∇B12·∇B12ᵀ))`, `linearity L=(κ₁−κ₂)/(κ₁+κ₂)` at 1.2 km. **Laplacian openness:** `∇²B12` via `G₁.₅` DoG. **Topo step:** `±600 m` cross-strike dipole on `B12` along `∇B12` normal. | Degraded late-Pleistocene piedmont scarps (0.3–1.2 m) smoothed in `B19` at 100 m but visible as curvature `∇²B12` + LRM persistence | **Lahontan shorelines (1330 m contour benches):** constant elevation, `L≈1` but `curvature` fails multi-azimuth corroboration + no `G_intra` support | LRM only in G91-COVER; S11 used slope only; S13/S14 not | **Low / Low** |
| 5 | **H92-5 Hydrothermal Magnetite-Destruction Joint** | `B02 rtp`, `B17 cond_surf`, `B10 deq_n100a15`, `B15 depth_to_base_surf`, `B18 iso_grav_anom_hg` | **Mag destruction trough:** `G₈(B02)−G₁.₅(B02)>0` (RTP low where fluids oxidized magnetite to pyrite). **Clay cap:** `G₃(B17)−G₁₂(B17)` isolates 300 m–1.2 km argillic halos. **Joint:** `max(z(mag_trough),0)·max(z(‖∇B17‖₂),0)`. **Footwall polarity:** `|B18|·exp(−0.5((B15−400)/450)²)` | Active blind conduits self-seal silica but leach magnetite & build smectite caps; have zero scarp but strong mag+conductivity lineament | **Miocene basalt dikes (positive RTP) & playa brines (broad):** `mag_trough<0` and DoG=0 | H91-E3 proposed but never validated; S12 never implemented | **Medium / Low** |

**Ranking rationale:** H92-1 has largest verified signal (`R²=0.4664`) and lowest cost (3 bands). H92-2 adds orthogonal physics (geodesy+seismicity) independent of potential fields, so corroboration should boost precision (β=0.8 rewards precision). H92-3/H92-4 are lower expected lift because prior lanes already used mag/topo heavily.

---

## 2. Experiments (budget: 3, Protocol Rule 6)

- **E1 (surface):** Deterministic cover-gated surface `S1 = σ((B15−220)/45) · √(z(G_intra_grad)·z(C_res_grad)) · L₁.₂ₖₘ · (1+0.3·z(‖∇B08‖₂))` normalized to [0,1] percentile in footprint. All transforms computed per-fold where regression involved (fold-safe). Scores: HOLDOUT-DTI `v1.0` (`gems91-hide-recover-v1.0`, 4 quadrants, 1 km buffer, 60,988 withheld, α=0.2 β=0.8 R=300 m triangular) + `v1.1-nohalo` (mask_buffer_predictions=False) for emission tuning. Canary: every single feature alone vs withheld truth, symmetric AUC ≤0.90.
- **E2 (kinematic+swarm):** `S2 = S1 · (0.6+0.4·σ(Wk−0.45)) · (0.7+0.3·σ(S_swarm))` gated by transtension & swarm index. Same scoring. Winner of E1/E2 by `v1.1`.
- **E3 (emission):** Full-map deterministic surface at winner geometry: deterministic far-field-weighted greedy with `d_min=2.8 px` (Poisson-disk thinning to 3.16 px spacing), collar `>3 px` from catalogue, budget 37,654 dots, 75% far-field target. `G_intra` and `C_res` recomputed globally (no fold) for final map; per-fold coefficients never leak into full map. Dots validated via `vendor.gems57.submission_writer` (all-finite [0,1], CRS/shape/transform, mass>0, zero catalogue mass, re-read, ZIP).

**Promotion rule:** `promote` iff (i) all format gates PASS, (ii) leakage canary all ≤0.90, (iii) registry uniqueness PASS (surface |ρ|≤0.90 AND dots ≤70% within 3 px vs every indexed raster), (iv) HOLDOUT-DTI `v1.0 ≥0.10` sanity floor (not degenerate vs random 0.0288), (v) submission bundle written and re-read. **No weekly slot spent by this session; slot use remains human selector decision (`SLOT_PLAN.md`).** Negative results are deliverables.

---

## 3. External data check

All 19 bands already pinned; no new acquisition needed. `gdr_wellspring_in_footprint.csv` used strictly as prior layer (vents≠truth). `geodawn_rad_u8.tif`/`lidar_scarp_features_u8.tif` explicitly excluded from this lane (licence-unchecked `IR-91-26`) — this lane is 100% official CC0 data.

---

## 4. Lane uniqueness statement

`H92-CGTF` is distinct from all GEMSDOE91 lanes: S13-PTHA (magnetic curvature/strain partitioning but never fold-safe Bouguer stripping), S14-LSRG (lidar+rad, not official-only), S11-MHTR (no stripping), H91-DDVTC (dip deprojection, not cover gating), CED91 (mag-gravity displacement, not stripping), G91-COVER (global depth detrend, not per-fold). Verified by grep: no prior lane contains `G_intra = B13 − ĝ(B15)` per-fold or `C_res = B17 − ĉ(B15,B12)` + `Wk` + `S_swarm` product.

---

## 5. Official sources (all reachable for manual review)

- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — DTI formula, format, test set.
- [Reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — `α=0.2 β=0.8 R=300 m`.
- [GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — DOI 10.5066/P93LGLVQ CC0.
- [GDR 1391 INGENIOUS](https://gdr.openei.org/submissions/1391) — earthquake density, MT, Qfaults provenance.
- [EPSG:32611](https://epsg.io/32611) — WGS84/UTM11N.
- [Tversky index](https://en.wikipedia.org/wiki/Tversky_index) — asymmetric scoring.
- [Rules PDF 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — 3 submissions/week, AI disclosure.
- [Faulds & Hinz 2015 framework](https://gbcge.org/current-projects/ingenious/) — structural controls on geothermal.

