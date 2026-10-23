# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2` (GEMSDOE32) — **hash-verified here** (both encodings),
  37,654 unit-mass dots, EPSG:32611, 3730×3292, 100 m, float32, footprint 5,167,373 px.
- **Best receipt:** **none.** There is no `receipt_score` in this lineage — 20/20 ledger
  rows are blank. `0.2778` for R0 is a **CLAIM**, not a receipt.
- **TOP_PUBLIC:** **____ (human must fill from the leaderboard, with date).**
  Upstream GEMSDOE88 carries `0.4413` as a human-supplied 2026-10-22 figure (**CLAIM**);
  this session did not verify it and does not adopt it.
- **Slots left this week:** **__ / __ (human must fill).**
- **Variants built this session:** **0.** Build blocked — see `IRREGULARITIES.md` IR-91-01/02/04.
  A preflight gate (`scripts/preflight.py`) refuses to start a build without
  `sample_submission.tif`, `existing_faults.tif`, `training_features.tif`.
- **AXIS for this session:** **MASS** — chosen here, not assigned. Still genuinely untested:
  the three existing MASS variants were ranked by a synthetic distance heuristic
  (`ranking_basis` = "NOT parent model ranking"), so no MASS result exists yet.
- **Next 3 slots (see `SLOT_PLAN.md`):**
  1. Rebuild and submit **R1 = PRUNE p3px** (`6f7ae705`) — the only fully collared file.
  2. **MASS m10minus on R1**, ranked by R1's own model (the brief's MASS recipe, first run).
  3. Conditional: **CONCENTRATION b10px-m20 on R1** if slot 1 lands ≥ R0 + 0.01, else
     **SNAP scarp2px on R1**.

## What this repo contains

| Path | Purpose |
|---|---|
| `registry/data_manifest.json` | 15 pinned inputs with sha256 + byte length; 3 re-hashed here |
| `registry/r0_verification.json` | Parent hash/grid/dot-count evidence (generated) |
| `registry/preflight.json` | Build-blocked verdict and exactly what is missing |
| `registry/raster_availability.json` | Which of the 20 ledger rows still have a raster |
| `registry/candidate_availability.json` | Hash + format status of the retrievable rasters |
| `src/gems91/metric.py` | DTI re-derivation + exact marginal gain |
| `src/gems91/gates.py` | The MUST gates; an unprovable gate is `UNVERIFIED`, never `PASS` |
| `scripts/` | `verify_parent_r0.py`, `preflight.py`, `validate_release.py`, `pinned.py` CLI |
| `ledger/submissions.csv` | 20 imported rows, provenance in `source`; empty receipt columns |
| `tests/` | 34 data-free tests (metric algebra, gates, ledger invariants) |

## Run it

```bash
pip install -r requirements.txt
python scripts/verify_parent_r0.py     # fetch pinned parent, verify sha256
python scripts/preflight.py            # BUILD ALLOWED / BUILD BLOCKED
python -m pytest                       # 34 tests, no competition data needed
```
