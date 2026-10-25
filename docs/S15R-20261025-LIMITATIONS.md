# S15R-HCPA limitations and irregularities — 2026-10-25

This companion record controls the corrected isolated S15-HCPA revalidation. See [`REVIEW-S15R-HCPA-20261025.md`](REVIEW-S15R-HCPA-20261025.md) and [`run-card-S15R-HCPA-20261025.json`](run-card-S15R-HCPA-20261025.json).

1. **Catalogue recovery is not organizer discovery scoring.** `HOLDOUT-DTI` hides known fault segments; it is a test of local recovery under the pinned protocol, not an organizer score on unseen expert-labelled geothermal faults.
2. **The failed holdout is nevertheless decisive for this lane.** Best corrected E2 is `0.084995 HOLDOUT-DTI` (95% CI `[0.075507, 0.094735]`) against the same evaluator/withheld-count internal quality bar of `0.267782`. No amount of external geological plausibility turns that into a promotion.
3. **The frozen registry is incomplete.** Only 62 of 64 pinned references are locally recoverable. The two absent GEOD25m10 references mean a universal clearance cannot be claimed. The failure is fail-closed even before considering the available-fleet duplicate.
4. **The literal directed overlap policy is lattice-dominated.** `99.599%` final-dot overlap with `calib_r13lattice_00904.tif` measures 3-pixel geographic coverage by a dense reference as well as lineage. The protocol nevertheless says “any registry raster”; no post-result exception, threshold change, or dot evasion is authorized.
5. **The low surface correlation does not prove novelty.** It only clears the surface half of a two-part check within the 62 available references. Final dots fail, so the result is a duplicate.
6. **The replay TIFF has no release receipt.** An isolated writer correctly rejected its missing SHA ledger. The TIFF is retained outside the checkout solely for forensic reproducibility, not as a downloadable artifact. Its byte hash is not a submission hash.
7. **Canary passing is limited evidence.** Worst single-feature symmetric AUC `0.5932` is below the `0.90` leakage alarm but cannot detect multi-feature leakage, proxy bias, geological confounding, or a train/test provenance defect.
8. **The reported GEMSDOE32 `0.2778` is unverified.** It remains an owner-reported claim without an authenticated organizer submission receipt in this checkout. It is not used as a score, threshold, or proof that sparse geometry is optimal.
9. **Data rights, eligibility, AI disclosure, upload, weekly slot choice, and organizer receipt are human-controlled.** No automation in this repository can make or attest to those actions.

**Resolution:** close S15R as `NEGATIVE_DO_NOT_PROMOTE`. Do not regenerate, package, upload, or call this a unique submission.
