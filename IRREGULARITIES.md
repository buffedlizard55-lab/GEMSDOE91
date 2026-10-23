# IRREGULARITIES — decision-changing items only

## 2026-10-23 — Existing active sibling PR contained PRUNE values initially selected here

- **Observed:** This repository began without a manifest, ledger, pinned inputs, or R0. After exact R0 reconstruction, initial local builds at `(R0, PRUNE, p3p2)` and `(R0, PRUNE, p3p7)` were made before the full active-PR audit. A later check of the sibling `GEMSDOE88` active PR #29 found those exact pairs already built there: p3.2, p3.7, and p4.3. Initial p3.5 also produced an exact raster-hash duplicate of p3.2. The active PR is https://github.com/buffedlizard55-lab/GEMSDOE88/pull/29 .
- **Decision impact:** Deleted the uncommitted p3.2/p3.7 TIFFs, fallbacks, ZIPs, receipts, and ledger rows; did not claim them as experiments or candidates. The p3.5 hash-colliding output was also discarded. Retained only the unique `p2p6` PRUNE variant. Future experiments must check active PR branches, not only merged/main ledgers, before construction.

## 2026-10-23 — Competition data mirrors are public; use/redistribution terms remain unchecked

- **Observed:** The pinned manifest sources include owner-mirrored competition template, catalogue and feature rasters from public sibling GitHub repositories. Their DrivenData redistribution terms could not be verified without prohibited automated access. DrivenData Terms of Use: https://www.drivendata.org/termsofuse/ . The manifest marks this `FLAGGED_DATA_USE_UNCHECKED` and records each source URL/hash.
- **Decision impact:** All input rasters and generated submission rasters remain gitignored under local `data/` and `releases/`; none is committed to this public repository or released on GitHub. The human owner must resolve data-use terms before further publication. No permission is inferred.

## 2026-10-23 — R0 claim, deadline, public target and slot budget are not receipt-verified

- **Observed:** R0 `0.2778` is still `CLAIM`; no submission-page receipt was supplied. `TOP_PUBLIC`, receipt-backed incumbent, weekly slots left, total slots, and competition deadline confirmation were blank/unknown. The brief states 2026-12-03, but the agent did not access the competition page.
- **Decision impact:** No scored submission was made or recommended as unconditional. The human must supply a receipt and current values; confirm timing/quota at https://www.drivendata.org/competitions/306/competition-doe-gems/ before spending any slot. The rules document is https://docs.nlr.gov/docs/fy26osti/96647.pdf .

## 2026-10-23 — Main advanced concurrently; merge conflict and local ledger scope need human reconciliation

- **Observed:** While this branch was being built, `origin/main` advanced from the original base to a 26-row experiment ledger, including `PRUNE` values `3`, `p1px`, `p3px`, `p4px`, `le3-norefill`, `le8-norefill`, and `le15-norefill`; `p2p6` is absent from that latest ledger. Main's latest changes are represented by merged PR #6: https://github.com/buffedlizard55-lab/GEMSDOE91/pull/6 . This branch's PR #7 currently has passing CI but GitHub reports `CONFLICTING`/`DIRTY` because both sides added/changed README, manifest, ledger, and policy docs.
- **Decision impact:** Do not merge PR #7. Leave it open per the brief (CI is green, but conflicts remain); the human should reconcile the complete main ledger with this one `p2p6` row before any future session or slot use. The local ledger deliberately contains only this session's row and is not a replacement for main's 26 historical rows.

## 2026-10-23 — R0 is 2–3 px from catalogue at some dots; PRUNE is the explicit exception

- **Observed:** The byte-exact R0 has 2,171 dots at distances `2 < d_cat <= 3 px`; the candidate uses `AXIS=PRUNE`, changes 941 parent dots (2.50%), holds count fixed, and has minimum catalogue distance 2.8284 px. It has zero mass on catalogue pixels. The user's hard constraint requires >=3 px for non-PRUNE axes and explicitly exempts PRUNE.
- **Decision impact:** Candidate is recorded as a PRUNE treatment and is not presented as a non-PRUNE gate-compliant file. It tests the 2.6 px collar only; no use of the PROXY result as a gate.
