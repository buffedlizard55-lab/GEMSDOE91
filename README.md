# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2`, `37,654` unit-mass dots (`RECEIPT`) on the pinned `3730×3292` `EPSG:32611` (`100 m`, `float32`, footprint `5,167,373` px, `0` dots on catalogue, min `2.236 px`) grid. Both pinned TIFFs rebuild byte for byte from either ancestor (`baeae321…c77dd`, `355,443` B; `c55bafc4…6fa9`, `219,065` B; dot digest `905cee9d…`). R0's `0.2778` / `0.3698` remains an unreceipted **CLAIM**.
- **Inputs (`15/15` pinned + `catalogue_px.tif` = `16/16` hash-verified `RECEIPT`):** `scripts/restore_data.py` now restores `training_features` (`gems-geodawn-numerical-features.tif`, `418,912,844` B, sha256 `4371c82e…3bc5` `RECEIPT`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)) from 5 pinned git blobs (`IR-91-25`) and unblocks **all 6 axes** (`MASS`, `CONCENTRATION`, `SNAP`, `PRUNE`, `RELIEF`, `TRACKB`; `scripts/preflight.py` → `BUILD ALLOWED`).
- **Ledger (`44` `BUILT` rows, `0` `SUBMITTED`, `0` live `RECEIPT`s):** `|Δ| < 0.01` = no evidence. **TOP_PUBLIC:** `____` (human must fill, with date). **Slots left this week:** `__ / 3` (`5.86` rolling weeks to unconfirmed `2026-12-03` deadline).
- **Session 6 (`arena/0ed37053-gemsdoe91`) — `TRACKB` built (Phase 2 only, IR-91-28):** 2,214 strike-consistent traces >=1 km (12,989 support dots) chained from R0 dots ranked by label-blind `S_struct`; three count-fixed arms relocate 10.0%/20.0%/10.0% of lowest-ranked off-trace dots onto traces (`t1k10` `8343ab38` **+0.004** MODEL, `t1k20` `ab72339b` **+0.005**, `t2k10` `6d16fd7a` **+0.002**), each with a per-trace evidence-paragraph GeoJSON. Not in the weekly slot queue unless the human decides.
- **Session 5 (`arena/42de3fed-gemsdoe91`) — `RELIEF` axis built and certified (`IR-91-26`, `IR-91-27`):** Relocates `4,518` dots (`12.00%` moved; `9,036` pixel symmetric diff = `24.00%` `RECEIPT`) at fixed count (`37,654` `RECEIPT`) and zero catalogue-collar drift (`2,171 → 2,171` `RECEIPT`) across equal-area relief terciles `0.90·pct(det_elev) + 0.10·pct(det_elev_slope)` (single-band leakage canary max AUC `0.5793` `PROXY` `≪ 0.90`):

  | id | value | dots (`RECEIPT`) | T1 / T2 / T3 share (`RECEIPT`) | 4-fold `PROXY` Δ ([GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)) | SGMC `PROXY` Δ ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) | predicted (`MODEL`) |
  |---|---|---:|---|---|---|---|
  | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c` | `r2p12` (`range->pied`) | 37,654 | 17.7 / 56.3 / 26.0% | −0.0017 | −0.0049 | **+0.006** `[−0.006, +0.018]` |
  | `h33-h33-2-b2-RELIEFr2b12-20261023-27443c30` | `r2b12` (`range->basin`) | 37,654 | 29.7 / 44.3 / 26.0% | −0.0032 | −0.0091 | **+0.003** `[−0.010, +0.016]` |
  | `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5` | `b2r12` (`basin->range`) | 37,654 | 5.7 / 44.3 / 50.0% | −0.0113 | **+0.0050** | **+0.005** `[−0.010, +0.020]` |

- **Merged fleet summary across sessions (`SLOT_PLAN.md`):**
  - **CONCENTRATION** (PR #13, GDR thermal prior): `gdr25rm10` (`c19adb01`, `+0.0123` `MODEL`), `gdr25m10` (`+0.0114`), `gdr10m10` (`+0.0113`).
  - **PRUNE** (PRs #4/#9/#10): delete-only `le3..le15` (`+0.002..+0.010` `MODEL`, `le10` `04002dae` `+0.008`) + fixed-count `p2.5`/`p2.9`/`p4.5px-h19cover`.
  - **MASS** (PR #14, lineage support): `cons1drop` (`−0.000` `MODEL`), `cons2drop` (`−0.015`), `cons3add` (`2803126d`, `+0.009`).
  - **SPACING** (PR #3, radius-2 ring): `spread40` (`6d389309`, `+0.0042` `MODEL`), `clump40` (`−0.0023`), `jitter40` (`0.000`).
- **Next 3 scored slots (`SLOT_PLAN.md`):** (1) `CONCENTRATIONgdr25rm10` (`c19adb01`, or R0 anchor if unreceipted) → (2) `PRUNE-le10-norefill` (`04002dae`) → (3) `RELIEFr2p12` (`6ff08e5c`, or `MASScons3add` `2803126d`).

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
