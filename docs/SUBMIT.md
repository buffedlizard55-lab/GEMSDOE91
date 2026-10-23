# SUBMIT — what the human does with a built file

The agent never submits. You upload from your own registered account, one file per
slot, and the receipt number you copy back is what turns a CLAIM into a RECEIPT.

## Before any slot is spent

```bash
python scripts/verify_manifest.py          # must print ALL OK
python -m pytest tests/ -q                 # must be green
python scripts/ledger.py state             # slots used this week; warns on missing hashes
```

If `verify_manifest.py` does not print ALL OK, nothing else in this file applies:
R0's sha256 has not been matched and no variant may be built (brief §5).

## Build and gate

```bash
python scripts/build.py --axis PRUNE --value 3 --id R0-PRUNE3-20261023-<sha8> \
    --rank data/features/rank.tif
```

`build.py` writes two files into `releases/` and runs every MUST gate on the first:

| file | use |
|---|---|
| `releases/<id>.tif` | **upload this one.** float32, EPSG:32611, 100 m, one band, values 0/1, NaN outside footprint |
| `releases/<id>-zeros.tif` | fallback only if the uploader rejects NaN. Fails the "NaN outside" gate *by design* (`--allow-zeros-outside` reports it as INFO). Note the parent session's own manifest marked its **zeros** twin `role: PRIMARY, portal_legal: true`, so zeros is a proven-acceptable upload; the ledger also records that twins score identically. One file per slot either way |

Never upload both for one slot — they are twins, not variants, and the ledger records
previous twins as wasted slots.

## The four fields

| field | value |
|---|---|
| file | `releases/<id>.tif` |
| name | `<parent>-<axis><value>-<yyyymmdd>-<sha8>`, e.g. `R0-PRUNE3-20261023-1a2b3c4d` |
| note (≤140 chars) | parent; change; predicted change. Example: `parent R0 (37654 dots, >=2px catalogue). PRUNE <=3px, refill to 37654 from parent rank. Predicted +0.005..+0.015, could be negative if new faults sit beside known traces.` |
| format receipt | paste the gate table from `build.py` output, plus `sha256` |

### Ready-made fields for this session's three files

| file | id | note (≤140 chars, verified) |
|---|---|---|
| `releases/R0-PRUNE3-…tif` | `R0-PRUNE3-20261023` | Parent R0 (37654 dots, >=2.2px catalogue). PRUNE <=3px: delete 2171 dots (5.8%), no refill. Predicted +0.002 (-0.002..+0.006). |
| `releases/R0-PRUNE8-…tif` | `R0-PRUNE8-20261023` | Parent R0. PRUNE <=8px: delete 9164 dots (24.3%), no refill; 3-8px shell has zero catalogue credit. Predicted +0.006 (-0.004..+0.014). |
| `releases/R0-PRUNE15-…tif` | `R0-PRUNE15-20261023` | Parent R0. PRUNE <=15px: delete 15665 dots (41.6%), no refill; largest dose. Predicted +0.010 (-0.008..+0.024). |

## After the score comes back

Append to `ledger/submissions.csv`, in this order of importance:

1. `receipt_score` — the number from the submission page, not a memory of it
2. `receipt_date` — ISO date, used for weekly slot accounting
3. `status` — `SUBMITTED`
4. `notes` — if the change was under 0.01, write "no evidence" (public chunks only)

Then update the CURRENT STATE block in `README.md`: best receipt, slots left, next
three slots. Do not edit any other block of the README.

## Interpreting a result

| observed | read it as |
|---|---|
| change ≥ +0.01 with a receipt | evidence for the axis; combine it with the runner-up next week |
| change between −0.01 and +0.01 | **no evidence** — public chunks only; do not promote it |
| change ≤ −0.01 | the mechanism's predicted sign was wrong; record the falsifier outcome in `SLOT_PLAN.md` |
| identical score to a previous file | check `ledger.py check`; you likely reused a slot on a twin |
