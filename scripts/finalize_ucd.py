#!/usr/bin/env python3
"""Finalize UCD91 bundle from already-emitted winner dots (releases/).
Numbers transcribed from evidence/ucd_run.log (E1/E2 HOLDOUT-DTI gems91-hide-recover-v1.0)."""
import json,sys,hashlib
from pathlib import Path
import numpy as np, rasterio
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts')); sys.path.insert(0,str(ROOT/'src'))
import submission_writer as SW
src=sorted((ROOT/'releases').glob('gems91-ucd91-*-zeros.tif'))[-1]
with rasterio.open(src) as s: dots=s.read(1).astype(np.float32)
bundle=SW.write_validated_submission_bundle(dots,stem_prefix='gems91-ucd91',date_tag='20261024T190000Z',
 template_path=ROOT/'data/official/sample_submission.tif',catalogue_path=ROOT/'data/official/existing_faults.tif',
 downloads_dir=ROOT/'docs/downloads',bundle_js_filename='ucd91_submission_bundle.js')
print(json.dumps(bundle,indent=2,default=str))
Path(ROOT/'evidence/ucd_bundle.json').write_text(json.dumps(bundle,indent=2,default=str))
