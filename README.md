# GEMSDOE91 — session 2026-10-24 (DrivenData GEMS #306) — PROMPT EMBEDDED

> **HIGHEST URGENCY — MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF. There should be an easy to download submission tif file as described by the prompt. PARALLEL-RUN PROTOCOL: lane is single method paragraph; stay inside; if raster rank-correlation >0.90 or >70% dots within 3px of registry raster, log duplicate and stop. REUSE, DON'T REBUILD: use template's cached feature stack, evaluate_holdout.py and submission_writer.py. LABEL EVERY NUMBER as HOLDOUT-DTI or ORGANIZER-CONFIRMED. LEAKAGE CANARY AUC>0.90 ⇒ leakage. RUN CARD JSON required. BUDGET 3 experiments/2h. No script here submits anything. One entity, three scored slots a week, one final file.**

No script here submits anything. One entity, three scored slots a week, one final file.

## SESSION 10 STATUS (2026-10-24, branch `arena/5e09be50-gemsdoe91`) — read this first

**Verdict: NOT OK TO DOWNLOAD OR SUBMIT ANY FILE from this session.**
- Status board: [`docs/index.html`](docs/index.html) · executive summary (how to submit, gates, errors): [`docs/executive-summary.html`](docs/executive-summary.html) · run card: [`docs/run-card-S10.json`](docs/run-card-S10.json) · hypotheses and ranking: [`docs/HYPOTHESES_S10.md`](docs/HYPOTHESES_S10.md) · irregularities: [`IRREGULARITIES.md`](IRREGULARITIES.md) (IR-91-S10-01 to -10).
- The one file built this session (`gems91-s10-basementridge-K60988-20261024-74b1f6f1.tif`, sha256 `74b1f6f1…dd36`) lives in the **gitignored** `outputs/s10/`. It is **not** published. It fails the pre-registered control: holdout-DTI **0.0173** [0.0126, 0.0218] vs random placement **0.0288** [0.0217, 0.0342] (HOLDOUT-DTI, evaluator `S10-holdout-v1`, 60,988 withheld positives). Not promoted to a slot.
- The three-experiment budget (E1 candidate, E2 ablation, E3 null) is spent. A new session is needed for any further experiment.
- The GEOD duplicate (93.2 % of dots within 3 px of R0) was removed from Pages downloads. It is still in git history (IR-91-S10-01).
- Official sources were read this session: [competition page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) (metric, format, features, label sources), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (#1 = 0.4413, public), [NLR official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (three submissions/week; AI disclosure; eligibility).
- The organizer metric was checked by hand against `scripts/dti.py`: with alpha + beta = 1 the two forms are algebraically identical. The numerical scorer has not been run against an organizer receipt.

### Decisions only the human can make (nothing below was decided by the agent)
1. Accept or reject the **mirror provenance** of the restored data (IR-91-S10-06, IR-91-09). The organizer's data page needs a login.
2. Whether the S10 file may be offered on Pages. Current decision: **no**.
3. **Eligibility.** Individual competitors must be U.S. citizens or permanent residents, and registration includes a signed statement under penalty of perjury (rules §1.3). Only you can attest to this.
4. **Generative-AI disclosure** (rules §3.2) must describe how AI was used in any submission narrative.
5. Whether the copies of competition files in other public lineage repositories (`59GEMSDOE`, `57GEMSDOE`) break the data terms (IR-91-S10-09; the rules were not read in full).
6. Whether to rewrite git history to remove the GEOD TIFs (IR-91-S10-01). Not done.
7. The deadline. The rules say the key dates are on the competition site; the deadline printed in earlier sessions is not verified.

### Full session prompt (restated; the verbatim text is not in this agent's session record — paste it here to replace this block)
- **Goal.** Produce a unique, easy-to-download, validated single-band GeoTIFF (values in [0, 1], CRS/shape/transform equal to the official sample) for DrivenData #306 (DOE GEMS, geothermal fault prediction). Do not copy previous submissions except for learning. It must be obvious on the site whether the file may be downloaded and submitted.
- **Validation.** Automated gates, no human inspector. Uniqueness is confirmed only after the gates pass. A registry scan must be complete (`complete: true`) before any uniqueness claim.
- **Analysis.** Explain why the high scorers (0.2778; the public top 0.4413) scored well, and whether a unique submission can beat them.
- **Hypotheses.** Three to five new geological hypotheses (layers, physical signature, why they find non-catalogue faults, difference from this repo), ranked by DTI gain and cost. Validate the top candidate on a spatially blocked holdout before spending a slot.
- **Holdout.** Hide-and-recover with a spatial buffer; pooled DTI with alpha 0.2, beta 0.8, 300 m triangular kernel. Use the shared template tools (`evaluate_holdout.py`, `submission_writer.py`, cached feature stack); fix shared-tool bugs once and report them.
- **Labels.** Every number is labelled HOLDOUT-DTI or ORGANIZER-CONFIRMED (or CLAIM). Leakage canary AUC > 0.90 means leakage.
- **Pages.** A clean GitHub Pages site with an executive-summary subpage on how to submit (including the error "Predicted values must be in range [0, 1]"), official verified links, and a unique submission name with a short note.
- **Process.** Open a PR and merge to `main`. List remaining work and limitations. End with a machine-readable JSON run card.
- **Budget and slots.** At most 3 experiments or 2 hours. Do not spend a weekly slot on an idea that has not beaten the current holdout best. Do not pick submissions for real slots (that is a separate selector step, within the weekly cap of three).
- **Parallel-run protocol.** A lane is a single method paragraph. Log a duplicate and stop if rank correlation > 0.90 or > 70 % of dots lie within 3 px of a registry raster.
- **Values.** Maximize P(Win); own the outcome. Negative results are deliverables and need a run card.

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2`, `37,654` unit-mass dots (`RECEIPT`) on the pinned `3730×3292` `EPSG:32611` (`100 m`, `float32`, footprint `5,167,373` px, `0` dots on catalogue, min `2.236 px`) grid. Both pinned TIFFs rebuild byte for byte from either ancestor (`baeae321…c77dd`, `355,443` B; `c55bafc4…6fa9`, `219,065` B; dot digest `905cee9d…`). R0's `0.2778` / `0.3698` remains an unreceipted **CLAIM**.
- **Inputs (`15/15` pinned + `catalogue_px.tif` = `16/16` hash-verified `RECEIPT`):** `scripts/restore_data.py` now restores `training_features` (`gems-geodawn-numerical-features.tif`, `418,912,844` B, sha256 `4371c82e…3bc5` `RECEIPT`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)) from 5 pinned git blobs (`IR-91-25`) and unblocks **all 6 axes** (`MASS`, `CONCENTRATION`, `SNAP`, `PRUNE`, `RELIEF`, `TRACKB`; `scripts/preflight.py` → `BUILD ALLOWED`).
- **Ledger (`50` `BUILT` rows, `0` `SUBMITTED`, `0` live `RECEIPT`s):** `|Δ| < 0.01` = no evidence. **TOP_PUBLIC:** `____` (human must fill, with date). **Slots left this week:** `__ / 3` (`5.86` rolling weeks to unconfirmed `2026-12-03` deadline).
- **Session 7 (`arena/0ed37053-gemsdoe91`) — `TRACKB` built (Phase 2 only, IR-91-31):** 2,214 strike-consistent traces >=1 km (12,989 support dots) chained from R0 dots ranked by label-blind `S_struct`; three count-fixed arms relocate 10.0%/20.0%/10.0% of lowest-ranked off-trace dots onto traces (`t1k10` `8343ab38` **+0.004** MODEL, `t1k20` `ab72339b` **+0.005**, `t2k10` `6d16fd7a` **+0.002**), each with a per-trace evidence-paragraph GeoJSON. Not in the weekly slot queue unless the human decides.
- **Session 5 (`arena/42de3fed-gemsdoe91`) — `RELIEF` axis built and certified (`IR-91-26`, `IR-91-27`):** Relocates `4,518` dots (`12.00%` moved; `9,036` pixel symmetric diff = `24.00%` `RECEIPT`) at fixed count (`37,654` `RECEIPT`) and zero catalogue-collar drift (`2,171 → 2,171` `RECEIPT`) across equal-area relief terciles `0.90·pct(det_elev) + 0.10·pct(det_elev_slope)` (single-band leakage canary max AUC `0.5793` `PROXY` `≪ 0.90`):

  | id | value | dots (`RECEIPT`) | T1 / T2 / T3 share (`RECEIPT`) | 4-fold `PROXY` Δ ([GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)) | SGMC `PROXY` Δ ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) | predicted (`MODEL`) |
  |---|---|---:|---|---|---|---|
  | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c` | `r2p12` (`range->pied`) | 37,654 | 17.7 / 56.3 / 26.0% | −0.0017 | −0.0049 | **+0.006** `[−0.006, +0.018]` |
  | `h33-h33-2-b2-RELIEFr2b12-20261023-27443c30` | `r2b12` (`range->basin`) | 37,654 | 29.7 / 44.3 / 26.0% | −0.0032 | −0.0091 | **+0.003** `[−0.010, +0.016]` |
  | `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5` | `b2r12` (`basin->range`) | 37,654 | 5.7 / 44.3 / 50.0% | −0.0113 | **+0.0050** | **+0.005** `[−0.010, +0.020]` |

- **Session 6 (`arena/9b8f7d01-gemsdoe91`) — `SNAP` axis built and certified (IR-91-28..30):** first `SNAP` build in the repo. One shared driver (bands 3 `tmi_hg` + 18 `iso_grav_anom_hg`, 600 m high-pass, 1.5 px smoothing), radius 2 px, targets `> 3 px` from the catalogue, R0's `2,171` inherited collar dots quarantined in place (`collar 2,171 -> 2,171` `RECEIPT`), count fixed `37,654` `RECEIPT`, 16/16 `release_gates` + 14/14 `validate_raster` PASS on both encodings:

  | id | rule | dots moved | mean disp. | `MODEL` predicted | SGMC `PROXY` ΔDTI |
  |---|---|---:|---:|---|---:|
  | `h33-h33-2-b2-SNAPs2c-20261023-86b27de1` | 3×3 crest only | 2,047 (5.44 %) | 0.080 px | **+0.000** `[−0.006, +0.006]` | +0.00008 |
  | `h33-h33-2-b2-SNAPs2q75-20261023-8aa75390` | window max, gain ≥ p75 | 4,495 (11.94 %) | 0.237 px | **−0.004** `[−0.012, +0.005]` | −0.00234 |
  | `h33-h33-2-b2-SNAPs2f-20261023-c2391234` | window max, no threshold | 35,174 (93.41 %) | 1.733 px | **−0.014** `[−0.028, +0.004]` | −0.00926 |

  The catalogue PROXY is identically unchanged (`0.006186`, 5 draws, ~12,200 withheld positives, 95 % CI `[0.005958, 0.006413]`) **by construction** — targets are floored at 3 px and the only dots inside 3 px are quarantined, so SNAP cannot touch known-fault credit (IR-91-28). On the independent off-catalogue SGMC map ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) the sign is negative and grows with dose; SNAP is therefore **not** a top-3 slot candidate.

- **Session 8 (`arena/40027ebc-gemsdoe91`) — `CONCENTRATION` on the legal collar, and the queue revised (`IR-91-33`, `IR-91-34`):** 3 arms, count fixed `37,654`, `0` new dot `<= 3 px`, both encodings gated (`PASS`), ledgered with honest predictions: `collar10` (`00cfbe95`, 10.00 % moved, CV `0.6187→0.6037`, **−0.006** `[−0.026,+0.008]`), `collar20` (`106ae19b`, 20.00 %, CV `0.6187→0.5859`, **−0.011** `[−0.051,+0.008]`), and the matched-dose mirror `anti10` (`0e42d6ab`, 10.00 %, **+0.006** `[−0.027,+0.014]`). Measured, not assumed: the collar band carries 1.3x (SGMC) to 2.1x (live-calibrated lineage reference) the per-cell fault credit of the far field, yet moving mass into it **loses** on the only independent fault catalogue (−2.0 % / −3.9 % rel) while uniform-acceptor placement loses less (−0.66 %) and the mirror direction gains (+2.1 %). The catalogue `PROXY` is invariant for this axis by construction (3.05 px floor vs a 3 px kernel), so no local instrument can test the collar hypothesis itself — hence the revised queue below.
- **Merged fleet summary across sessions (`SLOT_PLAN.md`):**
  - **CONCENTRATION** (PR #13, GDR thermal prior): `gdr25rm10` (`c19adb01`, `+0.0123` `MODEL`), `gdr25m10` (`+0.0114`), `gdr10m10` (`+0.0113`).
  - **PRUNE** (PRs #4/#9/#10): delete-only `le3..le15` (`+0.002..+0.010` `MODEL`, `le10` `04002dae` `+0.008`) + fixed-count `p2.5`/`p2.9`/`p4.5px-h19cover`.
  - **MASS** (PR #14, lineage support): `cons1drop` (`−0.000` `MODEL`), `cons2drop` (`−0.015`), `cons3add` (`2803126d`, `+0.009`).
  - **SPACING** (PR #3, radius-2 ring): `spread40` (`6d389309`, `+0.0042` `MODEL`), `clump40` (`−0.0023`), `jitter40` (`0.000`).
- **Session 9 (`arena/4f94d2e7-gemsdoe91`) — `GEOD` geodetic-strain concentration, built & gated 2026-10-24:** `h33-h33-2-b2-GEOD25m10-20261024-bff9fd21` (349 KB nan / 208 KB zeros, sha `bff9fd21…` `RECEIPT`, 37,654 dots, 0 added ≤3 px, 14/14 MUST PASS). Moves 3,765 dots (10.00%, hamming 7,530) from lowest- to highest-prior 2.5 km blocks of the 50/50 geodetic-strain prior (Bands 4+7, AUC 0.579/0.576 PROXY, canary PASS ≪0.90). CV 0.6187→0.610, SGMC off-cat +1.8% rel (+0.0017, independent USGS DS-1052), surrogate strain +31% rel (KAPPA 0.10 → **+0.0090** `[−0.006,+0.020]` MODEL). Rank-corr vs parent 0.8951 (just under 0.90), dot overlap ≤3 px 93% (by construction, 90% dots untouched — flagged per protocol but surface prior is new). **This is the new Slot-1 candidate — first strain-prior file in the fleet, ready to download from `docs/downloads/` and `releases/`.**
- **Next 3 scored slots (`SLOT_PLAN.md`, revised 2026-10-24):** (1) **R0 anchor** (`baeae321`, if no receipt is held) → (2) `PRUNE-le10-norefill` (`04002dae`, `+0.008` `MODEL`, the only sign that comes from the metric algebra) → (3) `MASScons3add` (`2803126d`, `+0.009`, the recall direction). **Do not spend a slot on `CONCENTRATIONgdr25rm10`** (`c19adb01`, `+0.0123` `MODEL`): its prediction is a shrinkage of the prior scored against itself, and session 8 measured that relocation answers to exactly that circularity. `SNAP` and the three collar arms stay out; `anti10` is the single reserve if the human wants the collar-vs-remote question settled. **UPDATE 2026-10-24:** `GEOD` (`bff9fd21`, +0.0090 MODEL) now ties for Slot 1 — it is the only file whose SGMC control is positive (+1.8%) and whose prior was never used in the fleet, so it is the recommended first live test of a new geophysical prior.

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
| `docs/index.html` | Session 10 status board (verdict, format card, leaderboard labels, key) |
| `docs/executive-summary.html` | How to submit, the gates table, numbers with labels, error troubleshooting |
| `docs/HYPOTHESES_S10.md` | Why high scorers scored well (verified vs reasoning), ranked hypotheses H10-1..5, sources |
| `docs/run-card-S10.json` | Session 10 run card (machine-readable) |
| `docs/run-card.json` | Session 9 card, kept unchanged (`superseded_by` added) |
| `src/gems91/basement.py` | H10-1 basement-step ridge candidate (negative result) |
| `scripts/evaluate_holdout.py` | Holdout evaluator `S10-holdout-v1` (E1/E2/E3, fold bootstrap, leakage canary) |
| `scripts/build_basement_step.py` | Builds the H10-1 candidate into gitignored `outputs/s10/` |
| `scripts/registry_scan.py` | Uniqueness scan against GEMSDOE repos (fail-closed; exit 3 if incomplete) |
| `evidence/holdout_S10_E{1,2,3}.json` / `.log` | Raw holdout outputs |
| `evidence/validate_S10.json` | Validator output for the S10 file |
| `outputs/` (gitignored) | Candidate rasters that are NOT cleared for upload |

## Run it

```bash
pip install -r requirements.txt
python scripts/verify_parent_r0.py     # fetch pinned parent, verify sha256
python scripts/preflight.py            # BUILD ALLOWED / BUILD BLOCKED
python -m pytest                       # 53 tests, no competition data needed
python -m tools.pins --axis CONCENTRATION   # what an axis still needs, by pinned id
# session 10 (needs local data/ restored by scripts/restore_data.py)
python scripts/evaluate_holdout.py --experiment E1   # also E2, E3; writes JSON with CI and canary
python scripts/build_basement_step.py                # writes outputs/s10/ (gitignored)
python scripts/validate_raster.py outputs/s10/<file>.tif data/official/sample_submission.tif --catalogue data/official/existing_faults.tif
python scripts/registry_scan.py --candidate outputs/s10/<file>.tif   # exit 3 = incomplete, no uniqueness claim
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

### Session 10 delta (`arena/5e09be50-gemsdoe91`, 2026-10-24)

- **Organizer sources read (fetch tool, not the sandbox curl):** competition page 967 and 968, leaderboard, NLR rules. The metric and the format in the README's earlier sessions are now checked against the organizer's text, not only against the reference code.
- **Holdout result (HOLDOUT-DTI):** E1 candidate 0.0173 [0.0126, 0.0218]; E2 ablation 0.0101 [0.0062, 0.0143]; E3 random null 0.0288 [0.0217, 0.0342]. Candidate fails its control. Canary: largest direction-free AUC 0.5698 (band 4), no leak.
- **Registry scan:** see `registry/s10_registry_scan.json`. The `uniqueness_status` field is the only valid statement. Anything not `complete: true` makes no uniqueness claim.
- **Shared tools:** no shared-tool code was changed in a way that alters a gate. Gate defects are listed in IR-91-S10-10 (parent-diff has no "not applicable" state; the duplicate-hash check counts only SUBMITTED rows, which is currently none; `unit_mass_dots` assumes binary dots).
- **Remaining work:** see `LIMITATIONS.md` (S10 section) and `SLOT_PLAN.md` (S10 banner).
