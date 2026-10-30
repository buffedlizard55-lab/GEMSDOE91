# Archived same-day repo review, 2026-10-30 (branch `arena/29d7bb05-gemsdoe91`)

> **Archive note:** this is a separate branch's 2026-10-30 review, not the active branch's current decision. See [`CURRENT_REVIEW.md`](CURRENT_REVIEW.md) for the active `arena/828b6720-gemsdoe91` review and status.

**Historical verdict in that review: NO NEW TIFF GENERATED · OK TO DOWNLOAD: NO NEW CANDIDATE · OK TO SUBMIT: NO.**
This review ran 0 geological experiments and used 0 of the 3 budgeted experiments. It spent 0 weekly submission slots.

## 1. What is blocking a new, valid submission

| Blocker | Evidence (checked this session) |
|---|---|
| The competition inputs are absent from this checkout. `data/` does not exist. | `ls data` returns nothing. The official files named in `registry/data_manifest.json` (`sample_submission.tif`, `existing_faults.tif`, `training_features`) live only on DrivenData behind a login. |
| The sandbox can only reach GitHub, PyPI and npm. | Sandbox policy. DrivenData and Dropbox are not on the allowlist. |
| `scripts/restore_data.py` fills the gap from **public GitHub mirrors** of other GEMSDOE repos. | See irregularity **I-1** below. I did not run it, and I did not use those mirrors. |

Without `sample_submission.tif` there is no organizer-defined grid, footprint, or transform to check a new raster against. Any raster I built now would be checked against a grid I had invented. That would be a fabricated format check, so I did not build one.

## 2. Verified facts (with links for manual review)

| # | Claim | Result | Source |
|---|---|---|---|
| F1 | Live leaderboard, rank #1 | **0.4544** (xiaofanhu, 35 submissions). The prompt's 0.4413 and 0.3195 are stale. | [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), fetched 2026-10-30 |
| F2 | Submission format | Single-band GeoTIFF, single raster layer, **100 m** resolution, covering the **entire GeoDAWN study area**. | [Official Rules, §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (fetch chunk 2 of 7; §3.2 text) |
| F3 | Submission limit | Up to **3 submissions per week**. One final submission. | Official Rules §3.2 and §3.4 |
| F4 | Generative-AI disclosure | Required **in the narrative** if generative AI was used. | Official Rules §3.2 |
| F5 | Evaluation metric | Distance-weighted Tversky index. False negatives are penalised more than false positives. | Official Rules §3.6.1 |
| F6 | Training labels source | INGENIOUS Great Basin compilation, DOI 10.15121/1881483. | Official Rules §3.3, footnote 4 |
| F7 | Format audit of the 70 research GeoTIFFs in `docs/downloads/` | 70 files. **7** have NaN outside the footprint (7,111,787 NaN cells each). **63** are fully finite in [0, 1]. Each of the 7 has a `-zeros` twin with the same number of positive cells. | `scripts/audit_download_formats.py` → [`tif-format-audit.json`](tif-format-audit.json) |
| F8 | Test suite | `pytest` exit 0 in `.venv` (pinned `requirements.txt`). No failures printed. | Run this session. The README's older note about one failing test (`test_prior_s18_files_are_registered...`) no longer reproduces. |

## 3. The "Predicted values must be in range [0, 1]" error

- **Best-supported cause (inference, not reproduced):** files that carry NaN outside the footprint (the `-nan` / unsuffixed twins). NaN fails a range check. F7 confirms these twins exist and are the only research files with NaN.
- **Format-only observation, not an action to submit:** every audited `-zeros` file was locally finite with values in {0.0, 1.0}, but this does not validate the official grid, geology, uniqueness, third-party rights, or organizer acceptance. The active review does not approve any historical file for download or submission. The suspected NaN cause is an inference; the organizer validator was not accessible, and the error was not reproduced.
- Earlier repo notes (`IRREGULARITIES.md` IR-S26-02, IR-91-S13-03) reached the same conclusion.

## 4. The nine focus sites (prompt values, user-reported, not organizer-confirmed)

| Site | Best claim in the prompt | Status in repo |
|---|---|---|
| GEMSDOE24 | 0.2477 | Listed in `docs/executive-summary.html` |
| GEMSDOE25 | 0.2600 | Listed |
| GEMSDOE27 | 0.2449 | Listed. **Omitted from the table:** `gems27-h29` 0.2190 and `gems27-h31` 0.2250. |
| GEMSDOE28 | 0.2710 | Listed. **Omitted from the table:** `h32-1` 0.2649 and `h38-1` 0.2707. |
| GEMSDOE30 | 0.2600 | Listed |
| GEMSDOE31 | 0.2708 | Listed |
| GEMSDOE32 | **0.2778** (highest of the nine) | Listed. Score is USER-REPORTED. No organizer receipt. |
| GEMSDOE33 | 0.2632 | Listed |
| GEMSDOE36 | 0.2750 | Listed |

No file on these sites has an organizer receipt. Their pairwise overlap is high, so they are not independent submissions. The repo's existing duplicate audit (`docs/executive-summary.html`) reports GEMSDOE28's best file at 100.00% overlap with GEMSDOE24. That is a repo-measured figure, not one I re-derived this session.

**Answer to "why did GEMSDOE32 score highest, and can we beat 0.2778?"** I cannot answer this from the repo alone. The score is user-reported, and no organizer receipt binds it to a file. The repo has no holdout-verified evidence that the GEMSDOE32 raster beats the others. Beating the user-reported 0.2778 would also not reach the 2026-10-30 public-leaderboard snapshot (0.4544), which is not a receipt for a focus-site file. I have not tested a candidate against it, so there is no basis for a claim that a new file would beat it.

## 5. Irregularities flagged for review

- **I-1 (data provenance/rights, unresolved): competition and derived rasters have GitHub mirror routes.** `registry/data_manifest.json` records `mirror` entries and `scripts/restore_data.py` fetches those copies in its default mode if local files are absent. This review used only `--check`; it did not fetch mirror data. The official competition data page redirects anonymous users to login. Rules §3.3 describes training data provision to registered participants and Appendix A.5 requires rights to third-party content, but this repository cannot establish authorization for the mirror copies. **Recommendation:** do not use mirror-backed competition inputs until provenance and rights are resolved via an authorized route. This is an unresolved risk, not a claim of a confirmed violation.
- **I-2 (process, historical to branch `arena/29d7bb05`): status banners conflicted in that checkout.** Its README's then-top banner said "OK TO DOWNLOAD: YES" for S27-OSDR while also saying "OK TO SUBMIT: NO" and recording a literal synthetic-lattice overlap failure. This archived finding does not describe the active branch's current README; the active top banner now states no new candidate is approved.
- **I-3 (unverified score):** every score in the prompt for the nine focus sites is user-reported. The repo labels them USER-REPORTED, which is correct.
- **I-4 (holdout vs. live):** holdout DTI values in the repo are measured on the repo's own withheld catalogue faults. They are not leaderboard scores. The repo's own check reported a weak live correlation for the hide-v2 holdout (Spearman +0.105). Treat holdout numbers as diagnostics only.
- **I-5 (uniqueness):** the uniqueness rule (≤70% of dots within 3 px of any other file) is applied only against the repo's registry. Files on other GEMSDOE sites that are not in the registry were not all checked this session.
- **I-6 (prompt scope):** the prompt asks for several things at once (leaderboard strategy, hypothesis ranking, a new TIF, a PR merge). With the data blocked, only the review and documentation parts can be completed honestly this session.

## 6. Labels for every number in this review

- Leaderboard `0.4544` → **PUBLIC-LEADERBOARD SNAPSHOT** (official page fetched 2026-10-30; not a submission-page receipt tied to any raster).
- Format audit numbers (F7) → **measured locally** from the repo's own files. These are file properties, not scores.
- 0.2778, 0.2710 and the other nine focus-site values → **USER-REPORTED** (from the prompt).
- No holdout DTI, projection, or estimated score is reported in this review.

## 7. What you need to do to unblock (no manual steps are needed in this sandbox beyond these)

1. Log in to DrivenData and download `training_features` (or the GeoDAWN feature TIFF), `labels`, `sample_submission.tif`, `existing_faults.tif`, and the DEM link list from the [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/). Place them in `data/official/` on a machine with the terms accepted. Do not use public mirrors.
2. Run `python scripts/prepare_data.py` to check the sha256 values against `registry/data_manifest.json`.
3. Once the grid is checked, a new lane can be assigned within the 3-experiment, 2-hour budget. Only then can a new TIF be generated and validated.
4. Decide I-1 before any further upload.

## 8. Next steps (in priority order)

1. Resolve I-1 (mirrored competition data) with the competition terms.
2. Get the organizer's exact portal message for the range error, to confirm the NaN cause (§3).
3. After step 1 of §7, run the full pipeline on the official grid and produce a `-zeros` file with a fresh uniqueness check and a holdout result labeled HOLDOUT-DTI.
4. Consolidate the conflicting README banners (I-2) into one current status.

## 9. Three-pass record

- **Pass 1 (implement and verify):** checked the leaderboard, the official rules, the data directory, the research TIFs (70 files), and the nine-site table. Wrote `scripts/audit_download_formats.py` and its output.
- **Pass 2 (bugs, missing requirements, assumptions):** found the GEMSDOE28 omission (§4), the conflicting banners (I-2), and the mirror issue (I-1). Confirmed each NaN file has a `-zeros` twin before recommending it.
- **Pass 3 (re-check against the original request):** the review gives no new score and no new file, because no valid input exists in this sandbox. Every number is labeled. The unblock path in §7 is what the user needs to act on.

Archived other-branch run card: [`run-card-arena-29d7bb05.json`](run-card-arena-29d7bb05.json). The active branch's separate negative run card is [`run-card.json`](run-card.json).
