# IRREGULARITIES — only items that change a decision

**I-1 · The repository is empty; R0 cannot be rebuilt. Nothing was built. (blocking)**
`main` (commit `f049d02`) contains one file, `README.md` (11 bytes). There is no
`registry/`, no `ledger/`, no `releases/`, no parent raster, no `sample_submission.tif`,
no catalogue mask, and no `.tif` anywhere on the sandbox filesystem. Brief §5 says:
verify the manifest, rebuild R0, match its sha256, "if you cannot, stop and report;
never approximate the parent". **R0 is therefore not reproduced and no variant can be
a one-change edit of it.** What was done instead: the harness was built and tested
against synthetic rasters so that the moment the parent is dropped in, the first
variant is one command away. This is the decision that shaped the whole session.

**I-2 · No receipt exists for any score, so there is no measured best. (decision-changing)**
There is no `ledger/submissions.csv` and no `ledger/raw_paste.txt`, so the climb
(0.1922 → 0.2477 → 0.2600 → 0.2708 → 0.2778) cannot be collapsed or checked. All of
it is **CLAIM**, not RECEIPT. Consequence: slot decisions must not treat 0.2778 as a
measured baseline, and any "delta vs R0" quoted now is a MODEL delta.

**I-3 · Brief §4.4 contradicts R0's own recipe on the catalogue buffer. (gate decision)**
§4.4 says "keep >= 3 px from [catalogue pixels]"; the accepted parent was made by
pruning "<= 2 px", which permits dots at 2.0–3.0 px. A validator that enforces
">= 3 px" would fail R0 itself. Implemented: `--min-gap-px 2.0` by default
(R0-compatible) and every dot in the (2, 3) px annulus is counted and reported as a
warning. **The human must decide which reading is the real gate** before the first
submission; if the strict reading is intended, R0 is not a legal parent either.

**I-4 · MASS and PRUNE cannot be built here without R0's ranking artifact. (axis decision)**
Both axes need "the parent's own ranking, rebuilt from the recorded recipe if it is not
stored" (§5). The ranking is by exact marginal gain, which requires the truth labels R0
was ranked against; those are not in the repo and are not derivable from the raster.
Re-ranking against a proxy would change *two* things at once (ranking + axis), which is
exactly what this brief forbids. Consequence: of the seven axes, only CONCENTRATION is
buildable from a parent raster + prior + catalogue; it is the axis chosen.

**I-5 · The metric code is not present; the pay threshold depends on one unverified assumption. (prediction decision)**
Brief §2 gives `DTI = T / (0.2T + 0.2(S−M) + 0.8|G|)` and states the isolated-pixel bar
is "about 0.056 at 0.28". That figure follows only if `|G|` is unchanged by adding a dot
(`tools/dti.py` assumption A3, unit-tested). If `|G|` is *remaining uncovered truth*,
the bar becomes `0.2·DTI/(1+0.8·DTI)` ≈ **0.0458** at 0.28 — a 22% difference that moves
absolute MODEL deltas but barely reorders dots. Consequence: no absolute predicted delta
from `tools/dti.py` may be quoted to a slot decision until the official metric code is
pinned. Ranking (order) is usable; magnitude is not.

**I-6 · TOP_PUBLIC, slot counts and the deadline are unknown and unverifiable here. (target decision)**
The brief leaves `TOP_PUBLIC = ____`, "slots left __ / __", and asks to confirm the
2026-12-03 deadline on the competition page. This sandbox is restricted to
github.com / pypi.org / npmjs.org, and the competition terms ban automated access
(`https://www.drivendata.org/termsofuse/`), which this agent must not circumvent.
Consequence: there is **no valid target number** and no valid slot count in this
session; "maximize P(win)" is currently unmeasurable. Handled by leaving placeholders
and refusing to invent one.

**I-7 · The public repo and the data-use terms are in tension. (handling decision)**
The repository is public (GitHub API: `"isPrivate": false`) and brief §4.2 says to keep
competition rasters out of public repos. It is not possible to check the data-use terms
from here. Consequence: rasters and any competition-derived data are `.gitignore`d;
only recipes, hashes, ledger rows and receipts are committed. If competition rasters
were ever pushed to `main` before this session, that is **unverified and unverifiable
from this sandbox** — the human should check the history of the upstream repo.

**I-8 · The DTI formula itself is only as good as the brief's transcription. (already noted, kept for visibility)**
No organiser source for `alpha 0.2 / beta 0.8 / zeta 0.2` is reachable; all of it comes
from the brief, which is treated as authoritative-per-brief but is not a receipt.
Recorded once; no further action possible from here.

**Items deliberately NOT listed** (they do not change a decision): the missing CI
(none existed; one was added), the absent `.gitignore` (added), stylistic choices in
`tools/`, and the fact that the fixture rasters are synthetic.
