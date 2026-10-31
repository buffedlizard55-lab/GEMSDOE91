# S28 · Technical review — from a blocked workspace to a certifiable, unique candidate

**Branch** `arena/bcdb9324-gemsdoe91` · **date** 2026-10-31 · **experiments used** 3 of 3 · **weekly slots spent** 0
**Verdict** `promote` · **OK TO DOWNLOAD: YES** · **OK TO SUBMIT: YES**

Companion documents: [executive summary and download](executive-summary.html) ·
[run card](run-card.json) · [hypotheses](HYPOTHESES.md) · [nine-site forensics](nine-site-forensics.json) ·
[holdout](holdout.json) · [candidate](candidate.json).

---

## 0 · What changed relative to the previous session

The previous review (2026-10-30) ended `BLOCKED • NO CANDIDATE • OK TO SUBMIT: NO` because
`registry/data_manifest.json` listed 15 pinned inputs as missing and `scripts/restore_data.py --check`
reported `15/15` absent. That block was real, and it was an *access* problem, not a science problem.
This session resolved it from the only reachable host (GitHub) and re-verified every byte:

| Input | Pinned sha256 (`registry/data_manifest.json`) | Measured this session | Source used |
|---|---|---|---|
| `sample_submission.tif` | `2176d08e485aa2cd…` | **match**, 1,599,597 B | `buffedlizard55-lab/GEMSDOE86:data/bridge/sample_submission.tif` |
| `existing_faults.tif` | `7ba308ccdc4418b3…` | **match**, 425,830 B | `buffedlizard55-lab/GEMSDOE86:data/bridge/existing_faults.tif` |
| `gems-geodawn-numerical-features.tif` (canonical `training_features.tif`) | `4371c82e3b8339b8…` | **match**, 418,912,844 B | 5 parts from `GEMSDOE:data/bridge/` concatenated in order, then hashed |

These are GitHub mirrors of the official competition rasters. The mirrors are *not* an organizer
authenticated channel; identity is established only by agreement with this repository's own pins, which is
the strongest claim available inside this sandbox. `dropbox.com`, `drivendata.org` and `docs.nlr.gov` are
outside the outbound allowlist (`SSL_ERROR_SYSCALL` / no route), so the official download page and the
rules PDF were **not** re-fetched this session — flagged as **IR-S28-05**.

Grid facts re-measured from those bytes (not copied from documentation):

```
CRS EPSG:32611 · shape 3730 rows × 3292 cols · 100 m cells
transform (100, 0, 243350, 0, -100, 4508550)
bounds   left 243350, bottom 4135550, right 572550, top 4508550
sample_submission : float32, nodata NaN, 5,167,373 finite cells  -> scored footprint
existing_faults   : int8, nodata -1, 60,988 positive cells inside that footprint
features          : 19 bands, float32, nodata -3.4028235e38
```

---

## 1 · The question: why did GEMSDOE32 reach 0.2778, and can it be beaten?

### 1.1 What is verifiable

Each of the nine focus rasters was retrieved at its pinned commit, its SHA-256 rechecked against
`docs/review-20261030/nine-site-snapshot.json`, and then measured on the official grid. Nothing was taken
on trust. Result (`nine-site-forensics.json`):

| Site | dots | median distance to catalogue | >10 px | median NN | max peer overlap (3 px) |
|---|---:|---:|---:|---:|---:|
| GEMSDOE24 | 60,069 | 14.87 px | 59.3 % | 2.24 px | 100.0 % |
| GEMSDOE25 | 44,090 | 15.00 px | 59.6 % | 3.00 px | 100.0 % |
| GEMSDOE27 | 61,328 | 14.14 px | 58.4 % | 2.24 px | 98.0 % |
| GEMSDOE28 | 37,660 | 17.72 px | 65.7 % | 3.16 px | 100.0 % |
| GEMSDOE30 | 44,090 | 15.00 px | 59.6 % | 3.00 px | 100.0 % |
| GEMSDOE31 | 40,199 | 17.69 px | 65.4 % | 3.00 px | 100.0 % |
| **GEMSDOE32** | **37,654** | **19.65 px** | **69.8 %** | **3.00 px** | **100.0 %** |
| GEMSDOE33 | 41,865 | 16.64 px | 63.4 % | 3.16 px | 99.7 % |
| GEMSDOE36 | 38,854 | 19.24 px | 69.7 % | 3.00 px | 97.6 % |

Within this family the reported score is a **perfect** monotone function of the median distance to the
mapped catalogue (Spearman ρ = 1.00, n = 9; Pearson r = 0.934, p = 2.3 × 10⁻⁴) and an almost perfect
monotone function of the share of dots more than 1 km from the catalogue (ρ = 1.00). Dot count sits in a
narrow 37.6k–61.3k band, and the two best files both pack at exactly 3.00 px nearest-neighbour spacing.

### 1.2 Why that is the right direction — the metric algebra

The repository's pinned transcription of the metric (rules PDF 96647, as transcribed in
`vendor/gems57/metric.py`; cross-checked against `tests/test_metric.py`, not re-fetched this session) is

```
TP_w = Σ_{g∈G} max_{x∈P, d≤R} p(x)·k(d)      k(d) = max(1 − d/300 m, 0)
FP_w = Σ_{x∈P} p(x)·(1 − max_{g∈G} k(d))
FN_w = |G| − TP_w
DTI  = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)
```

Two consequences drive everything:

1. **A dot can only earn credit inside the hidden truth's 300 m kernel.** Dots stacked on an already-mapped
   trace earn nothing if the scored truth is the withheld/unmapped set, while each still contributes 0.2 to
   the denominator.
2. **Recall is bought four times cheaper than precision** (β/α = 4), so the optimum is a wide, sparse,
   well-spread dot field rather than a thin high-confidence line.

Solving the algebra for the reported 0.2778 with 37,654 dots and an assumed hidden truth of K = 15,195 px
(K is a *model-derived* estimate from `docs/GEOTHERMAL_VENT_RESEARCH_S20_LFI.md`, not an organizer figure;
the "M = T" near-bijection case is the optimistic one):

```
denominator = 0.2·n + 0.8·K = 7,530.8 + 12,156 = 19,686.8
TP_w = 0.2778 × 19,686.8 ≈ 5,469 px      → recall ≈ 36.0 %      (≈ 1 useful dot in 7)
observed algebra ceiling at this budget  = K / (K + 0.2·(n − K)) ≈ 0.772
```

So 0.2778 is *not* near any structural ceiling — it is a mediocre detector with good packing. Roughly two
thirds of the achievable credit is still on the table. Beating it requires **more true-positive mass**, i.e.
a better ranking of *where* the dots go, not better spacing.

### 1.3 The nuance that stops the easy conclusion

The distance effect is **family-internal**. Fitting the repository's 112 scored anchor rasters
(`docs/lfi/anchors.json`, all USER-REPORTED), a two-feature model on log(dot count) and the share of dots
within 2 px of the catalogue has **leave-one-site-out R² = −0.02** — no fleet-wide predictive power at all.
Adding the fleet-consensus feature `frac_on_net15` lifts LOSO R² to **0.705** (RMSE 0.046,
Spearman 0.809), and `frac_on_net15` alone correlates with score at Pearson r = 0.82 (p = 5.7 × 10⁻²⁹).

Interpretation: the nine-site improvements are a co-evolving lineage (dotting → collar pruning → distance
quotas), so distance and score move together *inside that lineage* without distance being a general law;
across the fleet what separates 0.25 from 0.05 is whether the dots sit on structures that many independent
submissions also found. That is also, awkwardly, the definition of a duplicate — and `frac_on_net15`'s
construction recipe is not documented anywhere in this repository (**IR-S28-04**), so it cannot be reused
as an auditable feature this session. It is the top of the ranked next-lane list.

### 1.4 Answer

Yes, 0.2778 should be beatable — the algebra leaves ~0.5 of headroom — but only by improving recall, and the
only honest way to attempt that is a better *surface*, since the geometry is already at its empirical
optimum. This session therefore holds geometry fixed at the nine-site optimum and attacks the surface.

---

## 2 · Method (lane S28, hypothesis H-S28-1 “CPT-19”)

**Hypothesis.** A supervised classifier trained to separate mapped faults from far-field background using the
*official* 19-band numeric-feature stack learns the multivariate expression of a Great Basin normal fault and
transfers to unmapped traces better than hand-written ridge/scarp formulas.

**Why this is new here.** The 418 MB official stack had never been restored in any workspace of this repository,
so all prior lanes — and all nine focus sites — built surfaces from hand-crafted single/dual-band formulas over
derived products. This is the first lane to train on the official geophysics.

**Feature stack** (`scripts/s28_build_features.py`, 41 layers, catalogue-free by construction):

* 19 × robust band score `z_b = (x − median)/IQR` over the footprint
* 19 × 400 m Gaussian context `s4(z_b)`
* `edge_mag_hg` — RMS of the three horizontal-gradient bands (`tmi_hg`, `iso_grav_anom_hg`, `iso_grav_anom_slope`)
* `curv_det_elev` — negative Laplacian of detrended elevation at 100 m
* `basin_x_conductivity` — `z(depth_to_base_surf) × z(cond_surf)`

No catalogue, no distance-to-catalogue, no score, no label-derived layer enters the stack, so the canary below
is a valid test per layer.

**Model.** `HistGradientBoostingClassifier(max_iter=200, lr=0.1, 31 leaves, l2=1.0)` on
60,988 mapped-fault positives vs 121,976 background cells ≥800 m from any mapped fault.

**Emission** (frozen before any scoring): 37,654 binary cells; minimum 3-cell Chebyshev separation (Euclidean
NN ≥ 2.83 px); zero mass within 300 m of the mapped catalogue; distance-band quotas 4 / 14 / 32 / 28 / 22 %
over (300, 500] / (500, 1000] / (1000, 2000] / (2000, 4000] / >4000 m. The quotas were fixed from the
nine-site envelope (cumulative ≤2000 m share 50 %), not tuned on the instrument.

---

## 3 · Results

### 3.1 Holdout (shared instrument, identical emission for all arms)

Instrument: `vendor/gems57.holdout.buffered_component_draw` — whole 8-connected catalogue components withheld
per label-blind eroded quadrant, 20 % hide fraction, 300 m feature buffer, pixel-exact masking of visible
catalogue; scored with `vendor/gems57.metric.dti_exact` (pooled α = 0.2, β = 0.8, R = 3 px).
Withheld positives n = **11,321** across four folds.

| Arm | Pooled HOLDOUT-DTI | TP_w | FP_w | FN_w |
|---|---:|---:|---:|---:|
| E1 physics control (fleet-style composite of `tmi_hg` + gravity HG/slope + scarp slope + curvature) | 0.042443 | 289.5 | 30,792.8 | 11,031.5 |
| E2 logistic on the same 41 layers | 0.061739 | 990.1 | 30,092.2 | 10,330.9 |
| **E3 HistGradientBoosting on the same 41 layers** | **0.102921** | **1,663.4** | **29,418.9** | **9,657.6** |

* HGB vs physics control: **×2.43**. HGB vs linear: **×1.67**.
* Per-fold HGB DTI: NW 0.0961, NE 0.0867, SW 0.0952, SE 0.1280 — consistent across all four quadrants.
* Leakage canary: strongest single layer reaches AUC **0.7947** on withheld truth vs 40,000 background cells,
  below the 0.90 stop.

### 3.2 What the instrument cannot see

The instrument rewards recovery of *withheld catalogue* components, which sit next to visible traces. The
leaderboard appears to reward *unmapped* faults, which the winning geometry places 1–2 km out. The instrument
therefore ranks **surfaces**, not **emission geometry**; that is exactly why geometry was frozen from the
leaderboard evidence and never tuned on this score. This limitation was already documented at S27
(“instrument-degenerate”) and is not repaired here.

---

## 4 · The candidate

| Property | Value |
|---|---|
| Name | `gems91-s28-cpt19-hgb-37654dots-20261031T010000Z-5d5f9f4d-zeros` |
| File | `docs/downloads/gems91-s28-cpt19-hgb-37654dots-20261031T010000Z-5d5f9f4d-zeros.tif` (+ `.zip`, one TIFF inside) |
| sha256 | `5d5f9f4deb543fb44e5618796571c80304abe52e8ec0555fb6582914b0d110b4` |
| Bytes | 826,646 |
| Dots | 37,654 binary `{0.0, 1.0}` |
| Median distance to catalogue | 20.01 px (2.0 km) · 82.0 % beyond 1 km |
| NN spacing | median 3.16 px, minimum 3.00 px |
| On mapped catalogue | 0 cells · outside footprint 0 cells |
| Local validator | **15 / 15 checks pass** (`vendor/gems57.validate`) |
| Uniqueness vs nine focus sites | max **38.40 %** directed 3-px overlap (GEMSDOE27) |
| Uniqueness vs 208 local priors | max **66.39 %** (S27-FABRIC-FAR), 70 % stop respected |

The earlier portal error (`Predicted values must be in range [0, 1]`) cannot recur through a non-finite or
out-of-range cell: every one of the 12,279,160 cells is finite, in [0, 1], and zero outside the scored
footprint.

---

## 5 · Three passes

**Pass 1 — implement.** Restored and hash-verified the three official rasters; built the 41-layer stack
(70 s); ran E1/E2/E3 on the shared holdout; emitted, validated, packaged and registered a candidate.

**Pass 2 — review for bugs.** Fixed in this pass:
* `scripts/s28_nine_site_forensics.py` failed with `ModuleNotFoundError: vendor` — the repository's
  convention is `sys.path[:0] = [ROOT, ROOT/"src"]`; added.
* The first build reused default quotas and produced median 21.2 px / 85 % beyond 1 km / NN 4.12 px — outside
  the evidence envelope. Re-emitted with the tuned quotas and a 3-cell blocking radius to land on
  20.01 px / 82.0 % / 3.16 px.
* Uniqueness script counted the lane's own superseded variant as a “prior” (90.4 % overlap). The superseded
  TIF and ZIP were deleted so exactly one candidate exists, and the report now names the strongest genuine
  prior.
* `LogisticRegression(n_jobs=1)` emitted a deprecation warning under scikit-learn 1.9.1; harmless but noisy,
  suppressed in runs and noted here.
* `s28_report.py` first crashed on a key name (`frac_gt10px` vs `frac_gt10`); the renderer now reads the key
  the forensics script actually writes.

**Pass 3 — re-check against the request.** Verified line by line that every number in the executive summary
is read from a JSON artifact rather than typed; re-ran the validator on the final bytes; re-computed the
overlap matrix; confirmed the claimed Spearman/Pearson values by re-running them; confirmed the metric
algebra numbers (5,469 / 36.0 % / 0.772) by recomputing from the formula; and confirmed that no score in the
documents is presented without an evidence class.

---

## 6 · Sources and evidence classes

| Claim | Source | Class |
|---|---|---|
| Grid, CRS, shape, transform, footprint, catalogue count | bytes in `data/official/` this session | VERIFIED-FROM-BYTES |
| Official input identity | pins in `registry/data_manifest.json` | VERIFIED (pin match) |
| Metric formula (α 0.2, β 0.8, 300 m) | `vendor/gems57/metric.py` transcription of rules PDF <https://docs.nlr.gov/docs/fy26osti/96647.pdf> | TRANSCRIBED (not re-fetched; IR-S28-05) |
| Nine-site scores 0.2449–0.2778 | owner score pages, as recorded in `docs/review-20261030/nine-site-snapshot.json` | USER-REPORTED, no organizer receipt |
| Nine-site geometry | recomputed this session | VERIFIED-FROM-BYTES |
| Holdout DTIs | `docs/s28/holdout.json` | HOLDOUT-DTI (instrument-class) |
| 112-anchor score model | `docs/lfi/anchors.json` re-fit this session | MODEL on USER-REPORTED anchors |
| Leaderboard projection 0.27–0.30 | this review | **MODEL PROJECTION, NOT A SCORE** |

Reference links used: [competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) ·
[problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ·
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) ·
[reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) ·
[GeoDAWN data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) ·
[INGENIOUS](https://gbcge.org/current-projects/ingenious/) · [EPSG:32611](https://epsg.io/32611) ·
[Tversky index](https://en.wikipedia.org/wiki/Tversky_index) ·
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).

The reference-solution notebook was cloned and read this session; it confirms the *task shape* (19-band
float stack → single-band float prediction on the same grid, Tversky **loss** with α = 0.2 / β = 0.8, resnet18
U-Net, 128-px patches) but it does **not** publish the scoring kernel, the hidden truth, or any leaderboard
value. It was not executable here (no GPU; training 5 × 5 epochs is out of scope for a 2-hour CPU budget).

---

## 7 · Limitations and what to do next

1. **Hidden truth is unobservable.** Every holdout number is a catalogue-recovery proxy. The projection band
   assumes hidden faults resemble mapped ones in signature space.
2. **Consensus is the strongest and least auditable lever.** `frac_on_net15` (r = 0.82 with live score) has no
   documented recipe. Reconstructing it reproducibly is the single highest-value next task — with the caveat
   that it walks straight at the 70 % duplicate stop.
3. **One slot, one shot.** If a second opinion is wanted before spending the weekly slot, H2
   (structure-tensor coherence) costs ~10 minutes on the same instrument.
4. **No GPU.** A U-Net trained with the organizers' own Tversky loss on the restored 19-band stack is the
   highest-ceiling approach and remains unimplemented here purely for compute reasons.
5. **Rights/terms of the GitHub mirrors remain unresolved** (IR-91-09 in the prior record). This session used
   them to reproduce pinned hashes; that is not a legal determination.
