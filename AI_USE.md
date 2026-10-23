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
   this decides whether the brief's default week-1 plan is executable at all (IR-91-11).
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

7. Which collar reading binds (2 px as R0 was built, or 3 px as §4.4 states) — IR-91-11,
   now sharper because IR-91-06 voided the existing collar counts.
8. Whether the three imported CONCENTRATION rows count as "CONC already tried" (they should
   not — IR-91-07).
9. The external prior for CONCENTRATION: which band(s) of `training_features.tif`, and the
   block size (5 km default, 1 km if the dose-response is the goal).

---

# Session 3 disclosure (`arena/a5e7bf22`, SPACING)

<<<<<<< HEAD
Required by the competition rules (reproducible code, generative-AI disclosure;
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)). Written so a reviewer
can separate what the model produced from what the human decided.

## What the AI wrote

Everything committed in this repository, on 2026-10-23, on branch
`arena/a5e7bf22-gemsdoe91`:

* `src/gems91/` — raster IO, geometry, the ring-edit implementation, the format
  gates, and the report-only instruments (`hide_and_recover`, `uniform_truth_credit`,
  `canary`, `redundancy`, `block_density_cv`).
* `scripts/restore_data.py`, `scripts/build_spacing.py`, `scripts/validate.py`.
* The three candidate rasters in `releases/` and their `-zeros` twins, produced
  by that code with fixed seeds (91 for arms, 7 for the canary) from pinned inputs.
* `README.md`, `SLOT_PLAN.md`, `IRREGULARITIES.md`, `ledger/variant-cards.md`,
  `docs/SUBMIT.md`, this file, the tests, and the CI workflow.

The AI **chose the session's axis** (SPACING) because brief §1 leaves the choice
to it and every other axis already has prior builds; it **did not** choose it on
the human's behalf when the human had an opinion.

## What the AI did not do, and never did

* No submission, no login, no scraping, no leaderboard access, no credentials
  read, requested, stored or printed.
* No contact with drivendata.org or dropbox.com (brief §4.1); the pinned inputs
  came from GitHub mirrors whose data-use status is flagged in IR-91-11.
* No fabricated numbers: every quoted score is labelled RECEIPT / CLAIM / PROXY /
  MODEL, and **no receipt exists in this repository**.
* No label probing, no region-isolated or patterned files (brief §4.5).

## What the human decided, and what only the human can supply

1. **The axis delegation** — "pick your own session" — which authorised the
   SPACING choice.
2. **`TOP_PUBLIC`** (the leaderboard number and its date). Not supplied, not guessed.
3. **Slots remaining this week** and the entity's submission history. Not supplied.
4. **R0's receipt** for 0.2778. Every MODEL in the ledger is scaled by that
   number; while it is a CLAIM, the 0.01 evidence floor cannot be applied.
5. **Which file goes in which slot**, and the blind final pick. The plan is in
   `SLOT_PLAN.md`; the decision, and the upload, are the human's.
6. **Whether IR-91-13 (the 3 px collar rule vs the parent's 2.24 px) is
   binding.** If it is, the whole lineage must be rebuilt on a 3 px parent.

## Reproducibility

Fixed seeds, pinned inputs with sha256 verification, no hidden state:

```bash
python3 scripts/restore_data.py --check
python3 scripts/build_spacing.py --build
```

The build refuses to run unless the parent's dot set is reproduced exactly from
both pinned ancestors; it refuses to write the ledger unless every release passes
every hard gate.
=======
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
   this decides whether the brief's default week-1 plan is executable at all (IR-91-11).
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

7. Which collar reading binds (2 px as R0 was built, or 3 px as §4.4 states) — IR-91-11,
   now sharper because IR-91-06 voided the existing collar counts.
8. Whether the three imported CONCENTRATION rows count as "CONC already tried" (they should
   not — IR-91-07).
9. The external prior for CONCENTRATION: which band(s) of `training_features.tif`, and the
   block size (5 km default, 1 km if the dose-response is the goal).
>>>>>>> origin/main

