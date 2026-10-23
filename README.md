# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** R0 = `h33-h33-2-b2` (`h33-h33-2-b2-20261004-e5eb6e7e`), NaN `baeae321…c77dd`,
  zeros `c55bafc4…a6fa9`. 37,654 unit-mass dots, EPSG:32611, 3730×3292, 100 m, float32,
  footprint 5,167,373 px, **zero catalogue dots**, minimum catalogue distance 2.236 px. The dot
  set reproduces exactly from both pinned ancestors (44,090 → 37,654 and 40,199 → 37,654,
  0 differing cells, digest `905cee9d…`); its *bytes* are not re-encodable here (IR-91-16), so
  every artifact carries a sha256 **and** a dot-set digest.
- **Best receipt: none.** 38 ledger rows, **0 SUBMITTED, 0 receipts**. `0.2778` for R0 is a
  **CLAIM** — and IR-91-22 measures it 41× above what the only visible truth supports.
- **Inputs: 15/15 pinned entries present and hash-verified**, including the 419 MB feature stack,
  which was reassembled this session from five hash-pinned parts and matches its pin `4371c82e…`
  byte for byte (IR-91-17b). Every axis reads **READY**; only MASS remains unbuildable, for a
  documented reason, not for lack of data (IR-91-23).
- **Shipped and reproducible: 18 release pairs / 36 files**, all in `releases/MANIFEST.json` with
  `axis` and `n_dots`, all rebuilt and hash-checked by `make releases`
  (`manifest: 36 files, 0 problem(s)`): CONCENTRATION ×3, PRUNE delete-only ×6, PRUNE refill-held
  ×3, SPACING ×3, RELIEF ×3.
- **Cross-check (new, and it reorganises the plan).** Scored against the only truth visible here,
  R0 gets `dti_proxy` **0.006778**, and **100 % of its measurable credit comes from 1,611 dots
  inside 3 px of a mapped trace**; every delete-only PRUNE dose deletes that band and computes to
  `T = 0`. `SPACINGspread40` is the only shipped arm that *raises* measurable credit (+0.0011).
  The three CONCENTRATION arms agree to 6·10⁻⁶ and sit ~−0.0008, the RELIEF arms reproduce their
  predicted order (IR-91-21). Break-even for deleting a dot is 0.044 credit; the collar dots
  measure 0.237 — so the ladder is one bet on unmapped-fault geometry, not a dose-response.
- **TOP_PUBLIC:** **____ (human must fill from the leaderboard, with date).**
- **Slots left this week:** **__ / __ (human must fill).** Deadline 2026-12-03, unconfirmed.
- **Next 3 slots (merged plan, `SLOT_PLAN.md`):** 1) `CONCENTRATIONgdr25rm10-…-c19adb01`
  (**+0.0123**, the only prior independent of both the catalogue and the lineage mask),
  2) `PRUNEle15-norefill-…-1ca1ff6f` (+0.010, answers the whole delete-only family in one slot),
  3) conditional on their signs — `gdr25m10` / `le10` / `SPACINGspread40`, per the fork table.
  Do not spend slots on `gdr10m10`, `le4`, `le5`, `le8` or the RELIEF arms.

  | id | value | moved | tercile fraction (basin/pied/range) | predicted (MODEL) |
  |---|---|---|---|---|
  | `…-RELIEFr2m15-…-2c3839c9` | range→piedmont | 5,648 (15.00 %) | .204/.418/.377 → .204/**.568**/.227 | **+0.0070** [−0.003, +0.017] |
  | `…-RELIEFm2r15-…-3c3e832d` | piedmont→range (sign flip) | 5,648 (15.00 %) | → .204/**.268**/**.527** | **−0.0070** [−0.017, +0.003] |
  | `…-RELIEFnull15-…-6c057de2` | relocation null | 5,648 (15.00 %) | → .205/.417/.378 (unchanged) | **0.0000** [−0.010, +0.010] |

- **Cross-check (new, and it reorganises the plan):** scored against the only truth visible here,
  R0 gets `dti_proxy` 0.006778 and **100 % of its measurable credit comes from 1,611 dots inside
  3 px of a mapped trace**; every PRUNE dose deletes that band, so all six compute to `T = 0`.
  `SPACINGspread40` is the only shipped arm that *raises* measurable credit (+16 %). The PRUNE
  ladder is therefore one conditional claim about unmapped faults, not a dose-response
  (IR-91-21), and 0.2778 sits 41× above what this instrument supports (IR-91-22).
- **Next 3 slots (see `SLOT_PLAN.md`):** slot 1 = **`PRUNEle15norefill`** (the only file whose
  MODEL range crosses +0.01), slot 2 = **`SPACINGspread40`** (the only credit-adding arm), slot 3 =
  conditional on slot 1's sign. RELIEF waits; `le3`/`le4`/`le5`/`le8` wait behind them.

### Parallel session merged (`arena/f40e8bcd`, PRUNE ladder extension)

A second session landed while this one ran and is merged here, not replaced: three further
delete-only doses — `PRUNE-le4` (33,829 dots, 10.16 %), `PRUNE-le5` (32,017, 14.97 %) and
`PRUNE-le10` (26,294, 30.17 %) — plus `scripts/build_prune_ladder.py`, its own evidence file and
CI wiring. All six delete-only doses now rebuild byte-identically under one command. The two
sessions disagreed only about which dose goes first; `SLOT_PLAN.md` resolves it towards `le10`.

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

- **Sessions 4 + parallel (`PRUNE`):** six delete-only doses, `le3`/`le4`/`le5`/`le8`/`le10`/
  `le15` (5.77 % → 41.60 % removed). All rebuild **byte-identically** to their ledger hashes and
  all pass the gates twice over. Predictions rise monotonically with dose, +0.002 → +0.010 —
  which is exactly why the receipt from one middle dose is worth more than another build.
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
| `registry/data_manifest.json` | 15 pinned inputs with sha256 + byte length; all re-hashed here |
| `registry/r0_verification.json` | Parent hash/grid/dot-count evidence (generated) |
| `registry/preflight.json` | Build verdict (`BUILD ALLOWED`, 15/15 pins verified) |
| `registry/raster_availability.json` | Which of the 20 ledger rows still have a raster |
| `registry/candidate_availability.json` | Hash + format status of the retrievable rasters |
| `src/gems91/metric.py` | DTI re-derivation + exact marginal gain |
| `src/gems91/gates.py` | The MUST gates; an unprovable gate is `UNVERIFIED`, never `PASS` |
| `scripts/` | `build.py` / `build_spacing.py` / `build_relief.py` / `build_prune_ladder.py`, `validate_raster.py`, `validate_release.py`, `update_release_manifest.py`, `crosscheck_predictions.py`, `preflight.py`, `restore_data.py` |
| `ledger/submissions.csv` | 32 rows (20 imported, 12 built here), provenance in `source`; receipt columns empty |
| `tools/` | `run_concentration.py` (builder), `pins.py`, `raster_io.py`, `stor.py`, `make_fixture.py` |
| `tests/` | 137 tests (metric algebra, gates, ledger invariants, builders, relief, release integration) |

## Run it

```bash
pip install -r requirements.txt
python scripts/verify_parent_r0.py     # fetch pinned parent, verify sha256
python scripts/preflight.py            # BUILD ALLOWED / BUILD BLOCKED
python -m pytest                       # 137 tests; the release tests need the built files
python -m tools.pins --axis CONCENTRATION   # what an axis still needs, by pinned id
```

### Earlier session delta (`arena/5563ddf8`, same date)

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
