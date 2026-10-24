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
