# Submission guide — current automated decision

**OK to download the new research TIFF. NOT OK TO SUBMIT it.**

Use the [executive summary](executive-summary.html) for the exact process, short
name/note, range-error explanation and links to the real file. The [run card](run-card.json)
is authoritative evidence; `src/gems91/readiness.py` is the shared fail-closed policy.

```bash
python scripts/restore_data.py --only sample_submission,existing_faults
python scripts/verify_current_artifact.py --with-data
```

A format PASS is not a novelty/science/selector PASS. No human inspector is needed
to reach the current negative verdict, and no automatic competition upload exists.
Only a future candidate clearing every automated gate plus the separate selector
may use a weekly slot. Record actual organizer-page receipts as ORGANIZER-CONFIRMED;
never infer scores from projections, a filename or a third-party page.

Previous upload queues and model forecasts are archived, not active advice:
[historical instructions](archive/SUBMIT-before-CED91.md).

## H91 historical artifact — NOT OK TO SUBMIT

The H91 E1 file remains available as a research artifact, not as an upload
recommendation. The pinned shared checker measured **38,302/38,400 dots within
3 px (99.7448%)** of `calib_r13lattice_00904.tif`, above the strict >70%
duplicate threshold. Its earlier 20-raster pass is withdrawn because the local
checker omitted `data/fleet_registry` and used symmetric F1 for dense references.
See [`docs/h91-ddvtc.html`](h91-ddvtc.html), the
[machine-readable re-audit](data/h91_lattice_reaudit_20261024.json), and
[`docs/REVIEW-H91-REVALIDATION.md`](REVIEW-H91-REVALIDATION.md). The H91
`0.174030` is historical HOLDOUT-DTI from `gems91-hide-recover-v1.0`, not an
organizer receipt and not comparable to the pinned shared CED evaluator.

## DENOVO file pointer (merged 2026-10-24)

`docs/denovo.html` presents a second unsubmitted file
(`gems91-denovo-hgbctx-37654dots-s2.8-20261024-7941b7ab-zeros.tif`, both repo validators
PASS re-read from disk; audit JSON beside it in `docs/downloads/`). Format PASS is not
approval: under the current fail-closed readiness policy it is **not** cleared for a slot
(no complete-registry novelty pass, no selector approval). See IR-91-36…41 and
`reports/run_card_20261024.json`.

## Session 8, concurrent strain build (2026-10-24, `arena/6f079276-gemsdoe91`) — CONCENTRATION strain variants (built; **not** in the queue)

All three files and their `-zeros` fallbacks are on disk in `releases/`, pinned in
`releases/MANIFEST.json` (never committed). **No agent submits.** All three are predicted
**negative** (`MODEL`) under the frozen SGMC translator, so none is a slot candidate this
week; `strn25m10` is a reserve axis-retirement test only (behind `anti10`), conditional on a
concentration-family receipt first discrediting that translator (`SLOT_PLAN.md`, `docs/MECHANISM_CARDS_STRAIN.md`).

```bash
python3 scripts/restore_data.py
python3 scripts/build_strain_concentration.py --build
python3 scripts/validate.py releases/h33-h33-2-b2-CONCENTRATIONstrn25m10-20261024-85cc49d2.tif
python3 scripts/validate_raster.py releases/h33-h33-2-b2-CONCENTRATIONstrn25m10-20261024-85cc49d2.tif \
    data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif \
    --parent data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
```

| File (`releases/`) | Form note (exact length) | `MODEL` |
|---|---|---|
| `h33-h33-2-b2-CONCENTRATIONstrn25m10-20261024-85cc49d2.tif` | `h33-h33-2-b2; CONC strain 10%: 3765 dots (10.0%) low->high 2.5km blocks, count fixed; pred MODEL:-0.0056` (104) | −0.0056 `[−0.025,−0.003]` |
| `h33-h33-2-b2-CONCENTRATIONstrn25m20-20261024-a88ce2c2.tif` | `h33-h33-2-b2; CONC strain 20%: 7531 dots (20.0%) low->high 2.5km blocks, count fixed; pred MODEL:-0.0200` (104) | −0.0200 `[−0.051,−0.010]` |
| `h33-h33-2-b2-CONCENTRATIONstrd25m10-20261024-106e87d9.tif` | `h33-h33-2-b2; CONC dilatation 10%: 3765 dots (10.0%) low->high 2.5km blocks, count fixed; pred MODEL:-0.0152` (108) | −0.0152 `[−0.030,−0.008]` |

### Session 8 format receipt (`RECEIPT`, re-read from disk after write)

```text
1. h33-h33-2-b2-CONCENTRATIONstrn25m10-20261024-85cc49d2
   primary (.tif)        sha256=85cc49d2b572f1eb9967b84ae165941633f3a4b822157ed10ca9f9abce55dc4d (367,003 B)
   fallback (-zeros.tif) sha256=3b7038678a6f99c74d89c72f3499f79342dad87e4f68f8d3e0d922228af6251a (221,637 B)
   dots 37,654 unit-mass | count_matches_parent PASS | cat_mass 0 | min_d_cat 2.2361 px (added_le3px 0)
   collar 2,171 -> 2,171 | moved 3,765 (10.00%, Hamming 20.00%) | mean disp 2493.3 px
   gates: release_gates PASS (nan + zeros) | validate_raster 14/14 PASS | reread_from_disk PASS
2. h33-h33-2-b2-CONCENTRATIONstrn25m20-20261024-a88ce2c2
   primary (.tif)        sha256=a88ce2c270cdb68785dc89fa8da67342d55e9695f54af0c72e5c890737dc56ce (363,042 B)
   fallback (-zeros.tif) sha256=51dbfde66426661dd77cddcdfc17bfe69edcd4a61945b4eaeb4e9b5446ea6e47 (218,365 B)
   dots 37,654 unit-mass | count_matches_parent PASS | cat_mass 0 | min_d_cat 2.2361 px (added_le3px 0)
   collar 2,171 -> 2,171 | moved 7,531 (20.00%, Hamming 40.00%) | mean disp 2323.7 px
   gates: release_gates PASS (nan + zeros) | validate_raster 14/14 PASS | reread_from_disk PASS
3. h33-h33-2-b2-CONCENTRATIONstrd25m10-20261024-106e87d9
   primary (.tif)        sha256=106e87d9fa9e461c2f12cd635c92c4e050da5741fce2c19037efa06268792e95 (368,488 B)
   fallback (-zeros.tif) sha256=09eef831b15a28220d27be72af8eae7e414fc74bc539a2644490c4487eb5f58c (221,931 B)
   dots 37,654 unit-mass | count_matches_parent PASS | cat_mass 0 | min_d_cat 2.2361 px (added_le3px 0)
   collar 2,171 -> 2,171 | moved 3,765 (10.00%, Hamming 20.00%) | mean disp 1464.8 px
   gates: release_gates PASS (nan + zeros) | validate_raster 14/14 PASS | reread_from_disk PASS
PROXY (report only, never a score): catalogue hide-and-recover 0.006186 [0.005958, 0.006413],
5 draws, 12,198-12,201 withheld positives/draw - identical for R0 and all arms BY
CONSTRUCTION (donors quarantined, targets >3px; IR-91-28). SGMC off-catalogue (62,122 px,
USGS DS-1052): R0 0.095386 -> -0.00382 / -0.01356 / -0.01036. Band leakage canary max 0.5793.
```

**Do not** upload a strain arm ahead of the revised queue, and do not upload more than one:
they are one experiment whose control already answered against it.
