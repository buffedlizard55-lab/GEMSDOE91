# AI use disclosure — GEMS Prize (DrivenData #306)

## What the AI agent produced

- Selected `AXIS=PRUNE` for this session, as directed by the user not to ask for axis selection. It selected the new `p2p6` value after checking main ledgers in sibling repositories GEMSDOE84–88 and active PR descriptions relevant to PRUNE.
- Wrote the SHA-256-pinned manifest/restore helper, deterministic exact-R0 rebuild and PRUNE builder, shared local validation code, tests, ledger row, receipt/mechanism card, evidence report, and session documentation.
- Used only files declared in `registry/data_manifest.json`; verified 14/14 SHA-256 and byte-length pins before candidate construction. No LiDAR-derived raster was supplied or used.
- The predicted live change `+0.001` (range `[-0.007,+0.009]`) is an AI-generated `MODEL`, not a score. Local hide-and-recover and SGMC diagnostics are `PROXY`, not scores and not gates.
- Did not contact DrivenData or Dropbox; did not scrape a leaderboard, request credentials, or submit a file.

## Human decisions still required

- The user supplied the task/guardrails and the instruction for agent-selected axis. No axis, TOP_PUBLIC, incumbent receipt, or quota figures were supplied; agent selected PRUNE and left unknown values blank.
- The human competitor must verify the competition deadline, current public leaderboard target, remaining weekly/total slots, receipt-backed incumbent, any data-use terms for mirrored inputs, and whether this candidate should be submitted.
- No submission has been made or authorized by this AI output.

## Reproducibility

- Build: `python scripts/restore_inputs.py --verify-only && python scripts/build_prune_refine.py`.
- Independent local file check: `python scripts/validate_prune_release.py`; unit tests: `pytest -q tests/test_r0_and_dti.py` (the exact-R0 test needs restored local pins).
- Builder source commit recorded in receipt: `982434c6e7402f10828c164b0625cde58e54bc32`.
- Shared metric/validation module provenance: copied from the user's sibling repository `buffedlizard55-lab/GEMSDOE88` at commit `0796ccbd44280736ee09369d706358cfd6832f15` (https://github.com/buffedlizard55-lab/GEMSDOE88/commit/0796ccbd44280736ee09369d706358cfd6832f15). The R0 lineage recipe, manifest and previous candidate evidence are also from the user's sibling repositories, with sources recorded in the manifest.
