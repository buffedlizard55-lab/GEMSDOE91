# SUBMIT — what to upload, and what to paste back

**Status 2026-10-23: six CONCENTRATION files and three PRUNE files are gate-clean.** Rasters are
not committed; `releases/MANIFEST.json` is the sha256 contract and CI rebuilds every file from
the pinned inputs and asserts byte-identity. **No agent submits. One file per slot; the
`-zeros` twin is the fallback for the same slot, never a second entry.**

## Rebuild and verify (≈2 min, five pinned inputs, every sha256 checked)

```bash
python3 scripts/restore_data.py              # fetch + verify every pinned sha256
python3 scripts/build_concentration.py --build   # the three CONCENTRATION arms
python3 scripts/make_catalogue.py            # derived catalogue mask (PRUNE needs it)
python3 scripts/build.py --axis PRUNE --value 15 \
    --id h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f \
    --catalogue data/derived/catalogue_mask.tif   # verified to print 1ca1ff6f… today
python3 scripts/validate.py releases/<file>.tif   # must print PASS
```

## Files for the next three slots

| slot | upload (NaN-outside primary) | sha256 (must match `releases/MANIFEST.json`) | predicted (MODEL) |
|---|---|---|---|
| 1 | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` | `c19adb012aec8571fcca393e3401050b01011286cec7282393cbcc0cca6a6e30` | +0.0123, range −0.022 … +0.037 |
| 2 | `…-PRUNEle15norefill-20261023-1ca1ff6f.tif` (verified reproducible today) | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` | +0.010, range −0.008 … +0.024 |
| 3 | `…-CONCENTRATIONgdr25m10-20261023-08bf80cf.tif` *if slot 1 ≥ +0.005*, else `…-PRUNEle8norefill-20261023-e1dd69d0.tif` | `08bf80cf443cc68faeb0dd0eca8d0aecf85eb113e7d3094e3a778382bc180369` / `e1dd69d02b90f95e779c43de1843ac53c4064619e74c81ee230a08058ba15654` | +0.0114 / +0.006 |

Full names are `<parent>-<axis><value>-<yyyymmdd>-<sha8>.tif`; the parent is
`h33-h33-2-b2-20261004-e5eb6e7e`. Zeros twins exist beside every file and carry `-zeros.tif`.

**Form notes** (≤140 chars, already in `ledger/submissions.csv:form_note`, no score claimed):

```
h33-h33-2-b2-20261004-e5eb6e7e; 10.0% of 37654 dots moved to the highest-prior 2.5 km GDR-thermal blocks [gdr25rm10]; pred +0.0123 MODEL
h33-h33-2-b2-20261004-e5eb6e7e; 10.0% of 37654 dots moved to the highest-prior 2.5 km GDR-thermal blocks [gdr25m10]; pred +0.0114 MODEL
h33-2-b2; delete-only, 15,665 dots (41.6%) within <=15px of catalogue removed, no refill, count 21989; pred +0.010 MODEL
```

## Format receipt — copy this into the PR/session notes for the file you upload

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

1. `receipt_score` + `receipt_date` into `ledger/submissions.csv` (never into `predicted_change`);
   `status` → `SCORED`. Under |Δ| < 0.01 record "no evidence (public chunks only)".
2. `≥ +0.01` → that parent becomes the base for the next slot; `≤ −0.01` on the CONCENTRATION
   arm → the thermal prior does not transfer, retire the axis (SLOT_PLAN.md).
3. Update only the CURRENT STATE block of `README.md`.

## Do not

- Do not upload both twins of one file, or a file whose sha256 is already in the ledger
  (8+ upstream slots were spent on exact repeats).
- Do not submit the `gdr10m10` arm before the two 2.5 km arms have receipts: it is the same
  experiment at a finer block size (IR-91-17).
- Do not treat the catalogue proxy (0.0054 vs R0's 0.0062) as a score; it is PROXY, it fell
  by 12.6 %, and IR-91-15 explains why that is not evidence against this axis.
- Do not submit from any account but the one entity's. One final file, chosen blind.
