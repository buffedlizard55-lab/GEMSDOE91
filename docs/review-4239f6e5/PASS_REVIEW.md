# Three sequential implementation / review / recheck passes

All three passes concern engineering, evidence and governance, not a new geological experiment. The active lane is unassigned; **zero competition candidates and zero weekly submission slots** were used.

## Pass 1 — inspect and independently remeasure

- Read the full preserved README brief, shared evaluator and both writer paths, plan, manifest, recent run cards and historical corrections. The branch started from `45a2a4368cb1a1b2a21953fdcc4eedd116c19cc7` on main. No user files were removed or reset.
- Restored and SHA-checked only the sample/catalogue mirrors and one frozen lattice witness; recorded 13 missing manifest inputs. Recomputed the conditional 37,654-dot capacity bound from the actual pixels rather than relying on an archived number.
- Fetched all nine specified leader TIFFs as GitHub blobs, checked Git blob IDs and SHA-256s, grid and supplied footprint, and computed the full-precision Euclidean pairwise dot overlap. Refetched nine owner page inventories. None of this obtains a submission receipt or proves source rights.
- Reread S25 TIFF and single-member ZIP; checked exact final-dot ranks and directed overlaps vs nine leaders and the lattice, and stopped at the first duplicate. The prior out-of-fold holdout is not the final raster’s measurement.

## Pass 2 — adversarial implementation and review

- Fixed the shared legacy bundle writer and low-level encoder to reject malformed original outputs, silent float32 underflow, bad catalogue masks/grids and invalid ZIPs; staged, reread and validated outputs before no-clobber publication, with rollback on ordinary failures. A separate synthetic race test exposed the same check-then-replace risk in the pinned shared template writer; corrected it in place, archived its exact preceding bytes, and updated the active/historical template pins.
- Added adversarial synthetic tests for NaN/Inf, negative sentinels, pre-cast overshoot, support underflow, masked catalogue, grid mismatch, collar failure, corrupt ZIP, existing files, racing writers and rollback. Fixed the synthetic catalogue fixture so valid zero background is not tagged as NoData. A crash during multi-file publication and a race between identity-check and unlink remain outside the ordinary-exception guarantee.
- Detected the sample semantic discrepancy: the mirror has 60,988 positive cells, while the official description says its sample predicts total absence. Made preflight fail closed on a mismatch or unavailable semantic evidence; a zero sample alone still would not authenticate provenance.
- Corrected the older nine-site diagnostic so empty/undefined evidence is not a pass, full grid metadata is checked, and sampled correlation is described only as a diagnostic. Reused the archived shared checker in a new footprint-aware audit rather than changing its historical source identity. Refused to present the withdrawn S25-TLF projection as current.

## Pass 3 — requirements and delivery recheck

- Rebuilt the generated front door and detailed executive table from the saved negative card and exact evidence; the submission guide names all gates, the unverified outside-bounds encoding and separate selector. Added the three prospective hypotheses, named mimics, costs and official-source links. The entire standing prompt remains in README.
- The complete pytest suite passed with nine skips; local artifact-policy and historical byte/source verification passed. `make demo` and its validator passed on **synthetic fixtures only**; these ignored files are not submission TIFFs or geological experiments. A previous full run caught one historical wording assertion, corrected in the renderer without rewriting the old test.
- Real headless Chromium verified the new S25 research TIFF and ZIP download hashes, the current stop and sample warning, mobile layout, root redirect, simulated 8-of-9 GitHub-feed fallback, and accessibility. [Browser receipt](browser-verification.json): PASS, zero recorded HTTP/console errors, no mobile overflow, no WCAG A/AA violations on the checked pages. Browser/UI success is not scientific or organizer approval.
- Remaining blockers: real assigned method, coordinator resolution of the literal lattice/budget conflict, authenticated official sample and data rights, feature stack, complete frozen registry, matched comparable holdout, server format acceptance and a separate selector with live quota. A later repeated GitHub REST request was rate-limited; the earlier saved snapshots are dated and the feed preserves them when refresh fails.
