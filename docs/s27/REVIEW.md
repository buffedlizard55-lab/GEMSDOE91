# S27-FABRIC-FAR session review — 2026-10-29

Branch `arena/4b95209e-gemsdoe91`. Experiments used: **2 of 3** (preregistered;
the third slot was deliberately not spent chasing the diagnostics — see Pass 2).
Weekly submission slots used: **0**. Values: **Maximize P(Win)** — no slot on a
file whose live-anchored projection trails the incumbent family;
**Own the Outcome** — the negative verdict, its proofs and its instruments are
preserved below with receipts.

## Executive verdict

**A new, unique, format-valid TIF was generated. OK TO DOWNLOAD: YES
(research / selector review). OK TO SUBMIT: NO.**

| File to download (research) | Estimated leaderboard score (labelled) | Unique vs GEMSDOE24/25/27/28/30/31/32/33/36? | OK to submit? |
|---|---|---|---|
| [`gems91-s27-fabricfar-37654dots-20261029T144455Z-aa90130a-zeros.tif`](../downloads/gems91-s27-fabricfar-37654dots-20261029T144455Z-aa90130a-zeros.tif) (SHA-256 `fa894fff…`, single-TIFF ZIP beside it) | ORGANIZER-CONFIRMED: **none**. Estimated leaderboard score = LFI **MODEL_PROJECTION_NOT_A_SCORE 0.18731** (ridge10 0.17703; LOSO RMSE 0.0196, Spearman 0.954, 112 anchors). HOLDOUT-DTI **0.145207 [0.128814, 0.165761]** (`gems57-pooled-hide-v2`, v3 folds, 60,988 withheld — not a leaderboard score). SGMC>500 m diagnostic 0.076559 vs R0 0.088516 | **YES** — max 42.12% of dots within 3 px of any one leader; max 61.90% vs any competitive registry raster; surface \|ρ\| max 0.2135. **NO literal all-blankets** (98.82% vs 206,895-dot lattice; capacity-forced ≥82.34% at this budget for any raster) | **NO** — G4 (holdout) and G5 (SGMC>500 m) fail; selector step pending |

Front door with generated tables: [`executive-summary.html`](executive-summary.html)
(rendered from JSON receipts by `scripts/render_s27_portal.py`; no hand-typed
scores). Submission name + note (for a future selector-approved use) are on
that page and in `run-card.json` (name `gems91-s27-fabricfar-…-zeros`,
note 96/140 chars).

## What the science showed

1. **Emission geometry was necessary, not sufficient.** Preregistered
   distance quotas (5/15/25/25/30% over (3,5], (5,10], (10,20], (20,40],
   (40,∞) px) were hit **exactly** on the final map (0 redistributed dots),
   moving median dot distance-to-catalogue from S25's 5.831 px to 21.471 px
   (R0: 19.647 px). Consequences, all measured post-hoc on instruments the
   candidate was not built with: LFI projection **0.07917 → 0.18731** (×2.37),
   SGMC>500 m **0.049414 → 0.076559** (+55% relative), competitive-registry
   overlap **74.89% → 61.90%** (gate now passes; the ≤65% caps never bound —
   stratification alone did it). Yet both live-anchored diagnostics still
   trail R0 (LFI 0.27342; SGMC 0.088516). The remaining gap is far-field
   *ranking quality*: only 35.75% of S27 dots sit in ≥3-anchor consensus
   zones vs R0's 67.67%, because forced-far dots are ordered by a surface
   trained on catalogue labels. Geometry fixed; information didn't arrive.

2. **The shared holdout cannot measure emission geometry (new instrument
   finding, IR-S27-03).** All three preregistered arms (collar 3.05,
   collar 10, stratified) returned HOLDOUT-DTI **0.145207** with term-for-term
   identical per-fold components. Root cause, measured directly: every v3
   test quadrant contains **zero** visible catalogue pixels (whole
   intersecting components withheld + 80 px feature buffer); distance to the
   full visible catalogue inside regions has median 234–808 px and 99.7%+
   of pixels >40 px, vs median 23.1 px on the full map. Any collar/quota
   rule on distance-to-visible is therefore inert in-fold, and E2's
   quota+redistribution greedy provably returns the CTRL dot set.
   Holdout-DTI on v3 folds certifies *surface ranking* only. This also
   retrospectively explains part of the instrument's weak live correlation
   (S20/S22: Spearman ≈ +0.105): the near-catalogue false-positive waste
   that dominates live scoring barely exists inside v3 test quadrants.

3. **Detector reproduction is close but not bitwise (IR-S27-02).** Identical
   recipe/seed/inputs reproduced S25's canaries exactly (max sym AUC
   0.6130, band06 fold3) and fold-0 holdout terms to machine precision, but
   folds 1–3 differ slightly (pooled CTRL 0.145207 vs S25's 0.147741,
   well inside the [0.1288, 0.1658] CI). Cross-session HGB fit
   nondeterminism is the only remaining explanation; future lanes that need
   bitwise reproduction must pin thread counts inside the learner call, not
   just BLAS env vars.

4. **Uniqueness is now competitive-scope clean.** S27 is the first S25-lineage
   candidate to pass ≤70% against every competitive (≤90,000-dot) registry
   raster *and* all nine leaders, while the literal lattice scope remains a
   proven geometric impossibility at competitive budgets (capacity bound in
   the run card). The coordinator scope ruling requested since S21/S25/S26
   is still the top governance blocker — it decides whether "unique" can
   ever be literal-true; S27 neither self-exempted the lattice nor steered
   dots into its holes.

## Nine focus sites — per-site answer (bytes re-hashed 2026-10-29)

Claims are **USER-REPORTED, not ORGANIZER-CONFIRMED** (no organizer receipt
exists for any file named anywhere in this repository). Leaders were restored
by pinned git blob and re-hashed today; all 72 directed peer overlaps were
recomputed today (`nine-site-audit.json`); sibling main HEADs were refreshed
today via `git ls-remote` (REST API quota exhausted by blob restores).

| Site | Best claimed file (historical) | Claim (USER-REPORTED) | Unique among the nine? | S27 unique vs it? | Submit it? |
|---|---|---:|---|---:|---|
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (37,654 dots) | **0.2778** | No — 100.00% peer overlap | Yes (39.75%) | No — prior duplicate |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-…-zeros` (38,854) | 0.2750 | No — 97.58% | Yes (40.16%) | No |
| GEMSDOE28 | `h36-1-rung30-blind-r1-…-nan` (37,660) | 0.2710 | No — 100.00% | Yes (39.53%) | No |
| GEMSDOE31 | `h27-4-solo-d28-…-nan` (40,199) | 0.2708 | No — 100.00% | Yes (39.98%) | No |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-…` (41,865) | 0.2632 | No — 99.71% | Yes (40.23%) | No |
| GEMSDOE25 | `dotted-h19-5-d2-8-…-nan` (44,090) | 0.2600 | No — 100.00% | Yes (40.18%) | No |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-…` (44,090) | 0.2600 | No — 100.00% | Yes (40.18%) | No |
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-…-nan` (60,069) | 0.2477 | No — 100.00% | Yes (41.69%) | No |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-…-nan` (61,328) | 0.2449 | No — 98.02% | Yes (42.12%) | No |

**Prompt runner-up check (line by line).** Every additional score the sitting
prompt lists for these nine sites is ≤ its pinned leader: GEMSDOE24 gvc1
0.0859 < 0.2477; GEMSDOE25 h66 0.0742 < 0.2600; GEMSDOE27 h29 0.2190 and h31
0.2250 < 0.2449; GEMSDOE28 h27-4 0.2708, h32-1 0.2649, h38-1 0.2707, s18
0.0217, s21 0.0206 — all < 0.2710; GEMSDOE30 MSDB1 0.1462 < 0.2600; GEMSDOE33
s33 0.0963 < 0.2632; GEMSDOE36 kpl36 0.1647 < 0.2750. No discrepancy with the
pinned leaders. **Two prompt-level irregularities flagged:** (a) outside the
nine, the same prompt lists `gemsdoe92-lbmc1-…: 0.2784` — nominally above
GEMSDOE32's 0.2778; it is likewise USER-REPORTED with no receipt and no
pinned raster in this repo, so "highest claimed overall" depends on whether
that line is trusted (IR-S27-04). (b) The prompt's leaderboard ceilings
0.4413 / 0.3195 are stale: the official public board fetched today reads
**#1 = 0.4544, #2 = 0.3916, #10 = 0.3405** (`evidence/public-leaderboard-2026-10-29.json`),
so even the family's 0.2778 claim would sit far below the current top 10.
Chasing 0.2778 is chasing a mid-board number; the real bar is ~0.34+.

## Why 0.2778, and can a unique file beat it? (PhD-level summary)

R0's advantage is emission economics on shared support, proven from bytes in
S22 and re-verified since: one H19-5 ridge network → dotting at ~2.8 px
(most of the +0.086 family gain) → deleting dots ≤1 px, then ≤2 px, from the
catalogue. Under DTI with a 300 m triangular max-kernel and pixel-exact
masking of known faults, near-catalogue dots are nearly pure FP weight
(α = 0.2 is small but nonzero, and stacked kernels earn no extra numerator);
deleting 6,436 of them is almost free score. R0's dots additionally
concentrate where independent high-scoring methods agree (consensus ≥3:
67.67%), which the anchor inversion identifies as the highest truth-density
stratum. **Beating it with a unique raster** requires dots of equal or
higher mean credit *outside* that shared support. Three sessions of evidence
now bound what this 100 m stack can do under that constraint: S20's direct
inversion (optimistic, self-referential) ~0.36–0.40; S21-PDWC 0.1977;
S25-FABRIC 0.0792; S27-FABRIC-FAR 0.1873 — all MODEL projections, none a
receipt. The honest reading: the public stack's *catalogue-trained* surfaces
rank far-field pixels by extrapolation, and truth concentrates where the
fleet already agrees, so uniqueness itself taxes expected credit. The two
credible routes past 0.2778 (and toward the true ~0.34+ competitive band)
are (a) far-field-specialist training — PU/isolated-fault objectives that
learn the ranking *among catalogue-distant pixels* and are validated on
isolated-segment holdouts rather than quadrant recovery; and (b) new
information, pre-eminently 1 m USGS 3DEP scarp morphometry, which targets
exactly the sub-100 m scarps experts used to draw the hidden labels.

## Three passes

**Pass 1 — implement + verify.** Read README standing brief + S25/S26
reviews first. Restored 15/15 pinned inputs (SHA-verified), 62/64 frozen
registry references (2 known-missing recorded), 108/108 LFI anchors, 9/9
leaders by pinned blob. Re-verified official problem/metric/format and the
live leaderboard from primary sources today. Wrote and hashed the
preregistration (5 ranked hypotheses; S25's reserved emission-geometry lane
as rank 1) *before* any result. Implemented `gems91.far27` (stratified,
cap-aware emitter) with synthetic tests; rebuilt the frozen S25 feature
stack via the shared `fabric25` (canary reproduced exactly); retrained the
identical OOF/final HGB surfaces; ran E1/E2 paired on the shared v3
evaluator; packaged via the shared writer; froze the raster; then computed
SGMC + refitted-LFI + dot-profile diagnostics post-hoc and finalized gates.

**Pass 2 — adversarial review (bugs/edge cases found & fixed, or proved).**
(a) Identical arm scores triggered a stop-and-investigate: proved (not
assumed) the v3-fold degeneracy by measuring visible-in-region = 0 in all
folds — the preregistered holdout arms are certifiably the same dot sets;
recorded as an instrument finding instead of "fixing" the preregistration
after seeing results. (b) Diagnostics first run crashed on a variable
shadowing bug (`sgmc` dict overwrote the SGMC mask) — fixed by renaming;
no numbers were produced by the buggy run. (c) First emitter unit test
failed legitimately: the 60×60 synthetic grid has no >40 px band, so quota
redistribution correctly fired — test geometry fixed, emitter unchanged.
(d) `independent_tif_check.py --help` turned out to execute the full audit
(no argparse) and overwrote the historical S13 evidence file; detected via
`git status`, reverted, and replaced with a scoped independent checker for
the S27 raster only. (e) GitHub REST quota exhausted mid-audit → switched
HEAD verification to `git ls-remote` (same SHAs; dates recorded null, never
guessed). (f) Download audit refused the new candidate until registered in
`registry/artifact_policy.json` — registered with explicit research-only
reason; audit then PASSes the TIF/ZIP (123 files, 114 PASS / 9 historical
FAIL unchanged). (g) Decided **not** to spend the third experiment on
quota variants selected with G5/LFI in view — that would convert blind
diagnostics into tuning targets (the S20 optimizer's-curse failure mode);
the remaining question (far-field ranking) needs a new preregistered lane.

**Pass 3 — re-check against the original request.** Unique TIF generated ✓
(not a copy; 49.07% vs even its parent; SHA in run card); one-click download
at the very top of the executive summary and front door ✓; obvious verdict
**OK TO DOWNLOAD: YES (research) / OK TO SUBMIT: NO** on both pages before
any other content ✓; executive-summary table with file + labelled estimated
score + uniqueness + submit answer, per session candidate and per focus
site ✓; score estimation exists and is labelled MODEL projection with LOSO
error bars, never a score ✓; validation fully automated (canaries, surface
+ dot duplicate instruments before/after placement, shared evaluator,
SGMC control, shared writer, independent tifffile re-read, all-download
audit) — no human inspection anywhere ✓; submission name + ≤140-char note
recorded ✓; "Predicted values must be in range [0, 1]" class eliminated by
construction (binary all-finite zeros) and re-verified from bytes ✓; 3–5
ranked geological hypotheses with layers/signatures/mimics/data-gates
preregistered before implementation ✓; top candidate validated on the
spatially blocked holdout before any slot discussion ✓ (and the negative
gate honoured: no slot); ≤3 experiments (2 used), one JSON run card with
all protocol fields ✓; prompt already preserved in README (`#full-project-brief`)
and read at session start ✓; PR + merge to `main` performed at the end of
this session ✓. **Unmet by evidence, not omission:** no honest estimator in
this repo puts any *unique* current file above 0.2778, and no file here is
OK TO SUBMIT under the standing protocol.

## Limitations & next steps (ranked by expected gain per cost)

1. **Far-field-specialist detector (zero new data; preregister first).**
   Train the ranking only among catalogue-distant pixels (e.g. positives =
   whole catalogue components >1 km from every other component, ISO-style;
   negatives far-field only), validate on isolated-segment holdouts + SGMC,
   then emit with today's stratified/capped rule. Directly attacks S27's
   measured deficit (consensus-zone share, far-field ordering).
2. **USGS 3DEP 1 m / 10 m DEM lane (highest ceiling; needs unrestricted
   host).** Free public-domain source:
   https://www.usgs.gov/3d-elevation-program/about-3dep-products-services —
   sandbox allowlist blocks bulk hosts, so tile pinning must happen outside
   and enter via `registry/data_manifest.json` hashes. Same access would
   unlock the official `1m_DEM_links.csv` (DrivenData login).
3. **Holdout instrument repair (shared template, one fix).** Add an
   emission-sensitive evaluation domain (e.g. score final-map candidates
   against SGMC-offcat + isolated segments; or censor a *buffered halo*
   around withheld segments so near-known FP waste exists in-fold).
   Until then, never gate an emission-geometry lane on v3 HOLDOUT-DTI alone.
4. **Governance (coordinator decisions, previously requested).** Explicit
   method-lane assignment (still `lane: null`) and a versioned duplicate-rule
   scope for dense calibration blankets; without the latter, the literal
   rule is geometrically unsatisfiable and every session re-litigates it.
5. **Selector / receipts.** No authenticated DrivenData session exists in
   this sandbox: weekly cap, quota state and any organizer receipt must be
   confirmed on the live submission page by the account holder. First real
   receipt for any repo file should be treated as a calibration event
   (append to `registry/lfi_live_anchors.csv`, refit, re-issue estimates).

**Access needed (explicit):** (i) an unrestricted-network machine for 3DEP
tiles; (ii) DrivenData signed-in access for quota + receipts (no credentials
are requested or stored here); (iii) a coordinator ruling on lane assignment
and blanket-scope. Everything else used here is pinned, public, and
reproducible from this repository.

## Post-merge addendum — concurrent S26 lanes (2026-10-29, during PR #187)

While S27 ran, two concurrent lanes merged to `main` (PR #183 S26-FABRIC-EMIT,
a 10 px-collar variant of this same reserved lane; PR #184 S26 lidar-radiometric),
followed by a correction review (PR #186, IR-4239-*) that disabled their runners.
The frozen S27 candidate was measured post-hoc against all three concurrent
rasters (`concurrent-s26-overlap-addendum.json`, shared EDT ≤3 px operator):
S27 dots within 3 px of them = **42.98% / 50.05% / 36.42%** — competitive-scope
uniqueness survives; the frozen-registry maximum (61.90%) still binds. The
concurrent 22,163-dot raster is 77.97% within 3 px of S27 in reverse (their
lane is separately a lattice duplicate per IR-4239-03). Same-lane concurrency
is now a measured recurrence (cf. S25/S25-TLF): the coordinator lane-assignment
gap (IR-S27-01) is the fix. S27's verdict is unchanged: **negative, OK TO
DOWNLOAD research-only, OK TO SUBMIT: NO**, and its run card was not mutated.
