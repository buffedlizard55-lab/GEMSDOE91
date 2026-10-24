# Mechanism cards — SPACING/redcov (session 8, `arena/ed1ccddf-gemsdoe91`, 2026-10-24)

Written for a structural geologist. Parent for every card: **R0 = `h33-h33-2-b2`**
(37,654 unit-mass dots, sha256 `baeae321…c77dd`, rebuilt byte-exact from both pinned
ancestors this session before any variant was built; live 0.2778 remains **CLAIM**, no
receipt in `ledger/`). All predicted changes are **MODEL**; all SGMC numbers are
**PROXY** (report-only control: the independent off-catalogue USGS SGMC fault map,
[USGS DS-1052](https://pubs.usgs.gov/ds/1052/), 62,122 px at d_cat > 3 px). A live
change under 0.01 is no evidence. Full numbers: `evidence/redcov_axis_20261024.json`.

## The shared change (one axis: SPACING, matched count)

R0's dots are not spread over the ground its own lineage flagged as faulted — they
bunch. 11,415 of 37,654 dots have a neighbour closer than 2.83 px, i.e. inside each
other's 300 m DTI kernel. Because DTI credits each truth pixel with the *maximum*
kernel weight over dots, the second and third dot stacked on the same fault segment
add almost no `T` while still paying full mass in `S`. At the same time, large areas
that the lineage fields (H19-5/H19-4/H16-1) support have no dot within kernel range
at all, because the d2.8 thinning that made R0 discarded field pixels on a *spacing*
rule, not a score rule. redcov moves dots from the first population to the second:

- **Donors** — off-collar dots with the highest kernel-overlap redundancy
  `Σ_{0<d<6px}(1 − d/6)` (median donor redundancy 1.73; the best dot kept scores
  1.53). Pure parent geometry: no label, no feature band is read.
- **Recipients** — lineage-supported cells furthest from any surviving dot
  (redcov10: median 6.4 px, minimum 4.5 px to the nearest survivor), placed at
  ≥ 2.8 px spacing, all at d_cat > 3 px. R0's 2,171 inherited collar dots
  (2 < d_cat ≤ 3 px) are quarantined untouched (IR-91-27), so no arm is secretly a
  PRUNE. Donor cells may not be refilled.
- Count fixed at 37,654; zero catalogue mass; 1 km block-density CV falls
  0.619 → 0.556 (into the 0.51–0.59 band reported for the best historical files);
  mean nearest-neighbour distance rises 3.74 → 4.07 px.

**Hypothesis.** At fixed dot count, DTI is limited by *covered fault length*, not by
dots per segment: converting kernel-duplicated dots into dots on supported but
uncovered ground raises `T` at constant `S`, so the denominator cannot grow.

**Mechanism.** For line-like truth, a truth pixel earns credit once (max over dots).
A donor dot whose 3 px disk is already covered by two neighbours earns ~0 marginal
credit on almost any continuation of the local fault, while a recipient dot ≥ 4.5 px
from every other dot owns its whole disk: any new-fault pixel inside it converts from
0 to triangular credit. On the SGMC control this is not a precision argument but an
exact-metric one: `T` rises 7.7 % (redcov10) at constant `S` — and a live +0.01 needs
Δ*T*/*T* ≈ +3.6 % at fixed count.

**The non-fault process that could mimic it.** Survey and thinning geometry, in two
forms. (a) Recipient cells are far from dots partly because they sit on single-field
H19-5 support (2,444 of 3,765 redcov10 recipients are vote-1): if those cells are
flight-line or processing artefacts of one interpretation rather than thinned real
lineaments, coverage buys noise. (b) The SGMC map is a *mapped-fault* population
with long continuous traces; a coverage strategy is flattered by any truth set with
more total fault length than the live new-fault set. If live truth is shorter and
concentrated exactly where R0 already clusters (well-imaged range fronts), the same
move dilutes. The prediction therefore carries the fleet's 0.5 surrogate shrink plus
a widened downside for having selected this family by screening (IR-91-34).

**Falsifier (applies to all three arms).** redcov10 receipts ≤ 0.000 against a
receipted R0 anchor while its measured geometry moved as designed (CV 0.556, mean NN
4.07 px) ⇒ kernel-duplicated dots were *not* wasted — live new-fault truth really is
concentrated on the segments R0 over-samples — and the coverage family (including
the unbuilt proposals in `SLOT_PLAN.md`) is retired. The already-built sign flip
`SPACING/clump40` then becomes the interesting file. Receipt ≥ +0.010 ⇒ fault-length
coverage is the binding constraint and the 20 % dose is the next bracket.

## redcov10 — base arm (`…-SPACINGredcov10-20261024-8113d448`)

3,765 dots moved (10.00 % relocated, 20.00 % symmetric diff). Recipients: vote ≥ 1,
median d_cat 23.3 px (donors 22.8 px — the axis is *not* a catalogue-distance play in
either direction). **Predicted +0.011 MODEL `[−0.003, +0.021]`** from exact SGMC
Δ*T*/*T* = +7.69 % (ΔDTI_SGMC +0.00720 PROXY) × 0.2778 CLAIM × 0.5 shrink.
Relation to fleet: its donors are 84 % the same dots `SPACING/spread40` chose to
move — but spread40 nudged them ≤ 2.24 px, leaving them inside the same kernel
neighbourhood (recipient overlap 8/3,765). redcov10 is that diagnosis executed at
the scale the metric actually pays for. **This is the slot candidate.**

## redcov20 — dose arm (`…-SPACINGredcov20-20261024-191caf71`)

7,531 dots moved (20.00 %; donors a superset of redcov10's, recipients 93 % shared —
one dose ladder, not two experiments). **Predicted +0.013 MODEL `[−0.002, +0.026]`**
(relT +9.19 % PROXY). The screened response flattens hard: doubling the dose buys
+1.5 points of relT as recipients are forced closer to survivors (median 5.1 px) and
deeper into vote-1 support (3,751/7,531). Do not spend a slot on it unless redcov10
receipts ≥ +0.010; it then tests whether the coverage returns keep scaling or the
10 % arm already harvested them.

## redcov10v2 — support bracket (`…-SPACINGredcov10v2-20261024-9ae05686`)

Same donors, recipients restricted to ≥ 2-field support. **Predicted +0.006 MODEL
`[−0.005, +0.012]`** (relT +4.24 % PROXY) — *worse* than redcov10 on the control,
because strongly supported cells live nearer existing dots (median 4.1 px), so
restricting to them trades away the coverage that does the work. It exists to
decompose the mechanism if redcov10 receipts near zero: redcov10v2 > redcov10 live
would mean support strength, not uncovered distance, was the active ingredient, and
the vote-1 recipient population is artefact. Not a first slot.

## Report-only instruments (never gates, never scores)

Catalogue hide-and-recover PROXY is **identical** for R0 and all arms (0.006186,
5 draws, 12,198–12,201 withheld positives/draw, 95 % CI [0.005958, 0.006413]) by
construction — every donor and recipient is > 3 px from the catalogue (IR-91-28
pattern). Leakage canaries: lineage-vote ring AUC 0.5257; moved-dot canary AUC
0.40–0.45; both far below the 0.90 stop. Why MASS was *not* this session's axis
(every constructible ranking's bottom decile sits within ~2 points of the 11.8 %
break-even precision, IR-91-33) and the full screen log behind the axis choice
(IR-91-34) are in `IRREGULARITIES.md` and the evidence JSON.
