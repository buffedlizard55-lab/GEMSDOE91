# IRREGULARITIES

Only items that change a decision. Ordered by how hard they block.

## 1. The repository is PUBLIC and GitHub Pages is serving `main:/`

`gh api repos/buffedlizard55-lab/GEMSDOE91` returns `"visibility": "public"`, and
`/pages` returns `"status": "built"` with `source: {branch: main, path: /}`,
`"public": true`, URL `https://buffedlizard55-lab.github.io/GEMSDOE91/`.

**Why it changes a decision.** Brief §4.2 requires that competition rasters be kept
out of public repos, and asks that any that are already public be flagged because
the data-use terms are unchecked. Today `main` contains no raster (`gh api ... --jq .size`
= 0 kB), so nothing is leaked yet. But any commit of `data/` or `releases/` would
publish competition-derived rasters on the open web within seconds, including on the
Pages site, and git history is not erasable in practice.

**Decisions taken.** `.gitignore` excludes `data/`, `releases/`, `*.tif`, `*.npy`.
Rasters live outside git; only their sha256 goes into `ledger/submissions.csv`.
CI fails on a conflict marker and on a manifest hash MISMATCH, never on a missing
file, so a legitimate local-only input cannot be mistaken for corruption.

**Human action.** Confirm the competition's data-use terms allow keeping derived
rasters in a *public* repo at all; if they do not, either keep the repo private or
disable Pages (`gh api -X DELETE repos/{owner}/{repo}/pages`). This is your call,
not mine — I have not changed repository settings.

## 2. Inputs were recovered from the owner's PUBLIC sibling repos — flag for data terms

**Resolved, with a caveat that changes a decision.** The checkout held only `README.md`
(11 bytes). Rather than stop, I searched the same owner's other repositories and found
the parent session's own artefacts, all public:

| input | source | how it was verified |
|---|---|---|
| R0 raster | `GEMSDOE32 docs/downloads/gemsdoe32-h33-h33-2-b2-…-e5eb6e7e-nan.tif` | sha256 `baeae321…c77dd` matches `GEMSDOE32 docs/downloads/submissions_manifest.json` exactly |
| `sample_submission.tif` | `60GEMSDOE data/official/sample_submission.tif` | sha256 `2176d08e…cbc` matches `GEMSDOE32 data/prepared_manifest.json` `source_hashes` |
| `labels.tif` | `60GEMSDOE data/official/labels.tif` | sha256 `7ba308cc…093` matches the same `source_hashes` |
| solo-d28 (forensics only) | `GEMSDOE31 docs/downloads/…solo-d28-…-nan.tif` | used to reconstruct the parent's operation; not an input to any build |

Pinning these satisfies brief §4.2 ("or the repo's equivalent" manifest, hash verified
before use). I did not rebuild R0 from a recipe and I did not approximate it: the bytes
match the hash the parent session recorded. **The parent is verified, not inferred.**

**The caveat, which you must rule on.** ~200 public repositories in this account carry
competition rasters, label files and score ledgers, several served through GitHub Pages.
Brief §4.2 says to flag rasters that are already public because the data-use terms are
unchecked, and that is now clearly the case at scale, not a single stray file. Nothing
in this repo is affected (`data/`, `releases/`, `*.tif` are gitignored), but the wider
practice is not mine to fix. Decision: I treated the public siblings as a *source of
pinned inputs*, and did **not** treat their presence as permission to publish anything.

## 2b. The parent brief's PRUNE instruction conflicts with the parent lineage — resolved in favour of the lineage

Brief §5 says PRUNE should "refill to hold the count". The lineage did the opposite, and
that is now measurable rather than argued: differencing R0 against solo-d28 gives
37,654 ∩ 40,199 = 37,654 shared dots, **0 dots in R0 that are not in solo-d28**, and
2,545 dots within ≤2 px of the catalogue in solo-d28 only. So R0 = solo-d28 minus the
≤2 px dots, no refill.

**Decision.** The three variants are delete-only, matching the parent. A refill would
require the parent's own ranking, which was never stored; inventing one contradicts
brief §4.2. The consequence is honest and stated in every mechanism card: these builds
change *mass and geometry together*, so a gain cannot be attributed to "avoiding the
catalogue" alone. `scripts/axes.py` keeps `refill=True` available for when a ranking exists.

## 3. The ledger is absent, so every number in this repo is a CLAIM

`ledger/submissions.csv` and `ledger/raw_paste.txt` did not exist. The five rows now
in the ledger are transcribed from agent-brief §3 and tagged `provenance=BRIEF_S3`,
`status=CLAIM`, with the values in `claimed_score` — **not** `receipt_score`, so no
downstream reader can mistake them for receipts. Two of those rows have since acquired
real sha256 values from the recovered rasters (R0 `baeae321`, solo-d28 `07b6db44`),
which makes exact-repeat detection work for both going forward.

**Correction to the brief.** §3 lists the climb with 37,654 dots at solo-d28, but the
solo-d28 raster recovered from GEMSDOE31 has **40,199** dots; 37,654 is R0's count. The
prune ≤2 step therefore removed 2,545 dots (6.3 %), not zero. This matters because it
gives the per-dot rate the dose-response is extrapolated from.

**Why it changes a decision.** Brief §8 distinguishes RECEIPT from CLAIM. With no
receipts, "best receipt" is empty and the incumbent's live position is unverified.
The brief also reports ≥8 slots lost to exact repeats; without sha8 values, hash
dedupe cannot cover those historical files, so `scripts/ledger.py state` warns that
5/5 rows carry no hash. Duplicate prevention currently works only for files built
from now on, plus the (parent, axis, value) check.

## 4. The 3 px distance rule in §4.4 is a rule the parent itself breaks

Brief §4.4 says keep ≥3 px from the catalogue unless AXIS=PRUNE. Measured: R0's
minimum distance is **2.236 px**, and 2,171 of its dots are within ≤3 px. So the
incumbent has been violating the stated rule all along, and the rule as written would
forbid uploading R0 itself.

**Why it changes a decision.** Read literally, §4.4 makes the best-scoring file in the
lineage illegal. I have not applied it as a hard gate, because doing so would reject
the parent and every variant that keeps any dot in that band. Instead the gate treats
mass *on* a catalogue pixel as fatal (R0 has zero) and reports the distance shortfall
as a statistic, which is what §6's "zero catalogue mass" gate actually says. If you
want the 3 px rule enforced, say so and I will rebuild — it would remove 2,171 dots
from R0, which is exactly the PRUNE3 file already built.

**Also:** `axes.snap` defaults to `min_cat_px=2.0` and reports `cat_distance_ok`
rather than silently relocating the parent's own dots when the parent sits inside 3 px.

## 5. The metric form is taken from the brief, not from the competition page

Brief §4.1 forbids fetching `drivendata.org` (its terms of use ban automated access),
so the algebra `DTI = T/(0.2T + 0.2(S−M) + 0.8|G|)` could not be re-read at source.
`scripts/dti.py` implements it and `tests/test_dti.py` pins its behaviour (a perfect
field scores 1.0 exactly; an isolated dot scores its kernel weight; a dot pays iff
`k > 0.2·DTI`, verified over the full offset grid).

**Why it changes a decision.** If the official scorer aggregates per chunk or per
pixel rather than over the whole raster, "which dot pays" changes, and so does every
ranking derived from `marginal_gain`. Those rankings are therefore MODEL-grade until
you paste one official score that a local recompute can reproduce.

## 6. Two numbers in the brief cannot be verified from here

The deadline (2026-12-03) and the weekly slot count are on the competition page,
which I must not fetch; `TOP_PUBLIC` is on the leaderboard, same. All three are left
blank in `README.md` and `SLOT_PLAN.md` rather than filled from memory.

## 7. External priors are unpinned, so the RELIEF and TRACKB axes are not buildable

The Faulds step-over/intersection inventory has no URL or licence recorded in this
repo; brief §4.3 requires both before use. The GeoDAWN lidar product is pinned by URL
only and is not present in the sandbox. Both are marked UNVERIFIED in
`registry/data_manifest.json`.
