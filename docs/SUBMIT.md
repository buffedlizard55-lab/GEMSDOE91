# SUBMIT — what to upload, and what to paste back

**Status 2026-10-23: 12 release pairs (24 files) built and gate-clean.** `releases/*.tif` are
gitignored and rebuilt on demand; the hash contract is `releases/MANIFEST.json` (24 entries, each
with `axis`, `n_dots`, `sha256`, `bytes`). **No agent has ever submitted anything and none may.**
One file per slot; the `-zeros` twin is the fallback encoding, **not** a second entry.

## Rebuild and verify (≈2 min, every input hash-checked)

```bash
python3 scripts/restore_data.py       # 15 pins, incl. the 419 MB stack from 5 hash-pinned parts
make releases                         # catalogue + spacing + relief + prune ladder, then hashes
python3 scripts/update_release_manifest.py --check   # expect: 24 files, 0 problem(s)
python3 scripts/preflight.py          # expect: BUILD ALLOWED
python3 scripts/verify_manifest.py    # expect: 15/16 verified (catalogue_mask is derived)
```

`make releases` fails if any byte moved, if a file on disk is not in the manifest, or if a
manifest entry was not built. A hash that does not reappear means a **different file** — log it
in `IRREGULARITIES.md` before uploading anything.

## Slot ranking (see `SLOT_PLAN.md`; the human spends the slots)

| # | file | dots | % changed | predicted (MODEL) | why this order |
|---|---|---:|---:|---|---|
| 1 | `…-PRUNE-le10-norefill-20261023-04002dae.tif` | 26,294 | 30.17 | **+0.008** [−0.006, +0.019] | mid-ladder dose: one receipt tests the whole PRUNE direction *and* locates the curve |
| 2 | `…-PRUNEle15norefill-20261023-1ca1ff6f.tif` | 21,989 | 41.60 | **+0.010** [−0.008, +0.024] | largest predicted gain; confirms or breaks monotonicity after slot 1 |
| 3 | `…-PRUNE-le4-norefill-20261023-360fe57e.tif` | 33,829 | 10.16 | **+0.003** [−0.003, +0.009] | brackets the collar edge (3–4 px) if slots 1–2 came back flat |

If slot 1 returns **≥ +0.01**, slot 2 should be `le15` (deepen). If it returns **|Δ| < 0.01**,
PRUNE is exhausted at this resolution: spend slot 2 on `le4` to bracket, and slot 3 on the
best non-PRUNE arm. RELIEF is **not** a slot candidate this week (below).

## The hash contract (all 24 files, from `releases/MANIFEST.json`)

| axis | dots | encoding | file | sha256 | bytes |
|---|---:|---|---|---|---:|
| PRUNE | 21,989 | zeros | `h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f-zeros.tif` | `28273f12207fbdda4ac75ffd1902e5cf38807cefe6951d34999f2d15a94330e0` | 239,337 |
| PRUNE | 21,989 | NaN | `h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f.tif` | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` | 291,857 |
| PRUNE | 26,294 | zeros | `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae-zeros.tif` | `0842d86618dbe64acf6dfb4137feff423a9dc394b59d153317381fc22b06dbb8` | 174,857 |
| PRUNE | 26,294 | NaN | `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif` | `04002dae86db72c3fc47652bd66e3ec029e432c909cad779039e9e3749ae0839` | 321,924 |
| PRUNE | 28,490 | zeros | `h33-h33-2-b2-PRUNEle8norefill-20261023-e1dd69d0-zeros.tif` | `42c54d214b77aac590fb66f3ce6785b23085ce99d74339b866b1469960a79ba3` | 258,813 |
| PRUNE | 28,490 | NaN | `h33-h33-2-b2-PRUNEle8norefill-20261023-e1dd69d0.tif` | `e1dd69d02b90f95e779c43de1843ac53c4064619e74c81ee230a08058ba15654` | 311,319 |
| PRUNE | 32,017 | zeros | `h33-h33-2-b2-PRUNE-le5-norefill-20261023-5b6d3987-zeros.tif` | `2ecee552504209488ab5d2a0066dbd87f19cd4b1baea3003a4c34935b78e20c2` | 200,383 |
| PRUNE | 32,017 | NaN | `h33-h33-2-b2-PRUNE-le5-norefill-20261023-5b6d3987.tif` | `5b6d39870bc0fe9813813f231a56e3b9425e7e2ec149e3e2de8f3ae654b14ce8` | 347,613 |
| PRUNE | 33,829 | zeros | `h33-h33-2-b2-PRUNE-le4-norefill-20261023-360fe57e-zeros.tif` | `b2c4fa39c78c2f02cd17bcf932ca910369be6b7c222ec0f3e4fde6da3f001be4` | 208,254 |
| PRUNE | 33,829 | NaN | `h33-h33-2-b2-PRUNE-le4-norefill-20261023-360fe57e.tif` | `360fe57edd8286393a180f0ae53c8259899c4344e5bc7f4c4ec20dcdf28530a7` | 355,396 |
| PRUNE | 35,483 | zeros | `h33-h33-2-b2-PRUNEle3norefill-20261023-1209e863-zeros.tif` | `b4e5c5246dd24c2b6af710c01d6345f68dbed2a9834f1ce60ec0c777295b3582` | 278,508 |
| PRUNE | 35,483 | NaN | `h33-h33-2-b2-PRUNEle3norefill-20261023-1209e863.tif` | `1209e863a9ff58d86681e9e7f0375c4d185a59c50ef9769f02653ec1472198f2` | 331,161 |
| RELIEF | 37,654 | zeros | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFm2r15-20261023-3c3e832d-zeros.tif` | `231741727ea7f85fd8bec649f64977409eb262f7249fb3ce1c8dbef4a2d22396` | 219,309 |
| RELIEF | 37,654 | NaN | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFm2r15-20261023-3c3e832d.tif` | `3c3e832d4788a2c01fc7018c72a78964b0513f0c29e65670506f913764f81f75` | 366,272 |
| RELIEF | 37,654 | zeros | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFnull15-20261023-6c057de2-zeros.tif` | `bfa4f67ef74294fa4e008be6b7bad5275e9695310d5f3f49727aceb4ce8b4447` | 217,614 |
| RELIEF | 37,654 | NaN | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFnull15-20261023-6c057de2.tif` | `6c057de2ef3979912ca38c4daf08e5853a8406a44d29d6184628c50af77cac32` | 364,998 |
| RELIEF | 37,654 | zeros | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFr2m15-20261023-2c3839c9-zeros.tif` | `59671cea89c07c948f19f89ef8c18a195d3788c372cedeb2ef30e06cca8e97c5` | 213,077 |
| RELIEF | 37,654 | NaN | `h33-h33-2-b2-20261004-e5eb6e7e-RELIEFr2m15-20261023-2c3839c9.tif` | `2c3839c9a7aebef82bf096ac64cd21639031f52e43baf3a8fcf4773e362a984a` | 360,499 |
| SPACING | 37,654 | zeros | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGclump40-20261023-536d32ad-zeros.tif` | `d393c94f386015678e6f99f0c2a1a556aecd7cf733d59777b788f9a0423c80e7` | 224,741 |
| SPACING | 37,654 | NaN | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGclump40-20261023-536d32ad.tif` | `536d32ad49bdf70ade796eb6d3ba2e303c2622239cd4253c27c2ff96f1bfc60a` | 371,632 |
| SPACING | 37,654 | zeros | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGjitter40-20261023-39bb7288-zeros.tif` | `ad6dfa26043f7f195feba63852422efcc674da3eb448d4c42fc42858d26dd0d2` | 225,691 |
| SPACING | 37,654 | NaN | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGjitter40-20261023-39bb7288.tif` | `39bb728839d70ab08ddee645a270c1f693b69e1252f7961dadb3e4a758a95df6` | 372,814 |
| SPACING | 37,654 | zeros | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGspread40-20261023-6d389309-zeros.tif` | `5c517369be3c807c592e5dacfc9f7419a464f324c6d6a80f7eb6e0e5c6634d4e` | 226,284 |
| SPACING | 37,654 | NaN | `h33-h33-2-b2-20261004-e5eb6e7e-SPACINGspread40-20261023-6d389309.tif` | `6d389309aafaa79d01ecb2d62e6de89b2030f6d1bfb15f96024c32b5baf00eaa` | 373,103 |

## Form notes (≤140 chars, one per file, no score claimed)

```
Parent R0 h33-2-b2; PRUNE <=10px delete-only, 26294 dots (30.2% removed), count not held; predicted +0.008 MODEL
Parent R0 h33-2-b2; PRUNE <=15px delete-only, 21989 dots (41.6% removed), count not held; predicted +0.010 MODEL
Parent R0 h33-2-b2; PRUNE <=4px delete-only, 33829 dots (10.2% removed), count not held; predicted +0.003 MODEL
```

## The RELIEF triplet (built this session — do **not** spend a slot on it yet)

| arm | file suffix | predicted | tercile fraction after |
|---|---|---|---|
| range-front → piedmont | `…-RELIEFr2m15-20261023-2c3839c9.tif` | +0.0070 [−0.003, +0.017] | .204/**.568**/.227 |
| piedmont → range-front | `…-RELIEFm2r15-20261023-3c3e832d.tif` | −0.0070 [−0.017, +0.003] | .204/**.268**/**.527** |
| relocation null | `…-RELIEFnull15-20261023-6c057de2.tif` | 0.0000 [−0.010, +0.010] | .205/.417/.378 |

Matched (same 5,648 moves, same placement rule, count fixed 37,654, every new dot > 3 px from
the catalogue, all off the lineage's own detector support). Each prediction is ±0.007, **below
the 0.01 evidence bar**, and the arm is only interpretable as `r2m15 − null15`. Numbers:
`evidence/relief_axis_20261023.json`; mechanism: `docs/MECHANISM_CARDS.md` cards 4–6.

## Format receipt — copy this into the ledger / PR after uploading

```
candidate: h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae
encoding:  NaN-outside (primary)            zeros twin: kept as fallback
sha256:    __________________________________________
bytes:     ______
validate_raster.py : RESULT = PASS  (14/14 MUST gates)
validate_release.py: PASS (count_matches_parent is expected to differ for a delete-only arm)
n_dots:            26294
min_dist_catalogue_px: ______   zero_catalogue_mass: yes
receipt_score:     ______      receipt_date: ____________
```

## After the score comes back

1. Paste `receipt_score` and `receipt_date` into the row whose `id` contains `04002dae` in
   `ledger/submissions.csv`, set `status=SUBMITTED`, and leave `predicted_change` untouched.
2. **Gain ≥ +0.01** → mass is the lever. Next slot `…-PRUNEle15norefill-…-1ca1ff6f.tif`
   (deepen); R1 becomes the parent for later builds.
3. **|Δ| < 0.01** → no evidence at this dose. Next `le4` (bracket 3–4 px) and, if that is flat
   too, PRUNE is exhausted and the collar is not the lever.
4. **Loss ≥ 0.01** → the ≥ 3 px collar is wrong for this dataset: build the **add-in-collar**
   arm (3–8 px) instead of deeper deletes.
5. Update only the CURRENT STATE block of `README.md` and the slot table in `SLOT_PLAN.md`.
6. Compare against **TOP_PUBLIC** with its date. A change under 0.01 inside the public-chunk
   noise band is not evidence, whatever its sign.

## Do not

- Do **not** upload two encodings of the same file, or any file whose sha256 is already in
  `ledger/submissions.csv` (8+ upstream slots were spent on exact repeats).
- Do **not** upload a file whose `validate_raster.py` result is not `PASS`.
- Do **not** submit from any account but the entity's own; at most three scored files a week
  plus the one final blind choice.
- Do **not** contact drivendata.org, the leaderboard, or dropbox.com programmatically from
  this repo. The human reads the number; the repo only records it.
