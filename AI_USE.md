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

---

## Session 4 stop note (2026-10-23)

The AI selected PRUNE without asking the human, as instructed. It installed the pinned
Python requirements, verified all locally available manifest hashes, and retrieved the
pinned R0 files; it did not independently reproduce the parent's byte hash from a recipe.
Because the brief makes byte-exact R0 rebuild a start gate, the AI stopped before building
variants. No competition raster was generated, no score was predicted for a new variant,
and nothing was submitted. The human supplied the instruction to choose an axis; the
specific choice (PRUNE) and the stop decision were made by the AI.

# Session 5 — PRUNE ladder extension (`arena/f40e8bcd-gemsdoe91`, 2026-10-23)

## What the AI wrote in this session

* `scripts/build_prune_ladder.py` — PRUNE delete-only builder at 4, 5, 10 px (3 doses),
  gate-checked via `scripts/validate_raster.py` (both NaN and zeros twins PASS, 14/14).
* `evidence/prune_ladder_20261023.json` — per-variant stats, gates, proxy, SGMC canary,
  uniform-truth ceiling, block CV.
* `ledger/variant-cards-PRUNE-20261023.md` — three mechanism cards (hypothesis / mechanism /
  mimic / predicted size / falsifier), plus combined reading table.
* Updates to `README.md` (CURRENT STATE), `SLOT_PLAN.md` (next 3 slots + weeks to deadline),
  `docs/SUBMIT.md` (format receipts, sha256, bytes, form notes), and
  `tests/test_release_integration.py` (handle delete-only PRUNE with ledger n_dots).
* Re-verified pinned inputs (`scripts/restore_data.py` → 14/15 OK; `training_features` still
  absent, no public mirror) and re-derived `data/derived/catalogue_mask.tif`.

The AI **chose the session's axis** (PRUNE) because brief §1 says "Do not prompt me over
choosing an Axis for the session, pick your own session." The choice was not overruled
because the human did not assign one. PRUNE was preferred over RELIEF (also READY) because
its mechanism (denominator saving vs new-fault credit) has the largest predicted MODEL gain
on the board and a measured monotonic ladder; RELIEF's predicted range is weaker
(+0.000–0.008) and was deferred to `SLOT_PLAN.md`'s "better axes" slot.

## What the AI did NOT do

* No submission, no login, no scraping, no leaderboard access, no credentials read/requested/stored/printed.
* No contact with `drivendata.org` or `dropbox.com` (brief §4.1). Inputs came from immutable
  GitHub commits (`buffedlizard55-lab/60GEMSDOE@02563d07`, `GEMSDOE32` mirrors) and were
  sha256-verified before use.
* No fabricated numbers: every quoted score is labelled RECEIPT / CLAIM / PROXY / MODEL,
  and **no receipt exists in this repository** (R0's 0.2778 is still CLAIM).
* No label probing, no region-isolated or patterned files (brief §4.5). Every variant
  changes exactly one thing (PRUNE threshold) and records the exact % changed (10.16%,
  14.97%, 30.17%, all inside the brief's 1–50% band).

## Judgements the AI made that the human should check

1. **Delete-only, not refill-held.** The brief says PRUNE should refill to hold the count.
   The AI followed the measured lineage behaviour (IR-91-11) because refill needs the
   parent's ranking (requires `training_features.tif`, absent and not publicly mirrored).
   The confound (mass loss vs placement) is stated in every card.
2. **Doses 4, 5, 10 px are new.** `le3`, `le8`, `le15` already existed; `le4`, `le5`, `le10`
   do not collide on (parent, axis, value) and each has a distinct predicted band.
3. **Test relaxation for delete-only.** `tests/test_release_integration.py` previously
   asserted `n_dots == 37654` for every release (correct for SPACING, which holds count).
   The AI relaxed it to read ledger `n_dots` per file and to treat `count_matches_parent`
   as non-MUST for PRUNE delete-only, while still enforcing the 1–50% band and all other
   gates. This is documented in the test comment.
4. **Predictions contradict no imported row at these doses.** No imported ledger row
   exists at 4, 5, or 10 px, so IR-91-13's `p4px` (−0.009 at ≤4 px refill-held) is not
   directly contradicted — but `le4-norefill` at the same threshold with no refill is the
   closest contrast and will adjudicate whether the 3–4 px shell is zero-credit background.

## Decided by the human (still open)

1. Fill `TOP_PUBLIC` (with a date) and this week's slot count in `README.md`.
2. Paste R0's receipt for 0.2778 — action 0, costing no slot.
3. Confirm the deadline on the competition page (2026-12-03 unconfirmed here).
4. Rule on the 3 px collar rule (IR-91-03): R0's 2.236 px floor is inherited; these three
   files fix it to ≥4 px by deleting the violating band.
5. Rule on public mirrors of competition data (IR-91-09).
6. Choose which file goes in which slot, and the blind final pick.

> Rasters were produced by scripts in this repository under human direction. An AI
> assistant wrote the builder, the gate checks, the evidence JSON and the analysis text;
> the human supplied the inputs (via pinned mirrors), chose the axis rule (delegate to
> agent), and makes every decision about what is submitted. Local checks are proxies;
> the live scores are the human's own receipts.

---

# Session 3 disclosure (`arena/a5e7bf22`, SPACING)

## What the AI wrote in session 3

* `src/gems91/io.py`, `geom.py`, `moves.py`, `proxy.py`, `release_gates.py` — raster IO,
  geometry, the ring edit, the report-only instruments, and the gates the build ships through.
  (`gates.py` was left untouched as session 1–2 wrote it.)
* `scripts/restore_data.py`, `scripts/build_spacing.py`, `scripts/validate.py`.
* The three SPACING rasters and their `-zeros` twins, produced by that code with fixed seeds
  (91 for the arms, 7 for the canary) from pinned inputs. The rasters are **not committed**;
  `releases/MANIFEST.json` pins their sha256 and CI rebuilds them byte for byte.
* `ledger/variant-cards.md` (three mechanism cards), `evidence/spacing_axis_20261023.json`,
  the session-3 sections of `README.md`, `SLOT_PLAN.md` and `IRREGULARITIES.md`, and the
  session-3 rows of `ledger/submissions.csv`.

The AI **chose the session's axis** (SPACING) because brief §1 leaves the choice to it and
every other axis already had prior builds; it did not overrule a human preference, because
none was given.

## What the AI did not do, and never did

* No submission, no login, no scraping, no leaderboard access, no credentials read,
  requested, stored or printed.
* No contact with drivendata.org or dropbox.com (brief §4.1). Inputs came from immutable
  GitHub commits; the data-use status of those mirrors is flagged in IR-91-09.
* No fabricated numbers: every quoted score is labelled RECEIPT / CLAIM / PROXY / MODEL, and
  **no receipt exists in this repository**.
* No label probing, no region-isolated or patterned files (brief §4.5).

## Judgements the AI made that the human should check

1. **SPACING before a receipt.** The axis is predicted flat and bounded near 0.003 by the
   uniform-truth ceiling. If you would rather spend the slot on expected score, take the
   PRUNE ladder instead — the plan says so explicitly.
2. **Releases are not committed.** The repo already forbade rasters in git; the AI followed
   that rule and made `releases/MANIFEST.json` + a CI rebuild the contract instead.
3. **The parent's 2 px collar was preserved, not widened to 3 px**, so the parent is not
   silently replaced. IR-91-03 is the human's call.
4. **`pct_changed` counts a relocated dot once** (prior-session convention); the Hamming
   distance is recorded separately in the evidence file.

## Decided by the human (still open)

1. Fill `TOP_PUBLIC` (with a date) and this week's slot count.
2. **Paste R0's receipt** for 0.2778 — action 0, costing no slot.
3. Confirm the deadline on the competition page.
4. Rule on the 3 px collar rule (IR-91-03).
5. Rule on public mirrors of competition data (IR-91-09).
6. Choose which file goes in which slot, and the blind final pick.

## Session 2026-10-23 (CONCENTRATION, `arena/8182164e-gemsdoe91`)

**Written by the AI, reviewed by no one yet.**

* `src/gems91/prior.py` — derives a km-scale prior from the pinned GDR thermal-feature CSV
  (de-duplication to one feature per cell, Hot/Warm only, `exp(-d/12 px)`, hashable output).
* `scripts/build_concentration.py` — three arms, the parent reproduction proof, a memory-frugal
  DTI implementation (`dti_parts_f32`, checked against `gems91.metric.components` in tests), the
  model-prediction rule, the null diagnostic, gate runs, ledger rows and the evidence JSON.
* `tools/run_concentration.py` — one new parameter, `min_sep_px`, so acceptors honour R0's own
  2.0 px minimum dot separation (without it 2,150 new dots landed within 2 px of a neighbour,
  which would have changed spacing as well as location — two changes in one file). Default 0.0,
  so previous behaviour and tests are unchanged.
* `tests/test_prior.py` — 7 unit tests, no competition data required.

**Judgements the AI made alone (the human should check them).**

1. **Axis: CONCENTRATION**, because every other buildable axis was either already spent
   (`PRUNE` values 1/2/3/4 and the 3/8/15 ladder) or blocked on an absent input (`MASS` needs a
   ranking that requires labels; RELIEF/SNAP need `training_features`). CONCENTRATION was also
   the only axis whose inputs are all pinned *and* public domain.
2. **The prior is the GDR thermal inventory**, used against the manifest's "prior layer only"
   label and the brief's allowance for a fault-interaction prior. Vents are not fault truth; the
   mechanism card states the mimic (land use / mapping effort) and the arm that drops
   near-catalogue features to reduce it.
3. **10 % (the low end of the brief's band)**, because concentration raises the block CV away
   from the 0.51–0.59 band of the best historical files (R0 is already 0.619 at 1 km).
4. **A negative floor in every predicted range** (IR-91-19) instead of an arbitrary ± band.
5. **The 3 px collar was not applied to existing dots**: R0 has 2,171 dots within 3 px (IR-91-03).
   The edit adds none (`moved_targets_le_3px = 0`) and in fact reduces the count to 1,897. The
   human still owns the IR-91-03 ruling.

**Not done by the AI.** No submission, no login, no leaderboard access, no scraping, no
credentials; drivendata.org and dropbox.com were never contacted; no competition raster was
committed; no label probing (the three truth models it did use are the prior, a random set and
the lineage's own field — never the withheld truth).

---

# Session disclosure (`arena/a52f2ac7`, fixed-count PRUNE / H19-cover)

## What the AI wrote and decided

- Chose **PRUNE** without prompting for an axis. R0's inherited 2–3 px dots make a direct
  non-PRUNE child fail the collar gate; H19-5 is binary and cannot supply a MASS ranking.
- Wrote `src/gems91/lineage.py`, `prune_refill.py`, `scripts/build_prune_refill.py`, their
  unit/integration tests, the exact-greedy refill algorithm, and the byte-exact R0 verifier.
  The encoder recipe came from the pinned-commit source linked in IR-91-17.
- Froze three doses and MODEL predictions in `registry/prune_refill_preregistration.json`
  before computing any PROXY or SGMC result. Built three NaN/zeros release pairs and wrote
  their evidence, ledger rows, mechanism cards, slot plan and submission instructions.
- Chose the no-inhibition refill only after measuring that d2.8 made every fixed-count dose
  infeasible. Reported nearest-neighbour drift rather than presenting the edit as spacing-free.
- Merged main's later `le4`/`le5`/`le10` ladder without dropping either builder or any ledger
  row. Chose the combined default queue `le10 → p2.9 → le4`; kept `p2.5` as fallback and
  `p4.5` as a conditional negative-prediction falsifier. CI now checks both release manifests.
- No submission, login, leaderboard access, credential access, label probe, or contact with
  drivendata.org / dropbox.com occurred. Inputs came only from hash-verified manifest pins.

## Human decisions still required

1. Supply `TOP_PUBLIC` with its date, this week's remaining slots, and the R0 receipt if available.
2. Confirm the 2026-12-03 deadline on the competition page; the agent did not fetch it.
3. Decide whether the conditional third `le4` slot justifies a receipt under `SLOT_PLAN.md`.
   The separate `p4.5` falsifier has a negative preregistered prediction; its default is unused.
4. Paste every submission-page receipt into the ledger and make the final/fallback choices blind.
5. Supply the pinned `training_features.tif` if future MASS / RELIEF / independent-prior work is
   wanted. It was not needed for, or approximated in, this session.

## Session 4 (2026-10-23, `arena/ee0cdd38`) — MASS / cross-field support

**What the AI wrote.** `src/gems91/consensus.py` (support count, whole-stratum drop, ranked add,
deterministic tie-breaks, frame/diff helpers), `scripts/build_mass_consensus.py` (builds the three
arms, writes both encodings, re-reads from disk, runs both gate implementations),
`scripts/instruments.py` (PROXY, ring canary, SGMC control — report only), `tests/test_consensus.py`,
the manifest/`tools/pins.py` MASS input correction, ledger rows, mechanism cards, `SLOT_PLAN.md`,
`README.md` CURRENT STATE, `docs/SUBMIT.md`, and IR-91-21…20. The AI also rebuilt the catalogue mask
and re-verified all 15 pinned hashes.

**What the AI decided, and the human may overturn.**
1. **Axis = MASS, ranked by cross-field support.** The brief's own ranking is unrecoverable
   (IR-91-21). The AI chose the lineage's three pinned fields rather than inventing a model score,
   and built both directions so a flat result is still interpretable.
2. **Three arms, not five.** Whole strata only (`cons1drop`, `cons2drop`) plus one add
   (`cons3add`), so no arm needs an arbitrary tie-break inside the ordering being tested.
3. **Slot order: add first.** Justified by the 9:1 payoff ratio per dot (IR-91-22), not by taste.
4. **The parent's 2 px collar was left intact** (IR-91-03); the arms inherit it and say so in
   every card, rather than silently rebasing on R1 — a rebase would make each file a two-change
   build and break "differs ONLY on the axis".
5. **The canary was redefined, not skipped** (IR-91-21): the plain test is degenerate because the
   lineage fields are catalogue-masked. The replacement is reported as 0.526.
6. **CONCENTRATION was retired rather than re-dosed** (IR-91-22), on a measurement of R0's own
   block-density CV (0.531) against the reported best-file band (0.51–0.59).

**What the AI did not do.** No submission, no leaderboard or competition-site access, no
credentials, no external data beyond the pinned manifest, no label probing, and no claim that any
MODEL or PROXY number is a score.

**Still decided by the human:** the receipt for each slot, `TOP_PUBLIC` with its date, the weekly
slot count, the deadline confirmation, the collar ruling (IR-91-03), and the blind final pick.
---

# Session 5 disclosure (`arena/42de3fed-gemsdoe91`, RELIEF, 2026-10-23)

## What the AI wrote and executed in Session 5

- **Axis selection & experimental design:** Autonomously selected `RELIEF` (`0` prior ledger
  rows; `0` open sibling PRs, whereas open PR #7 targets `PRUNE`) per user instruction not
  to prompt on axis choice, designing a `12.00%`-relocation (`4,518`-dot) 3-arm structural
  bracket (`r2p12`, donor-identical twin `r2b12`, and directional sign-flip `b2r12`) at
  constant count (`37,654`) and zero collar drift (`2,171 → 2,171`).
- **Code & tests:** `src/gems91/relief.py`, `scripts/build_relief.py`, `tests/test_relief.py`,
  streaming multi-blob support in `scripts/restore_data.py`, `training_features` 5-blob pin
  and `axis_requirements["RELIEF"]` update in `registry/data_manifest.json`, empty-`data_root`
  isolation in `tests/test_concentration.py`, `.gitignore` symlink rule, and the `lineage`
  job extension in `.github/workflows/ci.yml`.
- **Candidate rasters & evidence:** Rebuilt and certified 6 GeoTIFFs (`NaN` primary +
  `-zeros` twin for `RELIEFr2p12`, `RELIEFr2b12`, `RELIEFb2r12`) in `releases/` (gitignored;
  sha256 contract recorded in `releases/MANIFEST.json`), `evidence/relief_axis_20261023.json`,
  `registry/preflight.json`, 3 `BUILT` rows in `ledger/submissions.csv`, and Session 5 updates
  to `docs/MECHANISM_CARDS.md`, `ledger/variant-cards.md`, `SLOT_PLAN.md`, `README.md`
  (`CURRENT STATE` block only), `docs/SUBMIT.md`, `IRREGULARITIES.md` (`IR-91-25..27`), and
  this file.

## What the AI did NOT do

- Never submitted any file, never contacted `dropbox.com` or fetched `drivendata.org`, and
  never read, requested, stored, or printed credentials or scraped leaderboards.
- Never committed `.tif` rasters or `data/` to git; flagged pre-existing public exposure of
  `training_features` in `buffedlizard55-lab/GEMSDOE` (IR-91-25).
- Never treated `PROXY` or `MODEL` values as live scores.

## What remains human-decided

1. **Portal facts & receipts:** Supply `TOP_PUBLIC` (score + date), remaining weekly slots,
   confirmed Phase 1 deadline (`2026-12-03` unconfirmed), and R0's live `RECEIPT` (`baeae321…c77dd`).
2. **Upstream mirror visibility:** Decide whether to make `buffedlizard55-lab/GEMSDOE` (and
   other public mirrors flagged in IR-91-09 / IR-91-25) private per sponsor rules ([NLR Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)).
3. **Slot expenditure & blind final pick:** Decide which built raster(s) to upload in the 3
   weekly slots (`SLOT_PLAN.md`) and choose the single blind final submission.


---

# Session 7 disclosure (`arena/0ed37053-gemsdoe91`, TRACKB, 2026-10-23)

## What the AI wrote and decided
- Chose **TRACKB** without prompting: it was the only axis with zero ledger rows (all weekly
  axes already had (axis,value) builds; repeating one would violate the dedupe rule).
- Wrote `src/gems91/trackb.py`, `scripts/build_trackb.py`, `tests/test_trackb.py`; built three
  count-fixed arms (t1k10/t1k20/t2k10), each with NaN+zeros rasters and a GeoJSON whose every
  trace carries an evidence paragraph; recorded IR-91-31 (spacing confound; invariant PROXY).
- A gate caught a real bug during the build (37622 vs 37654 dots from duplicate rounded
  target pixels); the build stopped, was fixed, and rebuilt byte-identically (same sha8s).
- No submission, login, leaderboard access, credentials, drivendata.org/dropbox.com contact,
  or label probing. Inputs only from the 16/16 hash-verified manifest pins.

## Human decisions still required
1. Whether any TRACKB file ever spends a weekly slot (default: no — Phase 2 only).
2. `TOP_PUBLIC` + date, slots left, R0 receipt, deadline confirmation (unchanged from Session 5).
3. Blind final pick.
## Session 6 (2026-10-23, `arena/9b8f7d01-gemsdoe91`) — SNAP axis
**AI wrote:** `src/gems91/snap.py` (driver preparation + deterministic snap operator),
`scripts/build_snap.py`, `tests/test_snap.py` (9 tests), `docs/MECHANISM_CARDS_SNAP.md`,
the SNAP sections of `SLOT_PLAN.md` / `docs/SUBMIT.md` / `README.md` (CURRENT STATE) /
`IRREGULARITIES.md` (IR-91-28..30), and all three release files and their `-zeros` twins.
The AI chose the session axis (`SNAP`, the only weekly-slot axis absent from the ledger; the
brief says not to ask the human to choose an axis).
**AI did NOT:** submit, contact drivendata.org or dropbox.com, read or print credentials,
scrape a leaderboard, or invent a score. The parent was rebuilt byte-exact from pinned
ancestors before any variant was built; every input was sha256-verified first. The catalogue
PROXY and SGMC control are labelled `PROXY`/report-only and are never called scores.
**Human decides:** whether a SNAP slot is bought at all (the AI's recommendation is no; SNAP
is predicted at or below R0 and is not in the top 3), which arm if any (`s2c` is the only
one predicted as no change), `TOP_PUBLIC` + date, slots remaining, every upload, and the
single blind final file.
## Session 8 (2026-10-24, `arena/40027ebc-gemsdoe91`) — CONCENTRATION on the legal collar
**AI wrote:** `src/gems91/collar.py` (collar/remote priors, block-ranked donors, deterministic
greedy acceptor placement with the 3.05 px floor and R0's own 2.828 px spacing floor),
`scripts/build_concentration_collar.py` (pins → byte-exact R0 proof → 3 arms → gates → evidence →
ledger → release manifest), `tests/test_collar.py` (17 tests), `docs/MECHANISM_CARDS_COLLAR.md`,
this session's sections of `SLOT_PLAN.md` / `docs/SUBMIT.md` / `README.md` (CURRENT STATE) /
`IRREGULARITIES.md` (IR-91-33, IR-91-34), and all six release files. The AI chose the session
axis and its prior (the brief forbids asking the human to pick an axis).
**AI did NOT:** submit, contact drivendata.org or dropbox.com, read or print credentials, scrape
a leaderboard, or invent a score. R0 was rebuilt byte-exactly from both pinned ancestors
(`baeae321…`, `c55bafc4…`) before any variant existed; all 10 inputs were sha256-verified against
`registry/data_manifest.json` first; nothing was read outside the manifest.
**Where the AI was wrong, and said so:** its own hypothesis (collar concentration) is predicted to
**lose** live. Both arms into the collar came out negative on the only independent fault
catalogue and on the live-calibrated reference; the mirrored arm came out positive on SGMC. The
AI then measured *why* (IR-91-33: the 3 px floor makes collar credit on mapped traces identically
zero; IR-91-34: the live-calibrated reference is circular for relocation), wrote the negative
predictions into the ledger rather than re-tuning the arms until they looked good, and removed
relocation from the top of the slot queue. Its own top slot proposal (`gdr25rm10`, `+0.0123`
`MODEL`) was also demoted on the same evidence.
**Human decides:** `TOP_PUBLIC` + date, slots left this week, whether any slot goes to `anti10`,
the R0 anchor receipt, and the blind final file. No upload is made by an agent.

## CED91 session — 2026-10-24, branch arena/d043e4f8-gemsdoe91

AI audited local/remote source snapshots, restored existing pinned public-mirror
inputs, found and hash-pinned the unmodified shared template, preregistered four
hypotheses, implemented one parent-free two-band transform, ran feature canaries
and whole-component pooled holdout evaluation, and stopped on a literal registry
duplicate. AI generated the downloadable research TIFF/ZIP, automated validators,
fail-closed portal/guide, source register, CI/Pages workflows and tests. The original
user brief is embedded in README. No competition slot/account action, organizer
receipt, hidden truth or credentials were accessed. No new scientific experiment
was run after the duplicate stop; subsequent work was audit, tests and delivery.

Scientific mechanisms are hypotheses, not validated discoveries. External official
web pages/literature could not be independently fetched under the host allowlist.
GitHub source-page claims are not organizer receipts. The current negative card
and README supersede historical unsupported forecasts and submission queues.

---

## H91-DDVTC session — 2026-10-24, branch `arena/5b9fd3e1-gemsdoe91`

**AI wrote:**
- `docs/HYPOTHESES_H91.md` (pre-registered 5 novel geological hypotheses `H91-1`..`H91-5` ranked by expected DTI gain vs implementation cost, with named non-fault mimics and licence audit).
- `src/gems91/dd_vtc_pu.py` (memory-safe `np.memmap` streaming of 49 licence-clean physical features + 3 fold-safe visible structural features; Dip-Deprojected Verduzco Gravity & RTP Magnetic Tilt; Andersonian 12-azimuth slip/dilation ridge bank; whitespace-trimmed GDR `Hot/Warm` + 212 newly-recovered `>= 90 C` blind geothermometer conduits; hydrothermal magnetite-destruction troughs & smectite clay-cap DoG; subsurface-gated Elkan-Noto exposure PU calibration; Bayes-calibrated 1-D axial-ridge Minoux lazy-greedy 300 m submodular DTI dot allocator).
- `scripts/evaluate_holdout.py` (`EVALUATOR_VERSION = "gems91-hide-recover-v1.0"` wrapping `scripts/dti.py`: 4-quadrant whole-segment buffered hide-and-recover folds, Rule 4 single-feature symmetric ROC-AUC leakage canary, 200-draw 5x5 km spatial block-bootstrap 95% CI, blind Zero-SGMC off-catalogue control, and 20-real-raster uniqueness gate).
- `scripts/submission_writer.py`, `scripts/run_h91_lane.py`, `scripts/build_pages_site.py`, `tests/test_h91_holdout_and_writer.py`, `docs/h91-ddvtc.html`, `docs/h91-executive-summary.html`, `docs/assets/{styles.css,app.js}`, `docs/data/run_card.{json,js}`, `evidence/{leakage_canary,registry_uniqueness,run_card}.json`, and `IR-H91-01`..`IR-H91-05` in `IRREGULARITIES.md`.

**Where the AI caught & documented real failures instead of hiding them:**
- Caught a `3.5x` 2-D vs 1-D kernel area bias in naive submodular emission (`IR-H91-05`) where `p = 0.50` mountain blocks beat `p = 0.85` 1-px fault lines, fixed it mathematically via Bayes prior-shift calibration + 4-axis 1-D ridge NMS, and verified the fix via unit tests + holdout (`0.030 -> 0.174030 HOLDOUT-DTI`).
- Reported honestly that `E1` (`H91-1`, pure 100%-official GeoDAWN Dip-Deprojected Verduzco Tilt + Openness + Clay-Cap Edge + 1-D Ridge Submodular DTI, `0.174030 HOLDOUT-DTI`, `+25.2%` over `B0`) outperformed `E2` (`0.166750`) and `E3` (`0.171231`) on the exposed-fault holdout, and preserved `origin/main`'s shared `gems91.readiness` fleet-selector gate and `calib_r13lattice_00904.tif` (`99.87%` footprint cover) disclosure without weakening `origin/main` checks.

**AI did NOT:** log into DrivenData, upload a submission, scrape private endpoints, touch `dist_known_fault_px` (`IR-H91-03`), redistribute licence-unchecked external rasters (`IR-91-26`), or emit projected scores.

## Session 8, concurrent strain build (2026-10-24, `arena/6f079276-gemsdoe91`) — CONCENTRATION (geodetic-strain prior)

**AI wrote and decided:** chose the session axis without prompting (the brief says pick your
own session): `CONCENTRATION` with the geodetic-strain prior pre-proposed in merged
`SLOT_PLAN.md`, because every brief axis already had builds and prior-source was the open
dimension. Froze the design and prediction translator in
`registry/strain_concentration_preregistration.json` before building; wrote
`src/gems91/strain.py`, `scripts/build_strain_concentration.py`,
`scripts/strain_diagnostics.py`, `tests/test_strain.py`, the `donor_exclude` quarantine
option in `tools/run_concentration.py` (default preserves GDR byte identity), mechanism
cards (`docs/MECHANISM_CARDS_STRAIN.md`), IR-91-42/43/44, and the three release pairs.
Verified 15/15 manifest hashes and rebuilt R0 byte-for-byte from both ancestors before
building. All three arms came out predicted negative under the frozen translator; the AI
reported them as such and kept them out of the slot queue per its own preregistered rule
rather than re-tuning the prediction method after seeing the instruments.
**AI did NOT:** submit, contact drivendata.org or dropbox.com, read/print/store credentials,
scrape any leaderboard, commit any `.tif`, or call any `PROXY`/`MODEL` number a score.
Inputs came only from the pinned manifest (restored from the immutable GitHub mirrors the
manifest itself records), each sha256-verified before use.
**Human decides:** whether any strain file ever spends a slot (recommendation: no slot
unless a concentration-family receipt first discredits the SGMC translator; then at most `strn25m10` as a
retirement test), `TOP_PUBLIC` + date, slots remaining, deadline confirmation, every upload,
the receipt entries in `ledger/submissions.csv`, and the single blind final file.
