# SUBMIT — PRUNE queue + MASS/consensus arms (2026-10-23)

**The agent never submits.** One registered entity, at most three scored files per rolling
week, one file per slot. The NaN-outside `.tif` is primary; its `-zeros.tif` twin is only a
fallback. Never upload both encodings of one variant. R0's 0.2778 remains **CLAIM**.

## SESSION 4 — MASS/consensus: the three files to upload (one per slot)

```bash
python3 scripts/restore_data.py                 # fetch + verify every pinned sha256
python3 scripts/make_catalogue.py               # rebuild the mask; must hash to c97c7819…
python3 scripts/build_mass_consensus.py         # writes the 3 pairs under releases/, ~20 s
python3 scripts/validate_raster.py releases/<file>.tif data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif \
    --parent data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
python3 scripts/validate_release.py releases/<file>.tif --axis MASS
```

Rebuilds are deterministic (no RNG anywhere) and were verified to reproduce the hashes below.

| slot | file | sha256 (NaN-outside) | zeros twin | bytes (NaN) |
|---|---|---|---|---|
| **1** | `h33-h33-2-b2-MASScons3add-20261023-2803126d.tif` | `2803126de23b7f3388d2d4db727c2e8a39b499308b6efc61941d4231606f9abd` | `597d6d0e…` | 384,079 |
| **2** | `h33-h33-2-b2-MASScons1drop-20261023-fc8f5500.tif` | `fc8f5500790eed45fe4957a3a548c55513db09774ecd46c300b67b4cc72d854e` | `9f24d22e…` | 354,433 |
| 3 (only if 1–2 flat) | `h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f.tif` | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` (rebuild first) | — | — |
| keep | `h33-h33-2-b2-MASScons2drop-20261023-e8871e7f.tif` | `e8871e7f7bd75b139173e2c93eda3a79f47063e6e71dd4dfef7672cf58c4662f` | — | 328,675 |

**Form notes** (≤140 chars each, no score claimed, counted):

```
1: h33-2-b2; +3765 dots (10.0%) at 3-of-3 cross-field support cells, >=3px off catalogue; pred +0.009 MODEL
2: h33-2-b2; -4541 single-support dots (12.1%), count 33113, whole stratum; pred -0.000 MODEL
3: h33-2-b2; delete-only <=15px collar, 21989 dots, no refill; pred +0.010 MODEL
```

**Format receipt — paste this back with the score:**

```
candidate: h33-h33-2-b2-MASScons3add-20261023-2803126d
sha256 (NaN)    : 2803126de23b7f3388d2d4db727c2e8a39b499308b6efc61941d4231606f9abd
sha256 (zeros)  : 597d6d0ea528c8630e301dfe354b62905534d49f985f5bd92f04a75e51d7e5cf
n_dots          : 41419        min_dist_catalogue_px: 2.236  (inherited from R0, IR-91-03)
validate_raster.py  : 14/14 PASS (§6 MUST gates)
validate_release.py : 14 MUST gates PASS; collar_ge_3px FAIL = inherited, R0 fails it identically (2171 dots, IR-91-03)
CRS EPSG:32611 | 3730x3292 | 100 m | float32 | 1 band | values {0,1} | NaN outside
zero catalogue mass: 0 px        ledger sha: new at build time
```

**Known wrinkle, stated up front:** all three arms inherit R0's 2,171 dots at 2–3 px from the
catalogue, so the brief's "≥3 px unless PRUNE" is violated by the parent itself, not by the edit
(IR-91-03). The new mass in slot 1 is ≥3 px by construction. If the human prefers a compliant
parent, rebase on `PRUNEle3norefill` (35,483 dots) instead — but then the file is a two-change
build and must not be described as a MASS-only arm.

---
 (`releases/`, rebuilt on demand —
`releases/*.tif` are gitignored, the sha256 contract is `releases/MANIFEST.json`).
**Nothing has ever been submitted by an agent, and no agent may submit.** One file per slot;
the `-zeros` twin is the fallback, not an extra entry.

## Rebuild first (10–40 s, five inputs, all hash-verified)

```bash
python3 scripts/restore_data.py           # fetch + verify every pinned sha256
python3 scripts/build_spacing.py --build  # rebuild the parent proof and all three arms
python3 scripts/validate.py releases/<file>.tif   # must print PASS
```

The build refuses to proceed unless R0's dot set is reproduced exactly from both pinned
ancestors, and refuses to write the ledger unless every release passes every hard gate.

## Session-3 files

| slot rank | file to upload | sha256 (must match `releases/MANIFEST.json`) | bytes |
|---|---|---|---:|
| 2 | `…-SPACINGspread40-20261023-6d389309-zeros.tif` | `5c517369be3c807c…` | 226,284 |
| — | `…-SPACINGspread40-20261023-6d389309.tif` (NaN-outside primary) | `6d389309aafaa79d…` | 373,103 |
| — | `…-SPACINGclump40-20261023-536d32ad-zeros.tif` (control) | `d393c94f38601567…` | 224,741 |
| — | `…-SPACINGjitter40-20261023-39bb7288-zeros.tif` (null) | `ad6dfa26043f7f19…` | 225,691 |

**Form note** (≤ 140 chars, no score claimed):

```
Parent R0 h33-2-b2; move 15,056 dots (39.99%) 2.0-2.24 px to emptier ground, count fixed 37,654; pred +0.004 MODEL
```

## Slot 1 — rebuild R1, then submit it

```bash
python src/gems91/pinned.py check                 # 15/15 pins OK
python scripts/preflight.py                       # BUILD ALLOWED
python scripts/validate_release.py releases/<id>.tif --axis PRUNE
```

- **File:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.tif`
- **sha256 must equal** `6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9`
  (zeros twin `dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f`).
  If the rebuild does not reproduce that hash, it is a **different file** — log it in
  `IRREGULARITIES.md` and do not call it R1.
- **Form note (103 chars, ≤140):**
  `h33-2-b2; PRUNE <=3px held at 37654 (-2171 in 2-3px, +2171 exact marginal gain >3px); pred +0.005 MODEL`
- **Which encoding:** upload the `.tif` (NaN outside footprint, spec-literal). Keep
  `-zeros.tif` as the fallback the rules allow. Note the open risk: **no receipt in this
  lineage has ever confirmed the all-finite `-zeros` encoding is accepted**, so do not
  assume the twins score identically on the organiser's reader — the ledger's line
  "NaN-outside and zeros-outside twins score identically" was never receipt-backed.

## Format receipt — copy this into the PR/session notes

```
candidate: h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705
sha256:    __________________________________________
bytes:     ______
validate_release.py: VERDICT = CERTIFIED      (paste the block; UNVERIFIED is not a pass)
gates: crs/shape/transform/dtype/band_count/values_in_0_1/no_nan_inside/nan_outside/
       zero_catalogue_mass/collar_ge_3px/sha_unseen=UNSEEN(passed)/reread_from_disk
n_dots:    37654      min_dist_catalogue_px: ______
```

## Then, the same day

1. Paste `receipt_score` and `receipt_date` into `ledger/submissions.csv` (never into
   `predicted_change`).
2. If the score moves ≥ +0.01, R1 becomes the parent for every later slot. If it moves
   ≤ −0.01, the 2–3 px shell carries truth and the ≥3 px gate is wrong for this dataset.
3. If |Δ| < 0.01, record it as **no evidence** and proceed on R1 anyway — it is the only
   compliant base.

## Do not

- Do not upload the three MASS variants as progress on MASS: `MASSm10plus` is MODEL −0.010
  and `MASSm20minus` is a nested cut of `MASSm10minus`; both are HOLD upstream, and all
  three inherit R0's 2–3 px collar.
- Do not upload a file whose hash is already in `ledger/submissions.csv` (8+ upstream slots
  were spent on exact repeats), or whose `validate_release.py` verdict is not `CERTIFIED`.
- Do not submit from any account but the one entity's. One final file, chosen blind.


---

## Session 3 — this session's three files, ready to paste

All three are built, gate-clean, and certified by both validators. Upload **one per slot**.

```bash
# re-verify any of them before uploading
python scripts/verify_manifest.py                       # expect PRUNE: READY
python scripts/validate_raster.py releases/R0-PRUNE3-20261023.tif \
    data/official/sample_submission.tif \
    --catalogue data/derived/catalogue_mask.tif --parent \
    data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
python scripts/validate_release.py releases/R0-PRUNE3-20261023.tif \
    --sample data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif --ledger ledger/submissions.csv
```

| # | file | name | note (≤140 chars, counted) |
|---|---|---|---|
| 1 | `releases/R0-PRUNE3-20261023.tif` | `R0-PRUNE3-20261023` | Parent R0 (37654 dots, >=2.2px catalogue). PRUNE <=3px: delete 2171 dots (5.8%), no refill. Predicted +0.002 (-0.002..+0.006). |
| 2 | `releases/R0-PRUNE8-20261023.tif` | `R0-PRUNE8-20261023` | Parent R0. PRUNE <=8px: delete 9164 dots (24.3%), no refill; 3-8px shell has zero catalogue credit. Predicted +0.006 (-0.004..+0.014). |
| 3 | `releases/R0-PRUNE15-20261023.tif` | `R0-PRUNE15-20261023` | Parent R0. PRUNE <=15px: delete 15665 dots (41.6%), no refill; largest dose. Predicted +0.010 (-0.008..+0.024). |

Fallback twins end in `-zeros.tif`; use one encoding per slot, never both.
The parent session's own manifest marked its **zeros** twin `PRIMARY, portal_legal: true`,
so zeros is a proven-acceptable encoding if the uploader objects to NaN.

### Field values

| field | value |
|---|---|
| format receipt | paste the `VERDICT: CERTIFIED` JSON from `validate_release.py` plus the sha256 |
| sha256 (slot 1) | `1209e863a9ff58d86681e9e7f0375c4d185a59c50ef9769f02653ec1472198f2` |
| sha256 (slot 2) | `e1dd69d02b90f95e779c43de1843ac53c4064619e74c81ee230a08058ba15654` |
| sha256 (slot 3) | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` |

### After each score comes back

1. `receipt_score` — the number from the submission page, not a memory of it.
2. `receipt_date` — ISO date; `scripts/ledger.py state` uses it for weekly slot accounting.
3. `status` — `SUBMITTED`.
4. `notes` — if the change was under 0.01, write "no evidence (public chunks only)".

Then update only the CURRENT STATE block in `README.md`.

---
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
