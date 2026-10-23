# Session preflight — 2026-10-23

Branch: `arena/5b08c5d7-gemsdoe91`; starting git SHA:
`9061410850c3dcbd6b100e954a6673fa55dbde26`.
Selected axis: **PRUNE**. Built variants: **0**. No submission or competition-page access.

## Verified locally

- Restored only manifest-pinned files using anonymous GitHub API requests; no credentials read.
- All 15 inputs match their SHA-256 and byte lengths. The rebuilt catalogue mask matches its pin (16/16 entries).
- `scripts/verify_parent_r0.py`: independent recompute, byte-exact rebuild of both twins; 37,654 dots; footprint 5,167,373 pixels.
- NaN twin: `baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd`.
- Zero twin: `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`.
- These are local validation results, **not RECEIPT** evidence. R0 0.2778 remains CLAIM.

## Why no new raster

`ledger/submissions.csv` already contains PRUNE `p1px`, `p3px`, and `3`;
R0 itself is the requested <=2 px baseline. No unused value remains within the
brief's explicit PRUNE menu (<=1, <=2, <=3 px). Renaming the same setting does
not make a new experiment. Existing wider-collar and delete-only rows are not
permission to expand that menu or repeat a build.

Other axes cannot resolve the literal >=3 px hard constraint while changing
ONLY that axis: R0 has 2,171 inherited dots at 2 < catalogue distance <=3 px.
IR-91-27's inherited-dot exemption is a prior repository decision, not an
explicit exception in this brief. Do not silently apply it. No alternative axis
was built to bypass the selected session axis.

No predicted live change is issued: there is no new candidate. Existing MODEL
predictions and unreceipted ledger entries are not promoted to scores. TOP_PUBLIC,
rolling slot availability, and the official deadline remain UNVERIFIED. Existing
public competition-data exposure remains flagged (IR-91-09 / IR-91-25); no raster
is added to Git. No external licensed layer was used in an experiment.

## Human information required

Supply copied submission receipts (including R0), dated TOP_PUBLIC, submission
timestamps for the preceding rolling seven days, and a manually checked official
deadline. Before further builds, explicitly authorize either an unused PRUNE
radius outside the stated menu or an inherited-collar exception for non-PRUNE
axes. These are alternatives, not requests to select this session's axis.

## Self-check

Full pytest run: 157 passed, 1 failed. Existing integration test
`test_every_release_passes_every_gate` requires at least one local release;
none was built under this stop decision. Do not fabricate a release or weaken
the test to get green CI. No new raster exists to run the release validator on.
Manifest and parent validators both pass; written documentation re-read.
