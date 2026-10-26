# Why GEMSDOE32 "R0" scored highest — and whether it can be beaten (Session 22)

**Evidence classes used below.** `BYTES` = recomputed from SHA-256-pinned rasters; `USER-REPORTED` = a live score copied from `registry/lfi_live_anchors.csv` (not an organizer receipt); `OFFICIAL` = text read from a cited DrivenData / DOE page on 2026-10-26; `MODEL` = derived from the previous classes under stated assumptions. Nothing here is `ORGANIZER-CONFIRMED`. Reproduce with `python3 scripts/analyze_r0_lineage_s22.py` → `docs/s22-xb/r0-decomposition.json`.

**The file.** `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, 37,654 binary dots, USER-REPORTED **0.2778** (GEMSDOE32). For scale: the public board on 2026-10-26 reads #1 0.4437, #10 0.3379, #24 0.3169, #50 0.2826 (OFFICIAL), so 0.2778 sits just below rank 50.

---

## 1. The metric, and the one identity that matters

OFFICIAL (DrivenData problem description, page 967) gives `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)` with `FN_w = |G| − TP_w` where `G` is the set of scored truth pixels. Writing `T = TP_w`, `FP = FP_w`:

```
DTI = T / (0.2·T + 0.2·FP + 0.8·|G|)
```

* `|G|` is a constant of the (hidden) public subset; the organizers pool all public-subset pixels into one index (OFFICIAL, forum 11550).
* Known-fault pixels are **masked out** of evaluation (OFFICIAL, forum 11516), and a "new fault" is "any fault pixel not already captured by USGS/INGENIOUS" (OFFICIAL, forum 11536).
* For a binary dot raster `T = Σ_g max_dots (1 − d/3)` (3 px = 300 m) and `FP = Σ_dots (1 − max_g (1 − d/3))`.

Adding one unmatched dot (expected credit ≈ 0, matched kernel mass ≈ 0) lowers the score by about `0.2·DTI²/T`; at `DTI ≈ 0.28`, `T ≈ 5.1×10³` that is **3 × 10⁻⁶ per dot**. A dot pays for itself only if its expected truth credit exceeds about `0.2·DTI/(1 − 0.2·DTI) ≈ 0.059` of a full unit.

## 2. The lineage, proven from bytes

(`BYTES`; `docs/s22-xb/r0-decomposition.json → nesting_exact`, `difference_sets`)

| Raster | Dots | Relation (pixel-exact) | USER-REPORTED |
|---|---:|---|---:|
| H19-5 "multiline" (binary ridge network) | 121,131 | root | 0.1922 |
| D2.8 (GEMSDOE25) | 44,090 | ⊂ H19-5 | 0.2600 |
| H27-4 solo (GEMSDOE28 / **identical pixels in GEMSDOE31**) | 40,199 | = D2.8 minus **3,891** dots at ≤ 1 px from the catalogue | 0.2708 (both sites) |
| **R0** (GEMSDOE32) | **37,654** | = H27-4 minus **2,545** dots at (1, 2] px | **0.2778** |
| GEMSDOE36 "anderson-pinn-38854" | 38,854 | = R0 **plus 1,200** dots (median 14.5 px from the catalogue, 0.08% on the H19-5 network) | 0.2750 |

Consequences: (i) R0 contains **no pixel that D2.8 does not**; its entire advantage over the 0.2600 file is the deletion of 6,436 dots lying within two pixels of the catalogue. (ii) The same 40,199 pixels scored **0.2708 on two separate sites** — the board is deterministic at four decimals, so these anchors are replicates, not noise. (iii) GEMSDOE36's file is not an independent detector: it is R0 with 1,200 extra far-field dots.

## 3. Why dots beside the catalogue are false positives (mechanism)

Because mapped-fault pixels are excluded and new faults are by definition *not* mapped pixels, a dot 1–2 px (100–200 m) from a mapped trace lands on neither a scored truth pixel nor a masked pixel; it is penalized as FP unless a new fault happens to run within 300 m. The fitted live-score inversion (`docs/lfi/fit_r10.json`, `MODEL`) puts the truth-density factor at ×0.61 / ×0.47 / ×0.46 for 1–2 / 2–3 / 3–5 px from the catalogue, ≈ ×0.93 at 5–10 px and ×1.16 / ×1.40 / ×5.94 at 10–20 / 20–40 / > 40 px: **new faults concentrate away from mapped ones**, i.e. where the catalogue is silent.

## 4. A one-parameter model that predicts the next two live scores

`MODEL`, assumption: the removed/added dot sets carry ≈ zero truth credit and are all false positives. Then `T` is unchanged and the denominator moves by exactly `0.2·|ΔN|`, so the first live pair identifies `T`:

* D2.8 → H27-4 (−3,891 dots, 0.2600 → 0.2708): **T ≈ 5,073** (rounding band ± 0.9%).
* Out-of-sample prediction 1: H27-4 → R0 (−2,545 dots) predicts **0.2784**; reported 0.2778 (residual +0.0006).
* Out-of-sample prediction 2: R0 → GEMSDOE36 (+1,200 dots) predicts **0.2742**; reported 0.2750 (residual −0.0008). Solving for the credit the added dots must have carried gives ≈ 16 in total, **≈ 0.013 per dot**, one tenth of R0's average.
* Step 2 alone implies a slightly larger T (5,470): the (1, 2] px set carried a little credit, which is why prediction 1 is high by 0.0006.

Implied scale for R0 (`MODEL`; bracketed by the unobservable matched mass `M`): average credit **T/n = 0.135 per dot**; `|G|` ≈ **12.1 – 13.4 thousand** truth pixels in the scored region; recall `T/|G|` ≈ **38 – 42%**. R0 is a high-recall, low-precision raster: about nine in ten of its dots are unmatched.

## 5. What the gain is made of (verified arithmetic on USER-REPORTED scores)

H19-5 network → R0 is +0.0856: **dotting to 2.8 px spacing +0.0678 (79%)**, **pruning ≤ 1 px dots +0.0108**, **pruning (1, 2] px dots +0.0070** (together 21%). The 79/21 split quoted in earlier sessions is reproduced from the scores; the *mechanism* above is what the bytes add.

## 6. Why the repo's own holdout ranks R0 last (collar paradox)

The hide-and-recover holdout (`gems57-pooled-hide-v2`) withholds parts of the *catalogue* and scores against them. A raster that has been collar-stripped of every dot within 2 px of the catalogue is blind to exactly that truth, so a static R0 scores **0.006697** there (95% CI [0.005969, 0.007450]; S21 reported the same value and this session re-measured it as the `static_R0` arm in `docs/s22-xb/holdout.json`). The same holdout gives a random equalized null **0.0713**. The holdout measures catalogue recovery; the live board measures *new* faults. Across 112 anchors the Spearman correlation between hide-v2 and the live score is **+0.105, 95% CI [−0.093, +0.294]** (bootstrap over anchors; `docs/s22-xb/instruments.json`; S20 reported 0.105), i.e. not distinguishable from zero. The blind-SGMC control, which S14-era notes called an *anti*-proxy on seven ancestors, is moderately and significantly *positive* on 112 anchors: **+0.442 [+0.264, +0.605]** (>500 m) — still only ≈ 20% of rank variance, never a gate (IR-S22XB-04).

## 7. Can R0 be beaten? What the evidence says

1. **More pruning.** If an oracle could remove *k* more dead dots from R0 the score would reach `0.281 / 0.294 / 0.313 / 0.358` for `k = 1k / 5k / 10k / 20k` (`MODEL`). That headroom is real, but it is unidentifiable without information about *which* dots are dead; the 1,200-dot GEMSDOE36 experiment shows far-field model dots can have one-tenth of R0's average credit.
2. **New detectors on the same 100 m stack.** Earlier independent lanes (hide-v2 0.15 – 0.20) project to 0.15 – 0.21 on the live-anchored inversion (re-run today; S21's card stored 0.16 – 0.20), with a leave-one-site-out error of about 0.02; none projects above R0's own model value (0.273 when S21's own function is re-run today; S21's card stored 0.254, see IR-S22XB-03).
3. **The uniqueness rule.** A raster that overlaps no registered raster by more than 70% within 3 px must put most dots where the fleet is not; the same inversion says the fleet already occupies the zones that carry value (truth factor ×19 where three independent fleet rasters agree). Pass-2 projections under hard caps were 0.16 – 0.22 (S21-FAM3).
4. **New information.** The only identified escape is a new data layer. A rank-5 team states publicly that it uses "20 m lidar-derivative U-Net ensembles" (OFFICIAL forum 11531); USGS 3DEP 1 m DEMs are free and public domain, but all eight official hosts tested from the sandbox return no connection (see `docs/OFFICIAL_SOURCES_VERIFIED_S22.md`).

**Answer.** R0 is the best-pruned member of a single family, not a better detector. Beating it with a *unique* raster needs information the sandbox cannot reach; beating it with a *derivative* is possible in principle (further pruning) but is excluded by the standing uniqueness requirement and cannot be evaluated here.

## 8. Assumptions and limits (read before quoting any number)

* Live scores are USER-REPORTED; the 4-decimal replicate agreement above supports consistency, not provenance.
* "Pure false positive" is a first-order assumption; residuals of ±0.0008 bound how far it fails for these three steps only.
* `|G|` and recall depend on the unobservable matched mass `M`; the table gives a bracket, not a measurement.
* The public subset is hidden and chunked; gains found by fitting the public score need not transfer to the private set or to the Phase 2 area (Rules §3.6.2).
* The standing prompt cites 0.3195 and 0.4413; the official board read 0.3169 (#24) and 0.4437 (#1) on 2026-10-26.
