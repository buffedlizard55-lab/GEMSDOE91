# SLOT PLAN — 1 entity, 3 scored slots / rolling week, 1 blind final pick

**Calendar (`2026-10-23` UTC):** `41 days` (`5.86` rolling 7-day weeks = `15–18` scored slots) to the **unconfirmed** `2026-12-03` deadline ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)). **Ledger:** `41` `BUILT` rows across five merged axis families (`CONCENTRATION`, `PRUNE`, `MASS`, `SPACING`, `RELIEF`), `0` `SUBMITTED`, `0` live `RECEIPT`s (`R0 = 0.2778` `CLAIM`). Never use multi-account feedback; `|Δ| < 0.01` = no evidence.

**Current session stop (2026-10-23):** PRUNE menu exhausted; zero builds. Existing slot order below is provisional, not upload clearance. Resolve IR-91-28, receipts and rolling quota first. Local validation is not RECEIPT evidence.

## Session 5 (`arena/42de3fed-gemsdoe91`) addition: `RELIEF` (`r2p12`, `r2b12`, `b2r12`)

Restoring `training_features` (`gems-geodawn-numerical-features.tif`, sha256 `4371c82e…3bc5` `RECEIPT`) unblocked all six axes (`16/16` manifest checks pass `RECEIPT`). `RELIEF` relocates `4,518` dots (`12.00%` moved; `9,036` symmetric pixel diff = `24.00%` `RECEIPT`) at fixed count (`37,654` `RECEIPT`) and zero catalogue-collar drift (`2,171 -> 2,171` `RECEIPT`) across equal-area terciles `0.90·pct(det_elev) + 0.10·pct(det_elev_slope)`: `RELIEFr2p12` (`6ff08e5c`, `+0.006` `MODEL`), donor-twin `RELIEFr2b12` (`27443c30`, `+0.003` `MODEL`), and directional sign-flip `RELIEFb2r12` (`e1fd28d5`, `+0.005` `MODEL`, `+5.2%` off-catalogue SGMC `PROXY`, [USGS DS-1052](https://pubs.usgs.gov/ds/1052/)).

## Next 3 scored slots in order (Week 1: one orthogonal axis per slot)

| Slot | Candidate (`releases/`) | Dots (`RECEIPT`) | Pred. `Δ` (`MODEL`) | What the live receipt changes |
|---:|---|---:|---|---|
| **1** | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` *(or R0 anchor if `baeae321…` has no receipt yet)* | 37,654 | **+0.0123** `[-0.022,+0.037]` | Highest-upside external thermal prior. `Δ ≥ +0.010`: prior transfer works -> test `15–20%` dose in Week 2. `Δ ≤ -0.010`: macro block-relayout costs structural recall -> retire `CONCENTRATION`. |
| **2** | `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif` | 26,294 | **+0.008** `[-0.006,+0.019]` | Collar-exempt (`AXIS=PRUNE`) denominator-cost test. `Δ ≥ +0.010`: rebase Week 2 winners onto pruned parent (`le10`/`le15`). `|Δ| < 0.010`: retire `PRUNE`. |
| **3** | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c.tif` *(swap in `MASScons3add` `2803126d`, `+0.009` `MODEL`, if testing count expansion first)* | 37,654 | **+0.006** `[-0.006,+0.018]` | Tests concealed piedmont-toe scarp enrichment (`-0.0017` 4-fold INGENIOUS `PROXY`, [GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)) at zero collar drift. `Δ ≥ +0.010`: test donor-twin `RELIEFr2b12` (`27443c30`) in Week 2; `Δ ≤ -0.010`: flip to bedrock `RELIEFb2r12` (`e1fd28d5`). |

## Rolling budget to deadline (`5.86` weeks remaining)

- **Week 1 (slots 1–3):** Anchor R0 receipt (cost 0 if already held, else Slot 1) + test 1 prior axis (`CONCENTRATION`), 1 mass/collar axis (`PRUNE`), and 1 terrain-regime axis (`RELIEF` or `MASScons3add`).
- **Week 2 (slots 4–6):** Bracket any Week-1 `≥ +0.010` `RECEIPT` winner (`RELIEFb2r12` vs `RELIEFr2b12`, `MASScons3add`, or top proposed axis below).
- **Weeks 3–4 (slots 7–12):** Compose two orthogonal `≥ +0.010` `RECEIPT` winners one step at a time onto a receipted parent.
- **Weeks 5–6 (slots 13–18 + 1 blind final):** Re-verify best receipted build + conservative fallback (`-zeros` / R0) on disk; pick **one** blind final file before `2026-12-03`.

## Proposed better axes (not built this session; all inputs now verified)

1. **`GEODETIC-STRAIN CONCENTRATION` (`Band 4 geod_2ndinv` + `Band 7 geod_shearrate`)**
   - **Mechanism:** Active transtensional shear maintains dilational geothermal permeability and unmapped Quaternary splays ([GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)); `geod_2ndinv` (`0.5793` `PROXY`) and `geod_shearrate` (`0.5761` `PROXY`) lead all 19 GeoDAWN bands on fault separation.
   - **Confounder:** ~50 km GPS station spacing smears strain across adjacent aseismic blocks.
   - **Falsifier:** Moving 20% of R0 mass into top-tercile `geod_2ndinv × S_struct` yields `Δ < +0.010` live vs R0.
2. **`SEDIMENT-DEPTH KERNEL BRACKETING` (`Band 15 depth_to_base_surf`-gated lateral pairing)**
   - **Mechanism:** Upward continuation through `>500 m` Cenozoic basin fill shifts gravity/magnetic gradient crests downdip of dipping normal fault surface traces, missing DTI's `300 m` kernel unless bracketed (`±200 m`).
   - **Confounder:** Variable listric fault dip (`40°–65°`) creates asymmetric hanging-wall offset.
   - **Falsifier:** Depth-bracketed basin dots fail to beat `RELIEFr2b12` (`27443c30`) by `≥ +0.010` live.
3. **`THERMAL-ANOMALY DILATIONAL GATING` (`Band 16 ieq_n100a15` × lineage terminations)**
   - **Mechanism:** Blind geothermal systems localize at fault tips/step-overs with elevated conductive temperature (`ieq_n100a15` AUC `0.5749` `PROXY`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)).
   - **Confounder:** Shallow groundwater outflow plumes advect heat `2–8 km` down-gradient off the fault conduit.
   - **Falsifier:** Thermal-gated step-over reallocation scores `≤` isothermal `RELIEFr2p12` (`6ff08e5c`).
