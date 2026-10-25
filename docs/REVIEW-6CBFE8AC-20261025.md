# Repository review — 6cbfe8ac — 2026-10-25

**OK TO DOWNLOAD: YES — existing OLC91 research file only. OK TO SUBMIT: NO.**

No new geological experiment, candidate surface, dots, TIFF or competition upload was produced. This negative result is intentional: the prompt supplies no single-method lane, and the literal registry gate makes the commonly used dot budget infeasible. No thresholds or registry entries were changed to manufacture approval.

[Current research download](index.html) · [Executive summary / submission procedure](executive-summary.html) · [Run card](run-card-6cbfe8ac.json) · [Fresh exact-download check](review-6cbfe8ac/front-door.json) · [All-download audit](review-6cbfe8ac/download-audit.html) · [Capacity proof](review-6cbfe8ac/capacity.json) · [Source manifest](review-6cbfe8ac/sources.json)

## Pass 1 — review and repair

Read the standing README brief, current download manifest, prior active-checkout and S18 next steps, shared renderer/validator, artifact policy and relevant tests. Installed the pinned CPU dependencies in an ignored `.venv`. Restored 15 SHA/length-pinned inputs through the existing restoration tool into ignored `data/`; these are GitHub mirrors, not newly authenticated DrivenData downloads. Restored the single pinned lattice reference to independently check the prior geometric bound.

### Defect fixed: verification targeted a different file

The website's canonical `docs/current-run.json` advertises OLC91, but the default `generate_submission.py` verified HEXFAR91. The `--run` help named OLC91 while launching the HEXFAR91 builder. A user could therefore receive a technical report about a different file from the one downloaded.

- The default command now calls `scripts/verify_front_door.py` and validates the canonical portal card, registered TIFF and exact single-member ZIP, and equality of the committed current-run pointer to the renderer's output.
- It reuses the shared portal raster-format check and, with `--with-data`, `audit_downloads.inspect_raster` against SHA-pinned sample/catalogue bytes. No private evaluator or writer was introduced.
- Missing inputs, pointer drift, corrupt ZIP/TIFF, malformed identity/note, and range/grid failures block download clearance. Delivery verification never authorizes an upload.
- `--legacy-hexfar` preserves the historical verifier explicitly. `--run` fails closed before any builder executes because this prompt has no assigned lane. Both legacy-verifier flags together are rejected.
- The OLC91 renderer now also works when invoked directly as a script, not just imported as a module.
- Corrected front-door wording: historical rather than newly generated file, research rather than unqualified “unique”, historical partial-registry checks rather than blanket uniqueness approval. Removed ambiguous leaderboard-like navigation labels. The executive guide now explains the exact default verifier and avoids claiming the cause of the user's failed upload is known.

The current download remains OLC91 deliberately. “Latest timestamped merged artifact” and “canonical research download” are different concepts. This review did not select S17-CDSC or any other file for a real submission slot.

## What actually explains GEMSDOE32?

Re-fetched its method page through the GitHub contents API. [Pinned team page](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/index.html) explicitly says **NO ORGANISER SCORE EXISTS**, and describes deleting dots within two pixels of the catalogue, leaving 37,654 dots. Consequently **0.2778 remains USER-REPORTED / UNVERIFIED, not ORGANIZER-CONFIRMED**. Its projected number is not a score and is not reused here.

The plausible mechanism is prediction-mass efficiency: distributed sparse dots can cover more distinct trace neighborhoods than redundant adjacent positive pixels, and pruning low-credit mass can improve a spatial Tversky ratio. That is a metric explanation, not proof of better subsurface fault localization, fault permeability, or geothermal-vent discovery. A nearby-catalogue deletion rule may exploit how mapped traces relate to scoring; a hide-and-recover catalogue holdout cannot establish its benefit on genuinely unmapped faults. The archived [pixel forensics](s16/gems32-forensics.json) establishes geometric relationships, not hidden-score causation. No hidden truth or submission receipt is available here.

**Can a method exceed 0.2778?** Possibly, but no such result was established in this session. The conflicting leaderboard figures in the prompt are not receipts. Prior S18's leaderboard snapshot is historical, not a fresh authenticated check. A higher HOLDOUT-DTI from another evaluator cannot be substituted for a leaderboard prediction.

The [official reference notebook](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb) was inspected: it uses Monte Carlo patch splits and a Tversky **training loss**, not our buffered segment-hide spatial evaluator. Its weights must not be used to claim that random-patch validation is an unbiased discovery test. Its [README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) supports CPU-only execution; the standing claim that GPU is mandatory is too strong. CPU training may be slower.

## Ranked screening hypotheses — not assigned lanes or tested results

The existing repo already contains many overlapping proposals and implementations. I cannot certify that these concepts have never appeared across all listed sites. They are **prior deferred proposals**, not invented claims of fleet-wide novelty; the request for 3–5 conclusively never-tried methods is therefore not fulfilled. No expected numerical improvement is asserted. The ranking is qualitative research priority, with uncertainty included.

| Priority | Specific layers / proposed signature | Why potentially catalogue-missing faults | Distinction, confounder, cost, status |
|---|---|---|---|
| 1 | B12 elevation and B19 slope: multiscale directional roughness/Hurst-exponent breaks, normalized within relief classes | A degraded or buried scarp can break roughness across strike even when absolute slope is weak | S18 proposed this but did not test it; differs from a simple ridge/curvature amplitude. Mimic: terrace, shoreline, lithologic/erosional boundary. Medium cost; local base bands available; no new external data required, but 100 m sampling may erase the signature. |
| 2 | B02 RTP and B13 isostatic gravity, with B03/B18 gradients: pair compatible endpoints of signed local cross-field residual breaks | Segmented concealed faults could create finite discontinuities not represented by a long continuous ridge | Prior active review deferred REP; PGRD/CED already contain related residual/edge ideas. Exact paired-endpoint statistic needs code-level novelty review. Mimic: intrusive apophysis or survey seam. Medium cost; base data available. |
| 3 | B12/B19 relief and B15 basement depth: geomorphic-domain-conditioned cross-field edge displacement using B02/B13 | Tests whether an edge survives transfer from exposed upland to covered basin rather than merely continuing familiar mapped terrain | BDT is a prior deferred evaluation proposal, not a new predictor. Mimic: lithologic/depositional contact. Medium-high cost; no external data required. Must retain the original holdout as well as a separately labeled domain-transfer diagnostic. |
| 4 | Official map-unit polygons plus B02/B13 signed displacement conditioned on unit/contact identities | Within-unit displacement, rather than generic lithologic contrast, might be more fault-specific | MUSD was previously proposed, not implemented by this review; related continuous proxies already exist. Mimic: intrusion or inaccurate map contact. High cost; **not viable here** until official USGS SGMC download/coverage/version is verified. [Official source lead](https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d) is outside permitted download hosts. No claim of obtainability is made. |

No implementation was authorized by this missing-lane prompt. Were an exact lane supplied, the top authorized candidate would first need per-feature leakage canaries, then the shared buffered whole-segment hide-and-recover test with visible-only catalogue features and pixel-exact masking, then matched incumbent/paired uncertainty checks. Registry screening must occur on its surface before placement and on final dots; either duplicate threshold stops further work. At most three experiments or two hours; no real weekly slot without the separate selector.

## Pass 2 — independent checks and edge cases

- `python generate_submission.py --with-data` now verifies exactly the OLC91 file linked on the front page: [report](review-6cbfe8ac/front-door.json). Shared inspection PASS: finite [0,1], no NaN inside footprint, zero outside footprint, visible catalogue masked, CRS/shape/transform match. This is technical evidence only.
- Fresh full registered-download audit: **87 files, 78 technical PASS, 9 FAIL**. All have `ok_to_submit: false`. Failing archived NaN/sentinel files remain quarantined; they were not rewritten into fake new submissions. Earlier README counts are historical.
- Artifact policy: **87 registered prediction artifacts; no raw raster/archive tracked**.
- Independently recomputed Euclidean 3-pixel dilation of the SHA-pinned lattice: 6,649 footprint pixels uncovered. At a 37,654-dot budget, unavoidable overlap is at least **82.341849%**, above the team's 70% limit. This is a **GEOMETRIC CAPACITY BOUND, not a score**. The capacity-only maximum is 22,163 dots; that is necessary, not sufficient, and is not permission to place anti-registry noise. No smaller-budget experiment was run.
- Fixed a shared inspector omission: `audit_downloads.inspect_raster` now explicitly checks float32, with uint8/float64 regression cases. No private validator fork was created.
- Added regression coverage for the real default CLI, canonical pointer/card mismatch, forged approval, corrupt TIFF/ZIP, overlong note, missing references and blocked legacy execution. Existing legacy verifier tests remain intact.

## Pass 3 — original-request check

The site already has one-click TIFF/ZIP links and an executive submission procedure. Those links remain research-only and the guide now matches the actual CLI. The protocol's no-lane and duplicate stops were not relaxed to satisfy the request for a new file. The historical full brief remains in the README, with this session's supplied GEMSDOE91/92 updates explicitly identified as unverified user claims. Final complete regression: **568 passed, 1 expected legacy-release skip**, with 62 Rasterio Affine pending-deprecation warnings; no scientific experiment was rerun. New test/audit results are recorded in [verification.json](review-6cbfe8ac/verification.json).

### Remaining blockers and next work

1. **Missing assigned method paragraph:** no new geological lane can be selected autonomously without contradicting the parallel-run instruction.
2. **Literal lattice novelty gate:** the usual dot budget is mathematically infeasible. A policy change, if ever made, must be explicit and versioned by the coordinating selector; this review made none.
3. **Data rights/provenance:** restored mirrors prove byte identity, not authorization. S18 previously recommended pausing mirrors for a rights review; this review used the existing restoration path for technical verification, not model training or redistribution. That unresolved recommendation is flagged, not treated as permission. Raw inputs stay ignored. The mirrored “sample” is not proof of official label semantics.
4. **Score and account access:** no authenticated DrivenData receipt, current weekly allowance or live private score is available. No upload was attempted. Do not infer the weekly cap from the number of repos.
5. **Scientific endpoint:** fault-map recovery is not vent detection or proof of exploitable geothermal permeability. New conduit claims require independent validation and confounder controls.
6. **Source access:** bulk research is limited to allowed GitHub/PyPI/npm hosts. Official USGS, DOE, Landsat and DrivenData URLs remain review leads unless supported by already pinned evidence; external-data obtainability and rights are not established here.
7. **Next implementation priority:** maintain a single explicit publication authority and a separate selector interface, version the gate policy, retain paired same-evaluator tests, and resolve data provenance before new training. No claim of complete fleet-wide or line-by-line external verification is made.

Core values: **Maximize P(Win)** means refusing unsupported promotion and preserving scarce slots. **Own the Outcome** means fixing the actual download verification mismatch and clearly recording the negative result rather than generating another misleading TIFF.
