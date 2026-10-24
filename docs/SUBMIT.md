# Submission status and procedure

## Current verdict

**NOT APPROVED — no active GeoTIFF is available to download or submit.** The old GEOD pair has been removed from `docs/downloads/`; it must not be reused. The current run is blocked before experiment because the assigned lane paragraph is missing, the shared `evaluate_holdout.py` / `submission_writer.py` are absent from this checkout, and the official data files are not present locally. See [`REVIEW-20261024.md`](REVIEW-20261024.md) and [`run-card.json`](run-card.json).

## Approval contract for a future candidate

Do not expose a TIFF link until all of these are recorded and pass:

1. A lane-specific, preregistered hypothesis and method.
2. The shared buffered whole-segment holdout: fold-specific features from visible faults only; visible faults masked pixel-exactly; pooled official DTI using `alpha=0.2`, `beta=0.8`, and the 300 m triangular kernel; evaluator version, withheld-positive count, and 95% CI recorded.
3. Single-feature leakage canaries, with AUC `>0.90` stopping the run until explained.
4. Pre-placement surface comparison and post-placement dot-overlap comparison against every registry raster. Rank correlation `>0.90` or more than `70%` of dots within 3 px of any registry raster is a duplicate and must stop.
5. Improvement over the current compliant holdout best.
6. Written-and-reread raster validation against the organizer sample: one float32 band, exact CRS/shape/geotransform, predictions in `[0,1]`, null/NaN outside bounds, and exact SHA256 recorded.
7. Separate selector authorization for one weekly slot.

An unknown or missing gate is **UNVERIFIED**, not PASS. Historical model/proxy values do not satisfy these criteria.

## How to submit after approval

1. Open the live [DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) and confirm current schedule, eligibility, and remaining quota.
2. Download only the single approved TIFF link shown on the GEMSDOE91 status page. Verify the file hash; do not re-encode, change nodata, or rename it.
3. On the New submission form, choose the single-band GeoTIFF (or a ZIP containing one GeoTIFF if the form offers that option), then paste the generated note (maximum 140 characters).
4. Save the organizer receipt and associate it with the exact TIFF hash. Only the receipt value is ORGANIZER-CONFIRMED.
5. Before the deadline, use the separate selector to choose one final submission across both prize phases. Official rules allow up to three scored submissions per week, subject to the live website; final content is due by 5 p.m. ET on the deadline date, whose current date must be checked on the live website. Finalists must provide reproducible code assets and documentation.

The official [format specification](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) requires EPSG:32611, 100 m resolution, the same bounds, a single float32 layer, values in `[0,1]`, and null/NaN outside bounds. The historical range-error report cannot be attributed without the exact uploaded file and organizer validation output; see the [executive summary](executive-summary.html).

No agent submits, logs in, stores credentials, or selects the final file. The registered competitor remains responsible for account actions, AI-use disclosure required by the official rules, the upload, and the final selector.
