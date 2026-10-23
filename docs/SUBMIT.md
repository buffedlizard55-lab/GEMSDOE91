# SUBMIT — combined PRUNE queue (2026-10-23)

**The agent never submits.** One registered entity, at most three scored files per rolling
week, one file per slot. The NaN-outside `.tif` is primary; its `-zeros.tif` twin is only a
fallback. Never upload both encodings of one variant. R0's 0.2778 remains **CLAIM**.

## Rebuild and verify before every upload

```bash
python3 scripts/restore_data.py
python3 scripts/make_catalogue.py
python3 scripts/build_prune_ladder.py
python3 scripts/build_prune_refill.py --build
python3 scripts/validate.py releases/<file>.tif
# Additional independent check for fixed-count NaN primaries:
python3 scripts/validate_release.py releases/<fixed-count-file>.tif --axis PRUNE
```

The fixed-count build reproduces both R0 TIFFs byte for byte, verifies every used input's
SHA-256, re-reads both encodings, and refuses registration on a format, count, collar,
canary, or duplicate-hash failure. `releases/MANIFEST.json` covers the delete-only ladder;
`releases/PRUNE_REFILL_MANIFEST.json` covers fixed-count H19-cover. Rasters are gitignored
and are not public release attachments.

## Default slot queue

### Slot 1 — `PRUNE-le10-norefill` (`04002dae`)

- **File / submission name:**
  `releases/h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif`
- **NaN SHA-256:** `04002dae86db72c3fc47652bd66e3ec029e432c909cad779039e9e3749ae0839`
  (314,889 B)
- **Zeros fallback:** same stem with `-zeros.tif`; SHA-256
  `0842d86618dbe64acf6dfb4137feff423a9dc394b59d153317381fc22b06dbb8` (174,857 B)
- **Dots / changed:** 26,294 / 30.17%; minimum catalogue distance 10.05 px.
- **Prediction:** +0.008 MODEL [−0.006,+0.019].

```text
Parent R0 h33-h33-2-b2; PRUNE <=10px delete 11360 dots (30.17%), count 26294; pred +0.008 MODEL
```

### Slot 2 — `PRUNEp2p9h19cover` (`9829bb66`)

- **File / submission name:**
  `releases/h33-h33-2-b2-PRUNEp2p9h19cover-20261023-9829bb66.tif`
- **NaN SHA-256:** `9829bb66c1958a779d361998908bd7482b136a8e38cf0f8cd7091a768864bab5`
  (354,947 B)
- **Zeros fallback:** same stem with `-zeros.tif`; SHA-256
  `125c036e1e64d1f99c2fc8016862d69d43e80f151f640d6994e09cae82cd7bc1` (218,666 B)
- **Dots / minimum catalogue distance:** 37,654 / 3.0 px; 1,611 dots relocated (4.278430%).
- **Prediction:** +0.004 MODEL [−0.005,+0.013].

```text
R0 h33-2-b2; PRUNE<=2.9px: relocate 1611 dots (4.28%) to exact-gain H19-5 cells, N=37654; pred +0.004 MODEL
```

### Slot 3 — `PRUNE-le4-norefill` (`360fe57e`)

Use only under the receipt conditions in `SLOT_PLAN.md`; leave the slot unused after two
losses rather than spending it automatically.

- **File / submission name:**
  `releases/h33-h33-2-b2-PRUNE-le4-norefill-20261023-360fe57e.tif`
- **NaN SHA-256:** `360fe57edd8286393a180f0ae53c8259899c4344e5bc7f4c4ec20dcdf28530a7`
  (348,403 B)
- **Zeros fallback:** same stem with `-zeros.tif`; SHA-256
  `b2c4fa39c78c2f02cd17bcf932ca910369be6b7c222ec0f3e4fde6da3f001be4` (204,203 B)
- **Dots / changed:** 33,829 / 10.16%; minimum catalogue distance 4.12 px.
- **Prediction:** +0.003 MODEL [−0.003,+0.009].

```text
Parent R0 h33-h33-2-b2; PRUNE <=4px delete 3825 dots (10.16%), count 33829; pred +0.003 MODEL
```

## Other fixed-count experiments built by this branch

### Smaller-dose fallback — `PRUNEp2p5h19cover` (`e6f2000d`)

- **File:** `releases/h33-h33-2-b2-PRUNEp2p5h19cover-20261023-e6f2000d.tif`
- **NaN SHA-256:** `e6f2000dae956483cb1bfe48b2e975556c8305fb114ee953c873b815fb91425b`
  (355,531 B)
- **Zeros SHA-256:** `2a9358331ebfdff2ae0c6a96dd2ea246da97e8e5c47f50f5c347b580bd18fa5a`
  (219,135 B)
- **Dots / distance:** 37,654 / 2.828427 px; 941 relocated (2.499070%); +0.002 MODEL.

```text
R0 h33-2-b2; PRUNE<=2.5px: relocate 941 dots (2.50%) to exact-gain H19-5 cells, N=37654; pred +0.002 MODEL
```

### Conditional falsifier — `PRUNEp4p5h19cover` (`691438f8`)

**Predicted to lose; not an automatic upload.**

- **File:** `releases/h33-h33-2-b2-PRUNEp4p5h19cover-20261023-691438f8.tif`
- **NaN SHA-256:** `691438f85f2cf907c9cba0db12440e3d1591f9717138851d2e41b05095644dd5`
  (352,689 B)
- **Zeros SHA-256:** `d182055228e4a966bd582fe2750252fe90d57742e84d172070280ecf62d93566`
  (216,584 B)
- **Dots / distance:** 37,654 / 5.0 px; 4,848 relocated (12.875126%); −0.015 MODEL.

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
fixed-count NaN primary, scripts/validate_release.py: VERDICT: CERTIFIED
re-read from disk: PASS
CRS/shape/transform/dtype/band-count: PASS
values in [0,1], no NaN inside, NaN outside (primary): PASS
zero catalogue mass / PRUNE collar / hash unseen: PASS
n_dots: ______     min_dist_catalogue_px: ______
```

## After the human's submission-page receipt arrives

1. Copy `receipt_score` and ISO `receipt_date` into `ledger/submissions.csv`; set `status` to
   `SUBMITTED`. Never put a live result in `predicted_change`.
2. Record `RECEIPT`, not CLAIM. A change under 0.01 is **no evidence** on public chunks.
3. Follow `SLOT_PLAN.md`; do not infer a dose-response from flat results.
