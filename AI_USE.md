# AI use disclosure

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
  came from GitHub mirrors whose data-use status is flagged in IR-91-03.
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
6. **Whether IR-91-05 (the 3 px collar rule vs the parent's 2.24 px) is
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
