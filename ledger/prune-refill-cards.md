# Mechanism cards — fixed-count PRUNE / H19-cover, 2026-10-23

Audience: a structural geologist. Parent R0 is `h33-h33-2-b2` (37,654 unit dots;
0.2778 is **CLAIM**, not a receipt). Both R0 encodings were independently rebuilt
byte for byte before these experiments. Predictions below are **MODEL**, never scores.

## Shared design and limits

R0 has 2,171 dots at `2 < d_catalogue <= 3 px`; only PRUNE is exempt from the brief's
3 px collar. Each variant removes one discrete distance shell set and restores exactly
37,654 dots from the pinned H19-5 binary ridge support outside the same collar. The
refill is deterministic exact iterative marginal-DTI coverage on that **parent-lineage
routing support**. H19-5 is not new-fault truth, and the objective's absolute value is
not a competition score.

Preserving d2.8 during refill was tested and was infeasible even for the smallest dose
(722 legal cells for 941 removals). The recorded no-inhibition PRUNE refill is therefore
used. This is not a separate spacing optimization, but the resulting spacing drift is a
real confound and is reported on every card. The code and predictions were frozen before
any PROXY or SGMC result was computed.

The catalogue PROXY uses 10 spatial-block draws, each withholding 12,198–12,207 known
positives. R0 mean credit is 0.006119 (95% CI 0.005961–0.006277). The variants are
0.001142 (0.001108–0.001177), 0.000000 (0–0), and 0.000000 (0–0), respectively. This
near-mechanical loss of catalogue-collar credit is **PROXY only**: known pixels are
masked live, so it cannot adjudicate the predictions. SGMC-off-catalogue control means
(n = 62,122) are R0 0.088819; variants 0.089124, 0.089101, and 0.085507. Also report-only.
Organizer context: <https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516>
and <https://community.drivendata.org/t/where-do-you-draw-the-line/11536>.

## 1. `PRUNEp2p5h19cover` — `e6f2000d`

- **Hypothesis.** The 941 dots in the 2.236 px (224 m) shell are still dominated by
  immediate-flank duplicates or potential-field side lobes of mapped traces. Moving that
  small dose onto uncovered H19-5 ridges will help more than it loses.
- **Mechanism.** Remove only `d_cat = sqrt(5)` dots; refill 941 cells at `d_cat > 2.5 px`
  by exact marginal coverage. Count is fixed. Added dots have minimum/mean catalogue
  distance 2.828/3.076 px. This changes 2.499070% of R0's dots (5.0% symmetric difference).
- **Non-fault process / confound.** Magnetic or gravity side lobes, pediment and alluvial
  fan margins can parallel a mapped range front without fault slip. Conversely, a genuine
  antithetic splay can sit at 224 m. Mean nearest-neighbour distance changes 3.735 → 3.700
  px and 176 dots acquire a neighbour <2 px, so a result is not purely attributable to collar.
- **Predicted live change.** **+0.002 MODEL**, range −0.006 to +0.010. It is expected to
  fall inside the brief's no-evidence band.
- **Falsifier.** A receipt ≤ −0.01 versus R0 says the immediate flank carried real new-fault
  credit; stop escalating PRUNE. A change within ±0.01 is no evidence. ≥ +0.01 justifies the
  2.9 px dose, not a claim about private chunks.

## 2. `PRUNEp2p9h19cover` — `9829bb66`

- **Hypothesis.** Adding the 670 dots at 2.828 px to the same treatment should capture the
  remainder of the beneficial below-3 px collar before the already-built 3 px experiments.
- **Mechanism.** Remove 1,611 dots at `d_cat <= 2.9 px`; refill exactly 1,611 outside 2.9 px.
  This changes 4.278430% of R0. Added-dot minimum/mean catalogue distance is 3.0/8.893 px.
- **Non-fault process / confound.** The same side-lobe and pediment mimics apply, but real
  relay splays become more plausible as the collar widens. Mean nearest-neighbour distance
  falls to 3.631 px and 830 dots have a neighbour <2 px; refill arrangement is a larger
  confound than in card 1. The catalogue PROXY and canary credit class are mechanically zero,
  so their null AUC is not evidence of safety or success.
- **Predicted live change.** **+0.004 MODEL**, range −0.005 to +0.013.
- **Falsifier.** A receipt ≤ −0.01 rejects the below-3 px mechanism. If p2.9 does not improve
  on p2.5 by at least 0.01, there is no resolved dose-response; do not infer one from two flat
  public-chunk results.

## 3. `PRUNEp4p5h19cover` — `691438f8`

- **Hypothesis.** Beyond the existing 4.3 px model bracket, genuine secondary splays and
  relay geometry should dominate any benefit from removing false catalogue-adjacent lineaments.
  This is an upper falsification bracket, not the preferred winner candidate.
- **Mechanism.** Remove 4,848 dots through 4.472 px and refill all 4,848 strictly beyond 4.5 px.
  This changes 12.875126% of R0. Added-dot minimum/mean catalogue distance is 5.0/26.485 px.
- **Non-fault process / confound.** Long-wavelength geophysical edges and basin/piedmont
  boundaries can supply convincing non-fault refill ridges. Mean nearest-neighbour distance
  falls sharply to 3.266 px; 4,594 dots have a neighbour <2 px. Apparent structural coverage
  can therefore be clustering of model support rather than newly detected faults. The SGMC
  control decline is consistent with caution but was not used to set the prediction.
- **Predicted live change.** **−0.015 MODEL**, range −0.030 to +0.003.
- **Falsifier.** A receipt ≥ +0.01 rejects the predicted loss and would justify investigating
  far-field unmapped geometry. A receipt ≤ −0.01 confirms that wide collars destroy useful
  credit; retire them. Within ±0.01, the result is inconclusive and the file is not a winner.

GeoDAWN positional-uncertainty context (not target evidence):
<https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7>.
