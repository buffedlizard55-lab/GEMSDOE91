#!/usr/bin/env python3
"""Write the S21-FAM3 candidate with the shared writer into outputs/s21/."""
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT)]
from vendor.gems57.submission_writer import write_submission  # noqa: E402
import run_lfi as R  # noqa: E402

fp, cat, net = R.base()
dots = np.load(ROOT / "work/s21/cand_dots.npy")
assert not (dots & cat).any() and not (dots & ~fp).any()
pred = dots.astype(np.float32)
h8 = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
n = int(dots.sum())
name = f"gems91-s21-fam3-{n}dots-{ts}-{h8}-zeros"
note = f"S21-FAM3: nine-site 3-family live-score inversion + gradB15, >3px collar, greedy E[DTI], {n} dots"
assert len(note) <= 140, len(note)
out = ROOT / "outputs/s21" / f"{name}.tif"
rec = write_submission(out, pred, ROOT / "data/official/sample_submission.tif", fp, note=note, name=name,
                       catalogue=cat, metadata=dict(lane="S21-FAM3",
                                                    emit=json.loads((ROOT / "work/s21/emit.json").read_text())["method"]))
print(json.dumps(dict(file=str(out), sha256=rec["sha256"], zip_sha256=rec["zip_sha256"], name=name, note=note,
                      note_chars=len(note), validator_all_pass=rec["validator"]["all_checks_passed"],
                      checks=rec["validator"]["checks"]), indent=1))
