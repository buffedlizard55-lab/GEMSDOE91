# SUBMIT — the human's side of a slot

The agent never submits. Each slot costs one of three weekly scored submissions plus the
single final one, so every upload is preceded by a green gate receipt.

## 1. Pick the file

Only from `ledger/submissions.csv` rows with `status = GATED` (every MUST gate passed).
Prefer the row with the best **receipt**, never the best MODEL number. Rows with
`status = BUILT` have not been through the validator.

## 2. File

- Upload **one** of the pair, primary `releases/<id>.tif` (NaN outside the footprint).
- The `-zeros.tif` twin is a fallback for a reader that rejects NaN; the two have been
  observed to score identically, so they are one experiment and share one ledger row.
- Name to use on the site: the file stem, e.g.
  `R0-CONCENTRATIONf10-blk50-20261023-<sha8>`.

## 3. Note field (≤ 140 characters, pre-composed by the builder)

Form: `<parent>; <the one change>; predicted <sign + size>`.
Example: `R0; moved 10% of dots from lowest- to highest-prior 5km blocks, count fixed; predicted +0.01`.

## 4. Format receipt (paste into `ledger/submissions.csv` and `docs/SUBMIT.md`)

```
id                     :
uploaded_utc           :
portal_accepted (y/n)  :
receipt_score          :
receipt_url_or_id      :
screenshot             : (keep out of this repo if it shows account identifiers)
```

Fill `receipt_score` from the submission page and nothing else — a score read from a
leaderboard widget, remembered from a previous week, or inferred is a **CLAIM**, and must
be written in `docs/SUBMIT.md` under "claims", not in `receipt_score`.

## 5. After the receipt lands

```bash
# record it (human edits the CSV — the agent does not)
#   status: SCORED, receipt_score: <value>, receipt_date: <yyyy-mm-dd>
python -m tools.stor                  # confirm the row and its hash
```

Then the AXIS gets a verdict: `|Δ| ≥ 0.01` is evidence, `< 0.01` is no evidence, and the
next slot is chosen by `SLOT_PLAN.md`, not by the size of the last number.

## Standing checks before every upload

- [ ] `sha256` of the file is in the ledger and was not sent before (exact-repeat rule)
- [ ] catalogue mass is exactly zero and the min dot gap is the intended one
      (`IRREGULARITIES.md` I-3 — decide which reading of the 3 px rule you are using)
- [ ] the file was re-read from disk after writing and hashed again
- [ ] `AI_USE.md` current for this session
- [ ] slot count for the rolling week still allows the upload
