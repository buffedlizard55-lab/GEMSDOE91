# SUBMIT — combined PRUNE queue (2026-10-23)

**Status 2026-10-23 (session 5): three MASS files are built, CERTIFIED and hash-recorded.**
Nothing here submits anything; the human uploads from their own account, one file per slot,
and copies the receipt number back into `ledger/submissions.csv` → `receipt_score` +
`receipt_date`. `releases/*.tif` are gitignored; `releases/MANIFEST.json` is the hash contract.

## Rebuild (≈3 min, eight pinned inputs, every sha256 verified)

```bash
python3 scripts/restore_data.py          # fetch + verify every pinned sha256
python3 scripts/build_mass.py --build    # rebuilds R0 proof + the three MASS arms
python3 scripts/validate_release.py releases/<file>.tif    # must print CERTIFIED
```

The build refuses to run if any input is unpinned, refuses to write if R0 does not come
back exactly from both ancestors, and refuses to record a file that fails a gate.

## The three slot candidates, in plan order

| slot | file | sha256 (check against `releases/MANIFEST.json`) | dots |
|---|---|---|---:|
| 2 | `…-MASSsup10plus-20261023-e23e5141.tif` | `e23e5141…` | 39,023 |
| 3 | *(rebuild)* `R0 & (d_cat > 3)` — see IR-91-18 | 35,483 dots; new hash ≠ `1209e863…` | 35,483 |
| — | `…-MASSsup10minus-20261023-7e7084af.tif` (do not spend a slot) | `7e7084af…` | 31,854 |
| — | `…-MASSsup24minus-20261023-e086e259.tif` (do not spend a slot) | `e086e259…` | 26,672 |

**Slot 1 of the plan is R0 itself**, uploaded unchanged, purely to obtain the receipt that
this lineage has never had. Nothing needs to be built for it.

**Form note** (≤ 140 chars, no score claimed) for `sup10plus`:

```
R0 h33-2-b2 + common 3px collar; add 3540 highest field-rank cells, count 39023; pred -0.002 MODEL
```

## Do not spend a slot on the PRUNE ladder

The PRUNE-extension session's rungs (`le4` `360fe57e`, `le5` `5b6d3987`, `le10` `04002dae`)
are built and CERTIFIED, but measured with the calibrated instrument they are predicted losses
(−0.009 / −0.020 / −0.048). Its slot-1 recommendation (`le10`) is the worst of the six doses
measured. See `SLOT_PLAN.md` and IR-91-19.

## Which encoding

Upload the `.tif` (NaN outside the footprint — spec-literal). Keep the `-zeros.tif` twin as
the rules-allowed fallback, but note: **`validate_release.py` fails the zeros twin on
`nan_outside_footprint` by design** (it passes 13/13 in `gems91.release_gates` with
`zeros_outside_footprint` substituted). No receipt in this lineage has ever confirmed that
the two encodings score identically.

## Format receipt — copy into the PR/session notes

```
candidate: h33-h33-2-b2-20261004-e5eb6e7e-MASSsup10plus-20261023-e23e5141
sha256:    __________________________________________
bytes:     ______
verdict:   CERTIFIED (scripts/validate_release.py, 2026-10-23) — 14/14 gates
```

---

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
