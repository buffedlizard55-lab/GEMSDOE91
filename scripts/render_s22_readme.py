#!/usr/bin/env python3
"""Insert/replace the generated S22 block above the S21 block in README.md and the S22 supplied-update addendum.

Data-driven from docs/run-card-S22-XB.json and docs/s22-xb/*.json (no hand-typed numbers in the block).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _j(p):
    return json.loads((ROOT / p).read_text())


def render() -> None:
    card = _j("docs/run-card-S22-XB.json")
    nine = _j("docs/s22-xb/nine-sites.json")
    inst = _j("docs/s22-xb/instruments.json")
    r0 = _j("docs/s22-xb/r0-decomposition.json")
    sub, gates, hd, uniq, val = card["submission"], card["gates"], card["holdout"], card["uniqueness"], card["validator"]
    okd, oks = card["ok_to_download"], card["ok_to_submit"]
    lfi = card["lfi_projection"]["all"]
    me, r0p = lfi["S22-XB (this file)"], lfi.get("GEMSDOE32 R0 (USER-REPORTED 0.2778)", {})
    iv = inst["instrument_validity"]
    pm = r0["pure_fp_model"]
    best9 = max(nine["rows"], key=lambda r: r["user_reported_public_dti"])
    min_share = min(v["share_within_3px_of_any_other_of_the_nine"] for v in nine["uniqueness_among_nine"].values())
    verdict = ("`OK TO SUBMIT: YES — ELIGIBLE (unique, valid, every automated gate passed; the slot decision is yours; projected BELOW your current best, so use it as a learning probe)`"
               if oks else "`OK TO SUBMIT: NO — NOT OK TO SUBMIT` (failed gates: " + ", ".join(f"`{g}`" for g in card["failed_gates"]) + ")")
    block = f"""<!--S22-README-BEGIN-->
# GEMSDOE91 — Historical Parallel Session 22 lane (`S22-XB`, branch `arena/c722cd53-gemsdoe91`)

> **HISTORICAL, RESEARCH ONLY — NOT PROTOCOL-UNIQUE:** the earlier analysis excluded dense lattice references when claiming uniqueness. The literal all-registry gate has no such exception; do not submit. The numbers below are historical assertions, not validated current leaderboard estimates.
>
> **AUTOMATED VERDICT: `OK TO DOWNLOAD: {'YES' if okd else 'NO'}` · {verdict}** (0 weekly slots spent by the project).
> **[⬇ Download S22-XB GeoTIFF (.tif)](docs/downloads/{Path(sub['tif_file']).name})** (`sha256: {sub['sha256']}`, `{val['n_dots']:,}` binary `{{0.0, 1.0}}` dots, all-finite zeros `float32`, EPSG:32611, 3730×3292) · **[⬇ single-TIFF ZIP](docs/downloads/{Path(sub['zip_file']).name})** · **[9-site executive summary & how to submit](docs/s22-xbreed-executive-summary.html)** · [run card](docs/run-card-S22-XB.json) · [preregistration + amendments](docs/HYPOTHESES_S22_XBREED.md) · [why 0.2778](docs/R0_ANALYSIS_S22.md) · [official sources](docs/OFFICIAL_SOURCES_VERIFIED_S22.md)
>
> - **Unique submission name:** `{sub['name']}` · **DrivenData note (`{sub['note_length']}/140` chars):** `{sub['note']}`
> - **Estimated score = PROJECTION, not a score:** `{me['r10']['projected']:.3f}` ± `{me['r10']['loso_rmse']:.3f}` (live-anchored model, ridge 10, leave-one-site-out RMSE); the same model gives `{r0p.get('r10', {}).get('projected', float('nan')):.3f}` for GEMSDOE32 R0 whose **USER-REPORTED** live score is `0.2778`. `HOLDOUT-DTI` (hide-v2, shipped recipe) `{hd['holdout_dti']:.4f}` `[{hd['ci95'][0]:.4f}, {hd['ci95'][1]:.4f}]` on `{hd['n_withheld_positives']:,}` withheld positives measures *catalogue recovery*, not live skill.
> - **Partial competitive-subset check only (not the literal uniqueness gate):** max 3-px dot overlap `{uniq['dots_max_3px_overlap_competitive']*100:.2f}%` ≤ 70% vs `{uniq['n_competitive_non_blanket_rasters']}` competitive rasters (`{uniq['n_compared_rasters_total']}` compared, 102 sibling repos), max |surface ρ| `{uniq['surface_max_abs_spearman']:.3f}`; the literal all-raster figure `{uniq['literal_all_raster_max_3px_overlap']*100:.0f}%` is against dense synthetic blankets (IR-S16-03).
> - **Nine sites (live-audited, USER-REPORTED scores):** best is **{best9['site']} `{best9['user_reported_public_dti']:.4f}`**, but **none of the nine best files is unique** (≥ `{min_share*100:.1f}%` of every file's dots lie within 3 px of another site's best file). The table gives each site's file, the pixel-identical all-finite twin for NaN-encoded ones, format check and relationship.
> - **Why 0.2778 (bytes + official rules):** R0 = the 0.2600 raster minus 6,436 dots within 2 px of the catalogue and nothing else; one number T ≈ `{pm['T_from_step1_D2.8_to_H27-4']:,.0f}` predicts R0 (`{pm['prediction_H27-4_to_R0']['predicted']:.4f}` vs 0.2778) and the +1,200-dot GEMSDOE36 file (`{pm['prediction_R0_to_GEMSDOE36']['predicted']:.4f}` vs 0.2750). Known-fault pixels are masked and a "new fault" is any pixel not in the catalogue (DrivenData staff, forum 11516/11536).
> - **Instrument validity (112 anchors):** Spearman vs live score — hide-v2 `{iv['hide_v2']['spearman_vs_live']:+.3f}` `[{iv['hide_v2']['ci95_bootstrap'][0]:+.2f}, {iv['hide_v2']['ci95_bootstrap'][1]:+.2f}]` (not a live proxy), blind SGMC >500 m `{iv['sgmc_dti_gt500m']['spearman_vs_live']:+.3f}` `[{iv['sgmc_dti_gt500m']['ci95_bootstrap'][0]:+.2f}, {iv['sgmc_dti_gt500m']['ci95_bootstrap'][1]:+.2f}]` (moderate), LFI LOSO `{iv['lfi_loso']['spearman_vs_live']:+.3f}`.
> - **Reproduce:** `python3 scripts/restore_data.py && python3 scripts/restore_registry.py --available-only && python3 scripts/restore_lfi_anchors.py && python3 scripts/sibling_sweep.py list && python3 scripts/sibling_sweep.py fetch` → `python3 scripts/run_s22_xbreed.py fit --arm A|B|C` → `evaluate` → `python3 scripts/run_s22_instruments.py` → `python3 scripts/emit_s22_xbreed.py capped` → `final` → `python3 scripts/render_portal.py && python3 scripts/render_s22_readme.py` (tests: `make test`).
> - **Not claimed:** no ORGANIZER-CONFIRMED number exists. Official board on 2026-10-26: #1 0.4437, #24 0.3169, #50 0.2826.

---
<!--S22-README-END-->
"""
    txt = (ROOT / "README.md").read_text()
    if "<!--S22-README-BEGIN-->" in txt:
        txt = re.sub(r"<!--S22-README-BEGIN-->.*?<!--S22-README-END-->\n", block, txt, count=1, flags=re.S)
    else:  # after the current-lane status, before the historical <details> block (or above the S21 block as a fallback)
        anchor = "\n---\n\n<details>"
        if anchor in txt:
            txt = txt.replace(anchor, "\n" + block + anchor, 1)
        else:
            txt = txt.replace("<!--S21-README-BEGIN-->", block + "<!--S21-README-BEGIN-->", 1)
    (ROOT / "README.md").write_text(txt)
    print("README S22 block rendered")


if __name__ == "__main__":
    render()
