# GEMSDOE91 — DrivenData GEMS #306 (three sessions, 2026-10-23)

## CURRENT STATE

**One entity. Nothing here submits**; the human uploads from their own account.

| field | value |
|---|---|
| **Parent** | `R0 = h33-h33-2-b2` (GEMSDOE32), 37,654 unit dots, EPSG:32611, 3730×3292, 100 m, float32, footprint 5,167,373 px |
| **Parent hash** | sha256 `c55bafc4…` (zeros) / `baeae321…` (NaN twin), **verified against the pin**; dot-set digest `905cee9d…` |
| **Parent rebuild** | **dot set reproduced exactly** from two independent pinned ancestors (`d2.8` 44,090 and `solo-d2.8` 40,199) by dropping every dot within 2.0 px of the catalogue → 37,654, **0 differing cells**. File *bytes* are not re-encodable here (IR-91-12) |
| **Best receipt** | **NONE** — 23/23 ledger rows have empty receipt columns. `0.2778` for R0 is a **CLAIM** |
| **TOP_PUBLIC** | **____ (human, with date)** — upstream GEMSDOE88 carries `0.4413` as a human-supplied 2026-10-22 figure (**CLAIM**), not verified here |
| **Slots left this week** | **__ / __ (human)** |
| **Variants built** | **3 this session** (SPACING, below); sessions 1–2 built 0 |
| **Build status** | **UNBLOCKED.** Sessions 1–2 concluded the build was blocked because the competition rasters were "not public" (IR-91-02). They are reachable: `scripts/restore_data.py` pulls all six from immutable GitHub commits and verifies every sha256 in **3 s / 5 MB**. See IR-91-11 |
| **Deadline** | 2026-12-03, **UNVERIFIED** (brief-supplied; confirm on the page) |

### Session 3 delta (`arena/a5e7bf22`, SPACING)

AXIS chosen here: **SPACING** — the only axis in brief §1 with **zero prior builds**
(checked across five fleet ledgers: 132 + 129 + 22 + 20 + 5 rows, no `axis=SPACING`).

Three arms, **matched on everything except the treatment**: the same 40 % of dots
(densest 1 km blocks), the same displacement budget (radius-2 ring, 2.0–2.236 px),
the same constraints (footprint, parent's 2 px collar floor, no cell reuse, ≥ 2 px
separation). Only *which* ring cell is chosen differs, ranked by a Gaussian-smoothed
dot-density potential (σ = 2 px).

| arm | relocated | mean disp. | density at target | predicted (MODEL) |
|---|---:|---:|---|---|
| `SPACINGspread40` | 15,056 (39.99 %) | 2.23 px | 0.066 → **0.035** | **+0.0042** [−0.004, +0.012] |
| `SPACINGclump40` | 14,973 (39.76 %) | 2.13 px | 0.066 → 0.058 | **−0.0023** [−0.010, +0.006] |
| `SPACINGjitter40` | 15,038 (39.94 %) | 2.15 px | 0.066 → 0.047 | **0.000** (null) [−0.008, +0.008] |

**The bound is the finding.** Under a uniform truth prior the edit moves expected
kernel credit by −0.17 % (spread) to −2.4 % (clump), capping the plausible live
effect near **0.003**. A live change ≥ 0.01 on this axis would be evidence of
something other than the spacing edit.

All six files pass every hard gate and are re-read from disk; **no raster is
committed** — `releases/MANIFEST.json` carries the sha256 of each, and one command
rebuilds them byte-identically (CI proves it).

#### Session 1–2 delta (unchanged, preserved)

Sessions 1 and 2 built the harness and **0 variants**: `src/gems91/metric.py` (DTI
re-derivation), `src/gems91/gates.py` (UNVERIFIED-never-PASS gates), `tools/run_concentration.py`
(the first count-preserving builder), a synthetic end-to-end fixture, and a fix for a
real transposed-distance bug (IR-91-06). Session 2 also found that the three imported
CONCENTRATION rows ranked blocks by *parent dot density* (IR-91-07) — they test
clustering, not prior transfer.

### Next three slots (details in `SLOT_PLAN.md`)

1. `PRUNE-le3p000` (already built by GEMSDOE86) — the only axis with a **measured live
   dose-response** behind it (0.2708 → 0.2778 for 2,545 collar dots). MODEL **+0.004**.
2. `SPACINGspread40` (this session) — closes the last unbuilt axis; if it is flat,
   geometry stops consuming slots. MODEL **+0.004**.
3. `RELIEF-frontp15` (already built by GEMSDOE86) — the only built variant that moves
   mass rather than deleting it. MODEL **+0.006**.

> A live change under ±0.01 is **not evidence**. Every prediction in this ledger sits
> inside that band: the three slots are about which mechanism survives, not about a
> score. The ledger's action 0 is to get a receipt.

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
