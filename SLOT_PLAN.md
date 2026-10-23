# SLOT PLAN — merged across the three 2026-10-23 sessions

**Parent R0** `h33-h33-2-b2`: 37,654 unit-mass dots, 2.236 px catalogue floor. R0's `0.2778` is a
**CLAIM** — 38 ledger rows, **0 receipts**, no live effect has ever been measured in this lineage.

**The board: 18 release pairs, 36 files, all gate-clean, all byte-reproducible in one command**
(`make releases` → `manifest: 36 files, 0 problem(s)`), every hash cross-checked against the
ledger. Four axes: PRUNE delete-only (6), PRUNE refill-held (3), CONCENTRATION on the public-domain
GDR thermal prior (3), SPACING (3), RELIEF (3).

| axis | arms | best MODEL prediction | what it varies |
|---|---|---|---|
| CONCENTRATION (GDR prior) | `gdr25rm10`, `gdr25m10`, `gdr10m10` | **+0.0123** [−0.022, +0.037] | *where* mass sits, using a prior independent of the catalogue |
| PRUNE delete-only | `le3/le4/le5/le8/le10/le15` | **+0.010** [−0.008, +0.024] | how much collar mass is removed |
| PRUNE refill-held | `p2.5px`, `p2.9px`, `p4.5px` h19cover | +0.004 … **−0.015** | delete *and* refill from the H19-5 coverage |
| SPACING | `spread40`, `clump40`, `jitter40` | +0.004 [−0.004, +0.012] | arrangement at fixed count |
| RELIEF | `r2m15`, `m2r15`, `null15` | +0.007 (≡0 against its own null) | which relief tercile holds the mass |

## What the cross-check adds (IR-91-21, IR-91-22)

Scored against the only truth visible from this sandbox — the 60,988-cell catalogue — with the
metric split into credit `T` and unmatched mass (`evidence/predictions_crosscheck_20261023.json`):

| file | `dti_proxy` | Δ vs R0 | what it means |
|---|---:|---:|---|
| R0 (parent) | 0.006778 | — | 100 % of `T` comes from **1,611 dots inside 3 px** of a mapped trace |
| `SPACINGspread40` | 0.007861 | **+0.001083** | the only shipped arm that *raises* measurable credit |
| `SPACINGjitter40` | 0.006761 | −0.000017 | null, as designed |
| `CONCENTRATIONgdr25rm10` | 0.005937 | −0.000841 | the three prior arms agree to 6·10⁻⁶ |
| `RELIEFr2m15` | 0.005888 | −0.000890 | arm order matches the mechanism cards |
| `PRUNEp2.5pxh19cover` | 0.001242 | −0.005536 | refill keeps a little collar credit |
| every delete-only PRUNE dose | 0.000000 | **−0.006778** | all six delete the entire credit-carrying band |

Three consequences, and they are the only places where this instrument overrules the MODEL:

1. The six delete-only doses are **one experiment on one coin**, not a dose-response: they all
   delete the 0–3 px band, so they lose the same credit and differ only in how much extra mass
   they remove. One receipt on the top dose answers the family; a second dose only refines *how
   much* was wasted.
2. Break-even for deleting a dot is **0.044 credit** (at the claimed 0.2778 and the parent's own
   collar geometry); the collar dots measure 0.237. The ladder is therefore a bet that the
   organisers' *unmapped* faults are nowhere near the parent's dots — untestable here, and the
   first receipt must be read that way.
3. Where the MODEL's two top candidates are within 0.002 of each other, prefer the one this
   instrument does **not** penalise. `SPACINGspread40` is currently the only such file.

## Next three scored slots, in order

| # | candidate (file in `releases/`) | MODEL | why this slot |
|---|---|---|---|
| 1 | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` | **+0.0123** [−0.022, +0.037] | The only file whose input is independent of both the catalogue and the lineage mask: if the prior transfers, this is a new source of location information, not a re-cut of the same one. Highest MODEL on the board, and its floor is *measured* (lineage coverage 88.6 % → 80.2 % ⇒ −0.022), not a formality. |
| 2 | `…-PRUNEle15-norefill-20261023-1ca1ff6f.tif` | **+0.010** [−0.008, +0.024] | Independent of slot 1 (mass vs location). The top of the delete-only ladder, so it answers the whole family in one slot, and it is byte-reproducible here. |
| 3 | **Conditional** — see the fork | — | Turns two points into a direction, or retires an axis. |

**Do not** spend a slot on `gdr10m10`, `le4`, `le5`, `le8` or `le10` before slots 1–2 return:
each is a notch inside a question those two slots answer in full. **Do not** spend a slot on the
three RELIEF arms: ±0.007 each, interpretable only as a *pair*, so two slots for one bit.
**Do not** repeat a file whose sha256 is already in the ledger.

## The fork, written before any receipt arrives

| slot-1 / slot-2 result | reading | slot 3 |
|---|---|---|
| `gdr25rm10` **≥ +0.01** | the thermal prior transfers | `gdr25m10` (does a wider prior help?) or build `w20` = 20 % dose as a new pair |
| `gdr25rm10` **≤ −0.01** | the lineage mask carries real recall; prior-chasing is wrong here | stop CONCENTRATION; `PRUNEle10` if slot 2 said mass is the lever, else `SPACINGspread40` |
| `le15` **≥ +0.01** | mass far from mapped traces is wasted | `le10` for the dose shape, or combine: PRUNE dose + the better CONCENTRATION arm in one file |
| `le15` **≤ −0.01** | the 3 px halo carries truth; the 300 m clause is about *their* mapping, not the metric | no deeper prune; build the **add-in-collar** arm (3–8 px) and spend slot 3 on it |
| either **\|Δ\| < 0.01** | **no evidence** (the brief's rule) — not "neutral" | `SPACINGspread40` if it is not already spent (the only proxy-positive file), else hold the slot |

Whatever the outcome: paste `receipt_score` + `receipt_date` into `ledger/submissions.csv` against
the row whose `id` carries the sha8, set `status=SUBMITTED`, never overwrite `predicted_change`.

## Weeks to the deadline (2026-12-03, still unconfirmed by a human)

- **Wk 1 (now):** slot 1 = `gdr25rm10`, slot 2 = `le15`. Read both against the fork table the same day.
- **Wk 2:** slot 3 per the fork. If both came back inside ±0.01, spend nothing on refinements —
  bank the best receipt and only build if the fork says a direction is live.
- **Wk 3–4:** combine the two winners into **one** file (a new `(parent, axis, value)` triple, so
  the ledger stays honest). PRUNE dose + `spread40` is the cheapest combination: arrangement does
  not change which cells exist near the collar.
- **Wk 5–6 (by 2026-12-03):** re-validate the final file from disk (`validate_raster.py` → PASS,
  `update_release_manifest.py --check` → 0 problems), ship it with its `-zeros` twin held back as
  the fallback, and make the final choice **blind**.

## What would change my mind

- **A dated leaderboard row for R0.** It settles IR-91-22 (0.2778 is 41× what the visible truth
  supports) and recalibrates every prediction in the ledger. Worth asking the human before slots
  are spent on refinements.
- **A ranking artifact for the parent's dots.** MASS (drop lowest 10 % / add next 10 % by the
  parent's own ranking) is unbuildable from this lineage — no rank is stored anywhere and its two
  thinning branches disagree about 44,461 cells (IR-91-23). A rank artifact makes the axis real.
- **Any sign that the organisers' truth extends inside 300 m of the catalogue.** That inverts
  IR-91-21 and makes every PRUNE dose a loss.

## What the human must supply

`TOP_PUBLIC` with its date · slots remaining this week · confirmation of the deadline · any
leaderboard row for R0 · the parent's ranking artifact if it exists. Do not contact
drivendata.org, the leaderboard, or dropbox.com from this repo — the human reads the numbers.
