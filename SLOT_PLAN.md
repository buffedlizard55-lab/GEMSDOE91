# SLOT PLAN — 1 entity, 3 scored slots / rolling week, 1 blind final pick

**Calendar (`2026-10-23` UTC):** `41 days` (`5.86` rolling 7-day weeks = `15–18` scored slots) to the **unconfirmed** `2026-12-03` deadline ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)). Never use multi-account feedback; record every live score in `ledger/submissions.csv` (`|Δ| < 0.01` = no evidence).

## Session 5 axis built: `RELIEF` (`r2p12`, `r2b12`, `b2r12`)

Restoring `training_features` (`gems-geodawn-numerical-features.tif`, sha256 `4371c82e…3bc5` `RECEIPT`) unblocked all six axes (`16/16` manifest checks pass `RECEIPT`). `RELIEF` had `0` prior builds and tests the central structural-geology ambiguity of Great Basin fault truth at fixed mass (`37,654` dots `RECEIPT`), fixed `12.00%` relocation (`4,518` dots; `24.00%` symmetric pixel diff `RECEIPT`), and zero catalogue-collar drift (`2,171 -> 2,171` `RECEIPT`): **concealed piedmont/basin faults vs exhumed horst bedrock faults**.

## Next 3 scored slots in order (Week 1: `2026-10-23` to `2026-10-30`)

| Slot | File (`releases/` or `data/registry/`) | Dots (`RECEIPT`) | Change vs R0 (`RECEIPT`) | Pred. `Δ` (`MODEL`) | What the live receipt changes |
|---:|---|---:|---|---|---|
| **1** | `data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif` (**R0**) | 37,654 | 0.00% (anchor) | `0.2778` / `0.3698` `CLAIM` | Replaces unverified `CLAIM` with first `RECEIPT` baseline. *(Skip to Slot 2 if human already holds an exact receipt for `baeae321…c77dd`, promoting `RELIEFr2b12` into Slot 3.)* |
| **2** | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c.tif` | 37,654 | 12.00% moved (`range->pied`) | **+0.006 `MODEL`** `[-0.006,+0.018]` | `Δ ≥ +0.010`: withheld truth favors concealed piedmont-toe scarps/relay ramps -> spend Slot 3 on donor-twin `RELIEFr2b12` (`27443c30`) to test deeper basin fill. `Δ ≤ -0.010`: T3 horst donors carried real bedrock truth -> keep Slot 3 on `RELIEFb2r12`. |
| **3** | `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5.tif` | 37,654 | 12.00% moved (`basin->range`) | **+0.005 `MODEL`** `[-0.010,+0.020]` | `Δ ≥ +0.010`: withheld truth tracks 1:24k–1:100k exhumed bedrock faults (`+5.2%` SGMC `PROXY`, [USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) -> scale `b2r` to 20–25% in Week 2. Both Slot 2 & 3 `|Δ| < 0.010`: retire `RELIEF`; pivot Week 2 to `PRUNEle15norefill` (`+0.010` `MODEL`) + strain/mass axes below. |

## Rolling budget to deadline (`5.86` weeks remaining)

- **Week 1 (slots 1–3):** Anchor R0 + bracket `RELIEF` (`r2p12` vs `b2r12` or `r2b12`).
- **Week 2 (slots 4–6):** Test mass/collar orthogonal lever (`PRUNEle15norefill`, `21,989` dots `RECEIPT`, `+0.010` `MODEL`) + winning `RELIEF` direction at `24%` dose + top proposed axis below.
- **Weeks 3–4 (slots 7–12):** Combine orthogonal ≥`+0.010` `RECEIPT` winners one step at a time (only after parent receipts exist) + calibrate total `MASS` (`alpha=0.2`, `beta=0.8`).
- **Weeks 5–6 (slots 13–18 + 1 blind final):** Freeze best receipted build + one conservative hedge (`R0` or minimal-edit winner); re-verify sha256 on disk before blind final selection (`2026-12-03`).

## Proposed better axes (not built this session; all inputs now verified)

1. **`GEODETIC-STRAIN CONCENTRATION` (`Band 4 geod_2ndinv` + `Band 7 geod_shearrate`)**
   - **Mechanism:** Active transtensional shear maintains dilational fracture permeability and unmapped Quaternary splays ([GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)); `geod_2ndinv` (`0.5793` `PROXY`) and `geod_shearrate` (`0.5761` `PROXY`) have the highest truth-adjacent signal among all 19 GeoDAWN bands.
   - **Confounder:** Coarse GPS station spacing smears strain across adjacent aseismic blocks.
   - **Falsifier:** Reallocating 20% of R0 mass into top-tercile `geod_2ndinv × S_struct` yields `Δ < +0.010` live vs R0.
2. **`SEDIMENT-DEPTH KERNEL BRACKETING` (`Band 15 depth_to_base_surf`-gated lateral pairing)**
   - **Mechanism:** Upward continuation through `>500 m` Cenozoic fill shifts gravity/magnetic horizontal-gradient crests downdip of dipping normal fault surface traces, missing DTI's `300 m` kernel unless bracketed (`±200 m`).
   - **Confounder:** Variable listric fault dip (`40°–65°`) creates asymmetric hanging-wall offset.
   - **Falsifier:** Depth-bracketed basin dots fail to beat `RELIEFr2b12` (`27443c30`, `+0.003` `MODEL`) by `≥ +0.010` live.
3. **`THERMAL-ANOMALY DILATIONAL GATING` (`Band 16 ieq_n100a15` × lineage terminations)**
   - **Mechanism:** Blind geothermal systems localize at fault tips/step-overs with elevated shallow conductive temperature (`ieq_n100a15` AUC `0.5749` `PROXY`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)).
   - **Confounder:** Lateral groundwater outflow plumes advect heat `2–8 km` off the structural conduit.
   - **Falsifier:** Thermal-weighted step-over reallocation scores `≤` isothermal `RELIEFr2p12` (`6ff08e5c`).
