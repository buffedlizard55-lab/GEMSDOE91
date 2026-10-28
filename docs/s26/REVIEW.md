# S26 three-pass review · 2026-10-28

**No new TIFF; no approved submission; no leaderboard estimate.** Historical TLF remains downloadable for research, not a new unique attempt. [Corrected executive summary](../s25-tlf/executive-summary.html) includes all nine requested sites and submission gates.

## Pass 1 — inspect and measure

- Read README, existing limitations, S25-FABRIC and TLF runners, shared metric/folds/writer and historical receipts. Installed pinned Python requirements.
- Restored 15/15 manifest inputs and 62/64 frozen references with hashes verified, plus 108 matched anchor files and nine leaders. Raw data stay ignored. Missing two retracted local references are reported, not excused.
- Baseline suite passed with 11 skips. Baseline artifact policy passed for 121 files.
- GitHub main CI run 40690857550 failed its all-download snapshot comparison (job API verified); regenerated `docs/download-audit.json` and HTML: 121 files, 112 technical PASS, nine FAIL.

## Pass 2 — adversarial scientific review

Rechecking TLF against all 62 restored frozen references found directed 3-px overlaps: lattice 99.601667%, r11 greedy 93.826667%, r14 union 76.061667%. This violates the user's literal rule regardless of nine-leader uniqueness. Complete universal clearance remains unknown. No further experiments were launched.

The prior “surface Spearman” measured smoothed final dots with arbitrary tie ordering over the rectangle, not the original pre-placement surface on the footprint. Final-dot exact ranks cannot retrospectively prove the required surface gate. Original surface was not saved. SGMC was used to choose weights and budget, so its result and spatial slices are not blind validation. Canaries were on SGMC rather than the requested holdout. Lidar input rights/provenance remain unresolved; B06 signed-tilt interpretation conflicts with prior internal band audits. A hash authenticates bytes, not semantics or permission.

The 0.36 forecast was a midpoint between an unreceipted historical claim and an assumed public ceiling. It has no calibrated uncertainty or lower-bound guarantee and is withdrawn. Historical HOLDOUT-DTI arithmetic is retained without a new scientific approval. Corrected run-card verdict to negative, disabled unsafe reruns and archived originals without changing TIFF/ZIP bytes.

## Pass 3 — reconcile delivery and requirements

Corrected README, root/docs front doors, TLF executive summary and renderer. Kept download links and exact filenames/name/note but explicitly marked research-only. Added deterministic audit and regression tests. Main renderer reapplies the correction so publication cannot revive the unsafe approval. Refreshed the stale download audit rather than weakening CI. Full project prompt already exists in README; the current review links it rather than duplicating 170 KB again.

## Official sources read this session

- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): expert-mapped new faults; 100 m EPSG:32611, float32 [0,1], triangular 300 m kernel, alpha .2/beta .8. B15 is conductive-base depth, not established sediment thickness. Fault predictions do not prove geothermal vents.
- [Staff mask clarification](https://community.drivendata.org/t/11516/4): known pixels masked exactly; new faults can occur within 300 m of known traces. Neither collar pruning nor sparse dots guarantee higher scores.
- [Official background](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/): topography and potential fields can help detect structures, not a validation of any proposed mechanism.
- [Live public board](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/): observed rank one 0.4544 on Oct 28, superseding supplied 0.3195/0.4413. Not an artifact receipt.
- [Staff reply Oct 28](https://community.drivendata.org/t/11587/3): changing two-round submission selection is unlikely, not an adopted rule change.
- [External-license discussion](https://community.drivendata.org/t/11584): no permission-granting organizer answer visible when read. Official external-data requirements still apply.

## Next session, in order

1. Resolve explicit method assignment and versioned registry scope with coordinator; do not self-exempt dense witnesses or move dots into lattice holes.
2. Confirm input provenance/licences and official band identities. Obtain same-fold, same-budget incumbent predictions, per-feature holdout canaries and retained surface evidence before comparing candidates.
3. Four ranked deferred hypotheses are in `preregistration.md`; none has a new measured improvement. Do not describe coarse detrended elevation as hydraulic head, B15 as known basement thickness, or strain invariants as a full stress tensor.
4. Need unrestricted bulk-data access for official 3DEP tiles or a licensed hash-pinned derived stack. No authenticated DrivenData session/quota/receipt is available here; no credentials requested. Current remaining quota cannot be inferred from historical three/week wording.
5. A future file must beat matched holdout best, pass every required gate and receive a separate selector decision. No promise of exceeding 0.2778, 0.3195 or current rank one is justified.

## Final local verification

Full `python -m pytest -q` passed after fixing two corrective-render integration issues; two data-dependent tests skipped in the restored checkout. Artifact policy PASS (121 registered files). `verify_frontdoor.py` passed. Fresh all-download JSON and HTML exactly match committed snapshots. `git diff --check` passed. Browser verification for the new summary was not run locally; existing CI browser checks remain enabled. These are software/delivery checks, not scientific validation or organizer acceptance.
