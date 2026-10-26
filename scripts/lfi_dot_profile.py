#!/usr/bin/env python3
"""Where do the candidate's dots sit (distance to catalogue / h19-5 network, consensus votes) vs R0 and the footprint?"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT)]
import run_lfi as R  # noqa: E402
fp, cat, net = R.base()
W = ROOT / "work/lfi"
d = np.load(W / "cand_dots.npy")
r0 = R.read_pred(ROOT / "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif", fp)[0] > 0
dcat, dnet, cons = np.load(W / "dcat.npy"), np.load(W / "dnet.npy"), np.load(W / "cons_votes.npy")


def prof(m):
    return dict(n=int(m.sum()), dcat_le5=round(float((dcat[m] <= 5).mean()), 3), dcat_gt10=round(float((dcat[m] > 10).mean()), 3),
                dnet_le1=round(float((dnet[m] <= 1.01).mean()), 3), dnet_gt6=round(float((dnet[m] > 6).mean()), 3),
                cons_ge3=round(float((cons[m] >= 3).mean()), 3), cons0=round(float((cons[m] == 0).mean()), 3))


out = dict(units="fractions of dots; dcat/dnet in 100 m px", candidate=prof(d), r0=prof(r0), footprint=prof(fp & ~cat))
(ROOT / "docs/lfi/dot-profile.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))
