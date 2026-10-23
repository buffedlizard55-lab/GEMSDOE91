# SUBMIT — what to upload, and what to paste back

**Status 2026-10-23: 32 BUILT rows, 0 submitted, 0 receipts.** Rasters are not committed;
`releases/MANIFEST.json` is the sha256 contract and CI rebuilds every file from pinned inputs and
asserts byte-identity. **No agent submits. One file per slot; the `-zeros` twin is the fallback
for that same slot, never a second entry.**

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
