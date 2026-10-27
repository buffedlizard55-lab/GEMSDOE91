# Three review passes — 27 October 2026

The scope is the current review, changed code and its relevant historical
receipts—not a claim that every line in the repository's extensive historical
archive or every outside site has been independently audited.

## Pass 1 — inputs, geometry, provenance

- Restored four SHA-pinned input files from community mirrors and 62/64 frozen
  references; source identity is not an authenticated organizer provenance.
  A separate radiometric mirror was later restored solely for a label-blind
  diagnostic; its provenance and redistribution licence remain unverified.
- Inspected GDAL masks, finding 3,061 finite NoData pixels inside the sample
  footprint in each of S22's two feature bands. Rejected masked/extreme data in
  the active feature helper, archived the prior implementation, and retained
  the old holdout values as compromised bookkeeping, not valid science.
- Independently reproduced the S18 99.605% witness and the fixed-plan
  82.341849% lower bound. Corrected the capacity preflight to ignore
  out-of-footprint reference cells, consistent with the actual dot comparator;
  regression-tested the synthetic edge case. The real pinned witness has zero
  such cells, so its bound did not change.

## Pass 2 — scientific claims and official sources

- Inspected all nine pinned historical file identities and 72 directed
  peer-overlap receipts; user claims remain unverified and estimates null.
- Checked the official score/format page, public board, staff mask/aggregation
  and submission-limit clarifications, USGS GeoDAWN, 3DEP, Landsat and SGMC,
  INGENIOUS GDR, and a blind-system case study. Sources and coverage limitations
  are linked in the current review.
- Ranked four provisional mechanisms and named non-fault mimics before coding;
  none was assigned, run or presented as a score forecast.
- Repaired the shared absolute-Spearman novelty threshold and archived its old
  source without changing historical provenance. The old S18 generator was
  replaced by a fail-closed stub; its source and misleading page are preserved
  as inert evidence.

## Pass 3 — implementation, delivery and tests

- Registered the two already-tracked S18 2026-10-26 research artifacts in the
  artifact policy, regenerated the technical audit, and checked historical
  TIFF/ZIP hashes. No old prediction bytes were replaced and no new competition prediction
  TIFF was generated; `make demo` produced only small synthetic test rasters
  under ignored `tests/_tmp`.
- Made the current portal derive from persisted receipts, clearly separate
  historical research downloads from upload permission, show all nine named
  files and their unverified claims, and provide a public GitHub-head refresh
  with partial-failure fallback and no credentials.
- Ran the full Python suite and pinned evidence verifiers, and exercised real
  Chromium desktop/mobile pages, downloads, axe accessibility and a mocked
  eight-success/one-failure public source refresh. The [run card](run-card.json)
  records the exact test counts; [browser evidence](browser-verification.json)
  and [local S22 validator output](historical-s22-validator.json) are stored
  separately. Tests and byte-format passes are not geological experiments or
  organizer acceptance.

## Remaining blockers

No supplied method paragraph, no viable frozen dot budget under the literal
registry rule, two unavailable reference files, no authenticated organizer
receipt/quota, no matched incumbent rerun, unknown official acceptance of the
outside-footprint encoding, and no authenticated organizer-origin data.

### Concurrent-main reconciliation

- Preserved the separately merged S23 research artifact and frozen receipts,
  independently reproduced its 99.895% duplicate-stop, and flagged the B06/B18
  semantic conflict and interior missing-data imputation. No S23 rerun occurred
  in this review. The original S23 and START HERE source/page bytes are
  archived; unsafe historical entry commands now fail closed or route to the
  current review. The concurrent nine-site diagnostic used Chebyshev distance;
  its source is archived and corrected to match the shared Euclidean gate.
