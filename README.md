# GEMSDOE91 — SPACING axis on R0

One entity, one lineage. This repository builds and validates candidate rasters
for the GEMS prize (DrivenData #306). **It never submits.** The human uploads
from their own registered account.

<!-- CURRENT STATE -->
## CURRENT STATE

| field | value |
|---|---|
| **Parent** | `R0 = h33-h33-2-b2-20261004T220000Z-e5eb6e7e` (GEMSDOE32), 37,654 unit dots |
| **Parent hash** | sha256 `c55bafc4…` (zeros) / `baeae321…` (NaN twin); dot-set digest `905cee9d…`, which matches the digest GEMSDOE86 recorded independently |
| **Parent rebuild** | **verified**: `d2.8` (44,090) − dots within 2.0 px of the catalogue = 37,654, **0 differing cells**; same result from `solo-d2.8` (40,199). File bytes are *not* re-encodable here (IR-91-04) |
| **Best receipt** | **NONE.** No row in any ledger has a submission-page receipt. R0's **0.2778 is a CLAIM** |
| **TOP_PUBLIC** | **not supplied by the human** (needed from the leaderboard, with a date) |
| **Slots left this week** | **not supplied** (3 per rolling week per entity; confirm on the competition page) |
| **Axis this session** | **SPACING** — the only axis in brief §1 with zero prior builds |
| **Built this session** | `SPACINGspread40`, `SPACINGclump40`, `SPACINGjitter40` (39.8–40.0 % of dots relocated, count fixed) |
| **Deadline** | 2026-12-03, **UNVERIFIED** (user-supplied in the brief; confirm on the page) |

**Next three slots (details and decision rules in `SLOT_PLAN.md`):**

1. `SPACINGspread40` — upload the `-zeros` twin. Closes the last unbuilt axis;
   predicted **+0.004 MODEL** [−0.004, +0.012], and bounded above by construction
   (see the ceiling instrument below).
2. `PRUNE-le3p000` (already built by GEMSDOE86) — the only axis with a measured
   live dose-response behind it (0.2708 → 0.2778 for 2,545 collar dots).
   Re-validate its format before upload; predicted **+0.004 MODEL**.
3. `RELIEF-frontp15` (already built by GEMSDOE86) — the only built variant that
   moves mass rather than deleting it. Predicted **+0.006 MODEL**.

> **A live change under ±0.01 is not evidence** (brief §5). Every prediction in
> this ledger sits inside that band, so the three slots above are as much about
> *which mechanism survives* as about the score.
<!-- /CURRENT STATE -->

## What this session established

* The parent's **dot set** is reproducible from two independent pinned ancestors
  (0 differing cells). Its **file bytes** are not reproducible with this
  sandbox's encoder — recorded, not worked around (IR-91-04).
* `sample_submission.tif` is **not a blank template**: its positive cells *are*
  the mapped catalogue. Any check that uses its values is checking the
  catalogue (IR-91-01).
* `labels.tif` is byte-identical to `existing_faults.tif`, so it is the
  catalogue, not new-fault truth (IR-91-02). Consequence: **no local instrument
  can adjudicate this axis**; the catalogue hide-and-recover proxy sees only the
  2–3 px collar and its sign on these arms is collar drift, not spacing.
* The ceiling on any spacing edit at matched count is small: under a uniform
  truth prior, moving 40 % of dots 2.1–2.2 px changes expected kernel credit by
  −0.2 % (spread) to −2.4 % (clump). Even the *most favourable* reading caps the
  live effect near 0.003.

## Repository map

| path | what |
|---|---|
| `registry/data_manifest.json` | every input, pinned to an immutable commit + sha256 |
| `scripts/restore_data.py` | fetch and verify the pins (`data/` is gitignored) |
| `scripts/build_spacing.py` | the whole build: lineage proof → 3 arms → gates → ledger → evidence |
| `scripts/validate.py` | re-run the format gates on any release file |
| `src/gems91/` | io, geometry, the ring edit, gates, report-only instruments |
| `ledger/submissions.csv` | this session's variants (human fills `receipt_score`, `receipt_date`) |
| `ledger/prior_fleet.csv` | imported prior-session record, **0 receipts**, provenance in `ledger/README.md` |
| `ledger/variant-cards.md` | mechanism cards, written for a structural geologist |
| `releases/` | `<id>.tif` (NaN outside footprint) and `<id>-zeros.tif` (fallback) |

## Reproduce

```bash
python3 -m pip install -r requirements.txt
python3 scripts/restore_data.py          # fetch + verify pinned inputs (~3 s, 5 MB)
python3 scripts/build_spacing.py --build # rebuild the parent proof and all three arms
python3 -m pytest -q
```

Evidence classes used here: **RECEIPT** (none exist) | **CLAIM** (owner-reported)
| **PROXY** (local, report-only) | **MODEL** (projection). No PROXY or MODEL in
this repository is ever called a score.
