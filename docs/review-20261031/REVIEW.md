# GEMSDOE91 review — 2026-10-31 (branch `arena/92dfcfdc-gemsdoe91`)

**Verdict: BLOCKED — no new TIFF was generated. `OK TO DOWNLOAD (new candidate): NO` · `OK TO SUBMIT: NO`.**

No file in this repository, and none of the nine user-named GEMSDOE files, is cleared for submission. The competition's inputs (`training_features.tif`, the labels, `sample_submission.tif`) are not in this sandbox. Their DrivenData download page requires a login that this environment cannot perform (verified below). Without them, no holdout score, no footprint check against the organizer's sample, and no lane-assigned experiment is possible. This review states what was verified, what is still unknown, and exactly what unblocks the work.

**Maximize P(Win) · Own the Outcome.**

---

## 1. Direct answers

| Question | Answer (evidence class) |
|---|---|
| Unique, validated TIF ready to download and submit? | **No.** None generated. Blocked on data (§4). |
| Which file should be submitted now? | **None.** Every candidate fails an open gate (§3). |
| Why did GEMSDOE32 (`0.2778`) score highest? | **Not proven.** Verified: its 37,654 dots are an *exact subset* of the 44,090-dot GEMSDOE25/30 raster, and the user-reported gap (+0.0178) is fully explained by the 6,436 removed dots (§2). Whether those removals caused the gain depends on the organizer labels, which we do not have. The `0.2778` value itself is **USER-REPORTED, no organizer receipt**. |
| Can we beat `0.2778`? | **Unknown.** No holdout, no labels, no evaluator run. Any subset of GEMSDOE32 is **100% within 3 px of GEMSDOE32**, so pruning it is a duplicate under the protocol's 70% rule (§2.3). A non-duplicate route needs new geology, which needs the data. |
| Is `0.2778` competitive? | **Not on the live board.** The rank-50 cutoff is `0.3195`; the top score is `0.4544` (ORGANIZER-PUBLIC leaderboard observation, §5). No user-reported site value appears in the top 50. |
| Estimated leaderboard score for any file? | **None.** No estimate is written as a score. Projections are not scores. |

---

## 2. Why the nine-site family scores the way it does (verified structure)

All numbers below come from `docs/review-20261031/nine-site-encoding-audit.json`, produced by `scripts/audit_nine_site_encoding.py` from the byte-verified cache of `scripts/verify_nine_site_leaders.py`.

### 2.1 Identity
Every one of the nine files matches its commit-pinned SHA-256 and byte count in `docs/review-20261030/nine-site-snapshot.json` (9/9 PASS). Each is single-band `float32`, `EPSG:32611`, `3730 × 3292`, 100 m, with values in `[0, 1]`.

### 2.2 Exact dot-set relations (cell-level, not 3-px)
| Subset (user score) | Superset (user score) | Dots removed from superset |
|---|---|---:|
| GEMSDOE32 (0.2778, 37,654 dots) | GEMSDOE31 (0.2708, 40,199) | 2,545 |
| GEMSDOE31 (0.2708, 40,199) | GEMSDOE25 = GEMSDOE30 (0.2600, 44,090) | 3,891 |
| GEMSDOE32 (0.2778, 37,654) | GEMSDOE25 = GEMSDOE30 (0.2600, 44,090) | 6,436 |
| GEMSDOE32 (0.2778, 37,654) | GEMSDOE36 (0.2750, 38,854) | 1,200 |

GEMSDOE25 and GEMSDOE30 have identical dot sets (their file encodings differ outside the footprint).

### 2.3 What this means
- **The score gap is a pruning effect, under the user's reported numbers.** On a fixed label set, `DTI(GEMSDOE32) − DTI(GEMSDOE25)` depends only on the 6,436 dots that were removed. The reported gap is +0.0178, so those dots were net-negative in the distance-weighted metric.
- **The per-dot gain is nearly constant along the chain:** 0.0178/6,436 ≈ 2.77×10⁻⁶; 0.0108/3,891 ≈ 2.78×10⁻⁶; 0.0070/2,545 ≈ 2.75×10⁻⁶ (scores from the user-reported values). A first-order model predicts this if the removed dots carry no true-positive credit, since each removal lowers only the false-positive term by α = 0.2. This is a consistency check on user-reported numbers, **not a measured result**.
- **Uniqueness blocks the obvious fix.** Any pruned subset of GEMSDOE32 has 100% of its dots within 3 px of GEMSDOE32. That is a duplicate under the protocol's 70% gate. A higher-scoring file must therefore be a *different* dot set, and choosing which dots to keep requires labels or a holdout.
- **Marginal rule used for any future selection** (pointwise approximation of the metric, derived here; not a measured result). With `T = TP_w`, `F = FP_w`, `N = FN_w`, adding one dot with expected TP gain `t`, FP gain `f`, and FN reduction `n` raises DTI iff `t·(αF + βN) > T·(αf − βn)`. A pure false positive (`t = 0`, `f = 1`, `n = 0`) can never raise DTI. The exact metric uses a max over neighbours, so this is a guide, not a proof.

### 2.4 Where the owner pages disagree (flagged, not resolved)
The GEMSDOE32 owner page (fetched 2026-10-31) says `0.2778` is an owner-provided log claim with no receipt, says "DO NOT SUBMIT anything below", and reports two contradictory H51 results (a `0.115134` hide-recover figure later corrected to `0.002289`, with the emitted H51 file lower than the champion). We did not verify those evaluator results. They are flagged for review.

---

## 3. Nine-site table (research downloads only)

Columns: file (commit-pinned raw link), user-reported value, dots, encoding outside footprint, SHA-256 identity vs snapshot, max 3-px overlap into any other of the nine (Euclidean, from `scripts/verify_nine_site_leaders.py`), closest peer, unique among the nine at 70%, download, submit.

| Site | File (commit-pinned) | Reported value | Dots | Outside footprint | Identity | Max 3-px overlap | Closest peer | Unique among nine? | Download | Submit |
|---|---|---|---:|---|---|---:|---|---|---|---|
| GEMSDOE24 | [gems24-…-nan.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE24/6284a525a9425ed442f8e3fc0e04dfbd6fce537d/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | 0.2477 (user-reported) | 60,069 | NaN | PASS | 100.00% | GEMSDOE25 | NO | research only | **NO** |
| GEMSDOE25 | [gems25-…-nan.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE25/b55a246a155c1d65430382aa3edaa51749d44360/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | 0.2600 (user-reported) | 44,090 | NaN | PASS | 100.00% | GEMSDOE24 | NO | research only | **NO** |
| GEMSDOE27 | [gems27-…-nan.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE27/494ec17625bf8fe9e19510ec3f39912451c4f7f7/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | 0.2449 (user-reported) | 61,328 | NaN | PASS | 98.02% | GEMSDOE24 | NO | research only | **NO** |
| GEMSDOE28 | [gems28-…-nan.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE28/a1c0e18f4a4f7394ce549f1d61f2a229d5cfabfa/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | 0.2710 (user-reported) | 37,660 | NaN | PASS | 100.00% | GEMSDOE24 | NO | research only | **NO** |
| GEMSDOE30 | [gemsdoe30-…-91eae1ca.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE30/d855914332b29c0b36974d5462ba9fd5dca21136/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 (user-reported) | 44,090 | zeros | PASS | 100.00% | GEMSDOE24 | NO | research only | **NO** |
| GEMSDOE31 | [gemsdoe31-…-nan.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE31/adf37ffd9d6a78e5b90a68bfe2033509124517d1/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | 0.2708 (user-reported) | 40,199 | NaN | PASS | 100.00% | GEMSDOE24 | NO | research only | **NO** |
| GEMSDOE32 | [gemsdoe32-…-zeros.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE32/0ffda7162e76291df34359345488ff08b4115aac/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | 0.2778 (user-reported) | 37,654 | zeros | PASS | 100.00% | GEMSDOE24 | NO | research only | **NO** |
| GEMSDOE33 | [GEMSDOE33-…-cb490425926e.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE33/1a7f53ca35648900998a061d7e864ab41ee1334d/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 (user-reported) | 41,865 | zeros | PASS | 99.71% | GEMSDOE27 | NO | research only | **NO** |
| GEMSDOE36 | [gemsdoe36-…-zeros.tif](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE36/e280188adbbe762e6b7ac6f3b8e105e8e7915026/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 (user-reported) | 38,854 | zeros | PASS | 97.58% | GEMSDOE27 | NO | research only | **NO** |

Estimated leaderboard score: **none** for every row (not organizer-scored, no receipt, no holdout). Full SHA-256 values are in `nine-site-encoding-audit.json`. Historic evidence-class labels are in `docs/review-20261030/`.

**Nothing in this table is a new unique submission.** Every row is in a single near-duplicate family (§2.2).

---

## 4. Format rules — verified against official text

Fetched 2026-10-31 (see §6 for links).

| Requirement (official text) | Source | Repo check |
|---|---|---|
| Projected CRS EPSG 32611 (UTM 11N) | DrivenData problem page | All nine: `EPSG:32611` |
| 100 m resolution | DrivenData problem page | All nine: `100.0 × 100.0` |
| Same bounds as training data; data outside the bounds is **null or nan** | DrivenData problem page | Five files use NaN outside a 5,167,373-cell footprint; four use **zeros** outside (§5 item 2) |
| Single layer, `float32`, values in `[0, 1]` | DrivenData problem page | All nine: 1 band, `float32`, finite min 0.0, max 1.0 |
| Up to three submissions per week | NLR official rules §3.2 | Operational cap, unused |
| Rounds: Initial Prize (private test set) then Final Prize (expanded labels) | DrivenData problem page; NLR §1.1 | Unchanged |

**Important limit:** the footprint used here is derived from the user's own files, not from the organizer's `sample_submission.tif` (absent here). The sample is described as predicting "total fault absence", but its outside-bounds encoding is unknown. Check that first when it is placed (§7).

---

## 5. Irregularities flagged for review

1. **The "[0, 1]" submission error is unexplained.** `docs/review-20261030/tif-format-audit.json` says NaN outside the footprint is "the likely cause". The official text explicitly allows NaN outside, so that inference conflicts with the rules. All nine files have values in `[0, 1]`, so either the failing file is not one of the nine, or the failure has another cause. **The cause cannot be determined without the organizer validator or the user's exact uploaded file.** Please send the exact file name and hash.
2. **Zeros-outside encoding conflicts with the literal rule.** Four of the nine files (GEMSDOE30, 32, 33, 36) put `0.0` in the 7,111,787 grid cells outside the 5,167,373-cell footprint. The rule says outside-bounds data is null or NaN. GEMSDOE36's owner page says a zeros-outside historical TIFF fails its strict outside-footprint check. Since the GEMSDOE32 file reportedly scored, the platform may accept zeros, but that is unverified. This needs an organizer answer, or a decision to use NaN outside (the literal reading).
3. **User-supplied leaderboard numbers do not match the live board.** The user said `0.4413` and `0.3195` was "the highest score". The live top score is `0.4544`; `0.3195` is the rank-50 cutoff (`evidence/public-leaderboard-2026-10-31.json`). The 2026-10-27 snapshot also differs from today's ranks.
4. **User-reported site scores have no receipt.** Nothing links them to a leaderboard row. They are all below the rank-50 cutoff, so if real they sit outside the top 50.
5. **Owner-page contradictions** (§2.4, GEMSDOE32 H51 claims) are unresolved.
6. **18 of 23 historical TIFFs fail a "strict" format audit** per the GEMSDOE36 owner page. Not re-verified here; no historical file is promoted.
7. **Method lane is missing.** The protocol says "your lane is the single method paragraph below". No such paragraph is in the prompt. `registry/experiment_plan.json` correctly holds `lane: null`. No experiment was run, and no lane was self-assigned.
8. **Public mirrors of competition data are not used.** `registry/data_manifest.json` pins hashes from GitHub copies of the competition inputs. The repo's own records (IR-S26-05, IR-91-09) say those mirrors have unresolved rights and must not be used. This review did not use them.
9. **Test environment:** the suite needs the pinned `imagecodecs==2026.3.6` from `requirements.txt`. Without it, 7 writer tests fail with `PREDICTOR.FLOATINGPOINT requires the 'imagecodecs' package`. This is an environment issue, not a code bug; with the pinned install, the full suite exits 0.
11. **Test side effects on tracked pages.** Running the suite rewrote `docs/submission-guide.html` during this session (one run replaced it with a page linking `review-4239f6e5/`, a folder not on this branch). The final run left the committed file unchanged. Check `git status` after any test run and do not commit renderer output that you have not reviewed.
10. **Earlier claims that cannot be verified here:** the GEMSDOE36 owner page labels its KPL result `0.1647` USER-REPORTED (no receipt). The user's prompt gives `0.4413` as the leaderboard top and an earlier repo note gives `0.4437`. The live board shows `0.4544`.

---

## 6. Official sources (fetched 2026-10-31; for manual review)

- DrivenData problem description, metric, and submission format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Official Rules (NLR, September 2026), §1.1 prize structure, §3.2 "three submissions per week": https://docs.nlr.gov/docs/fy26osti/96647.pdf
- DrivenData leaderboard (top 50 captured): https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- DrivenData data page — **login required**; not accessible in this sandbox: https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Official reference solution (cloned; commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`, dated 2026-06-16; writes predictions with the labels raster CRS and transform, no nodata): https://github.com/drivendataorg/gems-prize-reference-solution
- GeoDAWN data release (DOI `10.5066/P93LGLVQ`, cited in the official rules): https://doi.org/10.5066/P93LGLVQ
- EPSG:32611 (cited on the official problem page; not reachable from this sandbox): https://epsg.io/32611

Not reachable from this sandbox (checked with curl; resolution or connection failure): drivendata.org, dropbox.com, gdr.openei.org, usgs.gov, epsg.io. The fetch tool reached the DrivenData and NLR pages.

---

## 7. What unblocks the work (one item needs a human with a DrivenData login)

1. **Place the official files** in `data/` (exact names in `registry/data_manifest.json`): `training_features.tif`, the labels raster, `sample_submission.tif`, and the DEM link CSV. Verify each SHA-256 against the manifest. A mismatch must be reported, not patched. `scripts/restore_data.py --check` must not fetch from mirrors.
2. **Check the sample's outside-bounds encoding** (NaN or zero) and its footprint against the 5,167,373-cell footprint in §2. This settles the zeros-vs-NaN question for the organizer's grid.
3. **Confirm the method lane** as a single paragraph with its source. Until then, no experiment runs (protocol Rule 1).
4. **Send the exact file that produced the "[0, 1]" error** (name and SHA-256), so the cause can be checked.
5. **Decide the encoding policy:** NaN outside (literal rule) or zeros outside (matches four historical files). Recommendation: NaN outside, since it follows the official text. Confirm with the organizers if possible.

After those steps, the pipeline is: restore → catalogue mask → leakage canaries (single features, AUC ≤ 0.90) → hide-and-recover holdout (pooled DTI, α = 0.2, β = 0.8, 300 m triangular kernel, whole-segment buffered) → registry-wide uniqueness (surface ρ ≤ 0.90; final dots ≤ 70% within 3 px) → automated format validation → selector approval. Budget: at most 3 experiments and 2 hours.

---

## 8. Three-pass record

- **Pass 1 (implement and verify):** verified the official rules and live leaderboard; re-verified the nine files by commit-pinned SHA-256 (9/9 PASS); added `scripts/audit_nine_site_encoding.py` and recorded its output; computed exact dot-set relations.
- **Pass 2 (review for bugs, assumptions, edge cases):** found and fixed the test environment gap (`imagecodecs` not installed); found the audit's "NaN is the likely cause" inference conflicts with the official text and recorded it as an irregularity rather than repeating it; found the user's leaderboard numbers disagree with the live board and recorded it.
- **Pass 3 (re-check against the request):** no new candidate exists, so none is marked OK to download or submit. No holdout, estimate, or receipt was created. The run card (`run-card.json`) records the blocked state with null measurement fields. The full test suite passes with the pinned environment.

**Maximize P(Win):** don't spend a slot on a file that the evidence says is a duplicate or unverified. **Own the Outcome:** the data blocker is stated with the exact steps that remove it.
