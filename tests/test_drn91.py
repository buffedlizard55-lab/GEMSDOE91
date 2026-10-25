import json
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "docs/run-card-DRN91.json"

def test_drn91_card_is_honest_negative():
    d = json.loads(CARD.read_text())
    assert d["verdict"] == "negative" and d["ok_to_submit"] is False and d["ok_to_download"] is True
    e2 = d["holdout_dti"]["experiments"]["E2_all_plus_drainage_n37654"]
    assert e2["holdout_dti"] < 0.267782
    ci = e2["summary"]["scores"]["cand"]["ci95"]
    assert ci[0] < e2["holdout_dti"] < ci[1]
    assert d["canary_max_symmetric_auc"] <= 0.90
    assert d["registry_comparison"]["max_dot_overlap_3px"] <= 0.70
    assert len(d["note"]) <= 140 and d["slots_used"] == 0

def test_drn91_tif_range_and_grid():
    rasterio = pytest.importorskip("rasterio")
    name = json.loads(CARD.read_text())["submission_name"]
    p = ROOT / "docs/downloads" / f"{name}.tif"
    assert p.exists()
    with rasterio.open(p) as ds:
        a = ds.read(1)
        assert ds.count == 1 and str(ds.crs) == "EPSG:32611"
        assert (ds.height, ds.width) == (3730, 3292)
    assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
    assert int((a > 0).sum()) == 37654
