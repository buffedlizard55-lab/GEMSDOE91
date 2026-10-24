# GEMSDOE91 — session 2026-10-23 (DrivenData GEMS #306)

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Session 2026-10-24 (`arena/ea2646f3-gemsdoe91`): STOP at Gate 0.** All 15 pinned inputs and the derived catalogue mask are absent locally; no parent rebuild or raster validation is possible. Historical reports are not current verification. See `reports/session-20261024-ea2646f3-manifest.json`.
- **Parent:** `h33-h33-2-b2` (R0), expected 37,654 dots; expected NaN SHA-256 `baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd`. Not rebuilt this session; never approximated.
- **Best receipt:** none in ledger. R0 `0.2778` remains **CLAIM**. Local hash/format checks are not submission **RECEIPTs**.
- **TOP_PUBLIC:** unknown; human supplies value and date. **Slots left:** unknown / 3 per rolling week; total remaining unknown. Deadline `2026-12-03` is unconfirmed (40 days from this session).
- **Ledger:** 47 historical BUILT rows, seven axes, zero receipt scores; unchanged. No new variants, predictions, or submissions.
- **Chosen axis:** PRUNE, deferred until Gate 0 passes; no value reserved or repeated. This avoids treating inherited sub-3-pixel dots as an exemption to the non-PRUNE exclusion.
- **Next 3 slots:** all on HOLD; conditional order is baseline receipt reconciliation, one compliant fixed-count PRUNE comparison, then an orthogonal compliant comparison. See `SLOT_PLAN.md`. Do not upload from historical instructions without current validation.

## What this repo contains

| Path | Purpose |
|---|---|
| `registry/data_manifest.json` | 15 pinned inputs with sha256 + byte length; 3 re-hashed here |
| `registry/r0_verification.json` | Parent hash/grid/dot-count evidence (generated) |
| `registry/preflight.json` | Build-blocked verdict and exactly what is missing |
| `registry/raster_availability.json` | Which of the 20 ledger rows still have a raster |
| `registry/candidate_availability.json` | Hash + format status of the retrievable rasters |
| `src/gems91/metric.py` | DTI re-derivation + exact marginal gain |
| `src/gems91/gates.py` | The MUST gates; an unprovable gate is `UNVERIFIED`, never `PASS` |
| `scripts/` | `verify_parent_r0.py`, `preflight.py`, `validate_release.py`, `pinned.py` CLI |
| `ledger/submissions.csv` | 20 imported rows, provenance in `source`; empty receipt columns |
| `tools/` | `run_concentration.py` (builder), `pins.py`, `raster_io.py`, `stor.py`, `make_fixture.py` |
| `tests/` | 53 tests (metric algebra, gates, ledger invariants, builder, preflight) |

## Run it

```bash
pip install -r requirements.txt
python scripts/verify_parent_r0.py     # fetch pinned parent, verify sha256
python scripts/preflight.py            # BUILD ALLOWED / BUILD BLOCKED
python -m pytest                       # 53 tests, no competition data needed
python -m tools.pins --axis CONCENTRATION   # what an axis still needs, by pinned id
```

### Session 3 delta (`arena/5563ddf8`, same date)

Main had moved twice while this session ran, so this branch was **rebased onto** the merged
work rather than replacing it: the `src/gems91` package, `tools/`, `Makefile`, fixtures and
all 20 imported ledger rows are kept intact.

- **The blocking problem was solved, not worked around.** R0, `sample_submission.tif` and the
  labels raster were recovered from public mirrors and verified against hashes this repo
  already carried. No rebuild from a recipe, no approximation.
- **Parent forensics.** Differencing R0 against solo-d28 proves the lineage's PRUNE is
  delete-only (0 dots in R0 that are not in solo-d28; 2,545 removed at ≤2 px, none added).
- **Three buildable variants**, using `scripts/dti.py` + `scripts/axes.py` + `scripts/build.py`.
- **Two gate implementations now agree** on all three files. Fixing `sha_unseen` to ignore
  BUILT rows (IR-91-12) is what let them certify; before that the gate was unsatisfiable in
  the order the brief prescribes.
- **A real disagreement is recorded, not hidden:** my algebra predicts removal gains, the
  imported `p4px` row predicts −0.009. IR-91-13.
- **Honest about power:** the brief's evidence bar is ±0.01 and only `le15` has a plausible
  path past it. Doses 1 and 2 are refinements.
