# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2`, `37,654` unit-mass dots (`RECEIPT`) on the pinned `3730×3292` `EPSG:32611` (`100 m`, `float32`, footprint `5,167,373` px, `0` dots on catalogue, min `2.236 px`) grid. Both pinned TIFFs rebuild byte for byte from either ancestor (`baeae321…c77dd`, `355,443` B; `c55bafc4…6fa9`, `219,065` B; dot digest `905cee9d…`). R0's `0.2778` / `0.3698` remains an unreceipted **CLAIM**.
- **Inputs (`15/15` pinned + `catalogue_px.tif` = `16/16` hash-verified `RECEIPT`):** `scripts/restore_data.py` now restores `training_features` (`gems-geodawn-numerical-features.tif`, `418,912,844` B, sha256 `4371c82e…3bc5` `RECEIPT`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)) from 5 pinned git blobs (`IR-91-25`) and unblocks **all 6 axes** (`MASS`, `CONCENTRATION`, `SNAP`, `PRUNE`, `RELIEF`, `TRACKB`; `scripts/preflight.py` → `BUILD ALLOWED`).
- **Ledger (`44` `BUILT` rows, `0` `SUBMITTED`, `0` live `RECEIPT`s):** `|Δ| < 0.01` = no evidence. **TOP_PUBLIC:** `____` (human must fill, with date). **Slots left this week:** `__ / 3` (`5.86` rolling weeks to unconfirmed `2026-12-03` deadline).
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

### Session `arena/9cc58e7e` delta — RELIEF, and a cross-check over the whole board

Merged on top of the four sessions above, and it adds three things rather than re-cutting theirs.

- **The RELIEF triplet** (the one axis with zero ledger rows before this session):
  `r2m15` range-front → piedmont **+0.0070**, `m2r15` the exact sign flip **−0.0070**, `null15`
  tercile-neutral relocation **0.0000** — all 5,648 dots moved (15.00 %), count fixed 37,654,
  every new dot >3 px from the catalogue, every recipient off the lineage's own detector support.
  Cards in `docs/MECHANISM_CARDS.md`; numbers in `evidence/relief_axis_20261023.json`.
  **Not a slot candidate:** ±0.007 alone is below the 0.01 bar and the arm is only interpretable
  as a pair, i.e. two slots for one bit.
- **R0 is spacing-saturated on its own support (IR-91-26).** At the parent's own spacing floor
  (d_nn ≥ 2.8 px, measured minimum 2√2) only **90** support cells in the entire footprint are legal
  recipients, against 4,136,025 legal cells off support. Any long-range move of mass must leave
  support — which is why the RELIEF arms are off-support *by design*, in every arm.
- **A cross-check that reorganises the slot order (IR-91-25, IR-91-30).** Scored against the only
  truth reachable here (the 60,988-cell catalogue), with the metric split into credit `T` and
  unmatched mass (`scripts/crosscheck_predictions.py`, `evidence/predictions_crosscheck_20261023.json`):

  | file | `dti_proxy` | Δ vs R0 |
  |---|---:|---:|
  | R0 | 0.006778 | — |
  | `SPACINGspread40` | 0.007861 | **+0.00108** (the only positive arm) |
  | `CONCENTRATIONgdr25rm10` / `gdr25m10` / `gdr10m10` | 0.005937 / 0.005932 / 0.005931 | −0.00084 (the three agree to 6·10⁻⁶) |
  | `RELIEFr2m15` > `null15` > `m2r15` | 0.005888 / 0.005744 / 0.005823 | −0.00089 / −0.00103 / −0.00096 |
  | `PRUNEp2.5pxh19cover` | 0.001242 | −0.00554 |
  | every delete-only PRUNE dose | **0.000000** | **−0.00678** |

  **All of R0's measurable credit comes from 1,611 dots inside 3 px of a mapped trace.** Every
  delete-only dose deletes that band, so the six rungs are one experiment, not a dose-response:
  one receipt on the top rung answers the family. Break-even for deleting a dot is **0.044**
  credit; those 1,611 dots measure **0.237**, five times the bar — so the ladder is a bet that the
  organisers' *unmapped* faults lie nowhere near the parent's dots, which no local instrument can
  test. Where two candidates are within 0.002 MODEL of each other, prefer the one this instrument
  does not penalise: `SPACINGspread40` is the only such file.
- **The 0.2778 CLAIM is 41× the visible measurement (IR-91-30).** `|G|` sits in the denominator, so
  a larger truth set makes the gap wider, not narrower; the ranked explanations and the one-line
  thing that would settle it are in that item. It changes no ranking — every prediction in the
  ledger is a difference from R0 — but no absolute number here is a score.

### Cross-check over the whole board (`arena/9cc58e7e`, `IR-91-30`)

`scripts/crosscheck_predictions.py` scores every shipped primary against the only truth reachable
here — the `60,988`-cell catalogue — splitting the metric into credit `T` and unmatched mass
(`evidence/predictions_crosscheck_20261023.json`). `PROXY`, report-only, never a gate.

| file | `dti_proxy` | Δ vs R0 |
|---|---:|---:|
| R0 | 0.006778 | — |
| `SPACINGspread40` | 0.007861 | **+0.00108** (the only positive arm) |
| `CONCENTRATION` trio | 0.005931–0.005937 | −0.00084 (they agree to 6·10⁻⁶) |
| `RELIEF` trio | 0.006778 | 0.00000 (moves stay inside the collar) |
| `MASScons3add` / `cons2drop` | — | −0.00009 / −0.00163 |
| `PRUNEp2.5pxh19cover` | 0.001242 | −0.00554 |
| every delete-only `PRUNE` rung | 0.000000 | **−0.00678** |

**All of R0's measurable credit comes from `1,611` dots inside `3 px` of a mapped trace**; the
other `36,043` score exactly zero against mapped faults. Every delete-only rung removes that band,
so the six rungs are *one experiment, not a dose-response*: one receipt on the top rung answers
the family. Break-even is `0.044` credit per deleted dot; those `1,611` dots measure `0.237`, five
times the bar — the ladder is a bet that the organisers' *unmapped* faults lie nowhere near the
parent's dots, which no local instrument can test (`IR-91-30`). Where two candidates sit within
`0.002` `MODEL` of each other, prefer the one this instrument does not penalise:
`SPACINGspread40` is the only such file.

Two further items from the same session: R0 is **spacing-saturated on its own support** — at the
parent's own `d_nn ≥ 2.8 px` floor only **90** support cells in the whole footprint are legal
recipients against `4,136,025` off support (`IR-91-28`) — and R0's `0.2778` `CLAIM` sits **41×**
above what the visible truth supports, for a reason that no ranking depends on (`IR-91-31`).
