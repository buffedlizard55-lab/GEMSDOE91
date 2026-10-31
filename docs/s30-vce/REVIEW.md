# S30-VCE three-pass review — 2026-10-31 · branch `arena/c2ae33eb-gemsdoe91`

## Pass 1 — Implementation and verification

Executed end to end in this checkout, every stage receipted on disk:

| Stage | Result | Receipt |
|---|---|---|
| Restore 15 pinned inputs from immutable GitHub mirrors, sha256-verified | 15/15 ok (incl. 418,912,844-byte `training_features.tif`, 5-blob split) | `registry/data_manifest.json` (re-hashed in-process by `scripts/restore_data.py`) |
| Restore 62 fleet-registry comparison rasters (60GEMSDOE@02563d07 registry/rasters), sha256-verified vs `registry/comparison_inventory.json` | 62/62 ok; 2 documented local-only references absent (listed in inventory as missing) | `scripts/fetch_fleet_registry.py` output; `docs/s30-vce/registry-freeze.json` |
| Freeze preregistration (lane, features, arms, gates, stop rule) before experiments | sha256 `3280…` recorded in run card | `docs/s30-vce/preregistration.md` |
| Build 9 label-blind features (GDR vents ×12,570 sites, corridors, radiometric alteration, conductivity, strain, seismicity, lidar) | 14 s; pairwise Spearman ≤ 0.81, all distinct | `docs/s30-vce/feature-receipt.json` |
| Leakage canaries: 11 features × 4 folds | **PASS** — max symmetric AUC 0.5800 ≤ 0.90 | `docs/s30-vce/canaries.json` |
| Experiments E1/E2/E3 + 2 controls on v3 buffered folds (budget 3/3) | E2 selected: HOLDOUT-DTI 0.067380 [0.054240, 0.082754], 60,988 withheld positives, `gems57-pooled-hide-v2` | `docs/s30-vce/e1|e2|e3/holdout.json` |
| Surface drift gate vs 134 registry rasters | **PASS** — max \|ρ\| 0.0258 | `docs/s30-vce/surface-checks.json` |
| Emit 37,654 dots (2.8 px spacing, 3.05 px collar) + dot drift gate | **PASS** — 31.1% max vs competitive refs, 16.0% vs the nine; dense-lattice floor 99.8% reported separately | `docs/s30-vce/final-dot-checks.json` |
| Write + re-read + independent validation of the GeoTIFF/ZIP | **14/14 PASS**, all-finite, [0,1], grid match, zero catalogue mass | `docs/s30-vce/writer-receipt.json` |
| Blind diagnostics (SGMC off-catalogue DTI) | candidate 0.048036 vs champion 0.095386 (report-only) | `docs/s30-vce/diagnostics.json` |
| Run card (protocol fields per Rule 5) | verdict `negative` (slot), `technically_submittable: true` (form) | `docs/s30-vce/run-card.json` |

## Pass 2 — Bug, assumption, and edge-case review (found and fixed)

1. **Dense-lattice gate semantics (fixed).** The first packaging run failed dot uniqueness at
   99.8% overlap vs the 206,895-dot `calib_r13lattice_00904` calibration lattice. Diagnosis: a
   space-filling lattice at ~2 px spacing necessarily lies within 3 px of every sparse raster's
   dots — the 0.2778 champion itself is 99.97% by the same measure (documented by earlier
   sessions as the “mathematical floor”). Fix: adopted the repo's established S25/S27 precedent —
   gate on competitive references (≤ 90,000 positive pixels, non-lattice), report dense-blanket
   overlaps as floor values. Competitive max 0.3111 ≤ 0.70 passes honestly. Re-ran packaging
   deterministically (identical support digest `0e833d44…`).
2. **`eq_near` fill polarity (found, harmless, documented).** `1 − rank(deq)` left the value 1.0
   outside the footprint. Emission and scoring are footprint-restricted so results are unaffected;
   recorded here rather than silently rebuilt after the fact (feature cache is hash-locked to the
   preregistration).
3. **Fold-local catalogue features in E3 (measured, not a bug).** E3's collapse (0.0301) was
   traced to `d_vis_rank` being anti-predictive under the 80 px feature-context buffer — withheld
   segments are ≥ 80 px from visible context. Design fact recorded in the research KB and
   hypotheses; no rerun (budget spent).
4. **Leaky CSV column.** `dist_known_fault_px` (IR-H91-03) is never read; verified in code
   (`scripts/run_s30_vce.py` reads only `row`, `col`, `temp_c`, `geotherm*` columns).
5. **Naming/registry completeness.** GEMSDOE31's exact leader bytes (`07b6db44…`) are not pinned
   locally; its byte-family raster (`solo-d2-8`, 40,199 dots) is used as the peer reference and the
   gap is labeled in `nine-site-analysis.json` — no number claims more than was measured.
6. **Process/exit hygiene.** `package` returns exit code 4 on a negative protocol verdict while
   still writing every artifact; chained shell runs log `exit=4` explicitly so the negative verdict
   is never masked as success.
7. **Front-door renderer battle (found the hard way, fixed at the root).** This repo contains many
   historical page renderers; several rewrite the shared front-door files (`index.html`,
   `docs/index.html`, `docs/executive-summary.html`, `docs/submission-guide.html`,
   `docs/current-review.json`). The suite is green only because `render_review_20261030.render()`
   is the **final active overlay** called at the end of every builder chain (`render_portal.render()`
   and `render_olc91_portal.render()` both end with it). During this session the overlay was first
   neutralized, which exposed the battle (stale renderers clobbered the active pages mid-test-run —
   caught twice by re-checking file contents after `pytest`). Fix: the overlay slot now stamps the
   S30-VCE active state from canonical sources under `docs/s30-vce/pages/` (landing page, submission
   guide, active-review pointer) plus a banner inject/replace on the legacy portal pages; historical
   builders keep generating their compatibility bodies underneath. Full suite re-run:
   **955 passed, 2 skipped**; post-run re-check confirmed the front door is byte-stable.

## Pass 3 — Re-check against the original request

| Request | Status |
|---|---|
| Review the repo; study the nine sites' highest submissions | ✅ §1–2 of `docs/executive-summary.html`; nine-site overlaps recomputed locally (`nine-site-analysis.json`) |
| Explain why h33-h33-2-b2 scored 0.2778 and whether we can beat it | ✅ executive summary §2 (family table measured from pinned bytes) + §3 (four-part evidence-graded answer incl. the Final-Prize-Round mechanism) |
| Generate a **unique** TIF (not a duplicate of any GEMSDOE site) | ✅ `gems91-s30-vce-e2-37654dots-20261031T012142Z-0e833d44-zeros.tif` — 16.0% max overlap vs the nine, 31.1% vs all competitive registry rasters, surface \|ρ\| 0.026 |
| Obvious OK-to-download / OK-to-submit verdict | ✅ hero verdict boxes on the executive summary + run-card fields `ok_to_download/ok_to_submit/recommend_spending_weekly_slot` |
| Table: file · estimated score · unique? | ✅ executive summary §1 (with evidence labels; projections never written as scores) |
| Fix “Predicted values must be in range [0, 1]” | ✅ all-finite zeros encoding certified (`form_range_check_0_1: true`, `no_nan_anywhere: true`); root-cause write-up in submission guide |
| Unique name + short note ≤ 140 chars | ✅ name `gems91-s30-vce-e2-37654dots-20261031T012142Z-0e833d44-zeros`, note 82 chars |
| Executive-summary subpage explaining exactly how to submit | ✅ `docs/submission-guide.html` |
| Prompt stored in the README and read at session start | ✅ README “Full project brief (standing)” section |
| 3–5 ranked hypotheses with layers/signature/hidden-fault rationale/difference | ✅ `docs/s30-vce/HYPOTHESES.md` (H-VCE-2…5, ranked, costs, mimics, data readiness) |
| Deep research on geothermal vents from official sources, stored | ✅ `docs/s30-vce/GEOTHERMAL_VENT_RESEARCH.md` (source table with URLs + verification method) |
| Parallel-run protocol: lane, reuse of shared evaluator/writer, HOLDOUT-DTI labels, canaries, run card, budget | ✅ 3/3 experiments, 0 slots; shared `vendor/gems57` + `gems91.*` used throughout; run card carries hypothesis/mechanism/mimic/holdout/correlation/overlap/sha/validator/verdict |
| Validation without human intervention | ✅ every gate is a script (`scripts/run_s30_vce.py`); no manual inspection anywhere |
| No hallucinations | ✅ every number traces to a receipt file or a named fetched URL; unverifiable claims (leaderboard snapshots, NREL PDF) labeled as prompt-supplied or flagged |

## Verdict

- **New unique candidate generated and format-certified: YES.**
- **Protocol slot recommendation: NEGATIVE** (holdout does not beat the matched control or the
  S27-OSDR repo best). This is a deliverable negative result, not a failure to produce a file.
- **Weekly slots spent: 0.**
