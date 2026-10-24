# SUBMIT — MASS/consensus arms + merged PRUNE/CONCENTRATION queue (2026-10-23)

**Status 2026-10-23: 38 BUILT rows, 0 submitted, 0 receipts.** Rasters are not committed;
`releases/MANIFEST.json` is the sha256 contract and CI rebuilds every file from pinned inputs and
asserts byte-identity. **No agent submits. One file per slot; the `-zeros` twin is the fallback
for that same slot, never a second entry.**

## SESSION 4 — MASS/consensus: the three files to upload (one per slot)

```bash
python3 scripts/restore_data.py                 # fetch + verify every pinned sha256
python3 scripts/make_catalogue.py               # rebuild the mask; must hash to c97c7819…
python3 scripts/build_mass_consensus.py         # writes the 3 pairs under releases/, ~20 s
python3 scripts/validate_raster.py releases/<file>.tif data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif \
    --parent data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
python3 scripts/validate_release.py releases/<file>.tif --axis MASS
```

Rebuilds are deterministic (no RNG anywhere) and were verified to reproduce the hashes below.

| slot | file | sha256 (NaN-outside) | zeros twin | bytes (NaN) |
|---|---|---|---|---|
| **1** | `h33-h33-2-b2-MASScons3add-20261023-2803126d.tif` | `2803126de23b7f3388d2d4db727c2e8a39b499308b6efc61941d4231606f9abd` | `597d6d0e…` | 384,079 |
| **2** | `h33-h33-2-b2-MASScons1drop-20261023-fc8f5500.tif` | `fc8f5500790eed45fe4957a3a548c55513db09774ecd46c300b67b4cc72d854e` | `9f24d22e…` | 354,433 |
| 3 (only if 1–2 flat) | `h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f.tif` | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` (rebuild first) | — | — |
| keep | `h33-h33-2-b2-MASScons2drop-20261023-e8871e7f.tif` | `e8871e7f7bd75b139173e2c93eda3a79f47063e6e71dd4dfef7672cf58c4662f` | — | 328,675 |

**Form notes** (≤140 chars each, no score claimed, counted):

```
1: h33-2-b2; +3765 dots (10.0%) at 3-of-3 cross-field support cells, >=3px off catalogue; pred +0.009 MODEL
2: h33-2-b2; -4541 single-support dots (12.1%), count 33113, whole stratum; pred -0.000 MODEL
3: h33-2-b2; delete-only <=15px collar, 21989 dots, no refill; pred +0.010 MODEL
```

**Format receipt — paste this back with the score:**

```
candidate: h33-h33-2-b2-MASScons3add-20261023-2803126d
sha256 (NaN)    : 2803126de23b7f3388d2d4db727c2e8a39b499308b6efc61941d4231606f9abd
sha256 (zeros)  : 597d6d0ea528c8630e301dfe354b62905534d49f985f5bd92f04a75e51d7e5cf
n_dots          : 41419        min_dist_catalogue_px: 2.236  (inherited from R0, IR-91-03)
validate_raster.py  : 14/14 PASS (§6 MUST gates)
validate_release.py : 14 MUST gates PASS; collar_ge_3px FAIL = inherited, R0 fails it identically (2171 dots, IR-91-03)
CRS EPSG:32611 | 3730x3292 | 100 m | float32 | 1 band | values {0,1} | NaN outside
zero catalogue mass: 0 px        ledger sha: new at build time
```

**Known wrinkle, stated up front:** all three arms inherit R0's 2,171 dots at 2–3 px from the
catalogue, so the brief's "≥3 px unless PRUNE" is violated by the parent itself, not by the edit
(IR-91-03). The new mass in slot 1 is ≥3 px by construction. If the human prefers a compliant
parent, rebase on `PRUNEle3norefill` (35,483 dots) instead — but then the file is a two-change
build and must not be described as a MASS-only arm.

---

## Rebuild and verify everything (≈3 min, pinned inputs only, every sha256 checked)

```bash
python3 scripts/restore_data.py                  # fetch + verify every pinned sha256
python3 scripts/build_concentration.py --build   # 3 CONCENTRATION arms  (this session)
python3 scripts/make_catalogue.py                # derived catalogue mask (PRUNE needs it)
python3 scripts/build_prune_ladder.py --build    # PRUNE le4 / le5 / le10
python3 scripts/build.py --axis PRUNE --value 15 \
    --id h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f \
    --catalogue data/derived/catalogue_mask.tif  # le15 (verified to print 1ca1ff6f… today)
python3 scripts/build_spacing.py --build         # 3 SPACING arms (earlier session)
python3 scripts/validate.py releases/<file>.tif  # must print PASS
```

## The next three slots

| slot | upload (NaN-outside primary) | sha256 (must match `releases/MANIFEST.json`) | predicted (MODEL) |
|---|---|---|---|
| 1 | `h33-h33-2-b2-20261004-e5eb6e7e-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` | `c19adb012aec8571fcca393e3401050b01011286cec7282393cbcc0cca6a6e30` | +0.0123, range −0.022 … +0.037 |
| 2 | `h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f.tif` | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` | +0.010, range −0.008 … +0.024 |
| 3 | conditional — `…-CONCENTRATIONgdr25m10-…-08bf80cf.tif` if slot 1 ≥ +0.005; else `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif`; if both flat, `…-SPACINGspread40-…-6d389309.tif` | `08bf80cf443cc68faeb0dd0eca8d0aecf85eb113e7d3094e3a778382bc180369` / `04002dae86db72c3…` / `6d389309aafaa79d…` | +0.0114 / +0.008 / +0.004 |

The decision each receipt changes is in `SLOT_PLAN.md`. Naming is
`<parent>-<axis><value>-<yyyymmdd>-<sha8>.tif`, parent `h33-h33-2-b2-20261004-e5eb6e7e`.

**Form notes** (≤140 chars, already in `ledger/submissions.csv:form_note` where present):

```
h33-h33-2-b2-20261004-e5eb6e7e; 10.0% of 37654 dots moved to the highest-prior 2.5 km GDR-thermal blocks [gdr25rm10]; pred +0.0123 MODEL
h33-2-b2; delete-only, 15,665 dots (41.6%) within <=15px of catalogue removed, no refill, count 21989; pred +0.010 MODEL
```

## Other gate-clean files (fallbacks, same rules)

| file | n_dots | % changed | predicted (MODEL) | sha256 prefix |
|---|---:|---:|---|---|
| `…-CONCENTRATIONgdr25m10-20261023-08bf80cf` | 37,654 | 10.00 | +0.0114 | `08bf80cf…` |
| `…-CONCENTRATIONgdr10m10-20261023-d54e8815` | 37,654 | 10.00 | +0.0113 | `d54e8815…` |
| `…-PRUNE-le4-norefill-20261023-360fe57e` | 33,829 | 10.16 | +0.003 | `360fe57e…` |
| `…-PRUNE-le5-norefill-20261023-5b6d3987` | 32,017 | 14.97 | +0.005 | `5b6d3987…` |
| `…-PRUNE-le8-norefill-20261023-e1dd69d0` | 28,490 | 24.34 | +0.006 | `e1dd69d0…` |
| `…-PRUNE-le10-norefill-20261023-04002dae` | 26,294 | 30.17 | +0.008 | `04002dae…` |
| `…-PRUNE-le3-norefill-20261023-1209e863` | 35,483 | 5.77 | +0.002 | `1209e863…` |
| `…-SPACINGspread40-20261023-6d389309` | 37,654 | 39.99 (relocated) | +0.004 | `6d389309…` |
| `…-PRUNE-p2.9px-h19cover-20261023-9829bb66` (refill-held, count 37,654) | 37,654 | 4.3 | +0.004 | `9829bb66…` |
| `…-PRUNE-p2.5px-h19cover-20261023-e6f2000d` (refill-held) | 37,654 | 3.7 | +0.002 | `e6f2000d…` |
| `…-PRUNE-p4.5px-h19cover-20261023-691438f8` (refill-held) | 37,654 | 6.6 | **−0.015** | `691438f8…` |

## Format receipt — paste this with the file you upload

```
candidate: h33-h33-2-b2-20261004-e5eb6e7e-CONCENTRATIONgdr25rm10-20261023-c19adb01
sha256:    c19adb012aec8571fcca393e3401050b01011286cec7282393cbcc0cca6a6e30
bytes:     369017
scripts/validate.py: PASS        (both encodings tested)
gates: crs/shape/transform/dtype/band_count/values_in_0_1/no_nan_inside/nan_outside/
       zero_catalogue_mass/catalogue_floor/count_matches_parent/reread/unit_mass_dots
n_dots:    37654      min_dist_catalogue_px: 2.236 (unchanged from R0; no new cell inside 3 px)
```

## After each receipt

1. `receipt_score` + `receipt_date` into `ledger/submissions.csv`, `status` → `SCORED`; never into
   `predicted_change`. Under |Δ| < 0.01 record "no evidence (public chunks only)".
2. `≥ +0.01` ⇒ that parent becomes the base for the next slot. `≤ −0.01` on the CONCENTRATION arm
   ⇒ the thermal prior does not transfer; retire the axis. `≤ −0.01` on a PRUNE arm ⇒ the >3 px
   halo carries new-fault truth; stop pruning.
3. Update only the CURRENT STATE block of `README.md`.

## Do not

- Do not upload both twins of one file, or a file whose sha256 is already in the ledger (8+
  upstream slots went to exact repeats).
- Do not spend three slots on the CONCENTRATION arms: they are one experiment (IR-91-17). Same for
  the PRUNE ladder — one receipt on the top dose answers the axis.
- Do not read the catalogue proxy (CONCENTRATION arms 0.0054 vs R0 0.0062) as a score; it is PROXY
  and IR-91-15 explains why it cannot adjudicate this axis.
- Do not submit from any account but the one entity's. One final file, chosen blind.
---

## Session 5 (`arena/42de3fed-gemsdoe91`) — RELIEF variants, ready to upload

All six files (`NaN` primary + `-zeros` fallback twin for each of the 3 `RELIEF` arms) are built on disk in `releases/` and pinned byte-for-byte in `releases/MANIFEST.json` (never committed to git). Upload **at most one encoding per scored slot** ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)).

```bash
python3 scripts/restore_data.py
python3 scripts/build_relief.py --build --skip-fold-proxy
python3 scripts/validate.py releases/h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c.tif
python3 scripts/validate_raster.py releases/h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c.tif \
    data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif \
    --parent data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
```

| Slot order (`SLOT_PLAN.md`) | File (`releases/`) | Name | Form note (`<=140` chars, exact length verified) |
|---|---|---|---|
| **Slot 2** (after R0 anchor) | `releases/h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c.tif` | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c` | `h33-h33-2-b2; RELIEF shift 4518 dots (12.00%) Range->Piedmont tercile (det_elev/slope), count fixed 37654; pred +0.006 MODEL` (124 chars) |
| **Slot 3** (or swap with `r2b12` if Slot 2 ≥ +0.010) | `releases/h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5.tif` | `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5` | `h33-h33-2-b2; RELIEF shift 4518 dots (12.00%) Basin->Range tercile (det_elev/slope), count fixed 37654; pred +0.005 MODEL` (121 chars) |
| **Alt Slot 3** (donor-twin of `r2p12`) | `releases/h33-h33-2-b2-RELIEFr2b12-20261023-27443c30.tif` | `h33-h33-2-b2-RELIEFr2b12-20261023-27443c30` | `h33-h33-2-b2; RELIEF shift 4518 dots (12.00%) Range->Basin tercile (det_elev/slope), count fixed 37654; pred +0.003 MODEL` (121 chars) |

### Session 5 format receipt (`RECEIPT`, verified from disk after write)

```text
1. h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c
   primary (.tif):       sha256=6ff08e5c2785f7684798c25d5f86a61df5aeb2568fcaeda9482b25cf61858b07 (370,350 B)
   fallback (-zeros.tif): sha256=2b02433ae4193a965cdebe07c6f1ae498525829175ac3db7fda5a419ea6a9587 (223,541 B)
   grid: EPSG:32611, 3730x3292, 100 m, float32, 1 band, values in [0,1], 0 NaN inside footprint
   dots: 37,654 unit-mass | cat_mass=0 | min_d_cat=2.2361 px (added_le3px=0) | relocated=4,518 (12.00%; Hamming 9,036=24.00%)
   validators: validate.py=PASS | validate_raster.py=14/14 PASS | sha256_not_spent=PASS | reread_from_disk=PASS

2. h33-h33-2-b2-RELIEFr2b12-20261023-27443c30
   primary (.tif):       sha256=27443c301feff6f9bac035807d92a88c9830f8f198acab9bb53599700afbb6bd (370,517 B)
   fallback (-zeros.tif): sha256=baa1883fd76b0d374c6fdbd5914cecb66e6721aa7c92c2c326bf3552f276c2a4 (223,708 B)
   grid: EPSG:32611, 3730x3292, 100 m, float32, 1 band, values in [0,1], 0 NaN inside footprint
   dots: 37,654 unit-mass | cat_mass=0 | min_d_cat=2.2361 px (added_le3px=0) | relocated=4,518 (12.00%; Hamming 9,036=24.00%)
   validators: validate.py=PASS | validate_raster.py=14/14 PASS | sha256_not_spent=PASS | reread_from_disk=PASS

3. h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5
   primary (.tif):       sha256=e1fd28d57106bebbb2b7f5b4327ab5a186a3eb4a3085b7e5c4a06aad2286dc0f (369,469 B)
   fallback (-zeros.tif): sha256=3e47cb772a1b5ea261d5d756ee1b8e6038db09571c74682700ed77e026e18ee4 (222,473 B)
   grid: EPSG:32611, 3730x3292, 100 m, float32, 1 band, values in [0,1], 0 NaN inside footprint
   dots: 37,654 unit-mass | cat_mass=0 | min_d_cat=2.2361 px (added_le3px=0) | relocated=4,518 (12.00%; Hamming 9,036=24.00%)
   validators: validate.py=PASS | validate_raster.py=14/14 PASS | sha256_not_spent=PASS | reread_from_disk=PASS
```

---

## Session 7 TRACKB (Phase 2 only — upload ONLY if the human explicitly decides)

| File (`releases/`) | Name | Form note |
|---|---|---|
| `h33-h33-2-b2-TRACKBt1k10-20261023-8343ab38.tif` (+ `-zeros.tif` fallback, GeoJSON `...-8343ab38-traces.geojson`) | `h33-h33-2-b2-TRACKBt1k10-20261023-8343ab38` | `h33-h33-2-b2; TRACKB t1k10: relocate 10.0% lowest-S off-trace dots onto >= 1 km traces; pred +0.004 MODEL` |
| `h33-h33-2-b2-TRACKBt1k20-20261023-ab72339b.tif` | `h33-h33-2-b2-TRACKBt1k20-20261023-ab72339b` | same note with `t1k20`, `20.0%`, `+0.005` |
| `h33-h33-2-b2-TRACKBt2k10-20261023-6d16fd7a.tif` | `h33-h33-2-b2-TRACKBt2k10-20261023-6d16fd7a` | same note with `t2k10`, `>= 2 km`, `+0.002` |

Format receipt (RECEIPT, re-read from disk): all three 37,654 dots, EPSG:32611 3730x3292 float32 1-band, values in [0,1], NaN outside footprint (zeros twin = 0 outside), catalogue mass 0, min d_cat 2.236 px, release_gates PASS + validate_raster 14/14 PASS (`gems91.gates` collar_ge_3px FAILs identically on R0 itself — 2,171 inherited 2-3 px dots, IR-91-03/IR-91-31; zero TRACKB-added dots are <=3 px), sha256 as in file names / `evidence/trackb_axis_20261023.json`. Rebuild: `python3 scripts/restore_data.py && python3 scripts/build_trackb.py --build` (byte-identical, verified twice).
## Session 6 (`arena/9b8f7d01-gemsdoe91`) — SNAP variants (built; **not** in the top 3)
All three files and their `-zeros` fallbacks are on disk in `releases/`, pinned in
`releases/MANIFEST.json` (never committed). **No agent submits.** `SNAP` is predicted at or
below R0 on the only independent locator (off-catalogue USGS SGMC), so it is a reserve
axis-retirement test, not a slot candidate (`SLOT_PLAN.md`, `docs/MECHANISM_CARDS_SNAP.md`).
```bash
python3 scripts/restore_data.py
python3 scripts/build_snap.py --build
python3 scripts/validate.py releases/h33-h33-2-b2-SNAPs2c-20261023-86b27de1.tif
python3 scripts/validate_raster.py releases/h33-h33-2-b2-SNAPs2c-20261023-86b27de1.tif \
    data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif \
    --parent data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
```
| File (`releases/`) | Rule | Form note (≤140 chars, exact length) | `MODEL` |
|---|---|---|---|
| `h33-h33-2-b2-SNAPs2c-20261023-86b27de1.tif` | 3×3 crest only, 2,047 dots moved (5.44 %) | `h33-h33-2-b2; SNAP crest: 2047 dots (5.4%) moved 0.08px mean, count fixed; pred MODEL:+0.000` (92) | +0.000 `[−0.006,+0.006]` |
| `h33-h33-2-b2-SNAPs2q75-20261023-8aa75390.tif` | window max, gain ≥ p75, 4,495 moved (11.94 %) | `h33-h33-2-b2; SNAP maxq75: 4495 dots (11.9%) moved 0.24px mean, count fixed; pred MODEL:-0.004` (94) | −0.004 `[−0.012,+0.005]` |
| `h33-h33-2-b2-SNAPs2f-20261023-c2391234.tif` | window max, no threshold, 35,174 moved (93.41 %) | `h33-h33-2-b2; SNAP maxfull: 35174 dots (93.4%) moved 1.73px mean, count fixed; pred MODEL:-0.014` (96) | −0.014 `[−0.028,+0.004]` |
### Session 6 format receipt (`RECEIPT`, re-read from disk after write)
```text
1. h33-h33-2-b2-SNAPs2c-20261023-86b27de1
   primary (.tif)        sha256=86b27de1e6849101ebd6a3ab925183fdf1bed4f11257997678ee226ebe80ecb4 (371,722 B)
   fallback (-zeros.tif) sha256=b8f1a8ed6c80b038355a8f9aed7277c9b6d59817521fbe96af97c52abb15d42e (224,489 B)
   dots 37,654 unit-mass | count_matches_parent PASS | cat_mass 0 | min_d_cat 2.2361 px (added_le3px 0)
   collar 2,171 -> 2,171 | moved 2,047 | mean disp 0.0798 px | Hamming 4,094 (10.87%)
   gates: release_gates 16/16 PASS (nan + zeros) | validate_raster 14/14 PASS | reread_from_disk PASS
2. h33-h33-2-b2-SNAPs2q75-20261023-8aa75390
   primary (.tif)        sha256=8aa7539013b4e89df65e752da2a4a477ac4f7d0c972a46f03673b631490e94c9 (372,144 B)
   fallback (-zeros.tif) sha256=9c4c13d39b48147615e66340803274517c3cc15974d9451e8cf46bee4edf1fa9 (225,140 B)
   dots 37,654 unit-mass | count_matches_parent PASS | cat_mass 0 | min_d_cat 2.2361 px (added_le3px 0)
   collar 2,171 -> 2,171 | moved 4,495 | mean disp 0.2369 px | Hamming 8,990 (23.88%)
   gates: release_gates 16/16 PASS (nan + zeros) | validate_raster 14/14 PASS | reread_from_disk PASS
3. h33-h33-2-b2-SNAPs2f-20261023-c2391234
   primary (.tif)        sha256=c239123496deb176c6ed8d365284715570cd11bacd77d9c266064dd5a8b97c75 (372,581 B)
   fallback (-zeros.tif) sha256=f2fe14c1c46b133cf4bd16bcbde8bc0a07fd8b0de1e0038c97411cb860ac85c7 (225,819 B)
   dots 37,654 unit-mass | count_matches_parent PASS | cat_mass 0 | min_d_cat 2.2361 px (added_le3px 0)
   collar 2,171 -> 2,171 | moved 35,174 | mean disp 1.7331 px | Hamming 70,348 (186.83%)
   gates: release_gates 16/16 PASS (nan + zeros) | validate_raster 14/14 PASS | reread_from_disk PASS
PROXY (report only, never a score): catalogue hide-and-recover 0.006186 [0.005958, 0.006413],
5 draws, 12,198-12,201 withheld positives/draw -- identical for R0 and all three arms BY
CONSTRUCTION (targets >3 px, collar quarantined; IR-91-28).  SGMC off-catalogue (62,122 px,
USGS DS-1052): R0 0.095386 -> +0.00008 / -0.00234 / -0.00926.  Leakage canary max band AUC 0.5793.
```
**Do not** upload more than one SNAP arm for the "information" of it — they are one dose-response
experiment. If a SNAP receipt is bought, `s2c` is the only arm whose prediction is compatible with
no change, and `≤ −0.006` retires the axis.

---

# SESSION 8 — CONCENTRATION dose bracket + residual allocator (2026-10-24)

**Status: `50` BUILT rows, 0 submitted, 0 receipts.** These three files are **not** in the top 3
slots (see `SLOT_PLAN.md`); they are the reserve set behind Week 1. Nothing here is a score.

Build them (deterministic, ~100 s, no RNG beyond the fixed seed):

```bash
python3 scripts/restore_data.py                       # 15/15 pinned sha256 verified
python3 scripts/build_concentration_struct.py --build # 3 arms -> releases/, ledger, MANIFEST
python3 scripts/validate_raster.py releases/<file>.tif data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif \
    --parent data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
```

| slot | file (NaN outside footprint) | sha256 | zeros twin sha256 | dots | form note (≤140 chars) |
|---|---|---|---:|---:|---|
| reserve A | `h33-h33-2-b2-CONCENTRATIONres1km-m20-20261024-d9a0fcc4.tif` | `d9a0fcc4afde8d9a6a9502bc36301057181e92bf77e0135899ad936fa44ea13f` | `bcdb048210295e409b13228bdc6b9740c9f5704d135a6deec70e32e5613d622e` | 37,654 | `h33-h33-2-b2; CONCENTRATIONres1km-m20: 20.0% of 37654 dots reallocated across 1 km blocks (residual prior); pred +0.0114 MODEL` |
| reserve B | `h33-h33-2-b2-CONCENTRATIONst1km-m20-20261024-ba313f84.tif` | `ba313f841ef91cfd9fbd2a9b739fa0cc8f823b8de4121104bc9eab644e957347` | `28bd585ba8b9289ea47749235f7a65d482f644be0560110d3b49455126a0e195` | 37,654 | `h33-h33-2-b2; CONCENTRATIONst1km-m20: 20.0% of 37654 dots reallocated across 1 km blocks (struct prior); pred +0.0116 MODEL` |
| reserve C | `h33-h33-2-b2-CONCENTRATIONst1km-m10-20261024-45d1f4e9.tif` | `45d1f4e9d4beed04e34e62da43b5d02080c4cdb60edba8d50b98bf96976c3b30` | `7db0cd229bfd0d30a52d9ec7ce0a4d712eaa8560f30af7ceca3c6f06e34faa30` | 37,654 | `h33-h33-2-b2; CONCENTRATIONst1km-m10: 10.0% of 37654 dots reallocated across 1 km blocks (struct prior); pred +0.0062 MODEL` |

Upload exactly one of the pair per slot; the `-zeros` twin is the fallback for that same slot.

**Format receipt — paste this back with the score:**

```
candidate: <file name above>
sha256:    <the sha256 in the same row>
bytes:     NaN 369544-369832 / zeros 222785-222930 (read from `ls -l releases/`)
checks:    CRS EPSG:32611, 3730x3292, 100 m, float32, 1 band, values in [0,1],
           no NaN inside footprint, NaN outside, 0 dots on catalogue,
           min catalogue distance 2.236 px, 37,654 unit-mass dots
gates:     release_gates 16/16 PASS + validate_raster 14/14 PASS, both encodings
```

**What a receipt on any of these would decide.** `res1km-m20` ≥ `st1km-m20` ⇒ the parent
over-serves 1 km blocks, which also argues the delete-only PRUNE arms are right; `st1km-m20` >
`res1km-m20` ⇒ the residual is a dilution and the brief's `0.51-0.59` CV band carries no signal.
Any arm ≥ +0.010 ⇒ structural CONCENTRATION is a lever worth pairing with PRUNE in Week 2.
