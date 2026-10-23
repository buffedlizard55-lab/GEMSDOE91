# SUBMIT — what to upload, and what to paste back

**Status 2026-10-23 (session 5): 9 release pairs are built and gate-clean** (`releases/`,
rebuilt on demand — `releases/*.tif` are gitignored; the hash contract is
`releases/MANIFEST.json`, 18 files). **No agent has ever submitted anything and none may.**
One file per slot; the `-zeros` twin is the fallback encoding, not a second entry.

## Rebuild and verify (2–3 min, all inputs hash-checked)

```bash
python3 scripts/restore_data.py       # 15 pins, incl. the 419 MB stack from 5 hash-pinned parts
make releases                         # spacing + relief + prune ladder, then hashes vs MANIFEST
python3 scripts/preflight.py          # expect: BUILD ALLOWED
python3 scripts/verify_manifest.py    # expect: 15/16 verified (catalogue_mask is derived)
```

`make releases` prints `manifest verified: 18 files` and exits non-zero if any byte moved.
A hash that does not reappear means a **different file** — log it in `IRREGULARITIES.md`
before uploading anything.

## Slot 1 — the recommendation (`SLOT_PLAN.md`)

| field | value |
|---|---|
| file | `releases/h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f.tif` |
| fallback | `…-1ca1ff6f-zeros.tif` (one encoding per slot, never both) |
| sha256 (NaN) | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` |
| sha256 (zeros) | `28273f12207fbdda4ac75ffd1902e5cf38807cefe6951d34999f2d15a94330e0` |
| dots | 21,989 (parent 37,654; 15,665 deleted, 41.60 %, **no refill**) |
| form note (≤140) | `h33-2-b2; PRUNE <=15px delete-only, 21989 dots (41.6% removed), count not held; predicted +0.010 MODEL` |
| predicted | **+0.010** [−0.008, +0.024] MODEL — the largest on the ledger |

## The RELIEF triplet built this session (do **not** spend a slot on it yet)

| arm | file suffix | sha256 (NaN) | predicted |
|---|---|---|---|
| range→piedmont | `…-RELIEFr2m15-20261023-2c3839c9.tif` | `2c3839c9…` | +0.0070 |
| piedmont→range | `…-RELIEFm2r15-20261023-3c3e832d.tif` | `3c3e832d…` | −0.0070 |
| null | `…-RELIEFnull15-20261023-6c057de2.tif` | `6c057de2…` | 0.0000 |

They are matched (same 5,648 moves, same placement rule, count fixed 37,654, every new dot
> 3 px from the catalogue). They are **not** slot candidates this week: each prediction is
±0.007, below the 0.01 evidence bar, and the arm is only interpretable as
`r2m15 − null15`. Full hashes: `releases/MANIFEST.json`; numbers: `evidence/relief_axis_20261023.json`.

## Format receipt — copy this into the PR / session notes after uploading

```
candidate: h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f
encoding:  NaN-outside (primary)            zeros twin: kept as fallback
sha256:    __________________________________________
bytes:     ______
validate_raster.py : RESULT = PASS  (14/14 MUST gates)
validate_release.py: PASS (count_matches_parent False is expected for a delete-only arm)
n_dots:            21989
min_dist_catalogue_px: ______   zero_catalogue_mass: yes
receipt_score:     ______      receipt_date: ____________
```

## After the score comes back

1. Paste `receipt_score` and `receipt_date` into the row whose `id` ends `1ca1ff6f` in
   `ledger/submissions.csv`, and set `status=SUBMITTED`. Never write a score into
   `predicted_change`.
2. **Gain ≥ +0.01** → mass is the lever: next slot `…-PRUNEle8norefill-…-e1dd69d0.tif`
   (or a new deeper dose), and R1 becomes the parent for later builds.
3. **|Δ| < 0.01** → no evidence; PRUNE is exhausted, move to CONCENTRATION on a feature-stack
   prior (see `SLOT_PLAN.md`).
4. **Loss ≥ 0.01** → the ≥ 3 px collar is wrong for this dataset; build the **add-in-collar**
   arm (3–8 px) instead.
5. Update only the CURRENT STATE block of `README.md`.

## Do not

- Do **not** upload two encodings of the same file, or any file whose sha256 is already in
  `ledger/submissions.csv` (8+ upstream slots were spent on exact repeats).
- Do **not** upload a file whose `validate_raster.py` result is not `PASS`.
- Do **not** submit from any account but the entity's own, and do not submit more than the
  three scored files a week plus the one final blind choice.
