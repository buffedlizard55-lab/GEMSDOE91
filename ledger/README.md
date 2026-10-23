# Experiment ledger

`submissions.csv` on this branch currently contains the one unique variant built in this session. Its `receipt_score` and `date` are intentionally blank because no submission-page receipt was supplied and no file was submitted. It is not yet reconciled with the 26 historical rows on the concurrently updated `origin/main`; PR #7 remains open due conflicts. See `IRREGULARITIES.md`.

At build start this checkout had no `ledger/submissions.csv` or `ledger/raw_paste.txt`. Before choosing `PRUNE,p2p6`, the agent checked main ledgers in sibling repositories GEMSDOE84–88 and active PRUNE PR descriptions in GEMSDOE84, GEMSDOE85, and GEMSDOE88. Active PR #29 in GEMSDOE88 was found to contain p3.2/p3.7/p4.3; these values were not retained. This is not a claim that every historical experiment in every sibling repository has been imported here. Check all current main/active PR records before a future build.

All competition inputs and submission TIFF/ZIP artifacts are excluded from Git. Local release receipts contain SHA-256s and validation facts; the TIFFs remain local and gitignored. Data-use terms for public sibling mirrors are unchecked; see the manifest and `IRREGULARITIES.md`.
