#!/usr/bin/env python3
"""REPORT-ONLY instruments for the MASS/consensus arms (brief section 6).

    python scripts/instruments.py --label mass-consensus \
        releases/<id>.tif releases/<id>.tif releases/<id>.tif

None of these is a gate, and none may be quoted as a score:

  PROXY   catalogue hide-and-recover. The catalogue is split into four spatial
          blocks; each fold is withheld, and every candidate is scored with the
          DTI algebra against the withheld positives only. Reported with a 95% CI
          (t, n = 4). The withheld pixels are KNOWN USGS/INGENIOUS geometry, which
          the competition masks, so this measures recall of catalogue-like
          structure -- not of new-fault truth. Prior sessions measured this
          instrument correlating -0.87 to +0.54 with live scores (n = 12-14).

  CANARY  leakage canary. AUC of one feature (the cross-field support vote) for
          catalogue membership inside the footprint. AUC > 0.90 would mean the
          feature is effectively reading the answer; the brief says stop and
          investigate. A support vote *should* have AUC well above 0.5 -- the
          lineage was built from the same geophysics -- so the bar is 0.90, not 0.7.

  SGMC    control. Fraction of each arm's dots lying within 1 px of the independent
          Arizona SGMC 100 m fault compilation. A candidate that suddenly gains a
          large SGMC overlap would be tracking a public map rather than the
          submitted field.

Writes JSON; prints a table. Reads only pinned inputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import dti as D  # noqa: E402
from gems91 import consensus as C  # noqa: E402
from gems91 import io as G  # noqa: E402

TEMPLATE = "data/official/sample_submission.tif"
CATALOGUE = "data/official/existing_faults.tif"
SGMC = "data/external/derived_sgmc_faults_100m_u8.tif"
FIELDS = ["data/registry/calib_h195_01922.tif", "data/registry/calib_h194_01894.tif",
          "data/registry/calib_h161_01855.tif"]


def rd(p):
    with rasterio.open(p) as s:
        return s.read(1)


def folds(catalogue: np.ndarray, n_folds: int = 4, block: int = 8) -> list[np.ndarray]:
    """Contiguous spatial blocks of catalogue positives (no randomised split)."""
    h, w = catalogue.shape
    yy, xx = np.mgrid[0:h, 0:w]
    quad = ((yy // (100 * block)) % 2) * 2 + ((xx // (100 * block)) % 2)
    ys, xs = np.nonzero(catalogue)
    out = []
    for f in range(n_folds):
        m = np.zeros(catalogue.shape, dtype=bool)
        sel = quad[ys, xs] % n_folds == f
        m[ys[sel], xs[sel]] = True
        out.append(m)
    return out


def mean_ci(v: list[float]) -> tuple[float, float]:
    a = np.asarray(v, dtype=float)
    if len(a) < 2:
        return float(a.mean()) if len(a) else float("nan"), float("nan")
    se = a.std(ddof=1) / np.sqrt(len(a))
    t = {2: 12.71, 3: 4.303, 4: 3.182, 5: 2.776}.get(len(a), 1.96)
    return float(a.mean()), float(t * se)


def auc(score: np.ndarray, label: np.ndarray) -> float:
    """Rank-based AUC (Mann-Whitney), ties averaged."""
    from scipy.stats import rankdata
    r = rankdata(np.asarray(score, dtype=float))
    n1 = int(label.sum())
    n0 = int(len(label) - n1)
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((r[label].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--label", default="mass-consensus")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    fp = np.isfinite(rd(TEMPLATE))
    cat = rd(CATALOGUE) > 0
    out = {"schema": "gems91.instruments.v1", "label": args.label,
           "note": "REPORT ONLY. Never a gate, never a score.", "arms": {}}

    # --- PROXY: withhold one spatial block of catalogue positives at a time
    fs = folds(cat, 4)
    proxy: dict[str, list[float]] = {}
    for f in args.files:
        dots = G.dot_mask(rd(f))
        vals = []
        for held in fs:
            truth = held & fp
            if truth.sum() < 50:
                continue
            pred = np.where(fp, dots, 0).astype(np.float64)
            vals.append(D.dti(pred, truth))
        proxy[Path(f).name] = vals
        m, hw = mean_ci(vals)
        out["arms"].setdefault(Path(f).name, {})["proxy"] = {
            "mean_dti_vs_withheld_catalogue": round(m, 5),
            "ci95_halfwidth": round(hw, 5),
            "folds": [round(v, 5) for v in vals],
            "n_withheld_positive_folds": [int(x.sum()) for x in fs],
        }

    # --- CANARY: does the support vote know where the catalogue is?
    #
    # The plain test (catalogue pixels vs background) is DEGENERATE here and must not be
    # reported as a pass: all three lineage fields, like R0 itself, were built with the
    # catalogue masked out, so every catalogue pixel scores vote = 0 by construction
    # (measured: vote histogram on the 60,988 catalogue pixels is [60988, 0, 0, 0]).
    # The informative test is the 0-3 px RING around known traces: a feature that
    # concentrated there at AUC > 0.90 would mean the ranking had learned catalogue
    # proximity -- i.e. it would be a disguised PRUNE, not a support ordering.
    dcat = ndi.distance_transform_edt(~cat)
    ring = fp & ~cat & (dcat <= 3)
    far = fp & ~ndi.binary_dilation(cat, np.ones((7, 7), bool))
    keep = ring | far
    label = ring[keep]
    vote = C.vote_count([rd(p) > 0 for p in FIELDS])
    a = auc(vote[keep].astype(float), label)
    out["canary"] = {
        "feature": "cross-field support vote (0-3)",
        "test": "0-3 px catalogue ring vs background >= 7 px clear",
        "auc_vs_catalogue_ring": round(a, 4),
        "threshold": 0.90,
        "verdict": "STOP AND INVESTIGATE" if a > 0.9 else "below threshold",
        "degenerate_plain_test_note": (
            "AUC of the vote for catalogue-pixel membership is not reportable: the lineage "
            "fields are catalogue-masked, so all 60,988 catalogue pixels score vote=0."),
        "n_ring_px": int(ring.sum()), "n_background_px": int(far.sum()),
        "frac_ring_with_support": round(float((vote[ring] >= 1).mean()), 4),
        "frac_background_with_support": round(float((vote[far] >= 1).mean()), 4),
    }

    # --- SGMC control
    sgmc = rd(SGMC) > 0
    near = ndi.binary_dilation(sgmc, np.ones((3, 3), bool))
    for f in args.files:
        dots = G.dot_mask(rd(f))
        out["arms"].setdefault(Path(f).name, {})["sgmc"] = {
            "frac_dots_within_1px": round(float(near[dots].mean()), 4),
            "frac_sgmc_covered": round(float((dots & near).sum() / max(1, int(sgmc.sum()))), 4),
        }

    print(f"{'file':52s} {'PROXY dti':>10s} {'+-95%':>8s} {'SGMC 1px':>9s}")
    for name, a_ in out["arms"].items():
        p = a_.get("proxy", {})
        print(f"{name:52s} {p.get('mean_dti_vs_withheld_catalogue', float('nan')):10.5f} "
              f"{p.get('ci95_halfwidth', float('nan')):8.5f} {a_.get('sgmc', {}).get('frac_dots_within_1px', float('nan')):9.4f}")
    print(f"\nCANARY ring AUC (support vote, 0-3 px ring vs background) = "
          f"{out['canary']['auc_vs_catalogue_ring']} -> {out['canary']['verdict']}")
    print("PROXY is a local holdout with n=4 spatial folds; it is not a score and has never")
    print("tracked live results reliably (prior n=12-14: r = -0.87 to +0.54).")

    dest = Path(args.out or f"reports/instruments-{args.label}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
