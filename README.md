# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** R0 (`h33-h33-2-b2`), 37,654 dots on the pinned 3730x3292 EPSG:32611 grid. Both
  pinned TIFFs rebuild **byte for byte from either ancestor** (NaN `baeae321…c77dd`, 355,443 B;
  zeros `c55bafc4…a6fa9`, 219,065 B; dot digest `905cee9d…`) — see `src/gems91/lineage.py`.
  R0's 0.2778 remains **CLAIM**, never a receipt.
- **Inputs:** all 15 pinned entries present and re-hashed in this checkout; the 14 with a mirror
  match sha256 **and** byte length, and the derived catalogue mask rebuilds to its pinned hash
  (`c97c7819…`). `training_features.tif` has no mirror and stays UNVERIFIED, which is why MASS
  had to be re-ranked from the lineage fields (IR-91-21). `python scripts/preflight.py` now
  reports readiness **per axis**: PRUNE, MASS and RELIEF ready; SNAP, CONCENTRATION-by-bands and
  TRACKB blocked.
- **Three axis families are built on this parent, all gate-clean, from three merged sessions:**

  | axis | arms | predicted (MODEL) |
  |---|---|---|
  | **CONCENTRATION** (external GDR thermal prior, PR #13) | `gdr25rm10` / `gdr25m10` / `gdr10m10`, 10 % of dots moved, count fixed | **+0.0123** / +0.0114 / +0.0113 |
  | **PRUNE** (delete-only ladder + refill-held arms) | `le4` / `le5` / `le10` (and earlier `le3` / `le8` / `le15`); `p2.5` / `p2.9` / `p4.5px-h19cover` | +0.003 / +0.005 / **+0.008** (le15 +0.010); +0.002 / +0.004 / −0.015 |
  | **MASS** (cross-field-support ranking, this session) | `cons1drop` 12.06 % / `cons2drop` 28.53 % / `cons3add` 10.00 % | −0.000 / −0.015 / **+0.009** |

- **Ledger:** **38 BUILT rows**, 0 SUBMITTED, 0 receipts. Every sha256 and every
  (parent, axis, value) pair is unique. Live |Δ| < 0.01 is **no evidence**.
- **Next 3 slots — one receipt per axis** (full reasoning in `SLOT_PLAN.md`):
  1) `CONCENTRATIONgdr25rm10` (`c19adb01`, +0.0123 MODEL) — highest prediction, external prior;
  2) `PRUNE-le10-norefill` (`04002dae`, +0.008) — the only family the collar ruling cannot block;
  3) `MASScons3add` (`2803126d`, +0.009) — **contingent on the IR-91-03 ruling**; if the 3 px
  collar is ruled binding on every file, put `gdr25m10` (`d54e8815`) here instead.
- **Human still supplies:** the IR-91-03 collar ruling, TOP_PUBLIC with its date, slots remaining
  this week, deadline confirmation, every submission-page receipt, and all upload / final-pick
  decisions. No agent submits or touches the leaderboard.

### Session 4 delta (`arena/ee0cdd38`, MASS)

- **All pinned inputs restored and verified**, including the derived catalogue mask, which
  rebuilds byte-identically from `existing_faults`. The repo can now certify real files.
- **New builder:** `src/gems91/consensus.py` + `scripts/build_mass_consensus.py`, plus
  `scripts/instruments.py` for the three report-only instruments (PROXY, canary, SGMC).
- **The axis that could not be built as briefed:** the parent's continuous MASS ranking does
  not exist in any pinned file (all ancestors are binary; `training_features` is absent), so
  MASS is ranked by cross-field support over the pinned lineage fields (IR-91-17).
- **Three gate-clean arms** (all §6 MUST gates; the §4.4 collar is inherited, IR-91-03),
  whole-strata drops so no arm needs a tie-break: `cons1drop`
  (33,113 dots, MODEL −0.000), `cons2drop` (26,913, MODEL −0.015), `cons3add`
  (41,419, MODEL +0.009 — the only arm with a plausible path past +0.01).
- **Two findings that change the plan.** R0's 10 px block-density CV is already **0.531**,
  inside the reported 0.51–0.59 best-file band, and all four existing CONCENTRATION rows move
  CV *up* to 1.02–1.36 (IR-91-20) — that axis is spent, not untested. And the canary must be a
  **ring** test: the lineage fields are catalogue-masked, so the plain AUC is degenerate
  (IR-91-19). The ring canary is 0.526 — the support ordering knows nothing about catalogue
  proximity, which is what makes it a real MASS test rather than a disguised PRUNE.

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
