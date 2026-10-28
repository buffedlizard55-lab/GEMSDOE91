# GEMSDOE91 checkout review — 2026-10-28

## Decision: negative / blocked

**No new GeoTIFF was generated. OK to download: NO new artifact. OK to submit: NO.** Zero experiments and zero competition slots used. This is intentional: the current experiment plan has no assigned lane and the required local submission/registry rasters are absent. A submission made without the prescribed holdout and complete registry checks would contradict the user’s protocol, not satisfy it.

The supplied nine-site top score, GEMSDOE32 `h33-h33-2-b2…zeros`, **0.2778 USER/OWNER-REPORTED (unverified; not ORGANIZER-CONFIRMED)**, remains the historical benchmark from the request. It cannot be tied here to an organizer receipt. Neither that number nor the supplied overall-board values are a defensible estimate for a newly generated TIFF. No new candidate exists, so its estimated leaderboard score is **NOT ESTIMABLE** (not zero).

## What was checked

- `git status` was clean at review start.
- `python scripts/preflight.py` reported both required current review inputs missing: `data/official/sample_submission.tif` and `data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif`; 0/2 verified. All six listed build axes were blocked.
- Ran `python scripts/audit_focus_sites.py --workers 4 --output docs/review-20261028/focus-inventory.json`. It fetched non-truncated GitHub main snapshots for all 9 focus repositories (24, 25, 27, 28, 30, 31, 32, 33, 36). Receipt identifies each commit, page hash, found TIFF links and page excerpts. This is a dated source inventory, **not** an organizer leaderboard or score receipt, not the complete cross-repository registry, and not a byte-level audit of every linked raster.
- Page excerpts include warnings that historical artifacts may be research-only, duplicate, or fail a submission selector. For example, the current GEMSDOE36 excerpt reports a prior internal HOLDOUT-DTI and a high overlap against one registry witness; that is not a current verified live score or authorization. Current page contents must not be conflated with the user's earlier list of “highest” scores.
- No live DrivenData page or submission receipt was retrieved in this review; network/source inventory was GitHub-only. Do not state that a claimed score is organizer-confirmed.

## Site-by-site executive summary

Below are the best *user-supplied historical claims* among the entries in the prompt, not a verified current ranking. The snapshot receipt is the audit source for current site-page status. “Unique?” is **not established for a new candidate** because none was built; the existing pinned historical audit at [`../nine-site-audit-20261026.html`](../nine-site-audit-20261026.html) found that the nine historical rasters it compared fail the requested 3-pixel/70% peer novelty rule. Do not download those old files as a recommended submission.

| Site | Highest score supplied in prompt (provenance) | Claimed top artifact | Estimated score for a new artifact | Unique vs other eight | Download / submit decision |
|---|---:|---|---|---|---|
| GEMSDOE24 | 0.2477 USER/OWNER-REPORTED | `h25-1-dotted-h19-5-d1-5` | NOT ESTIMABLE | No, historical audit says fail | No new file; do not submit historical file |
| GEMSDOE25 | 0.2600 USER/OWNER-REPORTED | `dotted-h19-5-d2-8` | NOT ESTIMABLE | No, historical audit says fail | No new file; do not submit historical file |
| GEMSDOE27 | 0.2449 USER/OWNER-REPORTED | `topo-gap-closure-t-v2-on-d1-5` | NOT ESTIMABLE | No, historical audit says fail | No new file; do not submit historical file |
| GEMSDOE28 | 0.2710 USER/OWNER-REPORTED | `h36-1-rung30-blind-r1` | NOT ESTIMABLE | No, historical audit says fail | No new file; do not submit historical file |
| GEMSDOE30 | 0.2600 USER/OWNER-REPORTED | `d28-poisson300m-offcat-44090` | NOT ESTIMABLE | No, historical audit says fail | No new file; do not submit historical file |
| GEMSDOE31 | 0.2708 USER/OWNER-REPORTED | `h27-4-solo-d28` | NOT ESTIMABLE | No, historical audit says fail | No new file; do not submit historical file |
| GEMSDOE32 | **0.2778 USER/OWNER-REPORTED** | `h33-h33-2-b2` | NOT ESTIMABLE | No, historical audit says fail | Historical benchmark only; not submit |
| GEMSDOE33 | 0.2632 USER/OWNER-REPORTED | `h33d-analog-tip-stepover-r30` | NOT ESTIMABLE | No, historical audit says fail | No new file; do not submit historical file |
| GEMSDOE36 | 0.2750 USER/OWNER-REPORTED | `anderson-geothermal-pinn` | NOT ESTIMABLE | No, historical audit says fail | No new file; do not submit historical file |

Current snapshot inventory: [`focus-inventory.json`](focus-inventory.json). Historical overlap table and scope: [`nine-site-audit-20261026.html`](../nine-site-audit-20261026.html). These sources differ in date and scope; neither converts user/site-page values into organizer-confirmed receipts.

## GEMSDOE32 score: what can and cannot be concluded

The 0.2778 value is a supplied owner/user claim. Prior repository forensic notes describe the raster as related to earlier dense/dotted candidates with thinning and pruning near known catalogue traces. A plausible metric-level explanation is that reducing redundant predicted pixels can improve precision-like utility under a distance-tolerant Tversky-style metric, particularly when known catalogue faults are excluded from the target. However, this is **not a causal demonstration** and does not prove geothermal vent discovery: the hidden truth, receipt-to-raster binding, score decomposition, and a controlled ablation are unavailable here. The score may be exceeded in principle; this checkout provides no evidence to promise an improvement or quantify one.

## Candidate hypotheses to preregister after blockers clear

Qualitative ranking only, not score estimates. These are proposed contrasts, not assertions of global novelty; inspect implementations and all parallel-lane registries before selection. The repo codebase is extensive and includes numerous terrain, magnetic, radiometric, structural, and proxy experiments. The actual assignment says “single method paragraph below,” but no assigned paragraph is present in this checkout; therefore none is authorized to implement now.

| Rank | Hypothesis, layer(s), target signature | Why it may detect uncatalogued faults | Main non-fault mimic | Difference / cost |
|---|---|---|---|---|
| 1 | Cross-band **conditional edge discordance** in the cached magnetic RTP, gravity anomaly, and radiometric channels; test edge persistence after conditioning one band on the others, over fixed scales. | A concealed basement discontinuity may create a coherent anomaly in one physical field not explained by a mapped lithologic/contact response in the others. | Lithologic boundary, flight-line seam, altered/variable cover. | Tests conditional residual edges rather than simply fusing raw edge magnitude; medium cost, no new external data if specified cached stack is restored. |
| 2 | **Multiscale directional texture discontinuity** in detrended DEM and slope/curvature; compare structure-tensor orientation/entropy across opposing sides of candidate breaks. | Fault-related drainage or scarp fabrics can change across a concealed structure even where absolute relief is weak. | Fan margins, stream capture, roads, shorelines. | Focuses on cross-break anisotropy rather than lineament strength; medium cost, cached terrain bands required. |
| 3 | **Joint gravity–magnetic profile parity/reversal**: signed cross-strike profiles of gravity anomaly and magnetic RTP at multiple widths, prioritizing spatially persistent polarity/offset relationships. | A buried offset can produce paired field responses not represented by a surface-fault catalogue. | Intrusive contacts, remanent magnetization, survey seams. | Explicit signed profile geometry, not generic multi-channel rank fusion; medium/high cost. |
| 4 | **Exposure-controlled radiometric ratio break** across potassium/thorium/uranium ratios, conditioned on DEM-derived terrain exposure and slope. | Alteration or differential exposure along unmapped structures could leave a narrow ratio discontinuity. | Soil/vegetation, weathering, moisture, lithology. | Separates ratios and exposure controls; medium cost, requires verifying band identity, units, and NoData behavior first. |
| 5 | **Drainage deflection + profile-break conjunction** from official USGS 3DEP elevation products and cached DEM; require both a persistent channel-direction change and a cross-strike slope break. | Fault displacement can perturb channels beyond mapped traces; conjunction should reduce standalone geomorphic false positives. | Fan switching, anthropogenic drainage, lithologic control. | A two-observable geomorphic test rather than another single DEM scarp score. High cost; exact tile coverage/downloadability not verified, so not viable until checked. Official source: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). |

Before any test: confirm the bands and transforms from the authorized stack metadata, preregister the one assigned lane, and run single-feature canaries. If a needed layer is not in the cache, the experiment is blocked until an official source and exact coverage are verified. No public link alone proves local availability or suitability.

## Three-pass completion review

**Pass 1 — implementation/review:** read the current README decision banner, current review docs, preflight and site-inventory tool. Captured the current immutable GitHub snapshots for all nine requested repositories; did not edit old results or create an unsupported artifact.

**Pass 2 — errors and assumptions:** confirmed 0/2 required inputs, absent experiment assignment, and no ability to construct a valid new submission surface. Treated the nine historical score values as user-reported, not receipts. Kept historic overlap findings scoped to the pinned historical audit rather than presenting them as a new raster's uniqueness result. Checked that inventory explicitly says no organizer receipts and not universal registry coverage.

**Pass 3 — request compliance:** executive table, explanation of the 0.2778 claim, ranked five hypotheses, biological/geological mimics, source access caveat, three-pass log, no-projection discipline, and current download/submit verdict are included. A fresh unique TIFF is **not responsibly achievable** with missing inputs and no lane. This is a negative result, not a silently substituted prior TIFF.

## Required next actions and limitations

1. Restore the exact authorized, hash-pinned feature/fault/sample inputs using the documented allowed workflow; current preflight specifically requires sample raster and pinned parent reference. Do not retrieve or upload competition data through unauthorized routes.
2. Put the actual single-method assignment paragraph and owner/assignment provenance in the experiment plan.
3. Reuse the shared template cache, `scripts/evaluate_holdout.py` and `scripts/submission_writer.py`; fix shared utilities in place if broken. Withhold whole fault segments plus buffer, derive catalogue-based features only from visible segments, pixel-mask visible segments, use pooled DTI α=.2, β=.8, 300 m triangular kernel and report evaluator, withheld-positive count and 95% CI.
4. Test each feature alone on the holdout; AUC > .90 is a leakage alarm. Apply the specified rank-correlation and 3-pixel overlap duplicate stop to the surface before placement and final dots, against the complete registry. Existing nine-raster comparison alone is not complete registry clearance.
5. Require a positive, matched spatial holdout improvement before the separate slot selector. Validate values inside the footprint are finite and in [0,1], plus exact CRS/shape/transform. Preserve SHA-256, validator output, brief submission name and ≤140-character note. No weekly slot may be selected in this review.
6. Live organizer submission receipt, current leaderboard snapshot, current weekly quota and competition account status are unavailable here. Require a receipt to label any score ORGANIZER-CONFIRMED.

## Official/manual sources

Links for independent review (the links themselves are not evidence of a live check in this pass): [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [rules](https://www.drivendata.org/competitions/306/competition-doe-gems/), [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [DOE/NLR report](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), [EPSG:32611](https://epsg.io/32611). This review fetched GitHub snapshots only; it did not verify the current DrivenData, NLR, or USGS pages live.

## Run card (summary)

See [`run-card.json`](run-card.json). Values not measured are null; no holdout DTI, correlation, overlap, raster hash, or validator pass is fabricated.
