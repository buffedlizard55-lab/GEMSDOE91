# S23-TILTA — preregistered before experimental results

Date: 2026-10-27. Branch: `arena/40c331a5-gemsdoe91`. No assigned lane exists in the prompt; this is a self-assigned narrow lane, not a claimed coordinator assignment.

## Lane interpretation
**Tilt-angle magnetic contact × gravity horizontal-gradient concordance (TILTA):** use only cached Bands 06 (tc — tilt/total-curvature) and 18 (iso_grav_anom_hg — isostatic gravity horizontal gradient) from `data/bridge/gems-geodawn-numerical-features.tif`. Faults juxtapose magnetic basement blocks: the tilt-angle derivative has a zero-crossing/edge at a magnetic contact; the gravity HG has a ridge at a density step. A true fault should show *both* co-located and aligned. This is a hypothesis, not proof of geothermal permeability. No catalogue features, old raster values, predicted coordinates, supervised fitting, or leaderboard inversion. Non-fault mimics: unfaulted intrusive contacts, lava-flow margins, survey seam edges, and topographic flexure.

## Ranked hypotheses (qualitative expected benefit, not projected scores)

| Rank | Hypothesis / specific cached layers | Physical signature; missing-fault rationale | Difference from inspected implementation | Expected benefit / cost |
|---|---|---|---|---|
| 1 | **H23-1 TILTA, B06 + B18** | Tilt-angle zero-crossing / edge strength aligned with gravity HG ridge; buried magnetic-density contact without surface scarp | S19 uses second-moment semivariograms; S21 PDWC uses Cauchy-Hilbert waveform + phase congruency; S22 OMTJ uses signed third-moment (skewness) texture. None use tilt-angle × grav-HG product. | Uncertain, highest among feasible low-cost / ~15 min CPU; E1 only |
| 2 | **H23-2 CBPC, B17 + B12/B19** | Conductivity step (B17) coincident with det_elev piedmont concave flexure; groundwater-baffle fault dams flow, creates conductivity contrast under alluvial cover | Previous conductivity use was as residual vs B15 (HCBA), not as piedmont-flexure baffle. | Medium / ~20 min; not run |
| 3 | **H23-3 SRDR, B04 + B08** | Geodetic second-invariant (B04) ridge + dilatation-rate (B08) minimum; contemporary extensional strain localizes on blind faults before geomorphic expression | No prior session used geodetic strain bands as primary lineament detector (only as local residual in PDWC). | Low-medium / ~15 min; not run |
| 4 | **H23-4 EQLC, B10/B16 + B13** | Earthquake-intensity lineation (B10/B16) corroborated by isostatic gravity curvature; microseismic alignment on blind structures | B10/B16 were deprecated as thermal bands but never tested as seismic lineation detectors. | Low / ~10 min; not run |
| 5 | **H23-5 MVGWP, B09 + multi-scale worms** | Magnetic vertical-gradient (B09) worm persistence across upward-continuation scales (200/600/1500 m) | Previous worms used horizontal gravity/mag components at fixed scale; not multi-scale persistence. | Higher / ~30 min; not run |

All are proposed new combinations within inspected source; no guarantee they have never been tried in private/sibling work. No new external data needed. Stack is hash-pinned to `registry/data_manifest.json`.

## Frozen experiment and gates

- E1 only: B06 and B18 as described below; Gaussian smoothing σ=2 px for gradient fields; edge strengths normalized by in-footprint 95th percentile to [0,1]; combined surface = cbrt(edge_tilt * strength_grav * alignment²) where alignment is squared cosine between tilt-gradient normal and gravity-HG normal, clipped to [0,1]. No parameter search after results.
- Use existing `vendor/gems57/spatial.folds`, 80 px training buffer, whole 8-connected fault components; no catalogue-derived feature is used. Evaluation masks known/visible pixels exactly. Use shared `vendor/gems57/evaluate_holdout.py`, pooled α=0.2 β=0.8 300 m triangular kernel, 1,000 paired 20 km block bootstrap draws. Record actual positive count.
- E1 holdout dots allocated in proportion to each fixed quadrant's footprint area (total 20,000 to avoid dense-lattice capacity impossibility); use `pdwc21.emit_dots_nms` spacing 3.05 px and visible-catalogue collar 3.05 px. Historical best is context only, not paired comparison; no promotion without comparable incumbent re-evaluation.
- Canary every input/derived feature used, including combined surface: all held positives, every 4th negative, each fold; symmetric AUC >0.90 is hard stop. A pass does not prove no leakage.
- Pre-placement exact full-footprint Spearman via shared `SurfaceProbe` against frozen available registry and all pre-existing local downloads. Pin inventory before construction. No reference is excluded for density. Missing references keep clearance UNVERIFIED but disclosed.
- After holdout, create one new deterministic full-grid prediction (20,000 dots, collar 3.05 px from full catalogue, spaced 3.05 px) and package with shared `submission_writer.py` as all-finite zeros-encoded float32 GeoTIFF plus one-TIFF ZIP; immediately test final dots' exact rank correlation and directed 3-px overlap; on first breach stop. Keep any already-written raster only as negative research deliverable, never submit-ready.
- Budget 3 experiments / 2 h; 1 is planned. Selector and live weekly quota are separate and not authorized. No slots used.
- Organizer score / leaderboard estimate remain null unless authenticated receipt / defensible calibration exists. User-supplied numbers retained only as unverified claims.
