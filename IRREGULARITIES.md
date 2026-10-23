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
