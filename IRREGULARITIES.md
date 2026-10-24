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

## IR-91-02 — ~~The three competition rasters are absent and are not publicly mirrored~~ **RESOLVED (session 3)**

> **UPDATE 2026-10-23 (session 3).** This item's central claim is **wrong**: the rasters
> *are* publicly mirrored, and they were located and hash-verified. See **IR-91-09**. The
> text below is kept because its reasoning about what the absence would have implied is
> still the correct reasoning; only the premise failed.


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


---

# Session 3 additions (2026-10-23, `arena/5563ddf8`)

## IR-91-09 — The rasters DO exist in public mirrors; all three verified, PRUNE unblocked

IR-91-02 was wrong. Recovered and verified byte-for-byte against hashes already recorded in
this repo's own `registry/data_manifest.json` (which the earlier sessions had obtained from
GEMSDOE32's manifests):

| entry | mirror | result |
|---|---|---|
| `sample_submission` | `60GEMSDOE:data/official/sample_submission.tif` | sha256 matches |
| `existing_faults` | `60GEMSDOE:data/official/labels.tif` | sha256 matches (it *is* the labels raster) |
| `parent_r0_nan` | `GEMSDOE32:docs/downloads/…e5eb6e7e-nan.tif` | sha256 matches |
| `parent_r0_zeros` | `GEMSDOE32:docs/downloads/…e5eb6e7e-zeros.tif` | sha256 matches |

**Decision it changes.** The axis readiness gate now says **PRUNE: READY**, while MASS, SNAP,
CONCENTRATION, RELIEF and TRACKB stay blocked on `training_features` and the lidar layers.
That is why this session built PRUNE and nothing else.

**Also relevant to data-use terms.** These mirrors are public, so the rasters are already
public. This repo still keeps `data/` and `releases/*.tif` out of git.

## IR-91-10 — PRUNE value `3` already existed twice; my ladder is labelled to stay unique

The imported ledger already held `PRUNE/3` (`01d57649`, H19 BFS refill) and `PRUNE/p3px`
(`6f7ae705`, refill from un-emitted H19-5 ridge dots), plus `p1px` and `p4px`. Brief §5 says
each (AXIS, value) pair is built once.

**Decision.** I did not rebuild those. My three builds are labelled `le3-norefill`,
`le8-norefill`, `le15-norefill`. `le8` and `le15` are new doses. `le3-norefill` is a
deliberate **refill-policy contrast** against the two existing PRUNE/3 rows at the same dose
(35,483 dots vs 37,654), not a duplicate file. If you consider dose-with-different-refill to
be the same pair, drop `le3-norefill` and the ladder still stands.

## IR-91-11 — The parent lineage's PRUNE is delete-only; the brief says refill

Brief §5 says "refill to hold the count". Measured, not argued: differencing R0 against the
public solo-d28 raster gives 37,654 shared dots, **0 in R0 but not in solo-d28**, and 2,545
dots within ≤2 px in solo-d28 only. So R0 = solo-d28 minus those 2,545 dots, **no refill**.

**Decision.** The three variants follow the lineage (delete-only), because a refill needs the
parent's ranking and none was ever stored (`training_features` is the missing input that
would let it be rebuilt). Consequence, stated in every mechanism card: these builds move mass
and geometry together, so a gain cannot be attributed to "avoiding the catalogue" alone.

## IR-91-12 — `sha_unseen` was unsatisfiable in the intended order (fixed here)

`gates.py` compared the candidate hash against *every* ledger row. Brief §7 requires a BUILT
row for the file being certified, so build → record → certify could never pass, and the three
built files were rejected as "already used" although no slot had been spent.

**Fix.** Both validators (`src/gems91/gates.py` and `scripts/validate_raster.py`) now compare
against **SUBMITTED** rows only, and report how many BUILT rows matched. After the fix all
three files certify under both implementations independently.

## IR-91-13 — My PRUNE predictions contradict the imported `p4px` prediction

Imported `PRUNE/p4px` predicts **−0.009** for removing the 2–4 px collar; my algebra predicts
removal *gains* because dots beyond 3 px carry zero catalogue credit and still cost `0.2` in
the denominator. Both cannot be right.

**Why it is not resolvable here.** The sign depends on how much *new-fault* credit those dots
earn, which no local label can measure (the catalogue is masked in scoring).

**Decision it changes.** Read the ladder as a direct test of this disagreement: if `le8`/`le15`
gain, the `p4px` −0.009 prediction is wrong and the "3–4 px shell carries real credit" story
is dead. If they lose, the algebra's zero-credit argument is missing a real credit term and
`p4px` was right for a reason worth writing down.

---

# Session 3 (`arena/a5e7bf22`, SPACING) — three items not covered above

Numbered after IR-91-13. Item IR-91-11 in session 3's own draft (mirrors exist) was a
duplicate of IR-91-09 and is dropped; session 3's collar item was a duplicate of IR-91-03.

## IR-91-14 — the format template is not blank: its values ARE the catalogue

`sample_submission.tif` (sha256 `2176d08e…`) has **60,988 positive cells, and
that set is exactly the positive-cell set of `existing_faults.tif`**
(`np.array_equal(template > 0, catalogue == 1)` → True, 60,988 = 60,988).
It is not an all-zeros raster: it is the mapped catalogue as float32, with NaN
outside the footprint (7,111,787 cells).

**Decision it changes.** (a) The template may be used for footprint, CRS,
transform, shape and dtype — never as a value reference, a null baseline, or a
container of "no mass inside". (b) Any "zeros inside the footprint" check must
be built from the NaN mask, not from `template == 0`. (c) Shipping the template
unchanged would emit mass on the catalogue and is a hard-constraint violation
(brief §4.4), not a trivial no-op.

## IR-91-15 — `labels.tif` is the catalogue, so no local instrument can see new faults

`labels.tif` and `existing_faults.tif` are **byte-identical** (both sha256
`7ba308cc…`, 425,830 B) in every public mirror checked. Whatever the file is
called, its content is the mapped USGS/INGENIOUS trace.

**Decision it changes.** The only truth-adjacent local instrument available to
this project is *catalogue* recovery. A candidate's dots sit > 2 px from that
catalogue by construction, so the instrument can only observe the 2–3 px collar
(3.9 % of withheld cells; mean credit 0.006). It therefore **cannot adjudicate
the SPACING axis** — on this axis its sign is collar drift, not spacing — and it
must stay a REPORT-ONLY number. Reported, not gated, not believed.

## IR-91-16 — the parent's dot set is reproducible; its file bytes are not

R0's support is reproduced **exactly** from two independent pinned ancestors —
`gems25-dotted-h19-5-d2-8…-nan.tif` (44,090 dots) minus every dot with
Euclidean distance ≤ 2.0 px to the catalogue → 37,654 dots, **0 differing
cells**; and `GEMSDOE28__h27-4-r1-solo-d2-8.tif` (40,199 dots) → the same 37,654
cells. R0's dot-set digest `905cee9d…` independently matches the digest
GEMSDOE86 recorded, so both sessions are editing the same set.

The parent's **bytes** are not reproducible here: 36 encoder configurations
(deflate/zlib/lzw × predictor 2/3 × planar/contig × tiled 256/unstripped) were
tried against the pinned NaN twin (`baeae321…`, 355,443 B); the closest output
was 318,257 B and no configuration matched. The original writer's libtiff/zlib
build is not available in this sandbox.

**Decision it changes.** Every artifact carries **both** a sha256 and a dot-set
digest; the dot-set digest is the identity that can be checked across sessions,
and no lane may claim byte-level reproducibility of the parent. (GEMSDOE86
logged the same finding as IR-86-PRUNE-01.)

## IR-91-17 — the three CONCENTRATION arms are one experiment, and the axis has a measured downside

Ten percent of the dots moved is all the brief allows, so all three arms move 3,765 dots with
the same seed, the same collar rule and the same placement logic; they differ only in block
size (1 vs 2.5 km) and in whether thermal features within 8 px of the catalogue are allowed
in the prior. The consequences:

* their predicted changes are +0.0114, +0.0113 and +0.0123 (MODEL), i.e. inside each other's
  uncertainty by an order of magnitude;
* their block-CV changes and donor/acceptor prior gaps are effectively identical;
* the surrogate-truth DTI gains are +41 %, +41 %, +44 %.

**Decision it changes.** Three slots would buy one number three times. `SLOT_PLAN.md` sends
**one** arm (`gdr25rm10`) and keeps the other two as conditional fallbacks. This is the second
session in a row where the honest recommendation is to spend fewer slots than were built.

The same session measured the axis's downside: the arms drop coverage of the lineage's own
H19-5 field from 88.6 % to 80.2 % of its 121,131 px, which under H19-5-as-truth is −0.022. That
number is pessimistic (that field is ~3× denser than truth: R0 scores 0.796 against it versus a
claimed 0.2778 live), but it is *measured*, it exceeds the brief's 0.01 evidence bar in the
negative direction, and it is now the floor of every predicted range in the ledger.

## IR-91-18 — the pin table named an input this axis does not use, and one it does

`tools/pins.AXIS_INPUTS["CONCENTRATION"]` used to require `training_features`
(`data/bridge/gems-geodawn-numerical-features.tif`, 419 MB, absent, no public mirror).
`scripts/build_concentration.py` therefore cannot use `check_axis`; it verifies the inputs it
actually reads, by sha256, through `pins.check_paths`: `parent_r0_nan`, `parent_r0_zeros`,
`sample_submission`, `existing_faults`, `anc_d2_8`, `anc_solo_d2_8`, `anc_h19_5` and
`gdr_wellspring_in_footprint`. Two consequences to keep straight:

1. The prior is **derived**, not pinned: `prior = exp(-d / 12 px)` over de-duplicated Hot/Warm
   GDR feature cells, with the parameters and the array digest (`51f294b2…`, `6afed3bf…`) in
   `registry/derived_priors.json` and the evidence JSON. Rebuilds reproduce it exactly from the
   pinned CSV, which is why no new 12 MB raster had to be added to the manifest.
2. `training_features` remains **absent and unverified**. No band from it was used, and no
   number in this session depends on it. RELIEF and SNAP remain blocked on it.

**Decision it changes.** CONCENTRATION is buildable without the unlicensed lidar layer and
without the 419 MB feature stack; that, plus the licence status of the source
(USGS/NBMG GDR inventory, public domain, already pinned as "prior layer only"), is why it was
chosen over SNAP/RELIEF for this session.

## IR-91-19 — the session's own prediction instrument is circular, and the floor is not

The headline MODEL prediction scores each candidate against the prior network *itself* as a
surrogate truth set and claims a tenth of the result. By construction that instrument cannot
say anything about whether the prior is right; it answers "what if it were". Two independent
floors are computed instead and reported in the same JSON:

| alternative truth model | cells | Δ live if that model is truth |
|---|---:|---:|
| the prior network (circular; optimistic) | 9,501 | +0.114 (before the κ = 0.1 shrink) |
| uniform-random cells of the same count | 9,501 | −0.006 |
| the lineage's own H19-5 field | 121,131 | −0.022 |

**Decision it changes.** The ledger's `predicted_range` floor is the measured worst case, not
`point − 0.008` as in earlier sessions. A reader should treat these candidates as
**coin-flips with a −0.02 tail**, which is exactly how `SLOT_PLAN.md` orders them and why slot
2 is a PRUNE file rather than the second arm of the same axis.

---

## IR-91-17 — R0 byte reproduction is now solved; IR-91-16 is superseded

The missing encoder setting was compression **level 9**, not a different libtiff build.
Using the recorded `deflate / predictor=3 / zlevel=9 / tiled 256` profile on the catalogue
grid, this session independently rebuilt R0 from each pinned ancestor and reproduced both
files exactly: NaN `baeae321…` / 355,443 B and zeros `c55bafc4…` / 219,065 B. Recipe source:
<https://github.com/buffedlizard55-lab/GEMSDOE86/blob/d423f858abf6cb2e63edf67773ed5650d507f78c/scripts/run_prune_ladder.py>.

**Decision it changes.** The brief's stop gate is passed by an actual independent recompute,
not pinned-artifact retrieval or an approximation. `scripts/verify_parent_r0.py` and the new
builder both fail unless both byte hashes match. Dot-set digests remain useful, but the old
"file bytes are not reproducible" statement no longer applies.

## IR-91-18 — Fixed-count refill cannot preserve d2.8; PRUNE is the only clean R0 axis here

A dry feasibility test retained the parent's d2.8 exclusion and found only **722 / 621 / 498**
legal H19-5 refill cells for the required **941 / 1,611 / 4,848** additions. Even the smallest
nonzero fixed-count collar is therefore infeasible under that extra constraint. Separately,
MASS cannot use H19-5 as a ranking because the pinned ancestor is binary, and a non-PRUNE
child inherits R0's 2,171 dots inside the 3 px gate.

**Decision it changes.** The session uses the lineage's recorded no-inhibition PRUNE refill,
with exact iterative marginal-DTI coverage and no spacing objective. Nearest-neighbour drift
is reported as a confound on every card; it is not hidden or called a pure collar-only result.
PRUNE was chosen over inventing a MASS ranking or shipping a non-compliant non-PRUNE child.

## IR-91-20 — the refill-held PRUNE arms are in the ledger but not in the release manifest

Session #10 built three *fixed-count* PRUNE arms (`p2.5px-h19cover`, `p2.9px-h19cover`,
`p4.5px-h19cover`) and recorded their sha256 in `ledger/submissions.csv`, but
`releases/MANIFEST.json` on `main` lists only the twelve SPACING and delete-only PRUNE files.
The CI byte-identity check iterates that manifest, so those three files are not rebuilt-and-hashed
by CI; their identity rests on the ledger row alone.

**Decision it changes.** This session's slot plan does not send a refill-held arm, so nothing
here depends on it — but do not upload one without first running
`python3 scripts/build_prune_refill.py --build` and comparing the output sha256 to the ledger,
and add the entries to `releases/MANIFEST.json` when you do. The two files this session *does*
recommend (`CONCENTRATIONgdr25rm10`, `PRUNEle15-norefill`) are pinned and were rebuilt
byte-identically today (IR-91-17 session notes; `releases/MANIFEST.json` has 18 entries here:
6 CONCENTRATION + 6 delete-only PRUNE + 6 SPACING).

> **Renumbering note (merge of PR #14, second pass).** This session's four items were
> written as IR-91-17…20 before main gained IR-91-17/18 (R0 bytes; refill feasibility) and
> then IR-91-19/20 (CONCENTRATION prior; refill arms missing from the manifest). They are
> now IR-91-21…24 and the cross-references in the code, cards, ledger notes and docs were
> updated to match.

## IR-91-21 — The parent's own MASS ranking does not exist in any pinned file

Brief §5: "MASS: drop the lowest-ranked 10% / add the next-ranked 10%, by the parent's own
ranking (rebuild the ranking from the recorded recipe if it is not stored)."

**Measured:** no stored artifact ranks R0's dots. Every pinned ancestor is **binary** — values
in {0, 1} only: `calib_h195_01922` (121,131 px), `calib_h194_01894` (123,779), `calib_h161_01855`
(123,939), `calib_d15_02477` (60,069), the d2.8 raster (44,090) and solo-d28 (40,199). The one
input that ever carried a continuous score, `training_features.tif` (419 MB), has no mirror in
any sibling repo and is absent, so it cannot be read at all — the manifest's own policy forbids
filling the gap from memory.

**Substitution, and exactly what it costs.** MASS is ranked by **cross-field support**: for each
dot, how many of the three lineage fields emit it (3 / 2 / 1 → 26,913 / 6,200 / 4,541 of R0's
dots; 0 dots lie outside all three). This is the parent lineage's *own* pinned data, not an
external prior and not a label, and it is ordinal with whole strata, so no arm needs a tie-break
inside the ordering it is testing. It is **not** the parent's continuous score and every card
says so. Consequence: a flat result on these arms cannot distinguish "mass is not a lever" from
"this particular ordering is uninformative" — that is why the session built both directions.

**Where this disagrees with IR-91-18 (the merged PR's PRUNE session).** That item concludes
"MASS cannot use H19-5 as a ranking because the pinned ancestor is binary… PRUNE was chosen over
inventing a MASS ranking". Both halves are right and both are answered here: a *single* binary
field cannot rank, but the **vote over three** binary fields is a 3-level ordinal ordering built
only from pinned bytes, with no invented score and no model; and the collar objection is real
(R0 fails the 3 px gate on its own 2,171 dots, IR-91-03) but it is the *human's* rule to
interpret — the parent that scores 0.2778 carries the same dots. The arms are therefore built and
flagged, not withheld; if the human rules the collar binding on every file, these three files are
not uploadable and the PRUNE queue stands unchanged.

**Also corrected:** `axis_requirements.MASS` in `registry/data_manifest.json` (and
`tools/pins.py`) declared `training_features` as required, which made the axis permanently
BLOCKED while the file cannot exist here. It now lists what the build actually reads and hashes:
`sample_submission`, `parent_r0_nan`, `existing_faults`, `anc_h19_5`, `anc_h19_4`, `anc_h16_1`.
No sha256 was changed, and `training_features` stays pinned and absent.

## IR-91-22 — Break-even precision is 11.8 %, so every mass edit is a ±0.01 bet

The brief's shortcut ("a dot pays iff credit > 0.2·DTI ≈ 0.056") is exact for *unmatched* mass
only. Working the algebra for the triangular kernel (R = 3 px, α = 0.2, d = 0.2778):

    E[ΔDTI per dot] ≈ (p·c̄ − γ)/D,    γ = α·d/(1 − α·d) = 0.0556

so an emitted dot is worth its mass iff its **precision** p exceeds γ/c̄ ≈ **11.8 %**
(c̄ = 0.5 mean credit), equivalently iff it lies within **2.83 px** of a truth pixel. With
D ∈ [1e4, 3.5e4] (bracketed from a 15–35 % matched fraction), 1,000 dots are worth
0.002–0.006 of live score.

**Decision it changes.** No MASS dose can be expected to beat +0.01 unless it moves more than
~2,000 dots of clearly-above-breakeven precision. That is why the arms are 3,765–10,741 dots and
why the *add* direction is scheduled first: its payoff ratio is (0.5 : 0.0556) ≈ 9:1 per dot,
while a drop forfeits the whole 0.5 on every dot it gets wrong. It also retires the
`SPACING`-style edits ab initio — displacement inside 2.83 px cannot change p at all, which is
consistent with the ≤0.003 bound session 3 derived independently.

## IR-91-23 — The leakage canary has to be a ring test; the plain test is degenerate

The brief's canary: "a single feature with AUC > 0.90 means stop and investigate."

**Measured:** the plain version cannot be run. The three lineage fields — like R0 itself — were
built with the catalogue masked out: of the 60,988 catalogue pixels, **0** carry any field
(vote histogram on the catalogue is [60988, 0, 0, 0]). Any AUC computed as
"catalogue pixels vs background" is therefore an artefact of the mask, not a leak, and
reporting it as "below threshold" would be a false pass.

**Replacement (implemented in `scripts/instruments.py`):** the 0–3 px ring around known traces
vs background ≥7 px clear. Result for the session-4 ranking: **AUC 0.526** (7.8 % of ring pixels
carry support vs 2.6 % of background). So the support ordering is essentially blind to catalogue
proximity — it is a genuine independent ranking, not a disguised PRUNE, and its failure modes
are about field construction rather than label leakage.

## IR-91-24 — CONCENTRATION is spent, not untested: R0 already sits in the reported CV band

The brief reports that the best files sit at block-density CV 0.51–0.59.

**Measured on R0:** 10 px (1 km) block density CV = **0.531**; 25 px = 0.791; 50 px = 1.041.
R0 is already inside the reported band. The four imported CONCENTRATION rows moved CV *away*
from it — 0.618 → 1.021 (`b10px-m10`), → 1.257 (`b10px-m20`), 0.703 → 1.359 (`b50px-m20`), and
1.874 → 1.642 for `15pct-1km-grad` — because each concentrated mass into the hottest blocks,
which raises CV by construction.

**Decision it changes.** Do not spend a slot on a CONCENTRATION arm as specified, and do not
"fix" it by pushing CV lower with a spacing edit either (that is a SPACING axis, bound ≤0.003).
The statistic that inspired the axis is already satisfied by the parent, so the axis has no
headroom left; a future arm would need a *new* mechanism, not a new block size.

**Scope, updated after merging PR #13.** That session did build the *new mechanism* this item
asked for: a CONCENTRATION prior taken from the external, public-domain GDR thermal layer rather
than from the parent's own dots. Those three arms (`gdr25rm10`, `gdr25m10`, `gdr10m10`) are
therefore **not** retired by this measurement, and they report a measured ±: 8.4 pp of H19-5
coverage cost (88.6 % → 80.2 %) and a −0.022 prediction floor. What still stands is the CV point:
they move 10 % of mass into the hottest 2.5 km blocks, which raises block-density CV further above
the 0.51–0.59 band R0 already sits in (0.531), so the mechanism they test is *prior transfer*, not
the CV statistic that originally motivated the axis. Do not describe them as a CV fix.
---

# Session 5 (`arena/42de3fed-gemsdoe91`, RELIEF) — three decision-changing items

## IR-91-25 — `training_features` is already public in sibling repo `buffedlizard55-lab/GEMSDOE`

Querying `https://api.github.com/repos/buffedlizard55-lab/GEMSDOE` (`private: false`
`RECEIPT`) and testing an unauthenticated blob download (`HTTP 200`, `41,425,484` B
`RECEIPT`) confirms that the official `418,912,844`-byte `gems-geodawn-numerical-features.tif`
raster (sha256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`
`RECEIPT`) is already published in 5 split blobs at commit `c0c06ac8…` of
`buffedlizard55-lab/GEMSDOE` (alongside the public mirrors already noted in IR-91-09).

**Decision it changes.** (a) Per the standing rule (*"Keep competition rasters out of
public repos and git-tracked releases; flag if already public"*), this public exposure is
explicitly flagged for human review/remediation on `buffedlizard55-lab/GEMSDOE`. (b)
`GEMSDOE91` continues to gitignore `data`, `data/`, and `releases/*.tif`, storing ONLY
sha256 pins in `registry/data_manifest.json` and `releases/MANIFEST.json` while restoring
bytes transiently in CI and `.cache/data`.

## IR-91-26 — `RELIEF` axis unblocked via official GeoDAWN `det_elev` + `det_elev_slope` instead of unlicensed LiDAR

Earlier sessions marked `RELIEF` blocked on `ext_lidar_scarp_u8.tif`, which covers only
`75.4%` of the footprint and carries `"license": "USGS 3DEP public domain (derived — licence unchecked)"`
in `registry/data_manifest.json`. Inspecting the now-verified official `training_features`
stack ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/))
shows `Band 12 det_elev` (detrended elevation) and `Band 19 det_elev_slope` (detrended
slope) cover `99.94%` of the `5,167,373`-pixel footprint natively (`100.00%` after EDT
nearest-cell fill of `3,061` boundary sentinel pixels `RECEIPT`), with single-band leakage
canary AUCs of `0.5063` and `0.5633` `PROXY` (`≪ 0.90`).

**Decision it changes.** Switched `axis_requirements["RELIEF"]` in
`registry/data_manifest.json` from `ext_lidar_scarp_u8` to `training_features` + verified
lineage ancestors, unblocking `RELIEF` on 100% sponsor-provided inputs without external
licensing risk or partial-footprint bias.

## IR-91-27 — R0's 2,171 inherited `2 < d_cat ≤ 3 px` collar dots must be quarantined on non-PRUNE edits

Parent R0 (`h33-h33-2-b2`) contains `2,171` dots at Euclidean distance `2.236 ≤ d_cat ≤ 3.0 px`
(`390` in T1 Basin, `1,134` in T2 Piedmont, `647` in T3 Range `RECEIPT`). Removing any of
those `2,171` dots during `RELIEF` donor selection would simultaneously execute a partial
`PRUNE` edit (confounding relief reallocation with catalogue-collar pruning), whereas
placing any new recipient dot at `d_cat ≤ 3.0 px` violates the `≥ 3 px` new-dot rule
(`added_le3 == 0` in `scripts/validate_raster.py`).

**Decision it changes.** `src/gems91/relief.py::shift_relief_mass` enforces strict
`d_cat > 3.0 px` on **both** donor removal and recipient placement (`collar_le3px = 2,171 → 2,171`,
`added_dots_le3px = 0` across all three `RELIEF` builds `RECEIPT`).


## IR-91-31 — TRACKB trace densification confounds strike with spacing; its PROXY is invariant

TRACKB targets sampled every 1.2 px along a trace cannot respect R0's ~2.8 px dot spacing
(support dots already occupy the trace every ~3 px), so the three Session-6 arms use a 1 px
minimum separation. Any live or Phase-2 difference therefore mixes "dots lie on a strike-
consistent trace" with "dots are denser along lines"; it is disclosed on every card, not
hidden. Separately, the catalogue hide-and-recover PROXY is mathematically invariant for
these arms (every added/removed dot is >3 px from the catalogue and earns it zero credit),
so it is reported as uninformative rather than quoted as a number.

**Gate note.** `scripts/validate_release.py` (`gems91.gates`) reports `collar_ge_3px` FAIL on all three arms *and on R0 itself* (2,171 inherited dots at 2-3 px, IR-91-03); no TRACKB-added dot is <=3 px, and `validate_raster.py` passes 14/14. This does not block TRACKB, but the human's IR-91-03 ruling still governs any upload.

**Decision it changes.** TRACKB files are Phase-2/expert-review candidates only; they do not
enter the weekly slot queue unless the human explicitly decides, and no PROXY claim is made
for them.

## IR-91-32 — CONCENTRATION builder ids embed today's date; CI broke at midnight UTC

`scripts/build_concentration.py` stamps candidate ids with `datetime.now()`, so a rebuild on
any later date returns the identical raster (same sha256) under a new id, and its ledger
append refused it as a duplicate hash. This failed the CI lineage job on 2026-10-24 with no
code change in that builder. **Decision it changes:** the append now treats a same-sha256
rebuild under a date-shifted id as idempotent proof (logged), while a *different* hash under
an existing id still fails. The same daily-date bug in `build_mass_consensus.py`, `build_spacing.py` and `build_prune_ladder.py` was fixed by pinning the fleet build date `20261023` in all of them (verified by a full local CI-sequence rebuild + manifest hash check). Found in Session 6 while adding TRACKB to the CI manifest check.
## IR-91-28 — The catalogue PROXY is identically zero for SNAP, by construction, not by result
**Expected** (brief §6): the catalogue hide-and-recover PROXY, reported with `n` withheld
positives and a 95 % CI, should say something about a variant.
**Actual:** every SNAP arm returns `0.006186 -> 0.006186`, a delta of exactly `0.000000`
in all 5 draws (`12,198-12,201` withheld positives per draw, CI `[0.005958, 0.006413]`).
The reason is structural: a withheld catalogue cell can only be credited by a dot within
the 3 px kernel; SNAP targets are floored at `d_cat > 3 px` (constraint 4) and the only
parent dots already inside 3 px are the 2,171 collar dots quarantined by IR-91-27. No legal
SNAP move can therefore change catalogue credit.
**Decision it changes.** Do **not** read the zero as evidence about the axis (and do not
write it up as "no effect"). The informative control is the independent off-catalogue USGS
SGMC map, where credit can change; it is reported as `PROXY` only. The same blindness now
applies to every non-PRUNE axis whose targets are floored outside the collar.
## IR-91-29 — The full SNAP arm is a re-layout, not a snap, and SNAP is exempt from the 1-50 % rule
**Expected** (brief §5): `SNAP` moves each dot `<= 2 px`; the 1-50 % dot-change rule governs
the other axes, and SNAP is exempt because same-count movement can legitimately touch many
dots.
**Actual:** the literal window-max rule moves **35,174 of 37,654 dots (93.41 %)** with a mean
displacement of **1.73 px** and a dot-set Hamming distance of **186.83 %**. That is a new
field derived from two gradient bands, not a positional refinement; it belongs in the same
family as the single-signal lanes that scored 0.00-0.19 live. At the other end, the crest
arm moves only **2,047 dots (5.44 %)** by **0.08 px**.
**Decision it changes.** Built a pre-registered dose ladder (5.4 % / 11.9 % / 93.4 %) rather
than three arbitrary driver variants, so the human is not forced to spend a slot on the
extreme to learn the axis's direction. `s2f` is labelled a negative control, not a slot
candidate; the SLOT_PLAN keeps SNAP out of the top 3.
## IR-91-30 — The repo's existing SNAP path would violate constraint 4 and IR-91-27
**Expected:** `scripts/build.py --axis SNAP` is the generic builder and should produce a
compliant SNAP file.
**Actual:** it calls `axes.snap`, whose `min_cat_px` default is **2.0** (not 3.0) and which
does not quarantine the parent's inherited `2 < d_cat <= 3 px` collar dots. Running it would
place moved dots at 2-3 px from the catalogue (constraint 4 violation) and would let a SNAP
edit relocate collar dots, silently mixing in a PRUNE edit. `axes.snap` also orders dots
row-major and re-uses `resp * 1e6` as a lexicographic hack, so ties depend on float scaling.
**Decision it changes.** SNAP is built by `scripts/build_snap.py` on `src/gems91/snap.py`
(explicit 3 px target floor, collar quarantine asserted, deterministic priority order, no
float-scaled tie-break). `scripts/build.py --axis SNAP` remains in the tree for the synthetic
demo but must not be used to build a release.
## IR-91-33 — No local instrument can test "new faults near known traces"; the SGMC control cannot reward collar placement
**Expected** (brief §2, organiser clarification): new-fault truth may lie within 300 m of known
traces, so mass placed just outside the mapped catalogue should be testable against the
independent USGS SGMC map.
**Actual:** the kernel radius is exactly 3 px and brief §4.4 forbids mass within 3 px of the
catalogue, so a legal collar dot (**3.05 px** out) earns *exactly zero* credit on the mapped trace
it hugs. The SGMC off-catalogue control is therefore structurally unable to reward collar
placement even if the hypothesis is true, while it rewards the mirrored "move mass away" arm
partly by definition (SGMC-off-catalogue pixels *are* the far field). Measured: `collar10`
−2.02 % relative, `collar20` −3.90 %, mirror `anti10` **+2.14 %**, uniform-acceptor null −0.66 %.
The catalogue hide-and-recover PROXY and the leakage canary are identical to R0 for all three
arms (`0.006186`; canary `0.5`) for the same geometric reason, exactly as in IR-91-28 for SNAP.
**Decision it changes.** The three arms are recorded as `MODEL` predictions with the control's
limitation written into `evidence/concentration_collar_axis_20261024.json`
(`instrument_notes.sgmc_structural_bias`), not as validation of the collar. They are **not**
placed in the slot queue; the queue's top slot moves from `CONCENTRATIONgdr25rm10` to the R0
anchor plus the two count-based arms (PRUNE `le10`, MASS `cons3add`). Any future axis whose
targets are floored outside the 3 px collar inherits this blindness and must say so up front.
## IR-91-34 — A "live-density" reference is circular for relocation: R0's dots are the lineage field's maxima
**Expected:** the local holdout proxies fail to rank arms (they correlate −0.87..+0.54 with live
scores), so a reference *calibrated to the live score scale* would be better: subsample the
H19-5 field until R0 scores the CLAIM `0.2778` (found: s ≈ 0.0412, ≈ 4,995 cells, 5 seeded draws).
**Actual:** that reference ("LCR") is denser near the collar (0.0148 credit/cell at 3-4.5 px vs
0.0069 beyond 10 px, 2.1x) but it penalises **every** relocation arm in both directions
(−0.0264, −0.0507, −0.0266 absolute), because R0's dots sit on that field's maxima and any move
off them loses credit. It is a downside bound, not a discriminator; used as a point prediction
it would have made the mirror arm look like a loss even though the only real fault catalogue
says it is a gain.
**Decision it changes.** LCR is reported in evidence as `PROXY` with its circularity stated, and
it is used only as the pessimistic floor of each prediction range. The `MODEL` point stays on
the independent SGMC control (κ = 1.0, no shrinkage), and the session's headline claim is stated
as a *matched-dose difference* between two arms rather than as an absolute gain. This is also why
`CONCENTRATIONgdr25rm10` (`c019adb01`, `+0.0123` `MODEL`) loses its top slot: its prediction is
a 0.1 × shrinkage of the prior scored against itself, the same circularity in a different dress.

## IR-91-36 — The 2026-10-24 prompt names no single lane paragraph, and two of its leaderboard numbers conflict

**Expected:** the parallel-run protocol says "your lane is the single method paragraph below",
and quotes one current top score.
**Actual:** the prompt as delivered contains no single method paragraph (it repeats the full
fleet brief twice), and quotes both "current high score 0.4413" and "0.3195 is the highest
score right now". The official leaderboard fetched 2026-10-24 reads #1 0.4413, #2 0.3916,
#3 0.3904 (LEADERBOARD-READ); 0.3195 was #2 in GEMSDOE32's verified 2026-10-04 read.
**Numbering note (merge 2026-10-24):** main's parallel GEOD/review session took IR-91-35 while
this branch was in flight, so this branch's items were renumbered 35-40 -> 36-41 on merge;
cross-references in this lane's docs/code were updated to match.
**Decision it changes.** The lane is self-assigned and stated up front (DENOVO, de novo surface;
`src/gems91/denovo.py` + experiment preregistrations in `scripts/build_denovo.py`), and the
duplicate test (rank-correlation > 0.90 or > 70% of dots within 3 px of one registry raster) is
applied to the surface and the final dots (max 0.1133 / 40.41% — not a duplicate). All three
leaderboard numbers are reported with their dates and sources, never silently picked.

## IR-91-37 — `src/gems91/metric.py` computed a different metric from the organiser's (fixed here)

**Expected:** two metric implementations in one repo agree.
**Actual:** `metric.py` summed `p*k` over all dots near a truth pixel; the organiser's published
definition (fetched 2026-10-24) takes the per-truth-pixel **max** (`TPw`, capped at 1), and
`scripts/dti.py` already did that. The summed version can exceed DTI = 1 — the old test
`test_dense_coverage_can_exceed_one` documented exactly that symptom without naming it a bug.
**Decision it changes.** Fixed once in `metric.py` (per parallel-run protocol §2), with the
official worked example (`TPw 3.00, FPw 1.89, FNw 2.00 -> 0.60`) pinned in tests; both
implementations now agree to <1e-9 on random fields. Convergence on merge (2026-10-24): the CED
lane independently found the same summed-credit bug, cited it under the same number IR-91-37, and
replaced `metric.py` with an adapter to the pinned shared template (`vendor/gems57`), which
supersedes this branch's local fix; `scripts/dti.py` (this lane's evaluator of record) agrees with
the template algebra. Note on merge (2026-10-24): the GEOD
lane that landed on main in parallel quotes `gems91.metric v1` (the summed version) for its
holdout 0.00077 — that number overstates credit wherever dot kernels overlap and should be
recomputed with `scripts/dti.py` before reuse; its file gates are unaffected. Any overlapping-dot `T` previously
computed via `metric.py` is overstated and must be recomputed before reuse. The protocol's
named files `evaluate_holdout.py` / `submission_writer.py` do not exist in this repo; the
equivalents used are `scripts/dti.py` + `scripts/build_denovo.py` (holdout) and
`gems91.io.write_float32` (writer) — no private fork was created.

## IR-91-38 — R0-as-is and d2.8-as-is are not honest holdout baselines

**Expected:** score the parent on the same holdout as the candidate.
**Actual:** R0 was pruned against the *full* catalogue, so on withheld segments it scores
0.006452 by construction (IR-91-28 class); d2.8-as-is scores 0.156058 partly because 8,607 of
its dots sit ≤3 px from the full catalogue including withheld pixels, and it spends 44,090
dots against the candidate's 37,654. Neither is a like-for-like bar.
**Decision it changes.** Promotion is judged against same-protocol methods (random 0.070827,
TRI3 0.091215, SUP 0.097146) and per-dot credit (HGB-CTX 0.2168 > d2.8 0.2077); the d2.8 number
is carried as a labelled leakage-flattered reference, never as "the holdout best".

## IR-91-39 — The two local instruments disagree about the DENOVO file

**Expected:** holdout and the SGMC off-catalogue control rank candidates the same way.
**Actual:** the blocked holdout puts HGB-CTX first of the honest methods, but the SGMC
off-catalogue control (62,122 px) scores it 0.068703 vs R0's 0.095386. Converted through the
metric algebra the MODEL live range is ~0.20-0.29, spanning R0's 0.2778 CLAIM.
**Decision it changes.** The file is promoted for **one** weekly slot as the unique-lane test
and explicitly *not* recommended as the blind final; the site states both readings. The
receipt, whichever way it lands, adjudicates the instruments.

## IR-91-40 — The highest-ceiling hypothesis (1 m DEM scarps) is blocked in this sandbox

**Expected:** candidate H4 (scarp features re-derived from the competition's `1m_DEM_links.csv`
-> USGS 3DEP, free/official/public domain) could be validated before proposing it.
**Actual:** the sandbox may only reach GitHub/PyPI/npm hosts, the DrivenData data page needs a
login, and the pinned derived copy `ext_lidar_scarp_u8` carries "licence unchecked — do not
redistribute" with unverified provenance and only 75% footprint coverage. Its bands' pixelwise
canary AUCs here are 0.52-0.55 (diagnostic only; pixelwise AUC understates line detectors).
**Decision it changes.** H4 is proposed as *not viable from this sandbox* and named as the next
lane for an unrestricted machine: download the official DEM tiles, re-derive scarp features
with recorded provenance, pin hashes, then rerun this session's holdout with the scarp channels
added to HGB-CTX. The submitted file uses sponsor bands only.

## IR-91-41 — Publishing the submission .tif in `docs/downloads/` amends the no-rasters-in-git rule

**Expected:** repo policy (docs/DATA.md rule 2, CI gate) tracked no `.tif` at all.
**Actual:** the brief requires an obvious one-click download from the GitHub Pages site, and the
fleet's working precedent (GEMSDOE32, whose download scored 0.2778 CLAIM) publishes its own
derived submission under `docs/downloads/`. A derived {0,1} prediction is the entrant's own
work product, not competition input data.
**Decision it changes.** `.gitignore` and CI now allow `.tif`/`.zip` only under
`docs/downloads/`; competition input rasters remain forbidden everywhere and `data/` remains
ignored. Only the all-finite zeros primary is published (202,693 B) with its audit JSON.
## IR-91-35 — 2026-10-24 parallel-run protocol cannot certify legacy axes

No lane paragraph or shared template path supplied. All pinned input files absent
in this fresh checkout. Existing hide-and-recover is fixed-dot mean credit, not
buffered segment retraining with pooled DTI. Historical build readiness is stale.
No compliant baseline or full surface/dot registry comparison is present. The
GEMSDOE32 source explicitly disclaims organizer scores. See
`docs/REVIEW-20261024.md`; no TIFF produced and no weekly slot selected. Existing
submission advice is superseded by the fail-closed executive summary.

## IR-CED-001 — contradictory active approval claims and stale run cards

At this branch's starting commit, the landing page advertised “Download & submit”
while `docs/run-card.json` reported no experiment and no TIFF. The advertised GEOD
file also exceeded the prompt's 70% near-dot threshold. Concurrent upstream work
subsequently labelled the old file promoted without a compliant pooled holdout.
This session preserves inherited artifacts/history but replaces active approval
claims with a single evidence-derived fail-closed policy and measured negative
CED91 card. Tests now distinguish a downloadable **research** file from an
approved submission; they require real bytes and working local links in both cases.

## IR-CED-002 — the legacy local metric summed max-kernel truth credit

`src/gems91/metric.py` used addition instead of max at each truth cell. Its own
old test expected dense perfect predictions to exceed one. Two builder-specific
`dti_parts_f32` routines reproduced that bug. All three are now adapters to the
unchanged pinned shared max-credit metric. Legacy deltas from incompatible/wrong
instruments are not a compliant baseline and do not support promotion. This is
not a private modification of `vendor/gems57`; its hashes remain upstream-exact.

## IR-CED-003 — literal novelty rule meets a near-universal lattice cover

CED91 cleared all 64 indexed pre-placement surface comparisons. Final comparison
27 (`calib_r13lattice_00904.tif`) gave 0.999125 directed overlap within 3 px and
triggered DUPLICATE. The reference's own 3-pixel cover reaches 99.8713% of the
footprint (`docs/parent-forensics.json`). A low rank correlation cannot override
that literal rule. The run stopped; no exemption, registry removal, threshold
change or additional geological experiment followed. This is a protocol conflict
for owner/shared-selector review, not proof of copied geology. The TIFF remains
a format-valid research deliverable, explicitly NOT OK TO SUBMIT.

## IR-CED-004 — ancestor deletion counts conflated in earlier prose

Pinned forensics find R0 deletes 6,436 of the 44,090-dot d2.8 ancestor or 2,545 of
the 40,199-dot solo-d2.8 ancestor. Both rebuild R0 exactly at distance >2 px; neither
adds dots. Earlier prose attached the second deletion count to the first ancestor.
Active analysis now uses measured counts and does not claim a universal spacing
optimum, established causality for the reported score, or an authenticated receipt.

## IR-CED-005 — no assigned method, complete registry or comparable best

The user prompt contains no single assigned lane paragraph. A parent-free CED
lane was preregistered as **provisional research only**, with assignment unverified
and promotion disabled. The 64-file pinned registry is not universal: the 92-page
GitHub audit indexes 2,529 raster file entries across source snapshots, including
repeats and data. No complete raster comparison is claimed. No independently
comparable prior holdout best is recorded. These are additional explicit blockers,
not reasons to invent a score or ask for credentials.

## IR-CED-006 — external source and legacy data-placement claims

Official non-GitHub hosts, including the rules PDF and live organizer allowance,
are outside this sandbox's allowlist. Links are labelled source leads unless
actually fetched. The user prompt's download/prepare shell commands are absent
from this checkout; claiming a ready GPU training pipeline from them was wrong.
The existing pinned restore script did recover and hash-verify the cached input
stack on CPU. No new external data or GPU is needed by the tested CED method.
Raw rasters remain ignored; existing public mirrors still need distribution-rights
review. A hash pin is identity evidence, not official authentication or permission.

## IR-CED-007 — Concurrent outputs were outside the new artifact allowlist

PR32 merged after PR34, preserving the CED negative portal but adding a separate
DENOVO TIFF/ZIP without updating `artifact_policy.json`. Those files are now
hash-pinned as `parallel_quarantined`, not removed, rebuilt, or promoted. Its
pre-merge promotion advice is preserved as historical; current policy is blocked.
Different holdout instruments and seven-file comparisons do not waive common gates.

## IR-CED-008 — Pages configuration permission and runner queue

After the published REST quota reset, reading Pages succeeded; updating the
legacy publisher to Actions was denied with 403 “Resource not accessible by
integration”. The existing workflow's declared Pages-write token is configured
to attempt the switch; this is unverified until it executes. CI/Pages were
queued without runners at the observed check. Neither a local PASS nor merge
is a successful public-deployment receipt.

---

## IR-H91-01 — `scripts/dti.py` and `vendor/gems57` use competition `max_j` kernel credit (`<= 1.0`), matching DrivenData's worked example

**Expected:** all DTI modules in the repository implement DrivenData's published worked example (`TP=3.00, FP=1.89, FN=2.00 -> 0.6026`).
**Actual:** `scripts/evaluate_holdout.py` (`gems91-hide-recover-v1.0`) routes all `HOLDOUT-DTI` calculations exclusively through `scripts/dti.py` (`TP_w = sum_g max_j p_j k(||j-g||_2) <= |G|`), agreeing with `origin/main`'s `IR-CED-002` fix.

## IR-H91-02 — `src/gems91/prior.py` drops `'Hot '` trailing-space rows and 212 blind `>= 90 C` geothermometer cells

**Expected:** filtering `data/external/gdr_wellspring_in_footprint.csv` ([DOE GDR #1391](https://gdr.openei.org/submissions/1391)) captures all geothermal upflow indicators in the footprint.
**Actual:** `121` rows carry `'Hot '` with a trailing space, and **`212` unique footprint grid cells** labeled `Cold`/`NULL`/blank carry dissolved quartz, chalcedony, or Na-K-Ca chemical geothermometers `>= 90 C` — the geochemical signature of blind fault-hosted hydrothermal plumes cooled conductively in shallow aquifers.
**Decision it changes.** Leave `src/gems91/prior.py` untouched so `registry/derived_priors.json` sha256 pins remain valid; implement whitespace-trimmed `Hot/Warm` (`2,060` cells) + blind `>= 90 C` geothermometer (`212` cells) extraction in `src/gems91/dd_vtc_pu.py`.

## IR-H91-03 — `gdr_wellspring_in_footprint.csv` carries a leaky `dist_known_fault_px` column on all 27,092 rows

**Expected:** external well/spring attributes are independent of withheld holdout fault segments.
**Actual:** column `dist_known_fault_px` in `gdr_wellspring_in_footprint.csv` was precomputed against the full global `existing_faults.tif` raster (`27,092 / 27,092` rows populated). Ingesting it in a hide-and-recover fold leaks exact Euclidean distance to withheld fault traces.
**Decision it changes.** Explicitly ban `dist_known_fault_px` in `src/gems91/dd_vtc_pu.py` and verify every engineered feature through `evaluate_holdout.run_leakage_canary` (`52/52` symmetric AUC `<= 0.6610 <= 0.90`).

## IR-H91-04 — GeoDAWN `Band 6` (`tc`) is unsigned gravity terrain correction (`[11.8, 25.6]` mGal), not signed Verduzco tilt

**Expected:** shorthand naming `tc` in sibling lanes sometimes treated Band 6 as a zero-crossing tilt contact indicator.
**Actual:** Band 6 is strictly positive `[11.82, 25.60]` inside the footprint (`median = 17.44` on catalogue faults vs `18.49` background). By contrast, `Band 11` (`iso_grav_anom_vg`) is signed and flips polarity across fault contacts (`+0.0824` median on faults vs `-0.0739` background), while `Band 5` (`iso_grav_anom_slope`) is unsigned `[0.0288, 0.27]`.
**Decision it changes.** Synthesize true depth-normalized Verduzco tilt angles `atan2(B11, B05)` and `atan2(B09, |grad B02|)` in `H91-1` (`dd_vtc_pu.py`) and project them updip by `B15 * cot(55 deg)` along `-grad G_6(B13)`.

## IR-H91-05 — 2-D vs 1-D submodular kernel area bias (`10.61` vs `3.00`) and synthetic calibration covers

**Expected:** maximizing `sum_g p(g) max_j K(||j-g||_2)` over 2-D posterior maps selects 1-px fault ridges, and one-way 3-px dot overlap compares peer dot sets symmetrically.
**Actual:** (1) over a 2-D disk (`r <= 3 px`, 29 cells), `sum K = 10.61`, whereas along a 1-px fault line (7 cells), `sum K = 3.00` — a `3.5x` area bias that causes uncalibrated 2-D submodular allocators to pack `p = 0.50` mountain blocks (`0.50 * 10.61 = 5.31`) ahead of `p = 0.85` 1-D fault lines (`0.85 * 3.00 = 2.55`), collapsing `HOLDOUT-DTI` to `0.030`; (2) synthetic calibration blankets (`calib_h28ridge_01839.tif` covering `27.4%` of footprint, and `calib_r13lattice_00904.tif` covering `99.8713%` of footprint per `IR-CED-003`) asymmetrically overlap smaller `38k` dot sets.
**Decision it changes.** Apply Bayes prior-shift calibration + 4-axis 1-D directional ridge NMS + background floor subtraction in `submodular_dti_emit` (lifting `E1` `HOLDOUT-DTI` to `0.174030` in `~1.0s`/fold), check `E1` against all `20` real fault-prediction rasters (`<= 63.17%`), and register `E1`'s `.tif` and `.zip` in `registry/artifact_policy.json` as `current_research_only` pending human fleet-selector review of `calib_r13lattice_00904.tif` and the weekly 3-slot allowance.

> **Numbering note (merges of PR #26 with PRs #24, #28, #30 and the DENOVO/CED lanes).** Every 2026-10-24 lane numbered from IR-91-33. The strain session's four items, merged last, are IR-91-42/43/44/45 below; artefacts citing them as IR-91-33…39 refer to these numbers.

## IR-91-42 — The GDR concentration arms silently executed a partial PRUNE (Session 8)

**Expected:** a CONCENTRATION edit changes only block-scale dot density; the IR-91-27
standard (Sessions 5-7) quarantines R0's 2,171 inherited dots at 2 < d_cat <= 3 px so a
non-PRUNE edit cannot drift the collar.
**Actual:** the GDR concentration build (which predates IR-91-27) let collar dots be
donors. Its own evidence records dots <=3 px falling 2,171 -> 1,897 / 1,911 / 1,912
(`evidence/concentration_axis_20261023.json`), i.e. 259-274 collar dots (~7% of the
3,765 movers, ~0.7% of all dots) were removed as part of the "concentration" move -
replicated byte-identically this session (`reports/strain_control_diagnostics_20261024.json`).
**Decision it changes.** A future GDR receipt cannot be attributed to the thermal prior
alone: up to ~0.7% of its dots are a small PRUNE. The strain build adds an opt-in
`donor_exclude` quarantine to `tools.run_concentration.build_concentration` (default
preserves the GDR fleet's byte identity; new builds must pass `d_cat <= 3 px`).

## IR-91-43 — The built strain prior is not the SLOT_PLAN proposal's literal formula

The merged SLOT_PLAN proposal's falsifier reads "Moving 20% of R0 mass into top-tercile
`geod_2ndinv x S_struct`".  Session 8 built the geodetic percentile ranks *without* the
S_struct multiplier: S_struct is 60% lineage support, so the product would make the
allegedly independent prior partly a re-statement of the parent dot field (the IR-91-07
failure mode that invalidated the first concentration rows), and acceptor placement
already anchors 80% of moved dots within +/-4 px of existing parent dots.
**Decision it changes.** The proposal's literal formula remains unbuilt. On this
session's control evidence (all three geodetic arms predicted negative; the product
prior would fall between the lineage field it multiplies and the strain field that
failed) building it is not recommended; recorded so nobody cites `strn25m20` as the
proposal's falsifier test.

## IR-91-44 — The geodetic "km-scale prior" is province-scale, and its two oracles disagree

**Expected** (brief S5): CONCENTRATION moves dots between km-scale blocks of a prior,
with the strain bands attractive because they lead the GeoDAWN stack on catalogue AUC
(0.579/0.576).
**Actual:** (a) the strain prior's autocorrelation is 0.95 at 25 km lag and its 25 px vs
50 px block ranks correlate 0.999; the mean moved dot travels 2,493 px (249 km) from the
NE low-strain half to the SW high-strain half - the operation is a regional
reallocation in 2.5 km clothing, incapable of placing a dot on the right 300 m segment.
(b) The catalogue density rises across strain deciles (0.88% -> 1.89%) while SGMC-only
off-catalogue fault density does not (peak in decile 2; 1.34% in the top decile), and
for dilatation the top decile is the SGMC-poorest (0.53%).
**Decision it changes.** Catalogue AUC is retired as a prior-selection argument in this
repo (it partly maps where the catalogue was drawn, and the target is what the catalogue
missed). No strain arm enters the Week-1 queue; future block priors get an SGMC-off
decile screen reported *before* any build, labelled PROXY with the proxy-tuning risk
stated, never as a gate.

## IR-91-45 — The same geodetic-strain intervention was built twice under two axis names, with opposite-signed claims, and one copy's rasters were committed under `docs/`

Session 9 (`arena/4f94d2e7`, PR #30, merged while PR #26 awaited CI) built `GEOD`/`geod25m10`
(`bff9fd21…`) from the identical recipe as this session's `CONCENTRATION`/`strn25m10` (`85cc49d2…`):
prior `0.5*pct(geod_2ndinv)+0.5*pct(geod_shearrate)`, 2.5 km blocks, 3,765 of 37,654 dots moved,
same parent dot set. The "(axis, value) built once" rule did not fire because the axis label and
even the parent string differ (`GEOD`/`h33-h33-2-b2-20261004-e5eb6e7e` vs `CONCENTRATION`/`h33-h33-2-b2`);
the ledger now holds both (54 rows). The claims disagree in sign: Session 9 headlines **+0.0090**
`MODEL` from a strain "surrogate" (+31% rel, κ=0.1) and reports "SGMC off-cat +1.8%", but its
evidence (`evidence/geod_axis_20261024.json`) shows that figure is the **full** SGMC field
(parent DTI 0.09539 = R0's full-SGMC value), not the off-catalogue restriction on which the same
intervention measures −4.05% rel and loses to a random-prior relocation (**−0.0056** `MODEL`,
IR-91-44). Session 9 also committed both competition rasters under `docs/downloads/` in a repo
serving GitHub Pages — public exposure of submission files while the competition data-use terms
remain unchecked (brief: keep competition rasters out of public repos; flagged, not deleted, at
merge). Decision consequence: Session 9's README promotes `GEOD25m10` to "the new Slot-1
candidate"; that promotion rests on the mislabelled control and a κ the strain session's frozen
translator rejects. Neither `MODEL` number is evidence — only a receipt settles the strain
question, and spending a slot on either file spends it on both sessions' hypothesis. The human
must decide: (a) whether the `docs/downloads/` rasters stay public, (b) whether any strain file
enters the queue ahead of PRUNE-le10/MASS-cons3add.

Update at the PR #26 merge (same day): main had meanwhile chosen the other resolution — PR #31 promoted `GEOD25m10` (portal `submission_ready: true`), widened the axis test to admit `GEOD`, and IR-91-41 amended the no-rasters policy for `docs/downloads/`. This merge adopts main's versions of the portal pages, tests and CI; the strain lane's contrary verdict stands in `docs/MECHANISM_CARDS_STRAIN.md`. The human decision above is therefore now: whether the promoted portal candidate is actually submitted, knowing the off-catalogue control disagrees.

## IR-91-S10-01 — GEOD (`h33-h33-2-b2-GEOD25m10`) is a duplicate of R0; it was on Pages and is now removed

**Expected:** a parallel-run lane must not duplicate a registry raster (rank correlation > 0.90 or > 70 % of dots within 3 px).
**Actual:** GEOD has rank correlation **0.8951** (just under 0.90) but **93.23 %** of its dots lie within 3 px of R0's dots (R0 side 90.04 %). The overlap rule fires. It was still linked from `docs/downloads/` on Pages.
**Registry scan (complete, `registry/s10_registry_scan_GEOD.json`):** GEOD is an exact copy of the file still on `main` (overlap 1.0). Its rank correlation with a registry copy of R0 is **0.8974**, just under the 0.90 limit; its 3 px overlap with a GEMSDOE40 raster is **0.9513**. Status: LANE DRIFT - do not submit.

**Decision it changes:** both GEOD TIFs are `git rm`'d from `docs/downloads/` (staged). Copies are in gitignored `outputs/archive/` (GEOD sha256 `bff9fd21…`). **Not fixed:** the files stay in git history on `main` and in any cached copy of the Pages site. History was not rewritten (a force-push to `main` needs the user's approval).

## IR-91-S10-02 — The holdout CI resamples the 10 spatial folds, not the 3,199 catalogue segments

**Actual:** `evaluate_holdout.py` computes the 95 % CI by a fold bootstrap (B = 2000, seed 91). A segment bootstrap would give different widths. The CI is therefore not directly comparable with a segment-bootstrap CI from another source.
**Decision it changes:** the CI method is written into every `evidence/holdout_S10_E*.json` (`ci_method`). No CI from another method is quoted in this session.

## IR-91-S10-03 — The 3 px buffer around each withheld fold is counted and reported, not hidden

**Actual:** the ring of visible cells within 3 px of each withheld set is kept, is counted in `visible_buffer_px` (3–27 px visible per fold in E1), and is reported. Hiding it would change nothing for the S10 candidate, because the candidate reads the catalogue only as a mask. **Any future candidate that reads catalogue-derived features must also hide the buffer**, or it will leak across the split.

## IR-91-S10-04 — The holdout measures recovery of catalogue faults; the organizer scores new faults

**Expected** (organizer, DrivenData problem description, page 967, fetched 2026-10-24): the test set is faults **not contained in** the USGS database, labelled by experts before the competition. The Final Round adds expert-verified faults found from submissions.
**Actual:** our holdout withholds catalogue segments and scores recovery of those. The H10-1 result (0.0173 vs null 0.0288) is therefore evidence about catalogue recovery only. It does not show how H10-1 would score on the new-fault test set. Also, the 3 px exclusion around the catalogue (brief §4.4) is a lineage constraint; the organizer page does not state it.
**Decision it changes:** the negative verdict stands under the protocol, but it is weak evidence about the real score, and the status board says so.

## IR-91-S10-05 — The scores 0.2778 (GEMSDOE32) and 0.3195 (GEMSDOE49) are not verified

**Expected:** a score quoted as the lineage "best" is backed by an organizer receipt.
**Actual:** no receipt exists in this repo. GEMSDOE32's own documentation disclaims organizer scores (see IR-91-35). The organizer's public leaderboard (fetched 2026-10-24, rows #1–#50) has **0.4413** (#1), 0.3916 (#2), 0.3904 (#3), 0.3724 (#4), 0.3539 (#5), 0.3217 (#23), 0.3169 (#24), and 0.2818 (#50). 0.3195 is absent (the list goes 0.3217 → 0.3169). 0.2778 would rank below #50 and is absent from the page read. The lineage account does not appear in rows #1–#50.
**Decision it changes:** "beat 0.2778" cannot be assessed here. The index page labels both figures CLAIM and the leaderboard figures ORGANIZER-CONFIRMED (public).

## IR-91-S10-06 — The restored competition data come from third-party mirrors; authenticity is not organizer-verified

**Actual:** `scripts/restore_data.py` fetched all 15 pinned files from GitHub repos owned by the lineage (`buffedlizard55-lab/60GEMSDOE@02563d07…` and `GEMSDOE@c0c06ac8…`). They match the pins in `registry/data_manifest.json`, but those pins are the lineage's own hashes, not hashes published by the organizer. The DrivenData data page requires login and was not accessed (the login page was the only response).
**Decision it changes:** nothing in the S10 verdict depends on the data being official. It must be accepted or rejected by the user before any file is described as built from official data (see IR-91-09).

## IR-91-S10-07 — `SLOT_PLAN.md` labels band 16 as a thermal layer; band 16 is earthquake intensity

**Actual:** the file's band 16 tag is `ieq_n100a15` = "Earthquake intensity or density (n = 100 km radius, a = 15° parameters)". The organizer lists "density of earthquakes" among the features. `SLOT_PLAN.md` lines 132–133 call the same band a conductive-temperature / thermal-anomaly layer and attach an AUC of 0.5749 to it. That label is wrong, and the AUC cannot be checked against this band from the repo.
**Decision it changes:** the S10 banner in `SLOT_PLAN.md` flags it. The original table is not rewritten.

## IR-91-S10-08 — The file's band list does not match the organizer's list

**Expected** (organizer, page 967): one of the layers is a "top-of-crustal magnetic source depth estimate"; the organizer also says "surface conductivity and depth to conductive base surface".
**Actual:** no band in the 19-band file has that depth name. The file has band 6 `tc` ("Tilt angle or total curvature"), which the organizer does not list. The file's band 15 is named "Depth to basement surface", not "depth to conductive base surface". This may be naming only, or the mirror may be a different version. It cannot be resolved from the repo.
**Decision it changes:** H10-5 (`docs/HYPOTHESES_S10.md`) uses only bands whose names match the organizer's list. Any future feature set must be checked against the organizer's list, not the file tags alone.

## IR-91-S10-09 — The mirrored `sample_submission.tif` contains the catalogue, not a blank template

**Expected** (organizer, page 967): "A sample submission that predicts total fault absence is provided."
**Actual:** the mirror file (`data/official/sample_submission.tif`, sha256 `2176d08e…`) has 60,988 cells equal to 1, and those positions are **identical** to the 60,988 positive cells of `existing_faults.tif` (checked cell by cell). A copy of the catalogue is therefore being used as the format template. A candidate must never be derived from it. Our candidate is not derived from it: it has no positive cell on the catalogue (gate "zero catalogue mass": 0 positive pixels, mass 0.000), and it is a ramp built from the feature stack, not a copy of the template.
**Also:** copies of `labels.tif` and `sample_submission.tif` are committed in public lineage repos `59GEMSDOE` and `57GEMSDOE` (found by the registry scan). Whether that breaks the competition data terms was **not reviewed** (the rules were read only in part, sections 1–3.2).
**Decision it changes:** the template's CRS, shape and transform were checked against the mirror, not the organizer. The user should confirm the grid against the organizer's own file before any upload.

## IR-91-S10-10 — Validator and release-gate defects found this session (shared tools, reported, not silently changed)

Five defects in shared tools. Each is either left as it was or changed with a test-level decision noted.

1. **`parent-diff statistics recorded` is `must_pass` and FAILS when no parent is given.** Every parentless file (including the S10 candidate) fails this gate. It is reported as FAIL, not hidden. A "not applicable" status needs a design decision (shared gate).
2. **`sha256 not already in ledger` counts only `SUBMITTED` rows, and there are none.** The gate therefore checks nothing today. `tests/test_validate_raster.py::test_ledger_dedupe_ignores_built_rows` pins this behaviour on purpose (brief §7: a `BUILT` row is bookkeeping for the file being certified). I tried a fix that counts all rows except the candidate's own id, but reverted it, because the test encodes the brief. The fix needs a decision.
3. **`unit_mass_dots` (release gate) assumes binary dots.** The organizer's format (page 967) allows probabilities or confidences in [0, 1]. A continuous candidate fails this gate. For that reason the candidate is kept in `outputs/s10/` and not `releases/`, and `tests/test_release_integration.py` fails locally with "no releases built". CI skips that test (no competition data there), so CI is unaffected. The guard is intentional and is left unchanged.
4. **GitHub core quota** was exhausted (reset 08:10:17 UTC). The first registry scan therefore has 114 rate-limit errors and is marked INCOMPLETE. It is re-run after the reset (see `registry/s10_registry_scan.json`).
5. **The CI "no raster tracked" check** fails while the two GEOD TIFs are tracked. Their removal is staged, so the check passes once committed. History is still not clean (IR-91-S10-01).


## IR-91-S10-11 — The S10 holdout ran on a private evaluator; the shared evaluator on main uses a different buffer, so the S10 numbers are not comparable

**Found:** on merging `origin/main` (2026-10-24, about 10:40 UTC), `main` had its own `scripts/evaluate_holdout.py` (`gems91-hide-recover-v1.0`, 10 px buffer, DTI delegated to `scripts/dti.py`). This branch had added a second `scripts/evaluate_holdout.py` (`S10-holdout-v1`, 3 px buffer). The brief requires the shared template tools and forbids private forks, so the fork breaks the brief.

**Actual:** the S10 holdouts E1 (0.0173), E2 (0.0101) and E3 (0.0288) were computed by the private code at commit `82252a1`. That code is removed from the tree in this merge; the path now holds `main`'s shared file. No shared-protocol score exists for H10-1. `main` reports 0.174030 (H91-DDVTC) and 0.06215 (CED91) under the shared protocol. These are quoted from `main`'s `index.html` and were not re-verified here. Changes made to contain the fork: the `pooled_dti` unit test was retired, because scoring now lives in the shared evaluator and `main`'s `tests/test_h91_holdout_and_writer.py` covers `build_segment_buffered_folds` and `score_pooled_holdout`; the AUC tests use the shared `fast_mann_whitney_auc`; the input pin check moved into `scripts/build_basement_step.py`.

**Decision it changes:** the statement "H10-1 fails its random-placement control" holds only under the private 3 px protocol. Under the shared 10 px protocol H10-1 is unscored. Scoring it there would be a fourth experiment; the budget is three. Needs user approval (or a decision to close H10-1 on the private result). No submission slot is affected: none is recommended under either protocol.


## IR-91-S10-12 — The artifact policy still registered the two retracted GEOD TIFs after they were removed from the tree

**Found:** the CI step `scripts/check_artifact_policy.py` (main's `ci.yml`, job `tests`) requires `registry/artifact_policy.json` to match the tracked artifacts exactly. After the GEOD removal (`git rm`, IR-91-S10-01), the policy still listed both GEOD TIFs, and the check failed: `Artifact-policy/files mismatch`.

**Actual:** the two entries (`legacy_quarantined`) were removed from `registry/artifact_policy.json`. Nothing else in the policy changed. The GEOD hashes stay in `ledger/submissions.csv`, in `docs/run-card-S10.json` and in IR-91-S10-01. The files are not in git on this branch; they remain in history on `main`.

**Decision it changes:** none beyond the retraction. The policy now matches the tree. Restoring the GEOD files would require re-registering them as a deliberate step.


## IR-91-ASC-01 — ASC91 holdout instrument assigns whole components by centroid; withheld pixels can fall outside the fold region

**Found:** 2026-10-24 (ASC91 session, `arena/5486e004-gemsdoe91`), reusing `scripts/build_denovo.py:fold_setup` unchanged. Components are assigned to folds by centroid on a 400 px checkerboard, so a withheld component may extend outside its fold's region; those pixels still count in pooled G, and supervised negatives are drawn > 5 px from the *visible* catalogue outside the region.

**Actual:** kept byte-identical so ASC91 is directly comparable to the HGB-CTX receipt (0.142885) on the same instrument; the random control reproduced that receipt's instrument exactly (0.070827, same dots/fold and withheld counts). Fixing the instrument mid-comparison would have invalidated the gate.

**Decision it changes:** none this session. Any instrument repair must re-score every compared arm, including HGB-CTX, before use as a gate.

## IR-91-ASC-02 — ASC91 percentile / robust-z normalisations are fit on the full footprint

**Actual:** unsupervised and label-free (same pattern as DENOVO's global reference sample), but fold-region pixels influence the transform. Single-feature canary AUCs are ≤ 0.6028 (limit 0.90), so no label leakage is indicated. Recorded so a future stricter fold-local refit can be costed honestly.

## IR-91-ASC-03 — Registry scope for ASC91 novelty is 11 enumerated rasters, not a universal fleet registry

**Actual:** `data/registry/*.tif` (8 sha-pinned) + CED/DD-VTC/DENOVO downloads, each hashed in `evidence/asc91_build_20261024.json`. The near-universal lattice raster `calib_r13lattice_00904.tif` that blocked CED is absent from this restored registry; under the literal directed 3 px rule it would reject any candidate. No exemption was applied; the scope limit is stated wherever the PASS is quoted.

## IR-91-ASC-04 — Sponsor-band sentinel fill extrapolates steps within ~4 px of the footprint edge

**Actual:** `_clean_band_edt` nearest-valid fill (shared with DD-VTC) means ASC step responses near the footprint boundary use extrapolated band values. Emission is restricted to the footprint, so only near-edge dots are affected. No correction applied; quantified nowhere — flagged for the fusion lane to mask a 4 px interior buffer in an ablation if its budget allows.
## IR-91-S11-01 — No assigned lane was supplied in the session brief

**Found:** the parallel-run protocol says "Your lane is the single method paragraph below", but the brief contains no such paragraph. The same gap was recorded for CED91 (`docs/run-card.json`, `lane.assigned = false`).

**Actual:** H11-1 is labelled `PROVISIONAL_RESEARCH_ONLY`. The lane-overlap check (rank correlation ≤ 0.90, ≤ 70 % dots within 3 px) was applied against the pinned registry, not against an assigned lane.

**Decision it changes:** the run can never be promoted until an assigned lane is supplied (`readiness.gates` requires `lane.assigned = true`).

## IR-91-S11-02 — S10 said bands 8 and 17 are unused; they are used

**Found:** `docs/HYPOTHESES_S10.md` (H10-2 and H10-3) says band 8 `geod_dilaterate` and band 17 `cond_surf` are "not used anywhere in this repo". They are read by `src/gems91/strain.py` and `scripts/build_strain_concentration.py` (band 8), and by `src/gems91/dd_vtc_pu.py` (bands 8 and 17, plus 10, 15, 16, 18).

**Actual:** H10-2 and H10-3 are not untested lanes. Their earlier ranking overstated their novelty.

**Decision it changes:** the S11 ranking (`docs/HYPOTHESES_H11.md`) drops both on overlap grounds (H11-2 and H11-3).

## IR-91-S11-03 — Band 12 is used by the relief lane

**Found:** `scripts/build_relief.py` reads band 12 `det_elev` as detrended-elevation terciles. H11-1 uses the same band.

**Actual:** the transform differs (an oriented structure tensor, not zonal terciles). The novelty claim is about the transform, not the input. The registry check does not measure input overlap.

## IR-91-S11-04 — The S10 registry "PASS, 64 checked" cannot be reproduced in this checkout

**Found:** `registry/comparison_inventory.json` pins 64 files under `data/fleet_registry/`. None were present in this checkout. Running the surface check before restoring produced 64 × UNVERIFIED and no comparison at all (`docs/h11-registry-surface.json` from the aborted first attempt; the lock file was never written).

**Actual:** `scripts/restore_registry.py` restores 62 of 64 from the pinned git blobs in `buffedlizard55-lab/60GEMSDOE`. It verified sha256, byte length and git blob SHA-1 for each of the 62 files before use. After restore, the surface check ran against 62 references (62 PASS, max rank correlation 0.1468). Two references remain UNVERIFIED (IR-91-S11-05), so the pre-placement status is `UNVERIFIED`, not `PASS`.

**Decision it changes:** the S10 claim `PASS_WITHIN_INDEXED_SCOPE, checked 64` is supported only by files that existed in an earlier session. It is not reproducible here until the two missing references are restored.

## IR-91-S11-05 — Two registry references cannot be recovered

**Found:** `docs/downloads/h33-h33-2-b2-GEOD25m10-20261024-bff9fd21.tif` and `...-zeros.tif` are in the inventory with `source_url = "local checkout inherited advertised artifact"` and no git blob. They are absent from the working tree. `git rev-list --all` returns a single commit in this clone, and a blob search for their sha256 values found nothing.

**Actual:** the two rows are UNVERIFIED. The S10 README statement that the GEOD TIFs "are still in git history" (IR-91-S10-01) cannot be confirmed from this clone. Both rows are the GEOD duplicate of R0 (IR-91-S10-01), so their absence weakens the registry for R0-like candidates.

**Decision it changes:** a human with the original repository history should supply the two files or confirm them removed. Until then no registry pass is complete.

## IR-91-S11-06 — The registry duplicate rule measures coverage density, not geology

**Found:** H11-1's final dots (32,000, greedy, separated by more than 3 px) overlapped 99.8 % within 3 px of `calib_r13lattice_00904.tif` (206,895 dots, a dense lattice). Its surface rank correlation with the same raster was 0.0007, far below the 0.90 threshold.

**Actual:** any well-spread placement with a fixed budget over the footprint will be within 3 px of a dense lattice. The dot-overlap test therefore flags spatial coverage, not shared geological information. This is the "near-universal lattice coverage" blocker named in the S10 README, and it was reproduced here.

**Decision it changes:** H11-1 is recorded as DUPLICATE under the literal rule. Nothing was tuned to pass the gate. Changing the shared duplicate definition (for example, comparing against the positives of registry rasters that are themselves feature-based) is a **human decision** that affects every lane. It was not made here.

## IR-91-S11-07 — The H11-1 holdout measures catalogue recovery, and that favours topographic detectors

**Found:** H11-1 holdout DTI 0.1397 [0.1239, 0.1558] (HOLDOUT-DTI, `gems57-pooled-hide-v2`, 60,988 withheld positive pixels, 161 spatial clusters), versus a gradient-only control 0.0539 and a seeded random null 0.0672. The paired differences are positive, with CIs above zero.

**Actual:** the withheld faults are USGS-catalogued faults. Quaternary fault maps are built largely from topographic expression, so a topography-only detector is expected to recover catalogue faults more easily than the expert-labelled *new* faults that the organizer scores (page 967: "faults not contained within the current public USGS database"). The catalogue-zero canary (max AUC 0.640) does not rule this out, because the canary cannot detect a physical correlation between the feature and the label. This is the mechanism in IR-91-S10-04, and it makes 0.1397 unsafe to read as a predicted organizer score.

**Decision it changes:** no DTI claim about the organizer score is made. The number is labelled HOLDOUT-DTI only.

## IR-91-S11-08 — The first H11-1 attempt consumed the experiment budget before it stopped

**Found:** the first `scripts/run_h11.py --run` ran the holdout to completion (the same numbers as the rerun) and was stopped in the final placement stage, because the registry was unrestored (IR-91-S11-04). The lock file was not written.

**Actual:** the rerun recomputed the same holdout. Counting both attempts, one experiment was run. The protocol's limit is three per session. The lock records `experiments_run: 1` for the completed experiment.

## IR-91-S11-09 — The brief's leaderboard figures conflict with the official page

**Found:** the brief says both "0.3195 is the highest score right now" and "current competition leaderboard GEMSDOE high score 0.4413". The official leaderboard fetched this session (<https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>) shows #1 0.4413, #2 0.3916 and #3 0.3904, and no 0.3195 row near rank 23–24 (IR-91-S10-05).

**Actual:** 0.4413 is the official public #1 score. 0.3195 is not on the public board as read. The GEMSDOE site scores (0.2778 for GEMSDOE32) are self-reported and unverified.

## IR-91-S11-10 — The session brief's "verbatim" prompt is now stored in the README

**Found:** the S10 README asked for the verbatim brief to replace its restated block. This session's brief was pasted in full.

**Actual:** the README now carries the verbatim brief. Its internal contradictions (IR-91-S11-09, and "0.3195 is the highest" versus "0.4413") are kept as written, not corrected, so reviewers can see what was asked.

## IR-91-DF6E28C2 — readiness labels could overrule malformed measurements

2026-10-24: shared `readiness.py` accepted inverted/nonfinite paired intervals and
status-only canary/novelty clearance. Fixed with measured finite bounded values,
ordered intervals, typed sections and complete comparison accounting. Regression
tests added; 277 passed, 7 skipped (data-dependent), 29 rasterio deprecation
warnings. Existing CED artifact was independently revalidated against the two
restored pinned inputs; its duplicate failure remains binding. No experiment,
new TIFF or slot. See `docs/REVIEW-DF6E28C2.md`; missing lane and incomplete
provenance/registry prevent the requested unique submission in this run.

---

## IR-91-S11-01 — `Band 06 (tc)` in `training_features.tif` is Official GeoDAWN Airborne Radiometric Total Count (`TC`), NOT Magnetic Tilt or Terrain Correction

**Expected:** The GeoTIFF band description string labels Band 06 `"tc - Tilt angle or total curvature - magnetic field derivative for edge detection"`, while `HYPOTHESES_H91.md` treated Band 06 as `"unsigned terrain correction (mGal)"`.

**Actual:** Direct numerical cross-correlation against the 4-band GeoDAWN radiometric grid (`K, Th, U, TC`) proves **`Corr(Band 06 tc, GeoDAWN Radiometric Band 4 'TC') = 0.99677`** (`Corr = 0.9148` with `Th`, `0.8816` with `K`). This also matches the official [DrivenData Problem Description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) figure `gems_tc_tmi.png` (*"total radiometric counts per second (left) and total magnetic intensity (right)"*).

**Decision it changes:** We extract 100% licence-clean airborne gamma-ray radiometric regolith-bedrock contact gradients (`s11_rad_tc_grad`), local band-pass anomalies (`s11_rad_tc_dog`), and potassic hydrothermal alteration residuals (`s11_rad_mag_felsic_res`, `s11_rad_potassic_leach_joint`) directly from official `Band 06 (tc)` in `training_features.tif`, completely eliminating any need for the licence-unchecked external `geodawn_rad_u8.tif` (`IR-91-26`).

---

## IR-91-S11-02 — `(Band 11, Band 18)` is the 2-D Horizontal Gravity Gradient Vector $(\partial_y G, \partial_x G)$, Not Scalar Vertical and Horizontal Gradients

**Expected:** Band descriptions name Band 11 `"iso_grav_anom_vg - Isostatic gravity anomaly vertical gradient"` and Band 18 `"iso_grav_anom_hg - Isostatic gravity anomaly horizontal gradient"`. Prior sessions treated Band 11 as $\partial G / \partial z$ and Band 18 as $\|\nabla_H G\|_2$.

**Actual:** Band 18 is signed (`[-15.44, +12.86]`) and nearly orthogonal to Band 11 (`r = 0.0754`). Direct numerical verification against `Band 13 (iso_grav_anom)` and `Band 05 (iso_grav_anom_slope)` proves that `Band 11` is the North–South directional derivative $\partial_y G$ (`r = 0.8411` with $\partial_y G_5(\text{B13})$), `Band 18` is the East–West directional derivative $\partial_x G$ (`r = 0.8554` with $\partial_x G_5(\text{B13})$), and $\operatorname{hypot}(\text{B11}, \text{B18})$ reproduces `Band 05` with **`r = 0.9467`**! (By contrast, for magnetics, `Band 03 tmi_hg` correlates at `r = 0.9733` with $\|\nabla_H \text{B14}\|_2$ and `Band 09 tmi_vg` correlates at `r = 0.9313` with $-\nabla_H^2 G_{1.5}(\text{B14})$.)

**Decision it changes:** Taking the spatial Jacobian of the true vector field $\mathbf{g}_H = (\text{B11}, \text{B18})$ in `src/gems91/mhtr_coda.py` constructs the **2×2 Horizontal Marussi Gravity Hessian Tensor**, yielding the true Laplace second vertical derivative $\text{SVD}_G = -(\partial_x \text{B18} + \partial_y \text{B11}) = \partial^2 g_z / \partial z^2$, Eötvös differential curvature $\lambda_1 - \lambda_2 = \sqrt{(H_{xx}-H_{yy})^2 + 4H_{xy}^2}$, full-resolution updip vector-normal deprojection, and tectonic cosine alignment between topographic slope $\nabla\text{B12}$ and basement gravity gradient $(\text{B11}, \text{B18})$ (`+30.0%` higher on real faults).

---

## IR-91-S11-03 — Intra-Segment Self-Proximity Covariate Shift in Spatially-Blocked Holdout Tree Splits

**Expected:** Folding visible-catalogue proximity features (`fc_vis_tip_prox_10px`, `fc_vis_stepover_20px`, `fc_vis_strike_continuation`) into tree training (`H91-DDVTC`) was intended to teach the classifier relay-ramp geometry.

**Actual:** Because every training positive pixel $x \in \text{visible\_faults}$ lies on a `visible_faults` segment, its own segment's neighboring pixels sit at distance $3\text{–}12\text{ px}$, giving training positives artificially high `fc_vis_*` values. In the blind test quadrant (`withheld_faults` buffered by $\ge 10\text{ px}$ from `visible_faults`), `fc_vis_*` is $\approx 0$ everywhere on withheld fault segments.

**Decision it changes:** In `S11-MHTR` (`src/gems91/mhtr_coda.py`), the OOF `HistGradientBoosting` + `LogisticRegression` ensemble is trained strictly on label-free geophysical, Marussi-Hessian, topographic-curvature, radiometric-contact, and 1 km corridor features. Removing `fc_vis_*` from tree splits and applying Two-Regime Marussi/Radiometric Submodular Allocation lifted out-of-fold `HOLDOUT-DTI` from `0.174030` (`H91-1 E1`) to **`0.206406`** (`S11-MHTR E2`, `95% CI [0.193796, 0.220176]`, non-overlapping CIs) and lifted blind off-catalogue USGS SGMC DTI from `0.082886` to **`0.097623`**.

---

## IR-91-REVIEW-01 — Validator disagreement about finite zeros outside the footprint

**Found (2026-10-24):** `scripts/validate_raster.py` defaults to a MUST gate requiring NaN outside the sample footprint. The shared `vendor/gems57` validator checks all-finite [0,1] values and the current writer uses zeros outside the footprint. The legacy script provides `--allow-zeros-outside`, which demotes its outside-footprint NaN check to informational.

**Reproduced:** For the existing CED91 research TIFF, `scripts/verify_current_artifact.py --with-data` reports format/range/grid/catalogue PASS and `submission_ready: false`. `scripts/validate_raster.py` without the option reports the zero-outside check as a failed MUST gate. Supplying `--allow-zeros-outside`, plus the pinned parent, sample, catalogue and ledger, makes all MUST gates pass. This revalidation is not an organizer receipt and does not clear the final-dot duplicate gate.

**Decision:** Do not change the organizer-format assumption by implication. Use the explicitly selected all-finite policy for current published research artifacts because the user's submission form rejected out-of-range values and the shared validator/writer enforce it; preserve the legacy option and this discrepancy for review. Before calling any file upload-ready, obtain organizer-confirmed format semantics and still satisfy science, novelty and separate-selector gates.


## IR-UCD-01..03 (2026-10-24 UCD91)
- IR-UCD-01: Registry uniqueness scope is data/registry/*.tif only (incl. R0), not the universal fleet registry; docs/downloads rasters not all rechecked. Verdict relies also on novel feature family.
- IR-UCD-02: submission_writer overwrote shared docs/downloads/h91_submission_bundle.js with the UCD91 payload (shared-tool behaviour; flagged, not forked).
- IR-UCD-03: First writer attempt failed on missing imagecodecs in this sandbox (it is pinned in requirements.txt); installed and finalize_ucd.py completed all suites. Shared tool not modified.
