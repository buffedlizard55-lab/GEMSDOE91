# ledger/

`submissions.csv` — one row per candidate that has ever been built for this entity.

## Provenance

All 20 rows carry `source = IMPORT:GEMSDOE88 (not built in this session)`. They were
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
