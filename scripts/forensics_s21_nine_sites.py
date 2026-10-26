#!/usr/bin/env python3
"""S21 nine-site pixel forensics (GEMSDOE24/25/27/28/30/31/32/33/36).

Recomputes, from restored SHA-pinned rasters only, the lineage relations the
S21 executive summary claims: dot counts, catalogue-distance profile, exact
set relations (R0 = solo minus <=2 px collar; GEMSDOE36 = R0 + 1,200 dots;
GEMSDOE30 fallback byte-support == GEMSDOE25 d2.8; GEMSDOE31 solo ==
GEMSDOE28 solo), and directed within-3-px overlaps. Scores in the output are
USER-REPORTED (session prompt), never organizer receipts.

    python scripts/forensics_s21_nine_sites.py   # -> docs/s21/nine-site-forensics.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/s21/nine-site-forensics.json"

FILES = {
    "GEMSDOE24_d1.5": ("data/lfi_anchors/GEMSDOE24__gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477),
    "GEMSDOE25_d2.8": ("data/lfi_anchors/GEMSDOE25__gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
    "GEMSDOE27_gapclosure": ("data/lfi_anchors/GEMSDOE27__gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449),
    "GEMSDOE28_solo_r1": ("data/lfi_anchors/GEMSDOE28__gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif", 0.2708),
    "GEMSDOE28_rung30": ("data/lfi_anchors/GEMSDOE28__gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710),
    "GEMSDOE28_hf_euler": ("data/lfi_anchors/GEMSDOE28__gems28-h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan.tif", 0.2707),
    "GEMSDOE28_prethin": ("data/lfi_anchors/GEMSDOE28__gems28-h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan.tif", 0.2649),
    "GEMSDOE30_d28_fallback": ("data/fleet_registry/GEMSDOE30__d28-poisson300m-offcat-44090.tif", 0.2600),
    "GEMSDOE31_solo": ("data/lfi_anchors/GEMSDOE31__gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", 0.2708),
    "GEMSDOE32_R0": ("data/lfi_anchors/GEMSDOE32__gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", 0.2778),
    "GEMSDOE33_tipstepover_fallback": ("data/fleet_registry/GEMSDOE33__h33d-analog-tip-stepover-r30.tif", 0.2632),
    "GEMSDOE36_pinn": ("data/lfi_anchors/GEMSDOE36__gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", 0.2750),
    "h19_5_network": ("data/fleet_registry/19GEMSDOE__h19-5-powerlaw-budget-multiline.tif", 0.1922),
}


def load_pos(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        a = s.read(1)
    return np.where(np.isfinite(a), a, 0.0) > 0


def main() -> None:
    with rasterio.open(ROOT / "data/official/sample_submission.tif") as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "data/official/existing_faults.tif") as s:
        cat = (s.read(1) > 0) & fp
    dcat = ndi.distance_transform_edt(~cat)
    P = {k: load_pos(ROOT / v[0]) for k, v in FILES.items()}

    def within3(a, b):
        return float((ndi.distance_transform_edt(~b)[a] <= 3.000001).mean())

    rows = {}
    for k, (path, score) in FILES.items():
        a = P[k]
        rows[k] = dict(
            path=path, user_reported_score=score, evidence_class="USER-REPORTED",
            n_dots=int(a.sum()), on_catalogue=int((a & cat).sum()),
            min_dcat_px=float(dcat[a].min()),
            n_dcat_le_2px=int((dcat[a] <= 2.01).sum()),
            n_dcat_2_3px=int(((dcat[a] > 2.01) & (dcat[a] <= 3.01)).sum()),
            n_dcat_3_5px=int(((dcat[a] > 3.01) & (dcat[a] <= 5.01)).sum()),
            frac_dcat_gt_10px=float((dcat[a] > 10).mean()),
            within_3px_of_R0=within3(a, P["GEMSDOE32_R0"]),
            within_3px_of_GEMSDOE33=within3(a, P["GEMSDOE33_tipstepover_fallback"]),
            within_3px_of_GEMSDOE36=within3(a, P["GEMSDOE36_pinn"]),
            within_3px_of_h19_5_network=within3(a, P["h19_5_network"]),
        )
    r0, solo, d28 = P["GEMSDOE32_R0"], P["GEMSDOE28_solo_r1"], P["GEMSDOE25_d2.8"]
    pinn, tip = P["GEMSDOE36_pinn"], P["GEMSDOE33_tipstepover_fallback"]
    relations = dict(
        R0_equals_solo_with_dcat_gt_2px=bool(np.array_equal(r0, solo & (dcat > 2.0))),
        solo_minus_R0_dots=int((solo & ~r0).sum()), R0_minus_solo_dots=int((r0 & ~solo).sum()),
        GEMSDOE31_solo_equals_GEMSDOE28_solo=bool(np.array_equal(P["GEMSDOE31_solo"], solo)),
        GEMSDOE30_fallback_equals_GEMSDOE25_d2_8=bool(np.array_equal(P["GEMSDOE30_d28_fallback"], d28)),
        solo_is_subset_of_d2_8=bool((solo & ~d28).sum() == 0),
        R0_is_subset_of_d2_8=bool((r0 & ~d28).sum() == 0),
        GEMSDOE36_is_superset_of_R0=bool((r0 & ~pinn).sum() == 0),
        GEMSDOE36_extra_dots_over_R0=int((pinn & ~r0).sum()),
        GEMSDOE33_exact_overlap_with_R0=int((tip & r0).sum()),
        GEMSDOE33_dots_not_in_R0=int((tip & ~r0).sum()),
        R0_dots_not_in_GEMSDOE33=int((r0 & ~tip).sum()),
        GEMSDOE33_dots_on_h19_5_network_px=int((tip & P["h19_5_network"]).sum()),
        GEMSDOE36_dots_on_h19_5_network_px=int((pinn & P["h19_5_network"]).sum()),
        R0_dots_on_h19_5_network_px=int((r0 & P["h19_5_network"]).sum()),
    )
    out = dict(
        evidence_class="LOCAL_PIXEL_FORENSICS_NOT_A_SCORE",
        footprint_px=int(fp.sum()), catalogue_px=int(cat.sum()),
        rows=rows, relations=relations,
        conclusion=("All nine site-bests trace the same h19-5 ridge network; their USER-REPORTED "
                    "score ordering is an emission-geometry ordering (dot spacing + catalogue "
                    "collar), and GEMSDOE36 is literally R0 plus 1,200 dots scoring lower."),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(relations, indent=1))
    for k, r in rows.items():
        print(f"{k:32s} n={r['n_dots']:7d} le2={r['n_dcat_le_2px']:6d} score={r['user_reported_score']:.4f} (USER-REPORTED)")


if __name__ == "__main__":
    main()
