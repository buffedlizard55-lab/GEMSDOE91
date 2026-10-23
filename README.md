# GEMSDOE91 — GEMS Prize (DrivenData #306) candidate-build harness

One human, one registered entity, three scored slots a week. This repository builds
and validates candidate rasters. **It never submits and never contacts the
competition site.**

<!-- CURRENT STATE -->
## CURRENT STATE (2026-10-23)

- **Parent:** R0 = `h33-h33-2-b2` (GEMSDOE32) — **not reproducible in this checkout**:
  the raster is absent and no sha256 is pinned. Nothing was built.
- **Best receipt-backed score:** none. `0.2778` on R0 is a **CLAIM** (owner-reported,
  no receipt in `ledger/`). There is no `ledger/raw_paste.txt` to rebuild from.
- **TOP_PUBLIC:** `____` (human must fill from the leaderboard, with date).
- **Slots left this week:** `__ / __`. Deadline 2026-12-03 (unconfirmed here — the
  competition site is not readable from this sandbox, see `IRREGULARITIES.md` I-6).
- **Session axis (agent-chosen):** CONCENTRATION. Built and tested; **0 variants
  produced** because preflight blocks on missing inputs.
- **Next 3 slots:** (1) CONCENTRATION f10-blk50 — tests whether km-scale prior
  carries transferable signal at fixed count; (2) CONCENTRATION f20-blk50 only if
  (1) moves ≥ 0.01, otherwise spend the slot on PRUNE ≤3 px (needs `R0_ranking`);
  (3) SNAP ≤2 px (needs TMI + gravity gradients). See `SLOT_PLAN.md`.
- **Blocking ask:** put `data/sample_submission.tif`, `data/h33-h33-2-b2.tif`,
  `data/catalogue_mask.tif` and `data/prior_kmscale.tif` in `data/`, pin their
  sha256 in `registry/data_manifest.json`, then `make preflight`.

<!-- /CURRENT STATE -->

## What is here

| path | purpose |
|---|---|
| `tools/dti.py` | DTI algebra, kernel credit, exact marginal-gain ranking (MODEL, assumptions documented) |
| `tools/validate_submission.py` | the MUST gates (format, catalogue, dedupe, parent diff) + report-only proxies |
| `tools/run_concentration.py` | the CONCENTRATION axis builder (mechanism card in the docstring) |
| `tools/preflight.py` | refuses to build until every input is pinned and hash-verified |
| `tools/stor.py` | `ledger/submissions.csv` schema, dedupe rules |
| `tools/make_fixture.py` | synthetic fixture so the gates are testable without competition data |
| `registry/data_manifest.json` | pinned input hashes (currently all `null` = nothing may be built) |
| `docs/` | `DATA.md`, `SUBMIT.md`, `MECHANISMS.md` |
| `SLOT_PLAN.md`, `IRREGULARITIES.md`, `AI_USE.md` | the plan, the contradictions, the disclosure |

## Quick start

```bash
make install test          # 49 tests on synthetic data, no competition files needed
make preflight             # exits 2 and lists exactly what is missing today
# after the inputs land and are pinned:
make concentration         # writes releases/…  (not registered)
make validate CAND=releases/<id>.tif
```

Rasters are **not** committed: the repo is public and the competition data-use terms
are unchecked. Only recipes, hashes and receipts travel.
