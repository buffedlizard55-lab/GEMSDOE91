# IRREGULARITIES

Only items that change a decision. Each entry says what the rule/assumption was,
what is actually true, and what I did differently because of it.

---

## IR-91-01 — The repo was an empty scaffold; the brief assumes an existing lineage

**Expected** (brief §5): "verify manifest hashes; rebuild R0 and match its sha256;
read `ledger/` and `SLOT_PLAN.md`".

**Actual:** `buffedlizard55-lab/GEMSDOE91` contained one 11-byte `README.md`, 1 commit,
no `registry/`, no `ledger/`, no `SLOT_PLAN.md`, no data directory, no releases.

**What I did:** found the upstream lineage in the sibling public repo **GEMSDOE88**
(20-row ledger, `SLOT_PLAN.md`, `registry/data_manifest.json`, `registry/r0_verification.json`,
mechanism cards) and GEMSDOE32 (the parent's own build repo). I imported the manifest and
ledger from there with `source=IMPORT:GEMSDOE88` on every row, and re-hashed everything
retrievable rather than trusting the copy.

**Decision it changes:** before any build, confirm GEMSDOE88 is the intended upstream and
that this repo was meant to start empty (i.e. the real working data lives on the entrant's
machine, not here). If GEMSDOE91 was supposed to be a populated clone, the setup lost files
and any hash claims in it are void.

---

## IR-91-02 — The three competition rasters are absent and are not publicly mirrored

**Blocked gates:** footprint (needs `sample_submission.tif`), zero-catalogue-mass and the
≥3 px collar (need `existing_faults.tif`), block priors / edge fields / parent ranking
(need `training_features.tif`, 419 MB).

**Evidence:** code/filename search across every public repo in
`buffedlizard55-lab` returns 0 hits for `sample_submission.tif`, `existing_faults.tif`,
`training_features.tif`; the manifest paths (`data/official/`, `data/bridge/`) are
gitignored local paths.

**Good news:** no competition raster has leaked into a public repo, so the
data-use-terms concern in brief §2/§3 does not fire for these three files.

**Decision it changes:** brief §2 forbids filling gaps from memory and briefly demands
pinned+verified inputs. A variant that cannot be checked for catalogue mass or collar
cannot be certified, so I **built nothing** rather than fabricate a catalogue stand-in.
`scripts/preflight.py` now hard-blocks the build path.

---

## IR-91-03 — R0 itself violates constraint 4, so the brief's default plan cannot be compliant

Constraint 4: "keep >=3 px from [the catalogue] unless AXIS=PRUNE".

**Actual:** R0 keeps every dot **>2 px** away, not >3 px. Upstream's own PRUNE audit
(`releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.json`, `parent_diff`) records
`dots_le_2px = 0`, `dots_le_3px = 2171` — i.e. **2,171 R0 dots sit at 2 < d ≤ 3 px**
(this session could not re-measure them: no `existing_faults.tif`; the number is
therefore **CLAIM from a built artifact**, not verified here).

**Consequence:** every non-PRUNE variant whose parent is R0 **inherits** those 2,171 dots
and is non-compliant at construction, no matter how good the edit is. That is why 17 of the
20 ledger rows are `HOLD` in upstream's own words ("inherits R0's 2 px collar").

**Decision it changes:** the only gate-clean parent is **R1 = PRUNEp3px** (`6f7ae705`),
and any MASS / CONCENTRATION / SNAP / RELIEF / SPACING work must be **re-based on R1**.
`validate_release.py` treats `collar_ge_3px` as `FAIL` for every non-PRUNE file and
`UNVERIFIED` when the catalogue is missing — it never passes it by default.

**Open question for the human (rule scoping, not my call):** whether the ≥3 px gate is meant
to bind *controlled edits of R0* or only *new* dot placements. If it binds everything, the
default plan in brief §7 (wk1–2 MASS/CONC/SNAP/PRUNE/RELIEF on R0) is unexecutable as written.

---

## IR-91-04 — 17 of 20 ledger rows point at a raster that is a 404

`registry/raster_availability.json` walks every ledger row and GETs its declared raster
from the mirror. Result: **3 present, 17 absent**. The three present are the MASS variants
(`MASSm10minus`, `MASSm10plus`, `MASSm20minus`), fetched and re-hashed: all six files
(nan + zeros) match their ledger hashes and their recorded dot counts (33,889 / 41,419 /
30,123).

The recommended slot-1 file **`PRUNEp3px` (`6f7ae705`)** has a receipt naming
`releases/…6f7ae705.tif` (354,519 bytes) but that path has **never existed in git**
(`commits?path=…` returns 0), and no sibling repo carries it.

**Cross-session duplicate risk:** sibling repos hold builds of the *same* axes under
*different* value spellings — `GEMSDOE87` has `PRUNE1/PRUNE3/PRUNE4` (`4679d91c`, `bc00a06c`,
`f5c53782`) and `CONCc10/c15/c20`, `GEMSDOE85` has `conc10/15/20`, `GEMSDOE84` has
`pruned2p5/3p0/4p0`. The ledger's (parent, axis, value) dedupe cannot see those, so the same
experiment may already have been run (and possibly already spent) in another session.
Check the sibling `releases/` before spending a slot on PRUNE or CONCENTRATION.

**Decision it changes:** slots cannot be spent by downloading a finished, compliant file.
Slot 1 and slot 2 both require a **rebuild on the entrant's own machine** (where the pinned
inputs live). The only uploadable-today files are the three MASS variants, and two of them
are `HOLD` (negative MODEL, or a nested cut of another).

---

## IR-91-05 — No receipt exists anywhere, so no live effect has ever been measured

All 20 ledger rows have empty `receipt_score` / `receipt_date`. R0's 0.2778 is `CLAIM`.
`TOP_PUBLIC` is blank in the brief; the `0.4413` in upstream `SLOT_PLAN.md` is a
human-supplied figure dated 2026-10-22 (**CLAIM**), ~0.16 above the best claimed DTI of
this lineage — a gap no mechanism in the ledger explains.

**Decision it changes:** every "predicted change" in this repo is `MODEL`, and the brief's
own rule applies — a live change under 0.01 is **no evidence**. Two consequences:
(1) fill `TOP_PUBLIC` with a receipt-backed number before spending a slot, so a +0.02 MODEL
stop pretending to be progress against a 0.44 target; (2) paste receipt_score + date into
`ledger/submissions.csv` the same day, or the next session is blind again.

---

## IR-91-06 — The DTI re-derivation cannot produce absolute scores

`src/gems91/metric.py` implements the brief's algebra exactly
(`DTI = T / (0.2T + 0.2(S−M) + 0.8|G|)`, triangular R = 3 px). Two observations from the
unit tests: (a) for an isolated truth pixel, a single dot scores 1.0; (b) dense coverage of
a short truth set scores **> 1.0**, while live scores top out near 0.44. So the organiser's
normalisation differs from this re-derivation in a way the term structure does not expose
(most likely T is normalised per truth pixel, and/or the kernel is area-normalised).

**Decision it changes:** use this module only for **ordering** dots by exact marginal gain
and for sign checks. Never quote its absolute output as a score or as a predicted live
value, and do not tune any hyperparameter against it. Label `MODEL` everywhere.

---

## IR-91-06 — `min_distance_to_mask` transposed rows and columns (found and fixed here)

**Expected:** the collar gate counts dots within 1/2/3 px of the catalogue mask.

**Actual:** `cols, rows = np.nonzero(target); return dist[rows, cols]` indexes the
distance array as `[column, row]`. `np.nonzero` returns `(rows, cols)`, so every distance
was read from the mirrored cell, and any row index ≥ the array width raised `IndexError`.
The real grid is 3730 rows × 3292 columns, so both failure modes were live.
The 34 data-free tests could not see it (they use square, tiny arrays); the first
non-square raster through the gates — the synthetic 120×160 fixture — raised it immediately.

**What I did:** fixed the unpacking in `src/gems91/gates.py` and added the end-to-end
test (`tests/test_concentration.py::test_end_to_end_build_then_certify`) that runs the
gates on a real, non-square raster.

**Decision it changes:** every collar number produced before this fix is void, including
any `dots_le_1/2/3px` in `registry/candidate_availability.json` **if** it was produced by
this function rather than transcribed. Re-derive the 2,171 figure in IR-91-03 from
`existing_faults.tif` before citing it in a submission note. The bug is symmetric
(distance to the transposed cell), so it inflates and deflates indiscriminately.

---

## IR-91-07 — The imported CONCENTRATION rows rank by parent dot density, so they are not prior tests

**Expected** (brief §5): move dots from the lowest-prior blocks to the highest-prior ones.

**Actual:** the three `CONCENTRATION` rows in `ledger/submissions.csv`
(`b10px-m10`, `b10px-m20`, `b50px-m20`) record
`ranking_basis = "coldest->hottest … blocks by 2-block-smoothed parent dot density"`.
The block prior is the parent's own dots. A dot field moved toward its own density maximum
is a *clustering* edit; it cannot show whether an independent km-scale prior transfers.

**What I did:** `tools/run_concentration.py` requires `--prior` and documents that the
prior must not be derived from the parent's dots; the ledger row it writes says so in
`ranking_basis`.

**Decision it changes:** those three rows may be read as dose-response evidence for
*clustering at fixed count* (CV 0.618→1.021 and 0.618→1.257), which is still useful, but
they must not be cited as evidence about a prior. If any of them scores ≥ R0 + 0.01, the
correct follow-up is the same dose with an **external** prior, not a bigger dose.

---

## IR-91-08 — The pay threshold is 0.056 only if `|G|` is constant; the alternative is 0.0458

`src/gems91/metric.py` takes `|G|` = number of truth pixels, so adding a dot cannot change
it, and the brief's shortcut `c > 0.2·DTI` (0.056 at DTI 0.28) is exact **in this model**:
the denominator grows by exactly 0.2 because `+c` in `T` cancels `−c` in `(S − M)`.

If the official metric instead defines `|G|` as *remaining uncovered truth*, the bar becomes
`0.2·DTI/(1 + 0.8·DTI)` ≈ **0.0458** at 0.28 — a 22% lower bar. Dot *ordering* barely
changes; the size of any predicted delta does.

**Decision it changes:** quote ranking-level statements (sign, order) from the metric code,
never an absolute predicted delta, until the organiser implementation is diffed (it is not
public and the terms ban automated access). All predictions in `ledger/submissions.csv`
are therefore `MODEL:` and must stay that way.
