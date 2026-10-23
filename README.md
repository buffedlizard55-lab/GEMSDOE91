# GEMSDOE91

Agent workspace for the GEMS Prize (DrivenData #306). One entity, one competitor;
no script here submits anything.

<!-- CURRENT STATE:BEGIN -->
## CURRENT STATE

| field | value |
|---|---|
| parent | **R0 VERIFIED** = `h33-h33-2-b2`, 37,654 dots, 0 on catalogue, min 2.236 px. sha256 `baeae321…c77dd` matches the parent repo's own manifest |
| best receipt | **none yet.** R0's live 0.2778 is a CLAIM — GEMSDOE32's `submissions_manifest.json` records `receipt: null` for it |
| TOP_PUBLIC | **unfilled by the human** (needs leaderboard value + date); no other target is valid |
| slots left this week | **unknown** — needs the submission page (`__ / 3`) |
| next 3 slots | 1. `R0-PRUNE3` (5.77 % removed) · 2. `R0-PRUNE8` (24.34 %) · 3. `R0-PRUNE15` (41.60 %) — all BUILT and gated |
| status | 3 variants built, gates PASS, awaiting upload. Session axis: **PRUNE** |
<!-- CURRENT STATE:END -->

## Layout

| path | what |
|---|---|
| `registry/data_manifest.json` | pinned inputs + sha256 — 4/5 verified against the parent repo's recorded hashes |
| `scripts/verify_manifest.py` | checks presence + hash; exit ≠ 0 blocks any build |
| `scripts/dti.py` | DTI metric and exact marginal-gain ranking (unit-tested) |
| `scripts/axes.py` | MASS / PRUNE / SNAP / CONCENTRATION operators |
| `scripts/build.py` | parent → one axis → release pair → gates → ledger row |
| `scripts/validate_raster.py` | the MUST-pass gates from brief §6 |
| `scripts/ledger.py` | collapse raw paste, dedupe on hash and (parent, axis, value) |
| `ledger/submissions.csv` | one row per variant; the human fills receipt score and date |
| `docs/MECHANISM_CARDS.md` | one card per variant, for a structural geologist |
| `reports/proxy.json` | hide-and-recover PROXY — report only, never a gate |
| `SLOT_PLAN.md` | next three slots and the weeks to 2026-12-03 |
| `IRREGULARITIES.md` | only items that change a decision |
| `AI_USE.md` | what the AI wrote, what the human decided |

## Quick start (once inputs exist)

```bash
python -m pytest tests/ -q                 # 53 tests
python scripts/verify_manifest.py          # prints 4/5 verified; ALL OK
python scripts/build.py --axis PRUNE --value 3 --id R0-PRUNE3-20261023
python scripts/validate_raster.py releases/R0-PRUNE3-20261023.tif \
    data/sample_submission.tif --catalogue data/catalogue.tif
```

The three built files are in `releases/` (gitignored: this repo is public). They are
reproducible from the pinned inputs with the commands above.

Competition rasters are gitignored on purpose: this repository is public and GitHub
Pages serves `main:/`. See `IRREGULARITIES.md` item 1.
