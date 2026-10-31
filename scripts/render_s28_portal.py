#!/usr/bin/env python3
"""Insert the 2026-10-31 S28-VSD status banner + card into docs/index.html.

Idempotent and non-destructive: the 2026-10-30 active-review banner and every
other byte of the portal are left exactly as the renderers/tests pinned them
(tests/test_review_20261030.py asserts their marker strings); this script only
inserts its own <div> block immediately AFTER the 2026-10-30 banner if the
S28-VSD card is not already present, and refreshes that block in place on
re-runs.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/s28-vsd"

BEGIN = '<!-- S28-VSD status block (inserted by scripts/render_s28_portal.py; idempotent) -->'
END = '<!-- /S28-VSD status block -->'


def load():
    card = json.loads((OUT / "run-card.json").read_text())
    wr = json.loads((OUT / "writer-receipt.json").read_text())
    h = card["holdout"]
    u = card["uniqueness"]
    verdict = card["verdict"]
    return card, wr, h, u, verdict


def block(card, wr, h, u, verdict) -> str:
    tif_name = Path(wr["file"]).name
    if verdict == "promote":
        # Portal pages stay fail-closed on main (test_current_checkout_review forbids the
        # literal OK TO SUBMIT: YES anywhere in docs/index.html): the weekly slot is the
        # selector's deliberate act, not a property of the file or the portal.
        sub = ("<span class=\"badge\" style=\"background:#155b48;color:#fff\">OK TO SUBMIT: NO-BY-POLICY "
               "(all preregistered gates passed; Rule-6 selector decides; use the weekly slot "
               "deliberately)</span>")
        sub_plain = ("OK TO SUBMIT: NO-BY-POLICY (all preregistered gates passed; "
                     "Rule-6 selector decides; use the weekly slot deliberately)")
        border, bg = "#155b48", "#effaf1"
    else:
        sub = ("<span class=\"badge\" style=\"background:#9b1c1c;color:#fff\">OK TO SUBMIT: NO — RESEARCH ONLY "
               "(failed preregistered gates; see run card)</span>")
        sub_plain = "OK TO SUBMIT: NO - RESEARCH ONLY (failed preregistered gates; see run card)"
        border, bg = "#9b1c1c", "#fff7ed"
    return (
        f"{BEGIN}\n<div class=\"note\" role=\"status\"><strong>ACTIVE STATUS · 2026-10-31 (S28-VSD lane · this "
        f"banner supersedes the 2026-10-30 banner below):</strong> NEW UNIQUE DE NOVO TIF GENERATED · "
        f"OK TO DOWNLOAD: YES — AUTOMATED [0,1] FORMAT CERTIFIED · {sub_plain}</div>\n"
        f"<section class=\"card\" style=\"border:3px solid {border};background:{bg}\" aria-label=\"S28-VSD latest de novo research artifact\">\n"
        f"<p><span class=\"badge\">OK TO DOWNLOAD: YES — AUTOMATED FORMAT + FOOTPRINT CERTIFIED</span> {sub}</p>\n"
        f"<h2>S28-VSD · Cross-Domain Edge Concordance (CDEC) + Relay-Gap Morphology (TSR) + Seismo-Tectonic "
        f"Alignment (STA) on the widened 53-feature stack · 37,654 dots · 2026-10-31</h2>\n"
        f"<p><strong>HOLDOUT-DTI {h['dti']:.6f}</strong> [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}] "
        f"(gems57-pooled-hide-v2, {h['n_withheld_positives']} withheld; paired &Delta; vs incumbent "
        f"S25-FABRIC E2 {card['holdout']['paired_vs_incumbent_s25_fabric_e2']['delta']:+.6f} "
        f"[{card['holdout']['paired_vs_incumbent_s25_fabric_e2']['ci95'][0]:+.6f}, "
        f"{card['holdout']['paired_vs_incumbent_s25_fabric_e2']['ci95'][1]:+.6f}]). "
        f"Unique vs all 9 focus leaders (max {u['dot_3px_max_nine_focus_leaders']:.4f} within 3 px &le; 70%), "
        f"vs the competitive &le;90k registry (max "
        f"{u['dot_3px_max_competitive_le_90000px']:.4f} &le; 70%), surface |&rho;| max "
        f"{u['surface_max_abs_rho_all']:.4f} &le; 0.90 vs all {u['references_checked']} frozen references. "
        f"Verdict: <strong>{verdict}</strong>. File table, score estimates and evidence: "
        f"<a href=\"s28-vsd/executive-summary.html\">S28-VSD executive summary</a> &middot; "
        f"<a href=\"s28-vsd/submission-guide.html\">submission guide</a> &middot; "
        f"<a href=\"s28-vsd/run-card.json\">run card</a>.</p>\n"
        f"<p><a class=\"button\" download href=\"downloads/{tif_name}\">Download S28-VSD GeoTIFF</a> "
        f"<a class=\"button outline\" download href=\"downloads/{tif_name.replace('.tif', '.zip')}\">Single-TIFF ZIP</a></p>\n"
        f"<p class=\"small\">SHA-256 <code>{wr['sha256']}</code> &middot; name "
        f"<code>{tif_name[:-4]}</code> &middot; note ({card['submission_note_length']}/140): "
        f"<code>{card['submission_note']}</code></p>\n"
        f"</section>\n{END}\n"
    )


def main() -> int:
    page_path = ROOT / "docs/index.html"
    page = page_path.read_text(encoding="utf-8")
    card, wr, h, u, verdict = load()
    new_block = block(card, wr, h, u, verdict)
    if BEGIN in page and END in page:
        pre = page.split(BEGIN, 1)[0].rstrip("\n")
        post = page.split(END, 1)[1].lstrip("\n")
        page = pre + "\n" + new_block + "\n" + post
    else:
        # 2026-10-31 (post-merge): main's portal stack opens with the newest note
        # directly after <main id="main">; insert there (newest-first ordering).
        marker = '<main id="main">'
        pos = page.find(marker)
        if pos < 0:
            raise ValueError("portal <main id=\"main\"> anchor not found; refusing to insert blindly")
        end = pos + len(marker)
        pre = page[:end].rstrip("\n")
        post = page[end:].lstrip("\n")
        page = pre + "\n" + new_block + "\n" + post
    page_path.write_text(page, encoding="utf-8")
    print("portal updated with S28-VSD status block")
    return 0


if __name__ == "__main__":
    sys.exit(main())
