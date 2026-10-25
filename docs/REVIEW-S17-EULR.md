# Session 17 Review — `S17-EULR` Euler Deconvolution Fusion (2026-10-25)

**Verdict: `OK TO DOWNLOAD: YES — RESEARCH` · `OK TO SUBMIT: NO` (negative result; 0 slots spent).**
Artifact: [`gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif`](downloads/gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif)
(SHA-256 `3d07dcb81f01e8b19b5fa2cf2d4d7dc75eb1f7ec2d319a120f6ba7c37bf369d2`, 235,257 B,
44,000 binary dots) · [single-TIF ZIP](downloads/gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.zip)
(SHA-256 `78ef3eab…85885`) · [run card](run-card-S17-EULR.json) ·
[preregistration](HYPOTHESES_S17.md) (SHA-256 `34434194…c6a6`, frozen before any fit).
Submission name (records only): `GEMS91-S17-EULR-E3-f2ac27d7` · note (79/140):
`S17-EULR E3: Euler deconv fusion; HOLDOUT-DTI=0.2496; 44000 dots; HOLD selector`.

Every number below is labelled per Protocol Rule 3. `HOLDOUT-DTI` = internal
hide-and-recover estimate (evaluator `gems91-hide-recover-v1.0`, split
`0f874367…`, 60,988 withheld catalogue pixels); it is **not** a leaderboard
score or projection. Fleet scores are `CLAIM` (user-reported, no organizer
receipt in this repo). The public leaderboard value is `ORGANIZER-PAGE-READ`
(fetched 2026-10-25). No file from this project has an `ORGANIZER-CONFIRMED`
score.

---

## 1. Why 0.2778 (`h33-h33-2-b2`) led the fleet — verified post-mortem

### 1.1 Evidence status of the target numbers
| Number | Label | Basis |
|---|---|---|
| 0.2778 for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (GEMSDOE32) | **CLAIM — user-reported** | `docs/reported-results.csv`; GEMSDOE32's own page states no organizer score exists in-repo (pinned audit `docs/s16/gems32-forensics.json`). No submission-page receipt exists anywhere in this checkout. |
| 0.4413 public #1 (`xiaofanhu`, 30 submissions); #2 0.3916 | **ORGANIZER-PAGE-READ** | Read directly from the DrivenData leaderboard page on 2026-10-25. Authenticates the public board only, never any fleet file. The brief's “0.3195 high” is stale (would rank below #20 on the same read). |
| Metric: distance-weighted Tversky α=0.2, β=0.8, triangular kernel R=300 m | **ORGANIZER DOCUMENTED + byte-verified locally** | Problem page (fetched 2026-10-25); `scripts/dti.py` implements `DTI = T/(0.2T + 0.2(S−M) + 0.8|G|)`; grid re-verified from pinned bytes (3730×3292, EPSG:32611, transform (100,0,243350,0,−100,4508550), footprint 5,167,373 px, catalogue 60,988 px). |

### 1.2 What the winning raster actually is (recomputed from pinned bytes this session)
All 15 `registry/data_manifest.json` inputs were restored and SHA-256-verified
(`scripts/restore_data.py`). On those bytes, `h33-h33-2-b2-zeros` (37,654 dots)
is **exactly** the earlier `solo-d2.8` raster (40,199 dots) minus the 2,545 dots
within 2 px of the catalogue — 0 added, 0 moved. Dot geometry: min catalogue
distance 2.236 px, 69.8% of dots >10 px from any catalogue pixel, median
nearest-neighbour spacing 3.0 px (min 2.828), zero mass on catalogue pixels.

### 1.3 Mechanism (why the chain 0.1922 → 0.2778 CLAIM is mechanically coherent)
The scoring kernel gives each truth pixel credit equal to the **maximum**
kernel-weighted prediction within 300 m (3 px). Two consequences:
1. **Redundant mass is pure cost.** A second dot within 3 px of an existing dot
   adds ≈0 to the max-credit term `T`/`M` but fully increases the penalty
   `α(S−M)`. Solid/dense rasters (121k px, 0.1922 CLAIM) therefore lose to
   thinned ones (1.5 px spacing 0.2477 → 2.8 px 0.2600 → solo-pruned 0.2708).
2. **Near-catalogue dots cannot be paid.** Catalogue pixels are masked out of
   the hidden truth; dots ≤2 px from the catalogue mostly spend their 300 m
   kernel on already-known faults. Deleting them (the “B2” step, −2,545 dots)
   raised credit-per-dot again (0.2708 → 0.2778 CLAIM).
Each step removed dots, i.e. the progression is an **emission-geometry**
optimization on one fixed ranking surface (H19-5 lineage), stopping where the
marginal dot's expected credit ≈ its α-cost (break-even ≈ α·DTI ≈ 0.056).

### 1.4 Can it be beaten? (judgement, labelled MODEL)
The 0.2778 raster is **surface-limited, not packing-limited**: an independent
surface family (GEMSDOE36 Anderson PINN, 38,854 dots) plateaued at 0.275 CLAIM,
the same band. Further thinning/pruning of similar surfaces has no headroom —
the remaining error is *which* pixels are ranked top, i.e. faults the
exposed-scarp/geophysics-edge lineage ranks low. Beating 0.2778 — and
approaching the verified public 0.4413 — requires a materially better ranking
of **concealed** faults, which is precisely what Session 17 tested and what the
ranked untried hypotheses in §5 target. Whether any specific file beats 0.2778
live can only be settled by an organizer receipt, which this session does not
have and does not simulate.

---

## 2. What Session 17 did (preregistered, then executed exactly)

**Hypothesis H17-1:** windowed Euler deconvolution extracts buried-contact
*geometry* (3-D source position/depth from gradient ratios) that is
independent of anomaly *amplitude*, complementing this repo's amplitude-scaled
edge detectors and normal-throw concordance features — potentially ranking
concealed/lateral faults (catalogue-missing) higher. Named mimics: unfaulted
lithologic contacts (Euler-equivalent), volcanic plugs, flight-line seams.

**Method (`src/gems91/eulr17.py`, frozen in `docs/HYPOTHESES_S17.md`):** 11×11 px
least-squares Euler solutions at structural indices 0/1 for magnetics
(B14 field, B09×100 vertical derivative — verified `dz(B14)` in nT/m,
r=+0.98919) and gravity (B13 field, FFT `|k|` vertical derivative — B11/B18
were re-measured as *horizontal* components, r≈0.94/0.96 vs `dy`/`dx(B13)`,
and not used as vertical derivatives). Acceptance: ≥8 px from invalid data,
amplitude ≥40th percentile, depth 0.5–25 px, |offset|≤8 px, relative depth
uncertainty ≤0.20. Fourteen label-free features (density/depth/uncertainty ×
{mag0,mag1,grav0,grav1} + joint density + mag0-depth vs B15 agreement) feed the
unchanged shared learner/emitters. Solver correctness was established *before*
real-data use by unit tests (`tests/test_eulr17.py`): fast box-filter solver ≡
brute-force per-window solver, and exact recovery of known (x0,y0,d) on
Euler-homogeneous synthetic fields. Accepted solutions on real data:
mag0 1,237,163 (median depth 2.48 px ≈ 248 m), mag1 2,431,521 (4.82 px),
grav0 660,981 (8.11 px), grav1 278,764 (12.49 px) — physically ordered.

**Experiments (3 maximum, single-change ablation; 2,931.6 s ≤ 7,200 s budget):**
E1 = exact S13 recipe (75 features, corridor emission); E2 = E1 + 14 Euler
features (89, otherwise identical); E3 = Dinkelbach emission on the better OOF
(frozen S13 rule). Leakage canary over all 89 features before any fit: PASS
(worst symmetric AUC 0.665, existing `ptha_step_elev_abs`; Euler features
0.51–0.57). Pre-placement surface uniqueness vs 85 hash-distinct registry
rasters: PASS (E1 max |ρ| 0.1592, E2 0.1597, full-map 0.2191 — far under 0.90).

## 3. Results (all HOLDOUT-DTI, `gems91-hide-recover-v1.0`, 60,988 withheld)

| Exp | Recipe | HOLDOUT-DTI | 95% CI | Paired Δ vs E1 (5 km tiles, 400 draws) |
|---|---|---:|---|---|
| E1 | S13 ablation control (75 feat) | 0.198824 | [0.188734, 0.213287] | — (instrument check: S13-E2 corridor recorded 0.198407) |
| E2 | E1 + 14 Euler (89 feat) | 0.199155 | [0.187822, 0.211187] | **+0.000331 [−0.002264, +0.003222], P(>0)=0.60** |
| E3 | Dinkelbach on E2 OOF | **0.249626** | [0.234678, 0.264996] | +0.050802 [+0.045026, +0.056994] (emission effect) |

Per-fold E3: NW 0.219666 · NE 0.321277 · SW 0.186335 · SE 0.289112. The SW
(Walker Lane) fold remains weakest and Euler did **not** improve it
(E2 SW 0.132965 vs E1 SW 0.134492 at corridor emission) — the preregistered
SW motivation is falsified on this instrument. v1.1-nohalo receipts equal the
v1.0 values exactly (fold dots are buffer-excluded by construction; IR-S17-02).
Blind off-catalogue USGS SGMC control (independent geology, report-only):
candidate 0.100737 vs R0 0.095386 (Δ +0.005351).
Comparisons with no pairing (point-only, same evaluator/split/withheld):
E3 − S14-PTAC best (0.267782) = **−0.018156**; E3 − S13-E3 (0.244601) = +0.005025
(confounded by seeds and by E2-vs-E1 base choice; not an Euler effect — the
controlled paired E2−E1 is the Euler test and it is null).

**Registry (literal directed gate, 85 rasters, zero exemptions): FAIL.**
Dots within 3 px: synthetic lattice 99.827% (mathematically forced — its 3 px
dilation covers 99.8713% of the footprint, `docs/s16/registry-feasibility.json`),
**S13 sibling 93.836%**, S14-HVDC 91.477%, S14-PTAC 86.782%, R0 41.120%. 62/64
frozen-inventory rows byte-verified; 2 retracted-GEOD rows have no `git_blob`
pin and are recorded not-checked (IR-S17-03); `complete_universal_registry:
false`. Format: PASS on every automated suite (shared writer triple-validation,
independent gems57 suite, independent tifffile re-read: single band float32,
values exactly {0,1}, 0 NaNs, EPSG:32611 tiepoint/scale exact, ZIP single member
byte-identical). Readiness gates: format ✓, canary ✓, novelty ✗, assigned lane
✗, beats-comparable-best ✗, separate selector ✗ ⇒ `OK TO SUBMIT: NO`.

### Interpretation (MODEL judgement)
Euler adding ~nothing is geologically plausible in hindsight: with stride-1
windows and permissive (label-free) acceptance, 1.2–2.4 M magnetic solutions
cover most gradient terrain, so density largely re-encodes analytic-signal
amplitude already present in the stack, while depth/uncertainty at 100 m
sampling with 1.1 km windows are too smooth/noisy to separate faulted from
unfaulted contacts (the named mimic). The failure is informative beyond this
lane: **the entire S13-descendant family (S13/S14/S15/S17 winners) converges to
dot sets 87–94% mutually within 3 px** — incremental feature blocks on the same
stack + learner + emitter no longer produce structurally distinct candidates,
which itself blocks the fleet's literal uniqueness gate for any successor.

## 4. Irregularities flagged (not silently corrected)
- **IR-S17-01:** pinned `sample_submission.tif` is binary with 1.0 *exactly on
  the 60,988 catalogue pixels* (verified identical masks), contradicting the
  organizer text describing an all-absence sample. Used for grid/footprint
  only; its values must never be used as prediction/labels.
- **IR-S17-02:** shared `score_pooled_holdout` default flipped (S16) to
  v1.1-nohalo; S13–S15 cards are v1.0. S17 passes the argument explicitly and
  reports both (equal here) instead of editing the shared evaluator.
- **IR-S17-03:** frozen registry inventory has 2 rows without `git_blob` pins;
  `restore_registry.py` fails closed. S17 verified the 62 pinned rows by
  SHA-256 and records 2 as not-checked; the frozen file was not edited.
- Band tags B06 (radiometric TC mislabelled as tilt) and B11/B18 (horizontal
  components mislabelled as vertical/horizontal-gradient) were re-measured
  from bytes (§2); tags are never trusted over data.

## 5. Ranked untried hypotheses (from preregistration; expected gains are MODEL judgements)

| # | Hypothesis (layers) | Signature / why it catches catalogue-missing faults | Status after S17 |
|---|---|---|---|
| 1 | **Euler fusion** (B14/B09/B13/B15) | Gradient-ratio source geometry; amplitude-independent | **TESTED — null** (paired CI includes 0). Do not re-run variants without a design change (e.g. SI-clustering tightness instead of density). |
| 2 | **Dipping-contact forward-template bank** (B02/B14/B13) | Waveform *shape* match over depth×dip×strike; rejects symmetric dyke/plug anomalies | Untried; viable on pinned data; highest compute cost. Next in-lane candidate. |
| 3 | **Parker–Oldenburg basement stripping** (B13+B15) | Removes basin-fill gravity signal; intrabasement fault steps remain | Untried; viable; density-contrast/circularity care needed (B15 is gravity-informed). |
| 4 | **Fluvial χ / divide asymmetry** (absolute DEM) | Drainage reorganization precedes mappable scarps on young blind faults | **Blocked in sandbox:** needs USGS 3DEP DEM (The National Map, public domain); host unreachable from this environment (verified 2026-10-25). B12 is detrended — insufficient alone. |
| 5 | **Hypocenter planar lineations** (USGS ComCat/FDSN) | Blind seismogenic faults image at depth; B10/B16 are 15-km-smoothed densities | **Blocked in sandbox:** USGS FDSN unreachable (verified 2026-10-25); needs leakage-safe design. |

Geothermal context (why catalogue-missing faults are the prize): most Great
Basin geothermal systems are blind (no surface hot springs/fumaroles), and
favourable settings are structural — step-overs/relay ramps (~32%), fault
terminations (~25%) and intersections (~22%) of ~250 categorized systems
(Faulds & Hinz 2015). Competition labels are expert-mapped *new* faults, so a
candidate earns credit by finding real structure absent from the catalogue.
Fault predictions are **not** confirmed vents, temperatures, or resources.

## 6. Limitations, access needed, and recommended next steps
1. **No selector/weekly-cap authority** (standing): promotion needs the human
   fleet selector + authenticated DrivenData slot counter. Nothing here is
   submission-ready regardless of holdout value.
2. **Registry deadlock:** the literal ≤70%-within-3px gate is unsatisfiable at
   standard budgets while the synthetic lattice and 87–94%-overlapping siblings
   remain in scope. The fleet must either re-scope the gate (human decision —
   e.g. exclude synthetic blankets, or judge novelty vs *submitted* files only)
   or accept that no S13-family successor can ever pass. Do not weaken silently.
3. **Holdout ≠ leaderboard:** hide-and-recover rewards catalogue-style
   (exposed) faults; hidden labels are *new* faults, plausibly blinder. Prior
   sessions measured weak/negative holdout↔live rank correlation (small n).
   The SGMC blind control should accompany every future lane; it favoured S17
   slightly (+0.005 vs R0) even though the Euler ablation was null.
4. **External data (free, official; obtainability checked 2026-10-25):** USGS
   3DEP absolute DEM via The National Map TNM Access and USGS FDSN/ComCat
   hypocenters are public-domain but unreachable from this sandbox's egress
   allowlist (github/pypi/npm only). Run H17-4/H17-5 from an unrestricted host
   and hash-pin tiles/queries into `registry/data_manifest.json` before use;
   competition rules require a licence permitting challenge use + sponsor sharing.
5. **Next experiments (ranked):** (a) H17-2 dipping-contact template bank as a
   *replacement* surface family (not another block on the same stack) to break
   the 90%-overlap convergence; (b) emission-geometry novelty: optimize dots
   directly for mutual 3-px distance from *sibling* winners at fixed holdout
   (measured trade-off curve); (c) H17-3 Parker stripping; (d) H17-4/H17-5 when
   egress allows. Each still requires beating 0.267782 on `gems91-hide-recover-v1.0`
   with a paired test before any slot discussion.

## 7. Reproduction (pinned inputs; no manual steps)
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/restore_data.py            # 15 SHA-pinned inputs
.venv/bin/python scripts/run_s17_eulr_lane.py --stage all
.venv/bin/python -m pytest tests/test_eulr17.py     # solver algebra tests
.venv/bin/python scripts/check_artifact_policy.py   # 57 registered artifacts
```
Sources for manual review: competition/metric
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> ·
leaderboard <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> ·
reference solution <https://github.com/drivendataorg/gems-prize-reference-solution> ·
Reid et al. (1990) DOI 10.1190/1.1442774 · Faulds & Hinz (2015) WGC ·
GeoDAWN <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> ·
National Map <https://apps.nationalmap.gov/tnmaccess/> · USGS FDSN
<https://earthquake.usgs.gov/fdsnws/event/1/> · GDR 1391 <https://gdr.openei.org/submissions/1391>.

## 8. Run card (summary; full machine-readable card: `docs/run-card-S17-EULR.json`)
```json
{
  "lane": "S17-EULR (assigned: false; self-declared, frozen in docs/HYPOTHESES_S17.md)",
  "hypothesis": "H17-1 Euler deconvolution source-geometry fusion atop S13 stack",
  "mechanism": "Windowed Euler solutions (SI 0/1, mag+grav) -> density/depth/uncertainty features rank buried contacts independent of anomaly amplitude",
  "named_non_fault_mimic": "Unfaulted lithologic basement contacts; volcanic plugs; flight-line seams",
  "holdout_dti": {"label": "HOLDOUT-DTI", "evaluator": "gems91-hide-recover-v1.0", "value": 0.249626, "ci95": [0.234678, 0.264996], "n_withheld": 60988},
  "paired_euler_effect_e2_minus_e1": {"delta": 0.000331, "ci95": [-0.002264, 0.003222]},
  "vs_comparable_best_s14_ptac_0.267782": "point delta -0.018156 (not paired)",
  "canary": "PASS (89 features, worst symmetric AUC 0.665)",
  "registry": {"checked": 85, "surface_max_abs_rho": 0.22004, "dot_overlap_3px_max": 0.99827, "closest_real": "S13 sibling 0.93836", "gate": "FAIL"},
  "raster_sha256": "3d07dcb81f01e8b19b5fa2cf2d4d7dc75eb1f7ec2d319a120f6ba7c37bf369d2",
  "validator": "PASS (no NaN anywhere in zeros twin; values {0,1} in [0,1]; CRS/shape/transform match; gems57 independent PASS)",
  "submission": {"name": "GEMS91-S17-EULR-E3-f2ac27d7", "note": "S17-EULR E3: Euler deconv fusion; HOLDOUT-DTI=0.2496; 44000 dots; HOLD selector"},
  "verdict": "negative — OK TO DOWNLOAD: YES (research); OK TO SUBMIT: NO; slots_used: 0"
}
```
