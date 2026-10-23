# Ledger conventions

Two files, deliberately separate:

* **`submissions.csv`** — this session's variants only. One row per variant, as
  brief §7 asks. `receipt_score` and `receipt_date` are **blank on purpose**:
  only the human, from the submission page, may fill them. While they are blank
  every prediction in the file is a MODEL, not a result.
* **`prior_fleet.csv`** — the aggregate record imported on 2026-10-23 from
  `buffedlizard55-lab/GEMSDOE86/ledger/submissions.csv` (132 rows, the widest
  fleet record available), with exact-duplicate sha256 rows collapsed and
  columns reduced to the ones this session reads. Provenance, not endorsement:
  the numbers in its `score` column are CLAIMs and **it contains zero receipts**.

## Column meanings

| column | meaning |
|---|---|
| `id` | `<parent>-<AXIS><value>-<yyyymmdd>-<sha8>`; `sha8` is the first 8 hex of the released file's sha256 |
| `parent` | the artifact this was built from (only `h33-h33-2-b2-20261004-e5eb6e7e` this session) |
| `axis`, `value` | the single axis edited and its dose |
| `n_dots` | emitted unit-mass dots (count is held at 37,654 in every arm) |
| `pct_changed` | **relocated dots ÷ parent dots**, the prior-session convention (so a dot that moves counts once). The Hamming distance (added + removed ≈ 2× relocated) is in `evidence/spacing_axis_20261023.json` as `hamming_vs_parent` |
| `pct_relocated` | duplicate of `pct_changed`, kept explicit so the brief's "1–50 % of dots" rule can be checked without ambiguity |
| `sha256`, `sha256_zeros` | hashes of the NaN-outside primary and the zeros fallback twin |
| `status` | `BUILT` when the file exists and passes every hard gate |
| `predicted_change`, `predicted_range` | MODEL projection; a live change under ±0.01 is not evidence |
| `ranking_basis` | how the edit chose its targets, stated so it can be attacked |
| `evidence_class` | `MODEL` here; RECEIPT only ever by the human |

## Dedupe rules (brief §6)

Collapse only on (a) **exact sha256** and (b) **repeated `(parent, axis, value)`**.
Two fills of the same dot set (`-nan` / `-zeros`) are one experiment whose twins
score identically, and the zeros twin is listed as the upload. No
rank-correlation or dot-overlap "uniqueness" threshold is applied anywhere.
