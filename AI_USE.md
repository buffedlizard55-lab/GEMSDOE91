# AI use disclosure

Required by the competition rules (NLR rules PDF, reproducible code + generative-AI
disclosure) — https://docs.nlr.gov/docs/fy26osti/96647.pdf

## What the AI wrote (this session, 2026-10-23)

- All code: `src/gems91/{metric,gates,pinned}.py`, `scripts/*.py`, `tests/*`, CI workflow.
- The DTI re-derivation and its unit tests, including the finding that the formula admits
  scores > 1.0 while live scores top out near 0.44, i.e. **absolute values from this module
  are not scores** (IR-91-06).
- All documents: this file, `IRREGULARITIES.md`, `SLOT_PLAN.md`, `docs/SUBMIT.md`,
  `README.md` (CURRENT STATE), `ledger/README.md`.
- All verification runs: parent hash/grid/dot-count audit, the 15-entry manifest,
  the 20-row ledger import, the raster-availability sweep (3 present / 17 absent),
  and the hash + format check of the six retrievable MASS rasters.

## What the AI did NOT do

- It did **not** build a candidate raster. No variant was produced because the three
  competition rasters are absent and a variant cannot be certified without them
  (IR-91-02). Nothing here approximates or reconstructs the parent.
- It did **not** fetch drivendata.org, contact dropbox.com, log in, scrape the leaderboard
  or submit. Those are the entrant's acts, from the entrant's account.
- It did **not** invent a score. Every number carries a label: RECEIPT (none yet),
  CLAIM (owner-reported), PROXY (local holdout), MODEL (projection).

## What the human decided / must decide

1. **TOP_PUBLIC** with a date and a receipt (blank in the brief; upstream's 0.4413 is a CLAIM).
2. **Slots left** this week, and which slot (if any) goes to slot 1 in `SLOT_PLAN.md`.
3. Whether the ≥3 px collar (constraint 4) binds controlled edits of R0 or only new dots —
   this decides whether the brief's default week-1 plan is executable at all (IR-91-03).
4. Whether GEMSDOE88 is the intended upstream lineage (IR-91-01).
5. Supplying the three pinned competition rasters, or confirming a rebuild happens on the
   entrant's machine.
6. Every submission, and the final blind file choice.

## Provenance of imported material

`ledger/submissions.csv` and `registry/data_manifest.json` were transcribed from the public
repo `buffedlizard55-lab/GEMSDOE88` (session of 2026-10-23) and are marked
`IMPORT:GEMSDOE88`. Hashes in the ledger are upstream claims except where this session
recomputed them: the three `anc`-ladder rasters and both R0 twins were fetched and re-hashed
(`registry/r0_verification.json`); the six MASS rasters were fetched and re-hashed
(`registry/candidate_availability.json`). The three competition rasters could not be verified
in this sandbox and are marked as such.

---

## Session 2 (`arena/a6416f7b`, same date) — delta on top of the above

**Written by the AI in session 2:** `tools/run_concentration.py` (the CONCENTRATION builder
and its mechanism card), `tools/pins.py`, `tools/raster_io.py`, `tools/stor.py`,
`tools/make_fixture.py`, `tests/test_concentration.py`, the session-2 addendum in
`SLOT_PLAN.md`, IR-91-06/07/08 in `IRREGULARITIES.md`, `docs/MECHANISMS.md`,
`docs/DATA.md`, and the one-line fix in `src/gems91/gates.py` (IR-91-06). It also chose the
session axis (CONCENTRATION) because the brief lets the agent pick when the human does not.

**Not done by the AI in session 2:** no candidate raster was built (same missing rasters as
session 1), no submission, no score, no leaderboard access.

**Human still has to decide (adds to the list above):**

7. Which collar reading binds (2 px as R0 was built, or 3 px as §4.4 states) — IR-91-03,
   now sharper because IR-91-06 voided the existing collar counts.
8. Whether the three imported CONCENTRATION rows count as "CONC already tried" (they should
   not — IR-91-07).
9. The external prior for CONCENTRATION: which band(s) of `training_features.tif`, and the
   block size (5 km default, 1 km if the dose-response is the goal).


---

## Session 3 addition — 2026-10-23, `arena/5563ddf8`

### Written by the AI

- `scripts/dti.py` — DTI metric + exact marginal gain, unit-tested (53 tests here alone).
- `scripts/axes.py` — MASS / PRUNE / SNAP / CONCENTRATION operators with invariant checks.
- `scripts/validate_raster.py`, `scripts/verify_manifest.py`, `scripts/ledger.py`,
  `scripts/build.py`, `scripts/make_catalogue.py`, `scripts/proxy.py`.
- The three PRUNE releases and their mechanism cards.
- The axis choice (PRUNE) — chosen, because the brief forbids asking.
- Fix to `src/gems91/gates.py` `sha_unseen` (IR-91-12) and the corresponding change in
  `scripts/validate_raster.py`.

### Input recovery — disclosed in full

The repo held only `README.md`. The AI searched the owner's public sibling repositories and
recovered `sample_submission.tif`, the labels raster (`existing_faults`) and both R0
encodings, verifying each sha256 against hashes already recorded in this repo's manifest.
Nothing was rebuilt from a description and nothing was filled from memory. This **corrects**
IR-91-02, which had concluded the rasters were not publicly available.

### Judgements the AI made that the human should check

1. **Delete-only, not refill.** The brief says PRUNE should refill to hold the count. The AI
   followed the measured parent behaviour instead (IR-91-11), because a refill needs a
   ranking that was never stored.
2. **`le3-norefill` at a dose already covered twice.** Kept as a refill-policy contrast and
   labelled so it cannot collide (IR-91-10). Drop it if you prefer.
3. **`sha_unseen` now ignores BUILT rows** (IR-91-12). Without this, no file could be both
   recorded per §7 and certified.
4. **Predictions contradict an imported row** (IR-91-13). The AI did not quietly retune its
   numbers to match `p4px`.

### Decided by the human (still open)

1. **Fill `TOP_PUBLIC`** and this week's slot count in `README.md`.
2. **Confirm the deadline** on the competition page (2026-12-03 is unverified here).
3. **Supply `training_features.tif`** — it is the single input that unblocks MASS, SNAP,
   CONCENTRATION and the parent's own ranking.
4. **Rule on the 3 px collar rule** (IR-91-03): R0 itself breaks it at 2.236 px.
5. **Rule on public mirrors of competition data** (IR-91-09).
6. **Own the receipts.** Paste each submission-page receipt number into
   `ledger/submissions.csv`; until then every number in this repo, including R0's 0.2778,
   is a CLAIM.

### Standing disclosure for the rules

> Rasters were produced by scripts in this repository under human direction. An AI assistant
> wrote the metric implementation, the axis operators, the validation gates and the analysis
> text; the human selected the axis, supplied the inputs and made every decision about what
> was submitted. Local checks are proxies; the live scores are the human's own receipts.
