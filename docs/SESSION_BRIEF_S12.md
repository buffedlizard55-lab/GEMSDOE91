# Session brief — S12 (2026-10-24, `arena/80f7c032-gemsdoe91`)

**Read this first at every session start, together with the README.** It supersedes `docs/SESSION_BRIEF_S11.md` where the two differ.

> **Provenance note.** This brief is a summary of the session request, as recorded in the session memory. The user's exact text is not stored in this repository, so this is **not verbatim**. The S11 brief (`docs/SESSION_BRIEF_S11.md`) is verbatim for its own session.

## 0. Status in one screen

| Item | Status |
|---|---|
| Can the current file be **downloaded**? | **Yes, as research only.** The S11-MHTR E2 TIF is a format-valid research file. Download link: `docs/s11-mhtr.html` (research audit page). |
| Can it be **submitted**? | **No.** The shared fail-closed readiness gate (`src/gems91/readiness.py`) fails every check. See §3. |
| New GeoTIFF generated this session? | **No.** No candidate cleared the gates, and H12-1 scored below baseline. See §4. |
| Best verified holdout | **S11-MHTR E2 `0.206406`** (`HOLDOUT-DTI`, CI `[0.193796, 0.220176]`), reproduced byte-identically this session (§5). |
| Session 12 hypothesis | **H12-1 negative**: `0.113042` (CI `[0.102124, 0.123819]`). Its gravity-only control scores the same. |
| Experiment budget | 2 of 3 used (one invalid attempt, IR-91-S12-03). Reproductions and controls are not counted. |
| Lane | **Not assigned.** The brief has no lane paragraph (IR-91-S12-01). |
| Pull request | Opened and merged to `main` as described in §10 (after CI). |

## 1. Core values (the framework)

- **Maximize P(Win):** prefer falsifiable discovery, leakage-safe evaluation and honest negatives over speculative leaderboard deltas or filling scarce slots.
- **Own the Outcome:** generate real bytes, inspect them automatically with repo validators, preserve provenance, and state every blocker plainly.

## 2. Standing rules (apply to every session)

1. **Automated inspection only.** No human inspector. A format PASS is not a novelty, science or selector PASS.
2. **Never copy a previous GEMSDOE submission.** Learning from one is allowed. Any new file must be unique.
3. **Verify line by line.** Every number is labelled `HOLDOUT-DTI` (evaluator version, withheld-positive count, 95% CI) or `ORGANIZER-CONFIRMED` (copied from an organizer receipt). Projections are never scores. Labels used this session:
   - `0.4413` → ORGANIZER-CONFIRMED (public leaderboard row #1 read 2026-10-24; not a personal receipt)
   - `0.2778`, `0.3195` → **CLAIM, unverified** (IR-91-S10-05, IR-91-S11-09)
   - `0.206406`, `0.138999`, `0.113042` etc. → HOLDOUT-DTI
4. **Leakage canary.** Each feature alone is tested on the holdout; symmetric AUC above 0.90 means leakage.
5. **Run card.** End every session with one JSON card: `evidence/h12/run_card_S12.json` (S12).
6. **Budget.** Stop after 3 experiments or 2 hours. Do not pick a submission slot; that is a separate selector step within the weekly cap.
7. **Reproductions run in an isolated copy** (`/home/user/repro-s11`), so published evidence and downloads are never overwritten.
8. **Flag irregularities** in `IRREGULARITIES.md` and never silently change shared tools.

## 3. The current file: why "download yes, submit no"

- **Automated gate (fail-closed):** `readiness.gates()` on `docs/run-card-S11.json` returns False for `format`, `canary`, `novelty`, `assigned_lane`, `beats_comparable_best` and `separate_selector`.
- **The S11 card says `promote`, and this is a schema mismatch.** The card lacks the `canaries`, `lane`, `registry_comparison`, `holdout_dti` and `comparable_prior_holdout_best` fields that the gate reads. The lane gate also fails for the real reason: no assigned lane (IR-91-S12-02).
- **Real blockers that no agent can clear:** no assigned lane; no complete universal registry; no comparable prior holdout best; no selector approval; and the human-only items in §8.
- **Portal:** `docs/index.html` shows the status board (SHA-256, format status, "YES · research only" for download and "NO" for submit). Each row links to its audit page, not to a `download` file. The download test (`tests/test_submission_portal.py`) requires that only the current artifact is advertised as a download.

## 4. The unique TIF request — what was done and why no new file exists

- **No new GeoTIFF was generated this session.** The candidate that cleared the most checks is the S11 file already in `docs/downloads/`. Its gates still fail.
- **H12-1 (this session's only new candidate) scored below both the B0 baseline and the S11 candidate.** A file for it would have been a negative-score submission, and the project's policy is not to publish one as a submission.
- **Uniqueness.** The S11 candidate has SHA-256 `dbfe7dfc27a93792abc0e73aa9e2ade3a7bbe69e6f71ec0927e176466e588b15`. In the isolated S11 reproduction its E2 emission passed the registry duplicate gate (max 3 px overlap 0.4947 on `calib_h161_01855.tif`, limit 0.70; max surface |ρ| 0.1577, limit 0.90). The README's "62-raster" uniqueness claim was **not** re-run this session. The duplicate gate also passes a random null (IR-91-S12-10), so it is not evidence of novelty on its own.
- **To produce a new unique TIF:** a human must first assign a lane (IR-91-S12-01). The next experiment must beat the reproducible B0 and S11 baselines on the same folds. Budget remaining: 1 experiment.

## 5. Session 12 measurements (labels per §2.3)

### 5.1 H12-1 — physics-only gravity–magnetic co-location (`scripts/run_h12_colocation.py`)

Score (pre-registered, no tuned parameters): `max(z(tmi_hg),0) · max(z(hypot(B11,B18)),0)`. Dots: greedy top-score with 3.05 px spacing, S11 fold quotas, `gems91-hide-recover-v1.0`, α 0.2, β 0.8, R 300 m.

| Run | HOLDOUT-DTI | 95% CI | Withheld positives | Status |
|---|---|---|---|---|
| **E1 (attempt B) — H12-1 co-location** | **0.113042** | [0.102124, 0.123819] | 60,988 | valid candidate |
| C_random_placement | 0.039281 | [0.036582, 0.042025] | 60,988 | null control |
| C_gravity_only | 0.113965 | [0.09951, 0.127143] | 60,988 | single-field control |
| C_magnetic_only | 0.104154 | [0.092042, 0.115508] | 60,988 | single-field control |
| E1 (attempt A) — `\|B18\|` | 0.116884 | [0.107308, 0.127679] | 60,988 | **INVALID** (wrong gravity term, IR-91-S12-03) |

- **Reading:** the co-location product adds nothing over gravity alone (`0.113042` vs `0.113965`, CIs almost fully overlapping). The gravity term carries the signal, so H12-1 is **not supported as a co-location mechanism**.
- **Leakage canary:** `all_pass = True`. Worst symmetric AUC `0.57138` (`z_grav`), limit 0.90.
- **Registry overlap (8 rasters):** surface max |ρ| `0.03474`; final dot 3 px overlap max `0.24834` (vs `calib_h161_01855.tif`). Both gates PASS, but the random null also PASSES (IR-91-S12-10).
- **Named non-fault mimic:** lithologic and intrusive contacts, and basin margins, also carry joint gravity and magnetic gradients.
- **Verdict: negative. Not promoted.**

### 5.2 Reproduction of published lanes (isolated copy, not counted against the budget)

| Lane | Experiment | Published | Reproduced | Match |
|---|---|---|---|---|
| H91 | B0 (raw 19 bands, Poisson thinning) | 0.138999 | 0.138999 | exact |
| H91 | R0 SGMC control | 0.095386 | 0.095386 | exact |
| H91 | H91-1 E1 | 0.174030 | 0.174030 | exact |
| H91 | H91-1+2 E2 | — | 0.166750 | recorded in its log |
| S11 | E1 H11-1 | 0.202272 | 0.202272 | exact |
| S11 | E2 H11-1+2 (**winner**) | 0.206406 | 0.206406 (CI `[0.193796, 0.220176]`) | exact |
| S11 | E3 H11-1+2+3 | — | 0.205989 | recorded in its log |
| S11 | SGMC control (E2) | 0.097623 | 0.097623 | exact |

**Candidate bytes:** the isolated S11 run wrote `gems91-mhtr-e2-20261024T170000Z-9554f718-zeros.tif` with SHA-256 `dbfe7dfc27a93792abc0e73aa9e2ade3a7bbe69e6f71ec0927e176466e588b15`, byte-identical to the published file. The NaN twin is `9554f7183b39f2825432533a4276f3a95b4dae26887c2df3ad2b13793bb2ac94`, which also matches the README. The run then failed at a `git checkout` line outside a git repo, after outputs were written (IR-91-S12-12).

Two reproduction caveats are recorded, not hidden:
- The S11 lane reads `h91_fold_cat_full.dat`, which the H91 lane does not write. For the reproduction only, a symlink to `h91_full_cat_features.dat` was made in the gitignored `data/derived/` (IR-91-S12-07). The byte-identical result validates the bridge.
- The H91 lane prints `0.2778` as `ORGANIZER-CONFIRMED`. That is incorrect (IR-91-S12-05).

## 6. The question: why did 0.2778 score highest, and can we beat it?

**What the repository can verify**

- **0.2778 (GEMSDOE32, `h33-h33-2-b2-…-zeros`) has no organizer receipt here** (IR-91-S10-05). The repo's own documentation disclaims organizer scores (IR-91-35).
- **0.3195 is not on the public board read** (IR-91-S11-09). The board goes `0.3217 → 0.3169`.
- **Public leaderboard read, 2026-10-24** (`https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/`): #1 0.4413 (xiaofanhu), #2 0.3916, #3 0.3904, #4 0.3724, #5 0.3539, #23 0.3217, #24 0.3169, #50 0.2818. A score of 0.2778 would rank below #50 on that read. Whether it is "the highest among listed GEMSDOE sites" cannot be checked here.

**Why such a score could be high (mechanism, from the official metric)**

The official metric is a distance-weighted Tversky index with α = 0.2 (false positives) and β = 0.8 (false negatives), using a triangular kernel of R = 300 m (3 px) (official page 967: `https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/`). The β weight penalises missed faults about four times as heavily as false alarms. So a high score rewards **dense, well-spaced dots that cover plausible fault traces within 300 m**. Sparse, confident placements score poorly even when precise. The transcribed formula is checked by `tests/test_dti_official_formula.py` (40 random cases). This is a mechanism for why a dense placement can score well. It is **not** evidence about how GEMSDOE32 was built.

**Can a submission exceed 0.2778?**

- **Unknown and not demonstrated.** Our best holdout (`0.206406`) measures catalogue recovery, which is not the organizer's score on new faults (IR-91-S10-04). No holdout number converts to a leaderboard score. A public-board score of 0.2818 sits at #50, so a 0.28+ score is plausible, but this repository has no organizer-scored candidate.
- **Not achievable within the verifiable evidence:** a verified score above 0.4413 (public #1). The gap is large.

## 7. Sources (official, verifiable)

- Competition page & metric: `https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/` (page 968 is cited in the repo but was not re-read this session).
- Leaderboard: `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/`
- Official rules (Sept 2026): `https://docs.nlr.gov/docs/fy26osti/96647.pdf` (read in full this session, chunks 0–6).
- GeoDAWN data release: `https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and` (DOI `10.5066/P93LGLVQ`, CC0 1.0).
- INGENIOUS project: `https://gbcge.org/current-projects/ingenious/`. Training-label compilation DOI `10.15121/1881483`.
- CRS: `https://epsg.io/32611` (UTM 11N, the metric's CRS).
- USGS SGMC map DS-1052: `https://pubs.usgs.gov/ds/1052/`.
- Not yet read this session, listed for manual review: `https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516` (scoring masking clarification, which bears directly on IR-91-S10-04).

## 8. Rules items for a human (rules PDF, read this session)

- **§3.4 / §3.5:** one final submission per entity, chosen before the deadline across both prize rounds, and the choice is made without knowledge of private-set scores (§3.6.2). Feedback submissions are capped at three per week.
- **§3.5 finalists:** code and documentation sufficient to reproduce the results.
- **§A.1:** a human signatory must certify under penalty of perjury that the submission is true and that the competitor is eligible. **The agent cannot sign.**
- **§A.4 / §A.10:** elements designated public "become publicly available" and are licensed for public display. Publishing a TIF on GitHub Pages is a public release. Materials are DOE records subject to FOIA unless marked.
- **§A.5:** the submission must be an original work, with third-party content disclosed. Inputs include GeoDAWN (CC0), INGENIOUS labels, USGS DS-1052, and two licence-unchecked external inputs (`geodawn_rad_u8`, `lidar_scarp_u8`).
- **§3.2 / `AI_USE.md`:** AI use must be disclosed in the narrative. Not reviewed against this session's work.
- **§1.3:** eligibility (U.S. citizen or permanent resident, U.S.-incorporated entity, and the excluded categories) is a human attestation.

## 9. Irregularities raised this session

`IRREGULARITIES.md`, `IR-91-S12-01` to `IR-91-S12-12`. Headlines:
- **01** no lane paragraph (recurrence)
- **02** S11 card says `promote`; the shared gate fails closed on schema grounds; the H91 card self-declares PROMOTE
- **03** H12-1 attempt A used `|B18|`; its holdout line was seen before the stop
- **04** band 6 has three conflicting identities; measured range does not reproduce the stated mGal range
- **05** `run_h91_lane.py` labels 0.2778 `ORGANIZER-CONFIRMED`
- **06** registry scope is 8, 11 or 62 depending on the code path
- **07** cache-name drift between the H91 and S11 lanes
- **08** human-only rules obligations
- **09** duplicate IR IDs in `IRREGULARITIES.md`
- **10** the duplicate gate does not discriminate (the random null passes)
- **11** the portal download policy is a tested invariant
- **12** `run_s11_lane.py` fails outside a git checkout after writing its outputs

## 10. Pull request and merge

Changes are committed to `arena/80f7c032-gemsdoe91` and pushed. A PR into `main` is opened and merged, with CI checks as the gate. Nothing in this session changes the verdict of any candidate.

## 11. Remaining work (in priority order)

1. **Human:** assign a method lane (IR-91-S12-01). Without it, nothing can clear the gate.
2. **Human:** decide the S11 candidate's status. Its card says `promote` and the gate says no. Fix the card's schema, or record a negative.
3. **Human:** approve the one-line label fix in `run_h91_lane.py` (IR-91-S12-05) and the cache-name and `git checkout` fixes (IR-91-S12-07, -12).
4. **Human + legal:** §A.1 signatory, §A.4 public-element decision for the TIF on GitHub Pages, §A.5 licence review (`geodawn_rad_u8`, `lidar_scarp_u8`), §3.2 AI-use disclosure.
5. **Verify:** band 6 identity against the organizer documentation (IR-91-S12-04). Read the DrivenData scoring-clarification thread (§7).
6. **Experiment (1 left):** only under an assigned lane, and only if it beats B0 `0.138999` and S11 `0.206406` on the same folds.

## 12. How to verify this session

```bash
cd /home/user/GEMSDOE91
PYTHONPATH=.:src /home/user/venv-gems/bin/python -m pytest -q -p no:warnings
python3 scripts/check_artifact_policy.py
PYTHONPATH=.:src /home/user/venv-gems/bin/python scripts/run_h12_colocation.py   # writes evidence/h12/ only
PYTHONPATH=.:src /home/user/venv-gems/bin/python -c "import json; from gems91.readiness import gates; print(gates(json.load(open('docs/run-card-S11.json'))))"
```
