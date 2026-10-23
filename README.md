# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2` (`h33-h33-2-b2-20261004-e5eb6e7e`) — **reproduced this
  session from BOTH pinned ancestors**, `d2.8` and `solo-d2.8`, each minus every dot within
  2.0 px of the catalogue → 37,654 dots, digest `905cee9d…`, 0 differing cells.
  Twins: `baeae321…c77dd` (NaN) and `c55bafc4…a6fa9` (zeros). 0 dots on the catalogue,
  min distance **2.236 px**, 2,171 dots at ≤ 3 px.
- **Inputs:** 15 of 16 pinned entries verified here (`scripts/restore_data.py`); only
  `training_features.tif` (419 MB) has no mirror. SGMC control, lidar scarp, radon,
  wellsprings and GDR are all present and hash-checked.
- **Best receipt:** **none.** 35 ledger rows, **0 receipts**. `0.2778` is a **CLAIM**.
- **TOP_PUBLIC:** **____ (human must fill from the leaderboard, with date).**
- **Slots left this week:** **__ / __ (human must fill).**
- **AXIS this session: MASS** (chosen, not assigned — the one axis `ledger/README.md`
  documents as still open). Built with the parent's own **generation field** as the
  ranking (`anc_h19_5`, gaussian σ = 1 px), because `training_features` is absent (IR-91-16).
- **Variants built: 3, all CERTIFIED** (`scripts/validate_release.py`) and 14/14 in
  `gems91.release_gates`. All three carry the *same* brief-4.4 collar normalisation
  (2,171 dots at ≤ 3 px deleted identically), so they differ only on MASS (IR-91-03).

  | id (suffix) | change vs R0 | dots | predicted (MODEL) |
  |---|---|---:|---|
  | `MASSsup10minus-…-7e7084af` | −3,765 by field rank + collar | 31,854 | **−0.018** [−0.039, +0.007] |
  | `MASSsup24minus-…-e086e259` | −9,164 by field rank + collar (dose-matched to PRUNE le8) | 26,672 | **−0.034** [−0.071, +0.009] |
  | `MASSsup10plus-…-e23e5141` | +3,540 highest-rank cells, ≥ 3 px collar | 39,023 | **−0.002** [−0.007, +0.003] |

- **The session's real output is an instrument, not a file.** The independent SGMC fault
  map, *restricted to cells > 3 px from the catalogue*, reproduces the sign of the
  parent's own winning steps; the raw version reverses it. On that instrument every
  mass-removal edit outside the collar is a **loss**, because a deleted dot carries
  0.14–0.19 credit against 0.056 break-even. That re-orders the slot plan: the pending
  PRUNE `le8`/`le15` rungs are predicted −0.038 / −0.068. See `SLOT_PLAN.md`.
- **Next 3 slots:** (1) **R0 itself, for a receipt** — nothing in five ledgers is anchored
  to a real number; (2) `MASSsup10plus` (the only unsettled sign); (3) the pure collar
  delete.

### Session 5 delta (`arena/7dffc20d`, MASS)

Built `scripts/build_mass.py` (one ranking, one code path, 3 arms), `evidence/mass_axis_20261023.json`,
three mechanism cards, and the SGMC instrument calibration. Six draft MASS rows in the ledger are
`SUPERSEDED-DRAFT` (two withdrawn draft generations, both before any receipt); the three `BUILT`
rows above are the only slot candidates. Session 3's SPACING files were **rebuilt here byte for
byte** (`6d389309`, `536d32ad`, `39bb7288`) as a reproducibility check.

### Session 3 delta (`arena/a5e7bf22`, SPACING)

Session 3 restored the same mirrors independently (so IR-91-09 is confirmed twice), proved
the parent's **dot set** from two ancestors, and built the one axis nobody had built.

- **Axis: SPACING** — zero prior `axis=SPACING` rows in five fleet ledgers (132+129+22+20+5
  rows). Three arms, matched on everything but the treatment: the same 40 % of dots (densest
  1 km blocks), the same displacement budget (radius-2 ring, 2.0–2.236 px), the same
  constraints. Only *which* ring cell is chosen differs, ranked by a Gaussian-smoothed
  dot-density potential (σ = 2 px).

  | id | relocated | density at target | predicted (MODEL) |
  |---|---:|---|---|
  | `…-SPACINGspread40-20261023-6d389309` | 15,056 (39.99 %) | 0.066 → **0.035** | **+0.0042** [−0.004, +0.012] |
  | `…-SPACINGclump40-20261023-536d32ad` | 14,973 (39.76 %) | 0.066 → 0.058 | **−0.0023** [−0.010, +0.006] |
  | `…-SPACINGjitter40-20261023-39bb7288` | 15,038 (39.94 %) | 0.066 → 0.047 | **0.000** (null) [−0.008, +0.008] |

- **The bound is the finding.** Under a uniform truth prior the edit moves expected kernel
  credit by −0.17 % (spread) to −2.4 % (clump), capping the plausible live effect near
  **0.003**. The axis cannot produce a ≥0.01 win; one slot buys a *decision* (is arrangement
  a lever at all?), not a score.
- **Parent dot set reproduced exactly** from two independent pinned ancestors — `d2.8`
  (44,090 dots) and `solo-d2.8` (40,199), each minus every dot within 2.0 px of the catalogue
  → 37,654, **0 differing cells**, digest `905cee9d…`, which matches the digest GEMSDOE86
  recorded independently. The parent's *bytes* are still not re-encodable here (IR-91-16).
- **No raster is committed.** Session 3's files are rebuilt on demand and pinned by
  `releases/MANIFEST.json`; CI rebuilds them in a clean container and asserts the hashes
  byte for byte.
- **Session-3 slot ordering.** PRUNE first (the ladder above has the only *measured* live
  dose-response behind it, and `le15` carries the largest predicted gain on the board at
  +0.010), then `SPACINGspread40` (retires geometry if flat), then RELIEF or a CONC re-cut.

### Session 2 delta (`arena/a6416f7b`, same date)

Built on top of the above, after finding that main had moved: **0 variants built**, for the
same reason as session 1 (no competition rasters locally). What is new:

- `tools/run_concentration.py` — the repository's first *builder*: count-preserving,
  collar-safe, CV-reporting, refuses any input that is not pinned. It requires an
  **external** prior and refuses one derived from the parent's own dots, because the three
  imported CONCENTRATION rows ranked blocks by *parent dot density* (IR-91-07) — those test
  clustering, not prior transfer.
- `tools/pins.py` — maps each axis to the manifest ids it needs and verifies bytes.
- `tools/make_fixture.py` + `tests/test_concentration.py` — a synthetic fixture and an
  end-to-end build -> certify proof, the first time the gates have run on a real raster.
- **Fixed a live bug in `src/gems91/gates.py`**: `min_distance_to_mask` transposed rows and
  columns (IR-91-06). On the real 3730x3292 grid this raised IndexError or returned the
  distance at the mirrored cell, so every collar count in the lineage audit is suspect.

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
