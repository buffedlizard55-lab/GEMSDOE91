# SUBMIT — what the human uploads

The human uploads from their own registered account. Nothing here submits, logs
in, or reads the leaderboard. **One file per slot**; the `-zeros` twin is the
fallback, not an extra entry.

## The three files built this session

| slot rank | file to upload | sha256 (verify before upload) | bytes |
|---|---|---|---|
| 2 (session build) | `releases/h33-h33-2-b2-20261004-e5eb6e7e-SPACINGspread40-20261023-6d389309-zeros.tif` | `5c517369…` (full hash in `ledger/submissions.csv`) | 226,284 |
| — | `…-SPACINGspread40-20261023-6d389309.tif` (NaN-outside primary) | `6d389309…` | 373,103 |
| — | `…-SPACINGclump40-20261023-536d32ad-zeros.tif` (control, predicted ≤ 0) | `d393c94f…` | 224,741 |
| — | `…-SPACINGjitter40-20261023-39bb7288-zeros.tif` (null control) | `ad6dfa26…` | 225,691 |

**Which twin?** Both are accepted by the format gate. Prior sessions report the
`-nan` and `-zeros` fills score identically; the `-zeros` twin is smaller and is
the one the ledger lists first. Upload exactly one.

## Name / note fields

**File name** (already on disk, copy it verbatim):

```
h33-h33-2-b2-20261004-e5eb6e7e-SPACINGspread40-20261023-6d389309-zeros.tif
```

**Form note** (≤ 140 characters, no scores claimed):

```
Parent R0 h33-2-b2; move 15,056 dots (39.99%) 2.0-2.24 px to emptier ground, count fixed 37,654; predicted +0.004 MODEL
```

## Before you click submit

1. `python3 scripts/validate.py releases/<file>.tif` → must print `PASS`.
   It checks, by re-reading the file from disk: CRS EPSG:32611, shape
   3730×3292, transform `(100, 0, 243350, 0, -100, 4508550)`, float32, one band,
   values in [0, 1], no NaN inside the footprint, NaN outside (or zeros outside
   for the twin), zero catalogue mass, minimum catalogue distance > 2.0 px, and
   that the sha256 is not already in `ledger/submissions.csv`.
2. Record the receipt. After the submission page returns a score, put it in
   `ledger/submissions.csv` in `receipt_score` and `receipt_date` for that row.
   That single edit converts a CLAIM into a RECEIPT and is worth more than
   another variant — see `SLOT_PLAN.md`, action 0.
3. If the file fails a check, do **not** upload a hand-edited raster. Re-run
   `python3 scripts/build_spacing.py --build`; the build refuses to emit a file
   that fails a gate.

## What is deliberately not here

No automated upload, no session cookies, no leaderboard polling, no multiple
accounts. Three scored submissions per rolling week, one entity, one final file
chosen blind.
