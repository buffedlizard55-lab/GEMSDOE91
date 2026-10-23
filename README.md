# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2` — `h33-h33-2-b2-20261004-e5eb6e7e`.
  `baeae321…c77dd` (NaN) and `c55bafc4…a6fa9` (zeros), 37,654 unit-mass dots,
  EPSG:32611, 3730×3292, 100 m, float32, footprint 5,167,373 px, **0 dots on the
  catalogue**, min 2.236 px from it. Rebuilt this session from **two** pinned ancestors
  (dot-set digest `905cee9d…`, 0 differing cells); its *bytes* are still not re-encodable
  here (IR-91-16).
- **Inputs: 15 of 15 pinned entries present and hash-verified — including the 419 MB
  feature stack**, which was reassembled this session from five hash-pinned parts and
  matches its pin `4371c82e…` byte for byte (IR-91-17). Every axis reads **READY**:
  PRUNE, MASS, SNAP, CONCENTRATION, RELIEF, TRACKB.
- **Best receipt:** **none.** 29 ledger rows, 0 receipts. `0.2778` for R0 is a **CLAIM**.
- **TOP_PUBLIC:** **____ (human must fill from the leaderboard, with date).**
- **Slots left this week:** **__ / __ (human must fill).**
- **AXIS for this session: RELIEF** — chosen, not assigned. It was the only axis with **zero
  ledger rows** (PRUNE 7, SNAP 9, CONCENTRATION 4, MASS 3, SPACING 3), and it is the axis the
  brief names as the last untested one.
- **Variants built this session: 3, all gate-clean** (14/14 `validate_raster`, `PASS` in
  `validate_release`, count fixed, ≥3 px collar on every new dot, canary 0.424 ≪ 0.90).

  | id | value | moved | tercile fraction (basin/pied/range) | predicted (MODEL) |
  |---|---|---|---|---|
  | `…-RELIEFr2m15-…-2c3839c9` | range→piedmont | 5,648 (15.00 %) | .204/.418/.377 → .204/**.568**/.227 | **+0.0070** [−0.003, +0.017] |
  | `…-RELIEFm2r15-…-3c3e832d` | piedmont→range (sign flip) | 5,648 (15.00 %) | → .204/**.268**/**.527** | **−0.0070** [−0.017, +0.003] |
  | `…-RELIEFnull15-…-6c057de2` | relocation null | 5,648 (15.00 %) | → .205/.417/.378 (unchanged) | **0.0000** [−0.010, +0.010] |

- **Next 3 slots (see `SLOT_PLAN.md`):** not RELIEF. Slot 1 = `PRUNEle15norefill`
  (rebuilds byte-identically here, predicted +0.010 — the largest on the board); slots 2–3 are
  conditional on that receipt.

### Session 5 delta (`arena/9cc58e7e`, RELIEF) — what is actually new

1. **The blocking input was recovered, not worked around.** `training_features.tif` is
   stored, split into five ≤94 MB parts, in four public sibling repos; the parts' sha256 and
   the whole-file sha256 were known. All five verified, concatenated, and the result matches
   the pin exactly. `scripts/restore_data.py` now does this itself.
2. **R0 is spacing-saturated on its own detector support.** With the parent's own spacing
   floor (d_nn ≥ 2.8 px, measured: minimum = 2√2 = 2.828, 11,415 dots at exactly that
   distance) only **90** support cells in the entire footprint are legal recipients — against
   4,136,025 legal cells off support. Any long-range move of mass must therefore leave the
   detector's support. This is the single most decision-relevant measurement of the session
   (IR-91-18) and it constrains every future MASS/CONCENTRATION/RELIEF design.
3. **The brief's own RELIEF direction is a near-no-op on R0.** Basin→range-front moves mass
   between terciles whose mapped-fault densities are 1.077 % and 1.027 % (≈ −5 % credit per
   moved dot), and the audit's alternative relief definition leaves only 191 dots in the
   lowest tercile. It is not built; its prediction is computed and filed (IR-91-19).
4. **What was built instead** is the informative contrast: range-front ↔ piedmont, plus a
   tercile-neutral relocation null. Mapped faults are densest in the **middle** relief tercile
   under *both* candidate relief definitions (1.436 % det_elev, 1.534 % det_elev_slope), and
   R0's dot/catalogue ratio rises monotonically with elevation (0.415 / 0.636 / 0.803).
5. **The honest bound:** the arms move 15 % of the mass off support, so the like-for-like
   number is `r2m15 − null15`, not `r2m15` alone. Predictions are ≈ ±0.007, i.e. **below the
   brief's 0.01 evidence bar**. RELIEF cannot win a slot on expected score; it is built so the
   question is answered with one receipt pair if a slot ever becomes free.

### Earlier sessions, condensed

- **Session 4 (`arena/…`, PRUNE):** delete-only dose ladder `le3`/`le8`/`le15`
  (5.77 % / 24.34 % / 41.60 % removed). All three rebuild **byte-identically** to their ledger
  hashes (`make releases`) and all pass the gates twice over. `le15` carries the largest
  predicted gain on the board (+0.010) and is the recommended slot 1.
- **Session 3 (`arena/a5e7bf22`, SPACING):** three matched ±2 px re-spacing arms
  (spread/clump/jitter, 40 % moved), proof of the parent dot set from two ancestors, and the
  finding that the axis' ceiling is ~0.003.
- **Sessions 1–2:** ledger import (20 rows), the 15-entry manifest, the metric re-derivation,
  the gate library, and the first count-preserving builder.
- **Lanes that lost:** one-physical-signal fields (radon, Euler, tensor, strain) scored
  0.00–0.19; nothing in GEMSDOE76–81 beat R0 (best 0.2343).

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
