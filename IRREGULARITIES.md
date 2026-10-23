# IRREGULARITIES — GEMSDOE91

Only items that **change a decision**. Each names the decision it changes.
Nothing here is a score; none of it replaces the official rules, which win.

---

## IR-91-01 — the format template is not blank: its values ARE the catalogue

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

## IR-91-02 — `labels.tif` is the catalogue, so no local instrument can see new faults

`labels.tif` and `existing_faults.tif` are **byte-identical** (both sha256
`7ba308cc…`, 425,830 B) in every public mirror checked. Whatever the file is
called, its content is the mapped USGS/INGENIOUS trace.

**Decision it changes.** The only truth-adjacent local instrument available to
this project is *catalogue* recovery. A candidate's dots sit > 2 px from that
catalogue by construction, so the instrument can only observe the 2–3 px collar
(3.9 % of withheld cells; mean credit 0.006). It therefore **cannot adjudicate
the SPACING axis** — on this axis its sign is collar drift, not spacing — and it
must stay a REPORT-ONLY number. Reported, not gated, not believed.

## IR-91-03 — organizer rasters are published in public GitHub mirrors (data use unchecked)

`buffedlizard55-lab/60GEMSDOE`, `GEMSDOE24`, `GEMSDOE`, `52GEMSDOE` and others
publish byte-copies of login-walled DrivenData competition rasters
(`sample_submission.tif`, `existing_faults.tif`, the 419 MB training-feature
stack) in **public** repositories. The competition data-use terms have not been
checked against that, and this sandbox cannot read them (drivendata.org access is
banned by §4.1).

**Decision it changes.** This repository **adds no new copy of competition
inputs to Git**: `data/` is gitignored and restored from the pinned mirrors by
`scripts/restore_data.py` with sha256 verification. `releases/*.tif` are this
session's own outputs (brief §7) and contain no truth labels. The human should
treat redistribution as an open legal question before any of these mirrors is
made part of the submission materials — the rules require reproducible code, and
the code is reproducible without the data mirror only if the organizer inputs are
fetched from the competition page.

## IR-91-04 — the parent's dot set is reproducible; its file bytes are not

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

## IR-91-05 — the brief's 3 px collar rule contradicts the brief's own parent

Brief §4.4 requires "zero catalogue mass and keep ≥ 3 px from the catalogue
unless AXIS = PRUNE". R0 does not satisfy this: **941 of its dots sit at
2.236 px** (and 670 at 2.828 px). The assigned parent is therefore outside the
stated constraint.

**Decision it changes.** Re-cutting the parent to a 3 px collar would silently
substitute a different parent and destroy the only live dose-response the
project has (0.2708 → 0.2778). This session instead **holds the parent's own
floor (d_cat > 2.0 px, 0 dots on the catalogue)** for every arm and records the
conflict here, so that a reviewer sees the rule was not applied rather than
missed. If the human decides the 3 px rule is binding, every release in
`releases/` must be rebuilt on a 3 px parent — a new lineage, not an edit.
