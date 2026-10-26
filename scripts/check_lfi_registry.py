#!/usr/bin/env python3
"""Rule-1 uniqueness of a candidate vs the protocol registry (data/fleet_registry), the 108 LFI anchor
rasters (data/lfi_anchors) and this repo's own docs/downloads, using sibling_sweep.cmd_check unchanged
(same dense-reference rule) on a different manifest."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sibling_sweep as S  # noqa: E402
cand, out = Path(sys.argv[1]), Path(sys.argv[2])
dest = ROOT / "work/lfi/regset"; dest.mkdir(parents=True, exist_ok=True)
man = []
for sub, repo in (("data/fleet_registry", "protocol-registry"), ("data/lfi_anchors", "lfi-anchor"), ("docs/downloads", "GEMSDOE91-own")):
    for p in sorted((ROOT / sub).glob("*.tif")):
        man.append(dict(local=str(p.relative_to(ROOT)), repo=repo))
(dest / "fetched.json").write_text(json.dumps(man))
S.DEST = dest
S.cmd_check(cand.resolve(), out)
