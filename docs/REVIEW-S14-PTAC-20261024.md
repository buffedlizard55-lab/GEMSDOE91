# S14-PTAC three-pass implementation and review — 2026-10-24

## Final decision

**OK TO DOWNLOAD: YES — research/audit only. OK TO SUBMIT: NO.**

The generated competition-format artifact is:

- GeoTIFF: `docs/downloads/gems91-s14-ptac-e2-20261024T235500Z-76262b89-zeros.tif`
- Research name: `GEMS91-S14-PTAC-E2-e84046d8`
- SHA-256: `29a3c32b5dad73545b7bdbc8315a14ceed7bbb3472524fe6ca9b0943de7effea`
- Note (88/140): `S14-PTAC research only: final 3px overlap 99.852%; duplicate gate failed; do not submit.`

The file is byte-distinct and was generated from a distinct method, not copied from a prior submission. It is **not protocol-unique**: 99.852% of its dots are within 3 pixels of `calib_r13lattice_00904.tif`, above the literal 70% limit. The run card therefore records `STOPPED_DUPLICATE`, `technical_candidate_verdict=negative`, `portal_submission_verdict=NOT_OK_TO_SUBMIT`, and `submission_ready=false`. Zero organizer slots were selected or spent.

## Measured results and label discipline

All primary values below are **HOLDOUT-DTI**, evaluator `gems91-hide-recover-v1.0`, 60,988 withheld positives, whole fault segments hidden with buffers, and a 300 m triangular kernel. They are neither projections nor organizer scores.

| Arm | Mechanism | HOLDOUT-DTI | 95% CI | Paired delta vs S13 E3 | Paired 95% CI |
|---|---|---:|---|---:|---|
| E1 | Cross-fitted posterior-topology auto-context + arithmetic pool | 0.264229 | [0.250693, 0.279112] | +0.019628 | [+0.014455, +0.024972] |
| **E2** | E1 + two-sided bridge × independent physical crest | **0.267782** | **[0.253687, 0.281135]** | **+0.023181** | **[+0.017703, +0.028161]** |
| E3 | E2 + log-odds opinion pool | 0.266381 | [0.250902, 0.279871] | +0.021780 | [+0.016224, +0.026157] |

Frozen comparator S13-PTHA E3 reproduced at `0.244601 HOLDOUT-DTI`, 95% CI `[0.230592, 0.257058]`. The blind SGMC off-catalogue control for the emitted S14 file is `0.095760` (report-only), versus R0 `0.095386`. `ORGANIZER-CONFIRMED`: none.

## Why reported GEMSDOE32 `0.2778` may have led

No authenticated organizer receipt available to this checkout proves `0.2778` or ties it to `h33-h33-2-b2`; it remains an owner/user-reported claim. Byte forensics do verify the 37,654-dot artifact's thinning and catalogue-near pruning lineage. Under max-kernel DTI, nearby predictions saturate truth credit while redundant prediction mass continues to pay an α=0.2 false-positive cost. Sparse, separated, ridge-centered dots therefore plausibly outperform thick halos. This is a metric mechanism, not causal proof of the claimed result.

S14 is a genuinely distinct detector and its same-split paired interval is wholly positive. That supports posterior topology as a plausible improvement direction. It does **not** establish that S14 would beat `0.2778` on the organizer's hidden, newly interpreted faults. The present output must not be submitted because final support novelty failed.

## Pass 1 — implement and verify

1. Restored all 15 hash-pinned inputs and recovered the two missing GEOD registry rasters byte-for-byte from immutable repository history.
2. Reproduced the frozen S13 comparator before S14 work.
3. Preregistered five ranked geological hypotheses in `docs/HYPOTHESES_S14.md` before any S14 fit. Each names layers, signature, missing-fault rationale, mimics, difference from existing methods, expected gain, cost, and data availability.
4. Implemented `src/gems91/ptac14.py`, `scripts/run_s14_lane.py`, and synthetic tests in `tests/test_ptac14.py`.
5. Reused the shared evaluator, S13 Dinkelbach emitter, and shared submission writer.
6. Ran all 85 features alone as leakage canaries; worst symmetric AUC was `0.74517`, below `0.90`.
7. Executed exactly three preregistered arms, within the 7,200-second cap.
8. Emitted and re-read the all-finite TIFF and single-member ZIP; generated one JSON run card and evidence copy.

## Pass 2 — bug, requirement and edge-case review

Findings and fixes:

1. **Memory retention:** the initial full-map phase retained every fold/arm surface and was killed by the 4 GB sandbox after all holdout arms had completed. The runner now releases holdout-only surfaces, dots, masks and memmap views before topology extraction, and skips loading six dense pair surfaces when all fold auto-context caches exist. The resumed run reproduced every arm exactly. This did not add a geological experiment.
2. **Misleading upload field:** the negative card initially populated `recommended_upload_file`. The final schema sets it to `null` and exposes `research_download_file` instead.
3. **Negative note:** the note now explicitly states research-only, the measured 99.852% overlap, duplicate failure, and “do not submit” in 88 characters.
4. **Portal contradiction:** a historical G91 card still said “OK to submit: YES” under an obsolete exception. The renderer now states `NO` under the literal shared directed-overlap policy.
5. **Artifact policy:** registered the S14 TIFF and ZIP as `current_research_only`; no raw training, label, cache or external raster was added.
6. **Portal contract:** added S14 link, verdict, hash and render-reproducibility coverage to `tests/test_submission_portal.py`.

Verification after fixes:

- Full repository test suite: PASS (one existing skip; rasterio pending-deprecation warnings only).
- `scripts/validate_raster.py`: all mandatory checks PASS; 12,279,160 finite cells, `[0,1]`, 44,000 positive pixels, matching CRS/shape/transform, zero catalogue mass.
- Independent `vendor.gems57.validate`: all checks PASS.
- `scripts/check_artifact_policy.py`: PASS.
- TIFF and ZIP SHA-256 identities match the run card; ZIP has exactly one TIFF member.

## Pass 3 — final line-by-line recheck

1. Confirmed the preregistration hash in the run card matches `docs/HYPOTHESES_S14.md`.
2. Confirmed E1/E2/E3 values, confidence intervals, paired deltas and per-fold values are labelled HOLDOUT-DTI only.
3. Confirmed no organizer-confirmed score, live slot state, deadline or leaderboard claim is fabricated.
4. Confirmed the surface test ran before placement (`max |ρ|=0.22119 < 0.90`) and the final literal test checked all 73 hash-distinct local same-grid references (`99.852% > 70%`, duplicate).
5. Confirmed the written TIFF is single-band float32, EPSG:32611, 3730×3292, affine-matched, finite, `[0,1]`, `nodata=None`, zero on mapped catalogue pixels, and at least 3.1623 pixels from the catalogue.
6. Confirmed Pages landing, S14 audit, and S14 executive summary immediately state download `YES — research only` and submission `NO` with a direct file link.
7. Confirmed README preserves the standing prompt and now leads with the S14 result, limitations, irregularities and next steps.
8. Confirmed no autonomous organizer upload occurred and the three-experiment budget is closed.

## Sources and access limits

- Organizer-maintained reference code: <https://github.com/drivendataorg/gems-prize-reference-solution>, fetched through GitHub at commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`.
- GEMSDOE32 lineage source: <https://github.com/buffedlizard55-lab/GEMSDOE32>. This is forensic lineage, not organizer evidence.
- Official source leads are retained in `docs/HYPOTHESES_S14.md` and `docs/sources.json`. Non-GitHub DrivenData, NLR, USGS and GDR hosts and authenticated organizer account state were not reachable in this sandbox.
- Restored input hashes establish identity to repository pins, not organizer authenticity, redistribution permission, eligibility, or current account state.

## Next steps

1. Do not upload S14-PTAC E2.
2. Resolve or explicitly reaffirm the dense-calibration-lattice treatment in shared fleet policy before any future method fit; do not retrofit S14 dots to evade a known registry raster.
3. Supply an actual assigned method lane.
4. On an unrestricted host, establish official USGS 3DEP 1 m footprint coverage and permitted use before testing the preregistered micro-scarp hypothesis.
5. Retain `0.267782 HOLDOUT-DTI` as the frozen same-evaluator research baseline. Any live score must come from an authenticated receipt and be labelled ORGANIZER-CONFIRMED.
