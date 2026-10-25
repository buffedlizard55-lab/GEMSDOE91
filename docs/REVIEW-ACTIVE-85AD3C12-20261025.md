# Active-checkout repository review — 2026-10-25 UTC

**Branch:** `arena/85ad3c12-gemsdoe91` (active)
**Decision:** **No experiment, TIFF, or submission was produced. OK TO SUBMIT: NO.** This is a deliberate protocol stop, not a claim that a high-scoring candidate was found. The prompt's assigned single-method paragraph is absent, and this checkout lacks the sample grid, fault catalogue, registry parent and cached feature stack needed to run the shared holdout/writer workflow. Inventing a lane or manufacturing a raster without these controls would violate the user's higher-priority parallel-run protocol.

## What was checked (facts from this checkout)

- `git status --short --branch` started clean on `arena/85ad3c12-gemsdoe91`; there is no PR already open from this branch.
- `registry/preflight.json` and a fresh `python scripts/preflight.py` both report **BUILD BLOCKED**: `data/official/sample_submission.tif` and `data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif` are missing. The command exits 1 as designed. Since `data/` is absent, neither the fault catalogue nor feature stack needed for any lane can be used here.
- `docs/run-card.json` says `lane.assigned: false` and gives the reason: “No single assigned method paragraph supplied.” The user message contains no uniquely designated method paragraph. I therefore do not infer a lane from earlier sessions.
- The pinned template source is `buffedlizard55-lab/GEMSDOE78@30f1ab9400f92036b0bc613425f1b5b6046f3897` (`registry/template_pin.json`). The shared implementation is vendored under `vendor/gems57/`. This review did not alter it, build a private evaluator, or run a substitute holdout.
- The base environment initially lacked the pinned Python packages; installed `requirements.txt` into ignored `.venv/` for verification. The first full pytest run exposed three portal contract/reproducibility failures. Fixed the source-of-truth GEO91 templates and renderer (accessible `<main>` landmark, explicit `data-submission-ready=false`, archive navigation, and synchronized `docs/current-run.json`) and updated the current-page test to follow the active run-card rather than stale S16 hard-coding. The full suite now **passes** (with six skips and Affine `PendingDeprecationWarning`s). A standard-library syntax pass compiled 185 Python files from `scripts/`, `src/`, and `tests/` with zero syntax errors.
- No TIFF was generated or modified in this review; no live DrivenData upload, score receipt, or weekly slot was used. `ORGANIZER-CONFIRMED` score evidence is absent from this review. A historical damage-zone TIFF/ZIP/NaN companion are already tracked in `docs/downloads/`; they are prior artifacts, not outputs of this review. Their audit JSON records **HOLDOUT-DTI = 0.0** (`gems91-hide-recover-v1.1-nohalo`, 60,988 withheld positives, 95% CI [0, 0]) and says submit NO.
- Pass-2 inspection found `python scripts/check_artifact_policy.py` failed because those three tracked historical artifacts were missing from `registry/artifact_policy.json`. Registered their exact SHA-256 values with explicit research-only / do-not-upload reasons; rerun now passes for all 62 tracked prediction artifacts. This is policy bookkeeping, not scientific or format revalidation.

### Important evidence hygiene

Several repository records describe different historical branches/checkouts. For example, the top of `PASS_LOG.md` says inputs are restored and names branch `arena/e6fdea6b-gemsdoe91`; that is historical context, not the observed state of this active checkout. Likewise, the historical GEO91 result in `docs/run-card-GEO91.json` is not a result rerun here. The prompt's scores `0.2778`, `0.3195`, and `0.4413` remain **USER-REPORTED** in this review because no copied organizer receipt was examined. A filename and a reported score do not establish why it scored that way.

## Interpreting the reported GEMSDOE32 result

The candidate explanation documented elsewhere in the repository is plausible but must not be confused with a causal finding: sparse, separated binary predictions can be more efficient under a max-credit triangular-kernel Tversky/DTI objective than a dense line or halo, because excess nearby predicted mass can increase the false-positive term after truth-pixel credit saturates. Removing predictions close to already-mapped faults may also be sensible when the target excludes that catalogue. This describes a possible metric mechanism, not proof that the reported `0.2778` came from that mechanism, not a new score, and not evidence of geothermal-vent discovery. Establishing causality would require same-input, same-fold, same-evaluator matched ablations and an authenticated organizer receipt. No claim that this checkout beats `0.2778` is supported.

## Candidate hypotheses for later screening — not validated, not cleared as globally novel

The repository already contains a large family of derivatives, ridge/edge transforms, magnetic–gravity residuals, phase congruency, source/tilt-depth work, topology/context features, and lithology/conductivity models. The candidate mechanisms below do not appear under these exact operators in the checked implementation search; that is **not** proof that the ideas are absent from every GEMSDOE site or every prior raster. They are a research shortlist only, not a new assigned lane. Each assumes the relevant sponsor-provided bands are available through the authorized cached stack; they are not available in this checkout, so present viability is blocked.

| Rank | Candidate and layers | Target signature and rationale for a missing fault | Named non-fault mimic | Difference to screen against this repository | Expected DTI / cost (qualitative, not a score) |
|---|---|---|---|---|---|
| 1 | **Multi-field orientation-field winding / defect index** — magnetic RTP (B02), isostatic gravity (B13), basement depth (B15) structure tensors | Map the winding number / index of the unoriented strike director around coherent line ends and relay junctions. Buried fault intersections or relay terminations may create organized director defects even when no single edge is strong enough to rank; cross-field agreement is required to reduce isolated texture responses. | Ring dikes, caldera margins, and juxtaposed intrusive contacts can create genuine circular or branching field geometry without a fault. | The repo has orientation, junction, and phase features, but a cross-field director-winding statistic is a distinct operator to verify with a code-level ablation and negative controls. Must establish that it is not merely a relabelled structure-tensor/junction feature. | **Potentially medium, high uncertainty / medium**. Cached layers in principle; no local cache now. |
| 2 | **Cross-field bispectral phase coupling** — B02 RTP and B13 gravity (optionally B15 depth only as independent corroboration) | Estimate localized third-order cross-bicoherence/phase coupling at fault-relevant wavelengths. A common structural discontinuity can couple harmonics across potential fields even where simple linear transfer residuals or amplitude edges are weak; train/score only using visible catalogue segments under the common buffered holdout. | Shared survey levelling/ gridding seams can generate phase-locked harmonics; lithologic contacts can couple multiple fields without being faults. | Search of `src/` and `scripts/` found no bispectral/bicoherence implementation. Existing PGRD transfer residuals and PC91 phase congruency are adjacent methods, so require a preregistered test showing the third-order statistic adds information beyond both. | **Potentially medium, very high uncertainty / high** (FFT/window choices and leakage controls). Cached layers in principle; no local cache now. |
| 3 | **Scale-dependent magnetic source-depth contrast** — B02 RTP, B14 TMI, B09 vertical derivative, and B13 gravity as an independent check | Compare radially averaged local power-spectrum slopes / matched-filter depth estimates across adjacent windows; a sharp, spatially coherent source-depth change may mark a buried basement step rather than a high-amplitude edge alone. Rank only paired magnetic/gravity evidence and test off-catalogue folds. | Intrusive bodies of varying depth, remanent-polarity boundaries, and survey footprint/processing changes can mimic source-depth contrasts. | Different from local edge magnitude and PGRD linear residuals, but close to existing tilt-depth and potential-field analyses. It is only novel if a source-depth *contrast* statistic survives feature ablation and is not already encoded in the cached engineered stack. | **Low-to-medium, high uncertainty / medium-high**. Cached layers in principle; no local cache now. |
| 4 | **Radiometric–potential-field contact offset conditioned on cover** — B06 total count (verify file tag/units), B02 RTP, B13 gravity, B15 basement depth | Measure the signed offset between radiometric contact and subsurface edge, conditional on cover thickness; persistent displacement under cover could indicate concealed fault juxtaposition rather than a coincident outcrop contact. | Lithologic contacts, weathering/moisture changes, and flight-line seams may shift radiometric response independently of faults. | Cross-field discordance has adjacent treatments in existing fusion lanes. This candidate is distinct only if it explicitly tests a *signed offset conditional on cover* rather than coincident edge agreement; first verify the TC band metadata/unit irregularity noted in prior repo evidence. | **Low-to-medium / medium**. Cached layers in principle; no local cache now. |

**Ranking is a hypothesis-priority judgment, not a forecast.** No candidate was validated on holdout; no feature-alone canary was possible. No proposal requires new external data if restricted to the competition's own feature stack. Because that stack is absent here, none is presently buildable. An external-data detour (for example, high-resolution elevation or geology) is deliberately not proposed as viable: it is outside an assigned lane, is unnecessary for these hypotheses, and its access/licensing/provenance were not checked in this session.

## Three review passes

### Pass 1 — inspect and establish the executable state

Read the README standing brief, current cards, template pin, preflight, submission guide, core runner/evaluator references, CI and Pages workflows. Confirmed branch and clean initial worktree. Ran preflight, installed the pinned requirements into ignored `.venv/`, repaired the GEO91 portal/source-of-truth mismatch, ran the full test suite, and compiled Python sources. Outcome: repository tests and artifact policy pass, but this checkout cannot execute a fresh spatial holdout because required data/cache files and lane assignment are absent. No new raster is made.

### Pass 2 — challenge assumptions and failure modes

- **Do not rely on stale checkout claims:** prior logs say data restored, but actual `data/` is absent here; the new run card records this checkout only.
- **Do not mislabel metrics:** the user-provided fleet/leaderboard values are not copied from a submission-page receipt; no number in this review is an organizer score.
- **Do not bypass protocol:** no assigned method paragraph, complete registry, cached features, or sample template means no placement, no per-feature leakage AUC, no valid candidate holdout, and no TIFF certification.
- **Do not overstate novelty:** candidate shortlist is explicitly implementation-search novelty only, not fleet-wide uniqueness. Registry rank-correlation/dot-overlap cannot be tested without rasters.
- **Do not equate file formatting with submit permission:** there is no new file and no selector/slot approval.
- **Portal state must match its source:** the initial three UI-contract tests exposed that the GEO91 pages lacked a semantic main landmark/archive link, the test expected an old S16 run card, and the GEO91 renderer left `current-run.json` stale at S16. Updated the GEO91 source templates, renderer, and test contract so the current page, run-card pointer, and automated “not ready” state agree. Full suite now passes.

### Pass 3 — compare against the request and report the blockers

The requested unique, download-ready TIF and a candidate with holdout improvement were **not** achieved. Creating a dummy or recycled TIFF would give a misleading impression and violate the protocol. No experiment and no weekly submission slot were spent. The next valid action is to restore authorized, hash-pinned inputs and dependencies, have the authorized lane assigned, then preregister at most three experiments and run the existing shared canary → pre-placement registry scan → buffered holdout → final-dot registry scan → writer/validator flow. Candidate promotion remains a separate selector decision.

## Manual-review source pointers

These are links for review, not claims of fresh live verification during this session:

- [DrivenData competition overview and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data page (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution repository](https://github.com/drivendataorg/gems-prize-reference-solution)
- [GEMS prize submission PDF (NLR)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN survey source](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE Geothermal Data Repository submission 1391](https://gdr.openei.org/submissions/1391)
- [EPSG:32611](https://epsg.io/32611)

## Review run card

The machine-readable copy is [`run-card-85ad3c12.json`](run-card-85ad3c12.json). Null values mean not run; they are not zero scores.
