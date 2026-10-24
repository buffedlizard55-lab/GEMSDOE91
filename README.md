# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2`, `37,654` unit-mass dots (`RECEIPT`) on the pinned `3730×3292` `EPSG:32611` (`100 m`, `float32`, footprint `5,167,373` px, `0` dots on catalogue, min `2.236 px`) grid. Both pinned TIFFs rebuild byte for byte from either ancestor (`baeae321…c77dd`, `355,443` B; `c55bafc4…6fa9`, `219,065` B; dot digest `905cee9d…`). R0's `0.2778` / `0.3698` remains an unreceipted **CLAIM**.
- **Inputs (`15/15` pinned + `catalogue_px.tif` = `16/16` hash-verified `RECEIPT`):** `scripts/restore_data.py` now restores `training_features` (`gems-geodawn-numerical-features.tif`, `418,912,844` B, sha256 `4371c82e…3bc5` `RECEIPT`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)) from 5 pinned git blobs (`IR-91-25`) and unblocks **all 6 axes** (`MASS`, `CONCENTRATION`, `SNAP`, `PRUNE`, `RELIEF`, `TRACKB`; `scripts/preflight.py` → `BUILD ALLOWED`).
- **Ledger (`47` `BUILT` rows, `0` `SUBMITTED`, `0` live `RECEIPT`s):** `|Δ| < 0.01` = no evidence. **TOP_PUBLIC:** `____` (human must fill, with date). **Slots left this week:** `__ / 3` (`5.86` rolling weeks to unconfirmed `2026-12-03` deadline).
- **Session 5 (`arena/42de3fed-gemsdoe91`) — `RELIEF` axis built and certified (`IR-91-26`, `IR-91-27`):** Relocates `4,518` dots (`12.00%` moved; `9,036` pixel symmetric diff = `24.00%` `RECEIPT`) at fixed count (`37,654` `RECEIPT`) and zero catalogue-collar drift (`2,171 → 2,171` `RECEIPT`) across equal-area relief terciles `0.90·pct(det_elev) + 0.10·pct(det_elev_slope)` (single-band leakage canary max AUC `0.5793` `PROXY` `≪ 0.90`):

  | id | value | dots (`RECEIPT`) | T1 / T2 / T3 share (`RECEIPT`) | 4-fold `PROXY` Δ ([GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)) | SGMC `PROXY` Δ ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) | predicted (`MODEL`) |
  |---|---|---:|---|---|---|---|
  | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c` | `r2p12` (`range->pied`) | 37,654 | 17.7 / 56.3 / 26.0% | −0.0017 | −0.0049 | **+0.006** `[−0.006, +0.018]` |
  | `h33-h33-2-b2-RELIEFr2b12-20261023-27443c30` | `r2b12` (`range->basin`) | 37,654 | 29.7 / 44.3 / 26.0% | −0.0032 | −0.0091 | **+0.003** `[−0.010, +0.016]` |
  | `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5` | `b2r12` (`basin->range`) | 37,654 | 5.7 / 44.3 / 50.0% | −0.0113 | **+0.0050** | **+0.005** `[−0.010, +0.020]` |

- **Session 6 (`arena/9b8f7d01-gemsdoe91`) — `SNAP` axis built and certified (IR-91-28..30):** first `SNAP` build in the repo. One shared driver (bands 3 `tmi_hg` + 18 `iso_grav_anom_hg`, 600 m high-pass, 1.5 px smoothing), radius 2 px, targets `> 3 px` from the catalogue, R0's `2,171` inherited collar dots quarantined in place (`collar 2,171 -> 2,171` `RECEIPT`), count fixed `37,654` `RECEIPT`, 16/16 `release_gates` + 14/14 `validate_raster` PASS on both encodings:

  | id | rule | dots moved | mean disp. | `MODEL` predicted | SGMC `PROXY` ΔDTI |
  |---|---|---:|---:|---|---:|
  | `h33-h33-2-b2-SNAPs2c-20261023-86b27de1` | 3×3 crest only | 2,047 (5.44 %) | 0.080 px | **+0.000** `[−0.006, +0.006]` | +0.00008 |
  | `h33-h33-2-b2-SNAPs2q75-20261023-8aa75390` | window max, gain ≥ p75 | 4,495 (11.94 %) | 0.237 px | **−0.004** `[−0.012, +0.005]` | −0.00234 |
  | `h33-h33-2-b2-SNAPs2f-20261023-c2391234` | window max, no threshold | 35,174 (93.41 %) | 1.733 px | **−0.014** `[−0.028, +0.004]` | −0.00926 |

  The catalogue PROXY is identically unchanged (`0.006186`, 5 draws, ~12,200 withheld positives, 95 % CI `[0.005958, 0.006413]`) **by construction** — targets are floored at 3 px and the only dots inside 3 px are quarantined, so SNAP cannot touch known-fault credit (IR-91-28). On the independent off-catalogue SGMC map ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) the sign is negative and grows with dose; SNAP is therefore **not** a top-3 slot candidate.

- **Merged fleet summary across sessions (`SLOT_PLAN.md`):**
  - **CONCENTRATION** (PR #13, GDR thermal prior): `gdr25rm10` (`c19adb01`, `+0.0123` `MODEL`), `gdr25m10` (`+0.0114`), `gdr10m10` (`+0.0113`).
  - **PRUNE** (PRs #4/#9/#10): delete-only `le3..le15` (`+0.002..+0.010` `MODEL`, `le10` `04002dae` `+0.008`) + fixed-count `p2.5`/`p2.9`/`p4.5px-h19cover`.
  - **MASS** (PR #14, lineage support): `cons1drop` (`−0.000` `MODEL`), `cons2drop` (`−0.015`), `cons3add` (`2803126d`, `+0.009`).
  - **SPACING** (PR #3, radius-2 ring): `spread40` (`6d389309`, `+0.0042` `MODEL`), `clump40` (`−0.0023`), `jitter40` (`0.000`).
- **Session 6b (`arena/f8d67617-gemsdoe91`) — `SNAP` on the *vertical*-gradient bands, same conclusion from a different field:** PR #18 snapped to a high-passed **horizontal**-gradient composite (`tmi_hg` + `iso_grav_anom_hg`); this session ran the same axis on `0.50·pct(|Band9 tmi_vg|) + 0.50·pct(|Band11 iso_grav_anom_vg|)`, which no SNAP row had ever used, as a **radius** dose ladder (1/2/3 px, Euclidean) rather than a quantile ladder. Count `37,654`, collar `2,171 → 2,171` (R0's inherited 2–3 px dots frozen), min nearest-neighbour `2.000 px` enforced, `0` catalogue mass, both gate suites PASS on all six files:

  | id (`releases/`) | r | moved `RECEIPT` | mean disp `RECEIPT` | driver pct `PROXY` | SGMC Δ `PROXY` | frozen pred. `MODEL` |
  |---|---:|---|---:|---|---:|---|
  | `h33-h33-2-b2-SNAPvg1px-20261023-97606a78` | 1 px | 33,807 (89.78%) | 0.898 px | 0.536→0.588 | −0.0033 | +0.002 |
  | `h33-h33-2-b2-SNAPvg2px-20261023-353a9dda` | 2 px | 34,285 (91.05%) | 1.554 px | 0.536→0.614 | −0.0058 | +0.003 |
  | `h33-h33-2-b2-SNAPvg3px-20261023-435435a3` | 3 px | 34,635 (91.98%) | 2.298 px | 0.536→0.637 | −0.0098 | +0.004 |
  | *null (r=2, **random** legal target; no raster, no ledger row, no slot)* | 2 px | 32,157 (85.40%) | 1.228 px | 0.536→0.536 | −0.0013 | — |

  The control that PR #18's design could not run: the same-size **random** shuffle costs only `−0.0013` on SGMC, so the VG treatment loses **2.5–7.4× more** fault proximity than a coin flip, monotonically with dose, even as its own driver objective rises monotonically. Post-hoc expectation is **negative** (only the sign is robust; 1:1 transfer of the control Δ gives −0.003…−0.010, relative transfer ~3× that). **Two independent SNAP sessions, two different fields, both negative ⇒ the family is closed**, not the driver. IR-91-31; 14 new tests (`tests/test_snap_vg.py`; the suite is now `181` tests).

- **Next 3 scored slots (`SLOT_PLAN.md`):** (1) `CONCENTRATIONgdr25rm10` (`c19adb01`, or R0 anchor if unreceipted) → (2) `PRUNE-le10-norefill` (`04002dae`) → (3) `RELIEFr2p12` (`6ff08e5c`, or `MASScons3add` `2803126d`). **`SNAP` does not enter the top 3**; `SNAPs2c` (`86b27de1`, predicted `+0.000`) is a reserve axis-retirement test only.

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
| `tests/` | 181 tests (metric algebra, gates, ledger invariants, builders, SNAP invariants, preflight) |

## Run it

```bash
pip install -r requirements.txt
python scripts/verify_parent_r0.py     # fetch pinned parent, verify sha256
python scripts/preflight.py            # BUILD ALLOWED / BUILD BLOCKED
python -m pytest                       # 181 tests, no competition data needed
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
