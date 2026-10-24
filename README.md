# GEMSDOE91 — persistent project brief and current status

> **Required at the start of every project session:** read this README first. It is the durable project prompt and acceptance criteria from the user's request. Do not treat historical `MODEL`, `PROXY`, or `CLAIM` entries as scores, and do not make a downloadable TIFF appear unless the current protocol gates have all passed and the separate slot selector authorizes it.

## Mission and core values

Build a scientifically defensible, auditable workflow for the DOE GEMS Prize (DrivenData competition #306): predict geological faults that may indicate geothermal resources, using official competition data and reproducible analyses. The target is fault mapping, **not direct geothermal-vent classification**. The goal is to maximize the probability of a successful competition result while owning the outcome, including stopping when evidence is insufficient.

- **Maximize P(Win):** choose experiments for expected information and scoring value, not narrative appeal or speculative score chasing.
- **Own the Outcome:** verify code, data lineage, raster values, and claims end to end; log defects rather than hiding them.
- Use official, auditable sources; do not hallucinate, infer a score from a projection, or say an item is verified unless it was checked.
- Store durable research and source links here so future sessions can start from a useful baseline.
- Work autonomously within the authorized protocol; do not pause for discretionary input. If a mandatory lane, data entitlement, shared tool, or receipt is missing, fail closed and document the blocker rather than inventing a choice or asking for credentials.
- Review sources, code, tests, and site eligibility in multiple passes, including a final line-by-line diff/link/claims audit before presenting the result.

## Persistent operating contract from the user prompt

### Unique submission and clear download status

- The project should generate a **unique** single-band GeoTIFF for the competition, not copy a previous submission except for explicitly labelled learning/audit use.
- The site must make the download decision obvious at the top. It must say **NOT APPROVED / DO NOT SUBMIT** when any gate is missing; only a validated and separately selected artifact may receive a download link.
- A prior upload attempt is reported to have returned `Predicted values must be in range [0, 1]`; the exact uploaded bytes and organizer diagnostic are unavailable here, so do not attribute the cause. Validate the actual written-and-reread raster; do not assume an extension, preview, nodata tag, or previous validator proves the full value domain is acceptable.
- A future note must be unique and no longer than 140 characters. Never invent a note or a score for a file that has not passed the gates.

### Parallel-run protocol — hard stop rules

- **Lane:** use only the single method paragraph assigned for this run. The prompt refers to that paragraph, but no distinct method paragraph/lane is present in the received text. Do not choose a lane autonomously.
- **Novelty before and after placement:** compare the candidate surface to every available registry surface and final dots to every registry raster. If rank correlation is **greater than 0.90**, or more than **70%** of candidate dots are within **3 pixels** of a registry raster's dots, record a duplicate and stop. Missing comparisons are UNVERIFIED, not PASS.
- **Reuse, do not rebuild:** use the shared template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`. If a shared tool is defective, fix it in the shared template and report the fix; do not keep a private fork. None of those named tools/template paths is present in this checkout, so this is currently a blocker.
- **Holdout:** hide and recover whole fault segments with a buffer; derive all catalogue-based features from visible faults only; mask visible faults pixel-exactly; score pooled official DTI (`alpha=0.2`, `beta=0.8`, 300 m triangular kernel). Every score must identify the evaluator version, withheld-positive count, and 95% CI.
- **Leakage canary:** test each feature alone. AUC greater than **0.90** is leakage until proven otherwise.
- **Run card:** every run ends with one JSON card recording the hypothesis, mechanism, named non-fault mimic, compliant HOLDOUT-DTI and CI, registry correlation/overlap, raster SHA256, validator results, submission name/note, and promote/negative verdict.
- **Budget:** at most **three experiments or two hours**, whichever comes first. Promotion to a real submission slot is a separate selector step within the official weekly cap. Negative results are deliverables.

### Research and submission requirements

- Before implementing an experiment, list **3–5** not-yet-tried geological hypotheses. Each must identify layers, a physical signature/transform, why it might find a fault absent from the catalogue, how it differs from existing code, a non-fault mimic, expected potential (not a numeric score unless measured), and cost.
- Validate the top hypothesis on the compliant spatial holdout before any slot is considered. If it requires new data, name a specific free official source and verify availability before calling it viable. The five current proposals and their data/access caveats are in [`docs/HYPOTHESES_G91.md`](docs/HYPOTHESES_G91.md).
- The user requests an executive-summary submission page, an auditable source register, a clean GitHub Pages interface, and automated project-side validation. The site must never promise a successful organizer upload unless that upload produced a receipt.
- The user supplied many scores from sibling sites. They are leads/claims, not organizer receipts unless explicitly copied from an official submission-page receipt. Preserve provenance and do not use those values as hidden labels.

### Official submission format and competition rules

The official [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) specifies one float32 prediction layer on the EPSG:32611, 100 m grid, the same bounds, values in [0,1], and null/NaN outside the bounds. The [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) states up to three scored submissions per week (subject to the live website), one final submission selection across both prize phases, and a narrative disclosure describing how generative AI was used when applicable. `AI_USE.md` records this project's actual AI contributions and must be reconciled with any future entry. Finalists must provide reproducible code assets and documentation; final content is due by **5 p.m. ET on the submission-deadline date**. No current deadline date is verified here; check the live competition website before acting. The live [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) requires login; it redirected to login in this run. See [`docs/SOURCES.md`](docs/SOURCES.md) for the exact source audit and limits.

## Current status — 2026-10-24 UTC

# **NOT OK TO SUBMIT — no active TIFF download is available.**

This is an evidence-based stop, not a negative geological finding:

- No explicit method lane was assigned.
- `data/` is absent; `python scripts/restore_data.py --check` reported all **15** pinned files missing in this checkout. Historical `registry/preflight.json` said BUILD ALLOWED despite this; it has been refreshed and now reflects the local block.
- `evaluate_holdout.py` and `submission_writer.py` are absent. The existing `src/gems91/proxy.py` does not meet the required segment-buffered, fold-specific, pooled-DTI protocol. Also, `scripts/dti.py` and `src/gems91/metric.py` disagree on true-positive aggregation versus the official formula; neither is accepted as the shared evaluator. See IR-91-39.
- The previous GEOD candidate's own page recorded **93.2%** dot overlap within 3 px against its parent, above the **70%** duplicate stop. That historical measurement cannot be re-run without the missing parent input; fail closed. The old GEOD download pair has been removed from the public download folder and is not approved.
- No compliant HOLDOUT-DTI result, 95% CI, or registry-wide novelty result exists for a new candidate. No experiment was run, no slot was selected, and no submission was made.

### Score provenance

- The user-provided **`0.2778`** for `h33-h33-2-b2` is an **UNVERIFIED SITE/USER CLAIM**, not HOLDOUT-DTI and not ORGANIZER-CONFIRMED. The current [GEMSDOE32 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) explicitly says no organizer score exists for its artifacts and does not substantiate that reported value.
- The official [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) displayed **`0.4413` at rank 1 when checked on 2026-10-24**. **PUBLIC-LEADERBOARD OBSERVATION** only; neither HOLDOUT-DTI nor ORGANIZER-CONFIRMED for GEMSDOE91, and not a private-test result.
- No project candidate has a submission-page receipt in this checkout. A projected number is never written as a score.

## Research answers and next actions

The most defensible explanation for a *claimed* improvement from the H33-2-B2 lineage is metric arithmetic: under the official distance-weighted Tversky metric, redundant or low-credit prediction mass can add false-positive cost without increasing unique coverage; thinning can therefore help if it removes only low-marginal-credit cells. It can also hurt if those cells cover unseen faults. The available site snapshot does not establish a receipt or causal attribution, so no claim that it “scored” 0.2778 is accepted.

The next scientific work is **blocked before implementation** until the lane and shared evaluator are identified. Five distinct candidate hypotheses, each with a non-fault mimic and cost, are recorded in [`docs/HYPOTHESES_G91.md`](docs/HYPOTHESES_G91.md). The top proposal is fold-safe fault-tip/stepover dilation using fold-visible fault geometry with provided strain layers; it is not validated and must not use a slot without a compliant holdout win.

## Repository map

| Path | Purpose |
|---|---|
| `docs/index.html` | GitHub Pages status; prominently shows whether a download is allowed |
| `docs/executive-summary.html` | Submission instructions, including the current fail-closed status |
| `docs/run-card.json` | Current machine-readable run card; negative / not run |
| `docs/HYPOTHESES_G91.md` | Site-claim analysis, ranked proposals, and preregistered holdout requirements |
| `docs/REVIEW-20261024.md` | Three-pass repository review and evidence audit |
| `docs/SOURCES.md` | Official-source links, what was checked, and verification limits |
| `LIMITATIONS.md` | Current data, tooling, and competition-access blockers |
| `SLOT_PLAN.md` | Slot-selection status; no candidate is currently selected |
| `registry/data_manifest.json` | Pinned input hashes and local data requirements |
| `src/gems91/novelty.py` | Surface-correlation and final-dot-overlap checks (not a substitute for complete registry inputs) |
| `tests/` | Unit and portal regression tests |

## Run checks

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/preflight.py
.venv/bin/python scripts/restore_data.py --check
```

`restore_data.py` only verifies in `--check` mode. Its normal mode fetches pinned files from public GitHub mirrors, not directly from DrivenData; mirror provenance/permission must be reviewed before using those files. No credential is requested, stored, or printed by this project.
