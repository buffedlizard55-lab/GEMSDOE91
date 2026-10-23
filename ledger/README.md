# ledger/

`submissions.csv` — one row per candidate that has ever been built for this entity.

## Provenance

The 20 imported rows carry `source = IMPORT:GEMSDOE88 (not built in this session)`. They were
transcribed on 2026-10-23 from the public repo `buffedlizard55-lab/GEMSDOE88`, which is the
umbrella repo of this lineage. **Nothing in this session was appended** — no variant was built
(`../IRREGULARITIES.md` IR-91-02).

`receipt_score` and `receipt_date` are empty in all 20 rows. There is no receipt anywhere in
this lineage; R0's 0.2778 is a CLAIM. Do not treat `predicted_change` as a result.

## Columns

`id, parent, axis, value, n_dots, pct_changed, sha256, sha256_zeros, status, predicted_change,
predicted_range, ranking_basis, receipt_score, receipt_date, source, notes`

- `predicted_change` / `predicted_range` are **MODEL** projections from the build session.
- `ranking_basis` records what ranked the dots. All three MASS rows say
  "NOT parent model ranking" — that is why MASS is still an open axis.
- `receipt_score` is the ONLY place a live score may go, and only copied from the
  submission-page receipt.

## Dedupe rules (brief §6)

A candidate is rejected if either holds:

1. its `sha256` or `sha256_zeros` already appears in this file;
2. its `(parent, axis, value)` triple already appears.

Nothing else is deduped. No overlap threshold, no rank-correlation threshold, no
dot-position "uniqueness" score — the brief forbids those as gates.

## Appending a row

```bash
python scripts/validate_release.py releases/<id>.tif --axis <AXIS>   # must print CERTIFIED
# then append one row; every hash column is mandatory
```

`tests/test_ledger.py` enforces unique ids, unique hashes, unique triples, the axis vocabulary
and that `receipt_score` is either empty or a float.

## Session 3 (`arena/a5e7bf22`) — three rows appended

`SPACINGspread40`, `SPACINGclump40`, `SPACINGjitter40`, all built here and marked
`source = SESSION 3 (this branch)`. The file now has **23 rows and still 0 receipts**.

Two conventions this session adds, both to remove ambiguity:

* `pct_changed` is **relocated dots ÷ parent dots** (the prior-session convention: a
  dot that moves counts once). `pct_relocated` repeats it explicitly, and the Hamming
  distance (added + removed ≈ 2× relocated) lives in `evidence/spacing_axis_20261023.json`
  as `hamming_vs_parent`, so the brief's "1–50 % of dots" rule can be checked either way.
* `parent` is written as `h33-h33-2-b2-20261004-e5eb6e7e` (the full artifact id) for the
  session-3 rows, while the imported rows use `h33-h33-2-b2`. **These are the same
  artifact** — same sha256 `c55bafc4…`. Dedupe on the hash, never on the parent string,
  or a repeated `(parent, axis, value)` can hide behind two spellings.


## Session 5 (`arena/9cc58e7e`) — three RELIEF rows appended, still 0 receipts

`RELIEFr2m15`, `RELIEFm2r15`, `RELIEFnull15` — the axis had **no rows at all** before this
session (PRUNE 7, SNAP 9, CONCENTRATION 4, MASS 3, SPACING 3). The file now has **29 rows**.

* `pct_changed` is the brief's 1–50 % quantity as **relocated ÷ parent dots** (14.9997 %, i.e.
  5,648 of 37,654 moved); `pct_relocated` repeats it. The Hamming distance against the parent is
  exactly twice that (29.9995 %), recorded in `evidence/relief_axis_20261023.json` as
  `hamming_vs_parent`.
* `ranking_basis` says explicitly that **no ranking was used** — donors are uniform at a fixed
  seed inside the donor tercile; recipients are the same greedy rule in every arm. This is the
  opposite of the three imported MASS rows, which invented a ranking and admitted it.
* `predicted_change` stays MODEL and every row's `receipt_score` is empty. Session 4's PRUNE
  ladder rows and session 3's SPACING rows are unchanged and still receipt-free.

The PRUNE ladder's three hashes in this file now **reproduce byte for byte** from pinned inputs
(`make releases`), and all 18 shipped files are listed in `releases/MANIFEST.json`.
