# Submission handoff — human only

**No file has been submitted.** Do not use a candidate until you confirm the score receipt for the incumbent, current weekly/total quota, data-use terms, and competition deadline. The agent never submits.

## One built candidate

- **Primary (NaN outside):** `releases/h33-h33-2-b2-PRUNEp2p6-20261023-d7ebdd61.tif`
- **Fallback (zeros outside):** `releases/h33-h33-2-b2-PRUNEp2p6-20261023-d7ebdd61-zeros.tif`
- **Upload only one encoding per slot**; never upload both as separate experiments.
- **Form name:** `h33-h33-2-b2-PRUNEp2p6-20261023-d7ebdd61`
- **Form note (61 chars):** `R0 h33-h33-2-b2; PRUNE dcat≤2.6px, fixed 37,654; +0.001 MODEL`
- **Predicted change:** `MODEL +0.001` relative to R0, range `[-0.007,+0.009]`; absolute changes below `0.01` are no evidence under the brief.
- **Candidate SHA-256:** `d7ebdd616d15f5b2f7ac34a7805c82605cf6eae1b51651b9bf773261d54f1e92`
- **Zeros fallback SHA-256:** `250a6698ff396024783e789a1a05e617b58ef8dad37ef54f507e467d7b9cba50`
- **Local format receipt:** `releases/h33-h33-2-b2-PRUNEp2p6-20261023-d7ebdd61.json` (full gates and on-disk hashes); standalone recheck: `python scripts/validate_prune_release.py`.

## Must do after any human submission

1. Copy the submission-page receipt accurately into `ledger/submissions.csv` (`receipt_score` and `date`); distinguish it as a `RECEIPT`.
2. Update README CURRENT STATE with the receipt-backed incumbent, TOP_PUBLIC/date, and exact slot counts.
3. Do not call local hide-and-recover or SGMC outputs scores; both are `PROXY` and report-only.
