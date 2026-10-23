# SUBMIT — fixed-count PRUNE / H19-cover (2026-10-23)

**The agent never submits.** One registered entity, at most three scored files per rolling
week, one file per slot. The NaN-outside `.tif` is primary; its `-zeros.tif` twin is only a
fallback. Never upload both encodings of one variant. R0's 0.2778 remains **CLAIM**.

## Rebuild and verify before every upload

```bash
python3 scripts/restore_data.py
python3 scripts/build_prune_refill.py --build
python3 scripts/validate.py releases/<file>.tif
# Independent validator, NaN primary only:
python3 scripts/validate_release.py releases/<file>.tif --axis PRUNE
```

The build first reproduces both R0 TIFFs byte for byte. It then verifies every used input's
SHA-256, rebuilds all three variants, re-reads both encodings, and refuses registration on a
format, count, collar, canary, or duplicate-hash failure. `releases/PRUNE_REFILL_MANIFEST.json`
is the byte contract. Rasters are gitignored and are not public release attachments.

## Slot 1 — smallest dose

- **File / submission name:** `releases/h33-h33-2-b2-PRUNEp2p5h19cover-20261023-e6f2000d.tif`
- **NaN SHA-256:** `e6f2000dae956483cb1bfe48b2e975556c8305fb114ee953c873b815fb91425b` (355,531 B)
- **Zeros fallback:** same stem with `-zeros.tif`; SHA-256
  `2a9358331ebfdff2ae0c6a96dd2ea246da97e8e5c47f50f5c347b580bd18fa5a` (219,135 B)
- **Dots / minimum catalogue distance:** 37,654 / 2.828427 px
- **Form note (106 characters):**

```text
R0 h33-2-b2; PRUNE<=2.5px: relocate 941 dots (2.50%) to exact-gain H19-5 cells, N=37654; pred +0.002 MODEL
```

## Slot 2 — use if slot 1 is non-negative

- **File / submission name:** `releases/h33-h33-2-b2-PRUNEp2p9h19cover-20261023-9829bb66.tif`
- **NaN SHA-256:** `9829bb66c1958a779d361998908bd7482b136a8e38cf0f8cd7091a768864bab5` (354,947 B)
- **Zeros fallback:** same stem with `-zeros.tif`; SHA-256
  `125c036e1e64d1f99c2fc8016862d69d43e80f151f640d6994e09cae82cd7bc1` (218,666 B)
- **Dots / minimum catalogue distance:** 37,654 / 3.0 px
- **Form note (107 characters):**

```text
R0 h33-2-b2; PRUNE<=2.9px: relocate 1611 dots (4.28%) to exact-gain H19-5 cells, N=37654; pred +0.004 MODEL
```

## Slot 3 — conditional upper falsifier, predicted to lose

Do **not** spend this automatically. Use only under the receipt rule in `SLOT_PLAN.md`.

- **File / submission name:** `releases/h33-h33-2-b2-PRUNEp4p5h19cover-20261023-691438f8.tif`
- **NaN SHA-256:** `691438f85f2cf907c9cba0db12440e3d1591f9717138851d2e41b05095644dd5` (352,689 B)
- **Zeros fallback:** same stem with `-zeros.tif`; SHA-256
  `d182055228e4a966bd582fe2750252fe90d57742e84d172070280ecf62d93566` (216,584 B)
- **Dots / minimum catalogue distance:** 37,654 / 5.0 px
- **Form note (108 characters):**

```text
R0 h33-2-b2; PRUNE<=4.5px: relocate 4848 dots (12.88%) to exact-gain H19-5 cells, N=37654; pred -0.015 MODEL
```

## Local format receipt — paste into the session record

```text
candidate: __________________________________________
encoding: NaN-outside | zeros-outside (one only)
sha256: _____________________________________________
bytes: ______
scripts/validate.py: PASS
scripts/validate_release.py (NaN primary): VERDICT: CERTIFIED
re-read from disk: PASS
CRS/shape/transform/dtype/band-count: PASS
values in [0,1], no NaN inside, NaN outside (primary): PASS
zero catalogue mass / PRUNE collar / hash unseen: PASS
n_dots: 37654     min_dist_catalogue_px: ______
```

## After the human's submission-page receipt arrives

1. Copy `receipt_score` and ISO `receipt_date` into `ledger/submissions.csv`; set `status` to
   `SUBMITTED`. Never put a live result in `predicted_change`.
2. Record `RECEIPT`, not CLAIM. A change under 0.01 is **no evidence** on public chunks.
3. Follow the conditional rules in `SLOT_PLAN.md`; do not infer a dose-response from flat results.
