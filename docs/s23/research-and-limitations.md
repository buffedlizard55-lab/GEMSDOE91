# S23 scientific review, source ledger and limitations

Reviewed 2026-10-27. Statements distinguish observed source text, measured local results, and hypotheses. Not exhaustive or organizer-confirmed.

## What the competition measures

**Verified official sources:**
- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — target is geological faults indicative of geothermal resources, **not confirmed geothermal vents**. Experts supplied new faults outside existing catalogue; public/private split creates distribution shift. Metric is pooled distance-weighted Tversky α=0.2 β=0.8 with 300 m triangular kernel `k(d)=max(1-d/300,0)`.
- [Official Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §3.2/3.6 — 3 submissions/week, one final submission across both rounds, generative-AI disclosure required.
- [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — on 2026-10-26 rank 1 was 0.4437 (xiaofanhu), rank 50 was 0.2826. The prompt's 0.4413/0.3195 are earlier snapshots, not receipts for our raster.
- [DrivenData submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format) — single-band float32, EPSG:32611, 3730×3292, 100 m, values in [0,1], bounds must match sample.

## Why GEMSDOE32 (0.2778 USER-REPORTED) leads the nine-site history

**Forensic facts from 2026-10-26 re-hashing (see `docs/s23/nine-site-audit.json`):**
- GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` has 37,654 positive cells, SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`.
- All nine historical leaders share ≥84.7% of their dots within 3 px; GEMSDOE25 and GEMSDOE30 have *byte-identical support* despite different file hashes. None is unique under the protocol's >70% duplicate rule.
- GEMSDOE32's file is `H19-5 (0.1922) → collar-pruned 0.2477 → spacing-optimized 0.2778`. Spacing and collar are metric geometry, not necessarily better geology.

**Plausible DTI economics (not proven causation):**
- DTI for binary dots: `T = Σ_truth max_pred k`, `N = dots`, `M = Σ_dot max_truth k`, `G = |G|`. `DTI = T / [0.2(T+N-M)+0.8G]`. FP scales linearly with N, TP sublinearly due to 300 m max-pooling. Removing redundant dots cuts FP while preserving ~95% of kernel coverage → DTI rises.
- Dots within 1–2 px of catalogue have kernels swallowed by masked known-fault pixels (they contribute FP denominator without TP) → collar pruning helps.
- Known faults are masked; "new fault" = any pixel not in `existing_faults.tif` (DrivenData forum 11516/11536). Live truth is depleted near mapped faults (only 45% within 1 km vs hide-and-recover's 85% near), so pure proximity fails.

**Can it be beaten?** In principle yes — current leaders cover only ~38% of hidden truth (model inference). Beating 0.2778 needs ~1.6× more true-positive coverage at same FP budget, i.e., *tighter localization* of concealed intrabasinal faults under Quaternary fill, not sparser emission. No evidence in this session that S23-TILTA achieves that (HOLDOUT-DTI 0.0148).

## S23 hypotheses (ranked before experiment)

| Rank | Hypothesis | Layers | Signature | Why missing faults? | Differs from repo? | Mimic | Cost |
|---|---|---|---|---|---|---|---|
| 1 | **TILTA** | B06 tc + B18 iso_grav_anom_hg | Tilt-angle edge × gravity HG ridge aligned (squared cosine) | Magnetic-density contact without surface scarp, under 0.3–2.5 km cover | No prior used tilt × grav-HG product (S19 semivariogram, S21 waveform/phase, S22 skewness) | Unfaulted intrusive contacts, lava margins, survey seams | Low / tested E1 |
| 2 | CBPC | B17 cond_surf + B12/B19 | Conductivity step across piedmont concave flexure (groundwater baffle) | Fault dams groundwater, conductivity contrast under alluvium | Previous conductivity was B15 residual, not piedmont baffle | Saline playas, lithologic contacts | Medium / not run |
| 3 | SRDR | B04 geod_2ndinv + B08 geod_dilaterate | Geodetic strain second-invariant ridge + dilatation minimum | Active blind faults localize strain before scarp formation | No prior used geodetic strain as primary detector | Basin-scale flexure | Medium / not run |
| 4 | EQLC | B10/B16 deq/ieq + B13 iso_grav_anom | Earthquake-intensity lineation corroborated by gravity curvature | Microseismic alignment on blind structures | B10/B16 deprecated as thermal, never as seismic lineation | Volcanic swarms | Low / not run |
| 5 | MVGWP | B09 tmi_vg multi-scale | Vertical-gradient worm persistence across upward continuations | Deep-penetrating faults under thick fill | Previous worms single-scale horizontal | Equidimensional plugs | High / not run |

Only H23-1 was tested; others remain viable proposals.

## S23 result interpretation

- **Holdout:** 0.014803 [0.011131, 0.018893], `gems57-pooled-hide-v2`, 60,988 withheld positives. Did not beat incumbent 0.066223 → negative, no slot.
- **Canary:** max symmetric AUC 0.6134 ≤0.90 PASS — no feature alone leaks catalogue location.
- **Pre-placement surface:** max |Spearman| 0.041 ≤0.90 PASS.
- **Final dots:** literal 99.90% overlap vs `calib_r13lattice_00904.tif` (206,895-dot synthetic blanket) → **literal FAIL**. Competitive scope (≤90k dots) max ~20% → PASS. The dense blanket covers 99.87% of footprint within 3 px; at 20k budget the 70% literal rule is geometrically impossible without exemption — disclosed, not silently waived.
- **Format:** all-finite zeros outside footprint (`nodata=None`) avoids "Predicted values must be in range [0,1]" rejection; single-band float32, EPSG:32611, 3730×3292, transform matches sample, zero mass on catalogue, SHA new.

## Official data ledger

| Source | What was verified in S23 | Use / limitation |
|---|---|---|
| [USGS GeoDAWN CC0](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) DOI 10.5066/P93LGLVQ | Magnetic = subsurface structure, radiometric = surface; flight lines 400 m apart, 100 m raster ≠ 100 m resolving power | Survey seams/flight-line residuals mimic texture boundaries |
| [USGS GDR gravity/mag maps](https://doi.org/10.5066/P9Z6SA1Z) via GDR 1391 | Official isostatic anomaly source | Metadata verified, no new independent stack beyond cached 19 bands |
| [GDR 1391 INGENIOUS CC BY 4.0](https://gdr.openei.org/submissions/1391) DOI 10.15121/1881483 | Wells, springs, seismicity, paleogeothermal sinter/tufa, faults, geodetics | Fault datasets duplicate catalogue truth — quarantined from holdout |
| [Official reference U-Net](https://github.com/drivendataorg/gems-prize-reference-solution) | CPU path supported (`uv sync --extra cpu`) | GPU not mandatory; S23 ran CPU |
| [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | 3/week cap, final selection, AI disclosure | Quota not accessible in sandbox; zero slots used |

## Limitations and next steps

1. **No receipt** ties any 0.27–0.44 claim to a byte-identical upload; all are USER-REPORTED.
2. **Holdout ≠ leaderboard:** hide-and-recover withholds catalogue components; live truth is expert-added faults depleted near catalogue. LFI projection (LOSO ρ≈0.96) is best available proxy but still model-dependent (RMSE≈0.02).
3. **Registry impossibility:** dense calibration rasters make literal 70% impossible at ≥20k dots. Needs coordinator versioned policy.
4. **Next levers:** USGS 3DEP 1 m LiDAR scarp detector (rank-5 team's disclosed U-Net, 20 m derivatives) — highest expected gain (+0.05–0.15 live) but requires unrestricted host for 207 GB footprint; or joint PDWC×HGBR cross-breed with equalized quadrant budgets.
5. **Governance:** selector approval and authenticated weekly quota remain separate; zero slots spent.
