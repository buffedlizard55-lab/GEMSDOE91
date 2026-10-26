#!/usr/bin/env python3
"""Rule-1 uniqueness of the S21 candidate vs fleet registry + LFI anchors + own
downloads, using sibling_sweep.cmd_check unchanged (same dense-reference rule)
on the S21 registry-set manifest. Usage: check_s21_registry.py CANDIDATE.tif OUT.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sibling_sweep as S  # noqa: E402
cand, out = Path(sys.argv[1]), Path(sys.argv[2])
surface = ROOT / "work/s21/cand_q.npy"
dest = ROOT / "work/s21/regset"
dest.mkdir(parents=True, exist_ok=True)
man = []
for sub, repo in (("data/fleet_registry", "protocol-registry"),
                  ("data/lfi_anchors", "lfi-anchor"),
                  ("docs/downloads", "GEMSDOE91-own")):
    for p in sorted((ROOT / sub).glob("*.tif")):
        man.append(dict(local=str(p.relative_to(ROOT)), repo=repo))
(dest / "fetched.json").write_text(json.dumps(man))
S.DEST = dest
S.cmd_check(cand.resolve(), out, surface if surface.exists() else None)
