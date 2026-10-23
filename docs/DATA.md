# Data handling

## Rules this repository obeys

1. **Nothing is built from memory.** Every input must be pinned in
   `registry/data_manifest.json` with a sha256; `tools/preflight.py` refuses the build
   otherwise.
2. **No competition raster is committed.** The repo is public and the competition
   data-use terms cannot be verified from this sandbox
   (`https://www.drivendata.org/termsofuse/`). `data/` and `releases/*.tif` are
   `.gitignore`d; only recipes, hashes, ledger rows and receipts are committed.
3. **No automated access to the competition site.** The terms ban it. The human
   downloads, stores and submits; the agent only reads local files.
4. **External data** is used only if it is licensed for this challenge and shareable
   with the sponsor. Preference order: public-domain USGS / NBMG products. Every
   external layer needs `url` + `license` fields filled in the manifest before use.

## Inputs this harness expects

| id | what it must be | why |
|---|---|---|
| `sample_submission` | the organiser's raster: float32, EPSG:32611, 100 m, 1 band | CRS/transform/dtype gates, footprint |
| `R0_parent` | `h33-h33-2-b2.tif` exactly, unit mass per dot | the parent of every variant |
| `R0_ranking` | the ranking R0 was built from (dot id → rank/score), or the script + labels that rebuild it | MASS, PRUNE refill, TRACKB |
| `catalogue_mask` | binary mask of known USGS/INGENIOUS traces, pixel-exact, same grid | gates G6/G7, PRUNE |
| `km_prior` | km-scale prior **not** derived from the parent's dots | CONCENTRATION |
| `tmi_gradient`, `gravity_gradient` | gradient magnitude of the provided TMI / gravity bands | SNAP |
| `detrended_elevation` | DEM with a regional trend removed | RELIEF |

## How to pin an input (human, on their own machine)

```bash
sha256sum data/sample_submission.tif data/h33-h33-2-b2.tif data/catalogue_mask.tif
# paste into registry/data_manifest.json  ->  "sha256": "<64 hex>"
# for the parent also set "parent_sha256_expected" to the same value
make preflight   # must print CLEAR for the axis you intend to run
```

`preflight` additionally checks that every raster input shares the sample's CRS, height,
width and transform — a catalogue mask on a shifted grid silently produces a *wrong*
zero-mass gate, which is worse than no gate.

## Why the parent hash matters more than it looks

A parent that has been through a float64→float32 round trip, a re-compression, or a
nodata re-assignment is a *different raster* with a different sha256 but visually
identical dots. Brief §5 forbids approximating the parent. `preflight` therefore
requires `parent_sha256_expected` to be recorded; if it is absent, "R0 was reproduced"
cannot be claimed and the run stops.
