# SUBMIT — what to upload, and what to paste back

**Status 2026-10-23: 18 release pairs (36 files) built and gate-clean.** `releases/*.tif` are
gitignored and rebuilt on demand; the hash contract is `releases/MANIFEST.json` (36 entries, each
with `axis`, `n_dots`, `sha256`, `bytes`). **No agent has ever submitted anything and none may.**
One file per slot; the `-zeros` twin is the fallback encoding, **not** a second entry.

## Rebuild and verify (≈4 min, every input hash-checked)

```bash
python3 scripts/restore_data.py       # 15 pins, incl. the 419 MB stack from 5 hash-pinned parts
make releases                         # catalogue + every builder, then the hash contract
python3 scripts/update_release_manifest.py --check   # expect: 36 files, 0 problem(s)
python3 scripts/preflight.py          # expect: BUILD ALLOWED
python3 scripts/crosscheck_predictions.py            # PROXY table, report-only
```

`make releases` fails if a byte moved, if a file on disk is not in the manifest, if a manifest
entry was not rebuilt, **or if a built file's sha256 is not a row in the ledger**. A hash that
does not reappear means a *different file* — log it in `IRREGULARITIES.md` before uploading.

## Slot ranking (`SLOT_PLAN.md`; the human spends the slots)

| # | file | MODEL | why |
|---|---|---|---|
| 1 | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` | **+0.0123** [−0.022, +0.037] | the only prior independent of the catalogue *and* the lineage mask |
| 2 | `…-PRUNEle15norefill-20261023-1ca1ff6f.tif` | **+0.010** [−0.008, +0.024] | top of the delete-only ladder: one receipt answers the whole family |
| 3 | conditional | — | `gdr25m10` if slot 1 ≥ +0.005 · `le10` if slot 2 ≥ +0.01 · `SPACINGspread40` if both are flat |

## Every primary file (NaN encoding; zeros twin in `releases/MANIFEST.json`)

| axis | dots | file | sha256 (first 16) | bytes |
|---|---:|---|---|---:|
| CONCENTRATION | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-CONCENTRATIONgdr10m10-20261023-d54e8815.tif` | `d54e881580e332ef…` | 368,830 |
| CONCENTRATION | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-CONCENTRATIONgdr25m10-20261023-08bf80cf.tif` | `08bf80cf443cc68f…` | 369,066 |
| CONCENTRATION | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` | `c19adb012aec8571…` | 369,017 |
| PRUNE | 37,654 | `h33-h33-2-b2-PRUNEp2p5h19cover-20261023-e6f2000d.tif` | `e6f2000dae956483…` | 355,531 |
| PRUNE | 37,654 | `h33-h33-2-b2-PRUNEp2p9h19cover-20261023-9829bb66.tif` | `9829bb66c1958a77…` | 354,947 |
| PRUNE | 37,654 | `h33-h33-2-b2-PRUNEp4p5h19cover-20261023-691438f8.tif` | `691438f85f2cf907…` | 352,689 |
| PRUNE | 35,483 | `h33-h33-2-b2-PRUNEle3norefill-20261023-1209e863.tif` | `1209e863a9ff58d8…` | 331,161 |
| PRUNE | 33,829 | `h33-h33-2-b2-PRUNE-le4-norefill-20261023-360fe57e.tif` | `360fe57edd828639…` | 355,396 |
| PRUNE | 32,017 | `h33-h33-2-b2-PRUNE-le5-norefill-20261023-5b6d3987.tif` | `5b6d39870bc0fe98…` | 347,613 |
| PRUNE | 28,490 | `h33-h33-2-b2-PRUNEle8norefill-20261023-e1dd69d0.tif` | `e1dd69d02b90f95e…` | 311,319 |
| PRUNE | 26,294 | `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif` | `04002dae86db72c3…` | 321,924 |
| PRUNE | 21,989 | `h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f.tif` | `1ca1ff6f782d5ba3…` | 291,857 |
| SPACING | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGclump40-20261023-536d32ad.tif` | `536d32ad49bdf70a…` | 371,632 |
| SPACING | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGjitter40-20261023-39bb7288.tif` | `39bb728839d70ab0…` | 372,814 |
| SPACING | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGspread40-20261023-6d389309.tif` | `6d389309aafaa79d…` | 373,103 |
| RELIEF | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFm2r15-20261023-3c3e832d.tif` | `3c3e832d4788a2c0…` | 366,272 |
| RELIEF | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFnull15-20261023-6c057de2.tif` | `6c057de2ef397991…` | 364,998 |
| RELIEF | 37,654 | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFr2m15-20261023-2c3839c9.tif` | `2c3839c9a7aebef8…` | 360,499 |

Full 64-character sha256 for every file — primaries and zeros twins — is in
`releases/MANIFEST.json`; `python3 scripts/update_release_manifest.py --check` re-derives every one.

## What the cross-check says about the same files (PROXY, report-only)

| file | `dti_proxy` | Δ vs R0 |
|---|---:|---:|
| R0 | 0.006778 | — |
| `SPACINGspread40` | 0.007861 | **+0.001083** (only positive arm) |
| `CONCENTRATIONgdr25rm10` | 0.005937 | −0.000841 |
| `RELIEFr2m15` | 0.005888 | −0.000890 |
| `PRUNEp2.5pxh19cover` | 0.001242 | −0.005536 |
| every delete-only PRUNE dose | 0.000000 | −0.006778 |

R0 earns **all** of its measurable credit from 1,611 dots inside 3 px of a mapped trace. Nothing
here is a score: the instrument sees only mapped faults and is blind to the new ones that decide
the real metric (IR-91-21).

## Form notes (≤140 chars, one per file, no score claimed)

```
Parent R0 h33-2-b2; CONCENTRATION 10% into top GDR-prior 2.5 km blocks (>8px off catalogue), count fixed 37654; pred +0.012 MODEL
Parent R0 h33-2-b2; PRUNE <=15px delete-only, 21989 dots (41.6% removed), count not held; predicted +0.010 MODEL
Parent R0 h33-2-b2; SPACING spread40: 15056 dots (40.0%) to emptiest ring-2 cell, count fixed 37654; pred +0.004 MODEL
```

## Format receipt — copy this into the ledger / PR after uploading

```
candidate: <id from releases/MANIFEST.json>
encoding:  NaN-outside (primary)            zeros twin: kept as fallback
sha256:    __________________________________________
bytes:     ______
validate_raster.py : RESULT = PASS  (14/14 MUST gates)
validate_release.py: PASS
n_dots:            ______
min_dist_catalogue_px: ______   zero_catalogue_mass: yes
receipt_score:     ______      receipt_date: ____________
```

## After a score comes back

1. Paste `receipt_score` + `receipt_date` into the ledger row whose `id` carries the sha8, set
   `status=SUBMITTED`, leave `predicted_change` untouched.
2. **≥ +0.01** → that axis is live: take its next arm from the fork table in `SLOT_PLAN.md`.
3. **|Δ| < 0.01** → **no evidence**, not "neutral". Do not refine that axis by a notch.
4. **≤ −0.01** → the axis is wrong in the direction tested; the fork table says what replaces it.
5. Update only the CURRENT STATE block of `README.md` and the slot table in `SLOT_PLAN.md`.
6. Compare against **TOP_PUBLIC** with its date; a change inside the public-chunk noise is not
   evidence whatever its sign.

## Do not

- Do **not** upload two encodings of the same file, or any file whose sha256 is already in
  `ledger/submissions.csv` (8+ upstream slots were spent on exact repeats).
- Do **not** upload a file whose `validate_raster.py` result is not `PASS`.
- Do **not** submit from any account but the entity's own; at most three scored files a week plus
  the one final blind choice.
- Do **not** spend three slots on the CONCENTRATION arms — they are one experiment (IR-91-17) —
  or any slot on the RELIEF arms, which are interpretable only as a pair.
- Do **not** contact drivendata.org, the leaderboard, or dropbox.com programmatically from this
  repo. The human reads the number; the repo records it.
