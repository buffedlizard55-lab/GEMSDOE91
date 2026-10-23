# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2` — **verified locally and rebuilt from two independent pinned ancestors** (`d2.8` and `solo-d2.8` minus `d_cat ≤ 2.0 px` → exact `37,654` unit-mass dots `RECEIPT`, digest `905cee9d…`). `baeae321…c77dd` (NaN) and `c55bafc4…6fa9` (zeros), `EPSG:32611`, `3730×3292`, `100 m`, `float32`, footprint `5,167,373` px, `0` dots on catalogue, min `2.236 px` from it (`RECEIPT`).
- **Inputs present and hash-verified: 15 of 15 pinned entries (`16/16` including `catalogue_px.tif`, `RECEIPT`)** via `scripts/restore_data.py` + `scripts/verify_manifest.py` (`scripts/preflight.py` → `BUILD ALLOWED: 3/3`). `training_features` (`418,912,844` B, sha256 `4371c82e…3bc5` `RECEIPT`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)) is now restored from 5 pinned git blobs; public-mirror status is flagged in `IRREGULARITIES.md` IR-91-17.
- **Axis readiness (`scripts/verify_manifest.py`):** **ALL 6 AXES READY** (`MASS`, `CONCENTRATION`, `SNAP`, `PRUNE`, `RELIEF`, `SPACING`).
- **Best receipt:** **none.** All `29` ledger rows in `ledger/submissions.csv` have `status=BUILT` and blank `receipt_score`/`receipt_date` (`20` imported, `3` SPACING, `3` PRUNE, `3` RELIEF). R0's `0.2778` / `0.3698` remains an unreceipted **CLAIM**.
- **TOP_PUBLIC:** **____ (human must fill from the leaderboard, with date).**
- **Slots left this week:** **__ / 3 (human must fill; 1 entity, 5.86 rolling weeks to unconfirmed 2026-12-03 deadline).**
- **AXIS for Session 5 (`arena/42de3fed-gemsdoe91`):** **RELIEF** (`0` prior ledger rows). Reallocates `4,518` dots (`12.00%` relocated; `9,036` pixel symmetric diff = `24.00%` `RECEIPT`) at fixed count (`37,654` `RECEIPT`) and zero catalogue-collar drift (`2,171 → 2,171` `RECEIPT`) across equal-area relief terciles `0.90·pct(det_elev) + 0.10·pct(det_elev_slope)`:

  | id | value | dots (`RECEIPT`) | relocated (`RECEIPT`) | T1 / T2 / T3 share (`RECEIPT`) | 4-fold `PROXY` Δ | SGMC `PROXY` Δ ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) | predicted (`MODEL`) |
  |---|---|---:|---:|---|---|---|---|
  | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c` | `r2p12` (`range->pied`) | 37,654 | 4,518 (12.00%) | 17.7 / 56.3 / 26.0% | −0.0017 | −0.0049 | **+0.006** `[−0.006, +0.018]` |
  | `h33-h33-2-b2-RELIEFr2b12-20261023-27443c30` | `r2b12` (`range->basin`) | 37,654 | 4,518 (12.00%) | 29.7 / 44.3 / 26.0% | −0.0032 | −0.0091 | **+0.003** `[−0.010, +0.016]` |
  | `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5` | `b2r12` (`basin->range`) | 37,654 | 4,518 (12.00%) | 5.7 / 44.3 / 50.0% | −0.0113 | **+0.0050** | **+0.005** `[−0.010, +0.020]` |

  All 6 rasters (`NaN` primary + `-zeros` twin) pass `gems91.release_gates.validate_release` (`PASS`) and `scripts/validate_raster.py` (`14/14` `RECEIPT`), are re-verified from disk, and are pinned byte-for-byte in `releases/MANIFEST.json` (no `.tif` committed to git). Single-band leakage canary across all 19 GeoDAWN bands has max symmetric AUC = `0.5793` `PROXY` (`≪ 0.90`).
- **Next 3 slots (see `SLOT_PLAN.md`):** Slot 1 `R0` anchor (unless human already holds an exact receipt for `baeae321…c77dd`) → Slot 2 `RELIEFr2p12` (`6ff08e5c`) → Slot 3 `RELIEFb2r12` (`e1fd28d5`, or `RELIEFr2b12` if Slot 2 gains `≥ +0.010`).

### Earlier session deltas (`PRUNE`, `SPACING`, `CONCENTRATION` infra)

- **Session 4 (`PRUNE`):** Delete-only dose ladder `PRUNEle3norefill` (`35,483` dots `RECEIPT`, `+0.002` `MODEL`), `PRUNEle8norefill` (`28,490` `RECEIPT`, `+0.006` `MODEL`), `PRUNEle15norefill` (`21,989` `RECEIPT`, `+0.010` `MODEL`).
- **Session 3 (`arena/a5e7bf22`, `SPACING`):** Matched radius-2 local spacing arms `SPACINGspread40` (`6d389309`, `+0.0042` `MODEL`), `SPACINGclump40` (`536d32ad`, `−0.0023` `MODEL`), `SPACINGjitter40` (`39bb7288`, `0.000` `MODEL`).
- **Session 2 (`arena/a6416f7b`):** Added `tools/run_concentration.py`, `tools/pins.py`, and fixed row/column transpose in `src/gems91/gates.py` (IR-91-06).

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
| `tools/` | `run_concentration.py` (builder), `pins.py`, `raster_io.py`, `stor.py`, `make_fixture.py` |
| `tests/` | 53 tests (metric algebra, gates, ledger invariants, builder, preflight) |

## Run it

```bash
pip install -r requirements.txt
python scripts/verify_parent_r0.py     # fetch pinned parent, verify sha256
python scripts/preflight.py            # BUILD ALLOWED / BUILD BLOCKED
python -m pytest                       # 53 tests, no competition data needed
python -m tools.pins --axis CONCENTRATION   # what an axis still needs, by pinned id
```

### Session 3 delta (`arena/5563ddf8`, same date)

Main had moved twice while this session ran, so this branch was **rebased onto** the merged
work rather than replacing it: the `src/gems91` package, `tools/`, `Makefile`, fixtures and
all 20 imported ledger rows are kept intact.

- **The blocking problem was solved, not worked around.** R0, `sample_submission.tif` and the
  labels raster were recovered from public mirrors and verified against hashes this repo
  already carried. No rebuild from a recipe, no approximation.
- **Parent forensics.** Differencing R0 against solo-d28 proves the lineage's PRUNE is
  delete-only (0 dots in R0 that are not in solo-d28; 2,545 removed at ≤2 px, none added).
- **Three buildable variants**, using `scripts/dti.py` + `scripts/axes.py` + `scripts/build.py`.
- **Two gate implementations now agree** on all three files. Fixing `sha_unseen` to ignore
  BUILT rows (IR-91-12) is what let them certify; before that the gate was unsatisfiable in
  the order the brief prescribes.
- **A real disagreement is recorded, not hidden:** my algebra predicts removal gains, the
  imported `p4px` row predicts −0.009. IR-91-13.
- **Honest about power:** the brief's evidence bar is ±0.01 and only `le15` has a plausible
  path past it. Doses 1 and 2 are refinements.
