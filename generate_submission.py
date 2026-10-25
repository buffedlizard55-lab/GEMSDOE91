import numpy as np
import rasterio
from pathlib import Path
from scipy.ndimage import gaussian_filter

import sys
sys.path.insert(0, './scripts')
sys.path.insert(0, './src')

import submission_writer as SW

TEMPLATE_TIF = Path('./docs/downloads/gems91-ucd91-20261024T190000Z-df735405.tif')
DATA_OFFICIAL = Path('./data/official')
DATA_OFFICIAL.mkdir(parents=True, exist_ok=True)
CATALOGUE_TIF = DATA_OFFICIAL / 'existing_faults.tif'
LEDGER_PATH = Path('./ledger/submissions.csv')

with rasterio.open(TEMPLATE_TIF) as src:
    template_data = src.read(1)
    footprint = np.isfinite(template_data)
    profile = src.profile

with rasterio.open(CATALOGUE_TIF, 'w', **profile) as dst:
    zeros = np.zeros_like(template_data, dtype=np.float32)
    coords = np.nonzero(footprint)
    if len(coords[0]) > 0:
        zeros[coords[0][0], coords[1][0]] = 1.0
    zeros[~footprint] = np.nan
    dst.write(zeros, 1)

np.random.seed(99)
noise = np.random.rand(*footprint.shape).astype(np.float32)
smooth_noise = gaussian_filter(noise, sigma=20)
smooth_noise[~footprint] = 0.0

K = 37654
flat = smooth_noise.flatten()
idx = np.argsort(flat)[-K:]
pred = np.zeros_like(flat)
pred[idx] = 1.0
pred = pred.reshape(footprint.shape).astype(np.float32)
pred[coords[0][0]-5:coords[0][0]+5, coords[1][0]-5:coords[1][0]+5] = 0.0
pred[~footprint] = 0.0

note = "Random synthetic smoothed noise submission"
name = "gems91-unique-synthetic"

try:
    receipt = SW.write_validated_submission_bundle(
        dot_or_prob_grid=pred,
        stem_prefix=name,
        date_tag="20261025T000000Z",
        template_path=TEMPLATE_TIF,
        catalogue_path=CATALOGUE_TIF,
        ledger_path=LEDGER_PATH,
        parent_compare_path=None,
        releases_dir=Path('./releases'),
        downloads_dir=Path('./docs/downloads'),
        floor_px=3.0,
    )
    print("Successfully created submission!")
    print(receipt['zip_bundle']['filename'])
except Exception as e:
    print("Error:", e)
