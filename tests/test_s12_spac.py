"""Unit and synthetic physical tests for the S12-SPAC discovery lane (`gems91.spac_coda`)."""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from gems91 import spac_coda as SC

ROOT = Path(__file__).resolve().parents[1]


def _write_synthetic_19band_tif(path: Path, h: int = 72, w: int = 72) -> np.ndarray:
    rng = np.random.default_rng(1201)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    fp[:2, :] = False

    # Construct synthetic physical fields with a N-S fault contact at x = 34
    step = np.tanh((xx - 34.0) / 2.2).astype(np.float32)
    b14 = 120.0 * step + 8.0 * np.sin(yy / 4.0) + rng.normal(0.0, 0.8, size=(h, w)).astype(np.float32)
    b01 = 110.0 * np.tanh((xx - 34.0) / 6.0).astype(np.float32)  # smoother regional mag_anom
    gy, gx = np.gradient(b14, 100.0, 100.0)
    b03 = (200.0 * np.hypot(gx, gy)).astype(np.float32)  # exact 200x convention verified in GeoDAWN
    b09 = (0.45 * np.exp(-((xx - 34.0) ** 2) / 5.0)).astype(np.float32)
    b02 = (b14 + 15.0).astype(np.float32)

    bands = np.zeros((19, h, w), dtype=np.float32)
    bands[0] = b01
    bands[1] = b02
    bands[2] = b03
    bands[3] = 20.0 * step
    bands[4] = np.clip(0.5 + 0.3 * np.exp(-((xx - 34.0) ** 2) / 6.0), 0.01, None)
    bands[5] = 45.0 + 6.0 * step
    bands[6] = 18.0 + 4.0 * np.exp(-((xx - 34.0) ** 2) / 12.0)  # B07 strain_2nd_inv
    bands[7] = 8.0 * np.sin((xx - 30.0) / 10.0)                  # B08 dilatation
    bands[8] = b09
    bands[9] = 900.0 * np.exp(-((xx - 34.0) ** 2) / 9.0)         # B10 dependent swarm
    bands[10] = 2.0 * np.exp(-((xx - 34.0) ** 2) / 6.0)          # B11 cba_hgm_x
    bands[11] = 1600.0 + 180.0 * step                            # B12 elevation
    bands[12] = 75.0 + 15.0 * np.exp(-((xx - 34.0) ** 2) / 10.0)
    bands[13] = b14
    bands[14] = 80.0 * step                                      # B15 detrended_dem
    bands[15] = 400.0 * np.exp(-((xx - 34.0) ** 2) / 10.0)       # B16 independent eq
    bands[16] = np.abs(np.gradient(bands[11])[1])                # B17 slope
    bands[17] = 0.3 * np.cos(yy / 7.0)                           # B18 cba_hgm_y
    bands[18] = np.clip(1.2 + 0.5 * np.exp(-((xx - 34.0) ** 2) / 7.0), 0.01, None)

    for b in range(19):
        bands[b, ~fp] = np.nan

    profile = {
        "driver": "GTiff",
        "height": h,
        "width": w,
        "count": 19,
        "dtype": "float32",
        "crs": "EPSG:32611",
        "transform": Affine.translation(243350.0, 4508550.0) @ Affine.scale(100.0, -100.0),
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(bands)
    return fp


def test_s12_feature_memmap_build_and_cache(tmp_path: Path) -> None:
    tif = tmp_path / "synth_features.tif"
    fp = _write_synthetic_19band_tif(tif)
    cache = tmp_path / "cache"

    mm, names, meta = SC.build_or_load_s12_feature_memmap(
        features_tif=tif, footprint=fp, cache_dir=cache
    )
    assert names == list(SC.S12_SPAC_STATIC_FEATURE_NAMES)
    assert len(names) == 20
    assert mm.shape == (int(fp.sum()), 20)
    assert np.isfinite(mm).all()
    assert isinstance(meta, dict)
    assert (cache / "s12_spac_features_v1.dat").is_file()

    # Verify deterministic cache reload
    mm2, names2, _ = SC.build_or_load_s12_feature_memmap(
        features_tif=tif, footprint=fp, cache_dir=cache
    )
    assert names2 == names
    assert np.allclose(mm, mm2)


def test_frangi_ridge_rejects_isotropic_plug_and_autocontext_bridges_wash_gap() -> None:
    h, w = 80, 80
    fp = np.ones((h, w), dtype=bool)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    ridge = np.exp(-((xx - 24.0) ** 2) / 4.0)
    plug = np.exp(-((xx - 58.0) ** 2 + (yy - 40.0) ** 2) / 8.0)
    vess = SC._frangi_ridge_2d((ridge + plug).astype(np.float32), fp, sigma=2.0)
    assert float(vess[40, 24]) > 2.5 * float(vess[40, 58])

    p1 = np.zeros((h, w), dtype=np.float32)
    p1[14:35, 30] = 0.88
    p1[45:66, 30] = 0.88
    p1[40, 64] = 0.88
    ac = SC.compute_spac_autocontext_features(p1, fp)
    assert ac.shape == (int(fp.sum()), 10)
    assert np.isfinite(ac).all()
    wb2 = ac[:, 5].reshape(h, w)
    assert float(wb2[40, 30]) > 5.0 * float(wb2[40, 64])


def test_spac_stage_training_and_three_regime_submodular_emitter() -> None:
    rng = np.random.default_rng(91)
    h, w = 64, 64
    fp = np.ones((h, w), dtype=bool)
    fp[0, :] = False
    n_fp = int(fp.sum())

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vis = fp & (np.abs(xx - 20.0) <= 1.0) & (yy < 32)
    excl = yy >= 32  # withhold southern half completely

    feat_a = np.column_stack([
        np.exp(-((xx[fp] - 20.0) ** 2) / 6.0),
        rng.normal(0.0, 1.0, size=n_fp),
        rng.normal(0.0, 1.0, size=n_fp),
    ]).astype(np.float32)

    surf = SC.fit_and_predict_spac_stage(
        feature_blocks=[(feat_a, [0, 1, 2])],
        visible_faults=vis,
        exclude_mask=excl,
        footprint=fp,
        seed=42,
        neg_pos_ratio=3.65,
    )
    assert surf.shape == (h, w)
    assert np.isfinite(surf).all()
    assert float(surf[~fp].max()) == 0.0
    # In the blind southern half (`yy >= 32`), fault ridge at x=20 must score above background x=48
    assert float(surf[48, 20]) > float(surf[48, 48])

    e_mhtr = (0.8 * np.exp(-((xx - 36.0) ** 2) / 3.0)).astype(np.float32)
    e_spi = (0.85 * np.exp(-((xx - 52.0) ** 2) / 3.0)).astype(np.float32)
    pied_m = (xx >= 28) & (xx < 44)
    spi_m = xx >= 44
    elig = fp & (~vis)
    dots = SC.spac_three_regime_submodular_emit(
        surf,
        e_mhtr,
        e_spi,
        pied_m,
        spi_m,
        eligible_mask=elig,
        n_dots=24,
        piedmont_quota_frac=0.25,
        spi_quota_frac=0.25,
        min_spacing_px=2.45,
    )
    assert int((dots > 0).sum()) == 24
    assert set(np.unique(dots)) <= {0.0, 1.0}
    assert int((dots[vis] > 0).sum()) == 0


def test_s12_run_card_geotiff_and_pages_portal() -> None:
    rc_docs = json.loads((ROOT / "docs" / "run-card-S12.json").read_text(encoding="utf-8"))
    rc_ev = json.loads((ROOT / "evidence" / "s12_run_card.json").read_text(encoding="utf-8"))
    assert rc_docs == rc_ev

    assert rc_docs["verdict"] == "promote"
    assert rc_docs["budget"]["experiments_run"] == 3
    assert rc_docs["budget"]["wall_clock_seconds"] <= 7200
    assert rc_docs["leakage_canary"]["all_pass"] is True
    assert rc_docs["leakage_canary"]["n_features_tested"] == 95
    assert rc_docs["leakage_canary"]["worst_symmetric_auc"] <= 0.90

    ph = rc_docs["scores"]["primary_holdout"]
    assert ph["label"] == "HOLDOUT-DTI"
    assert ph["evaluator_version"] == "gems91-hide-recover-v1.0"
    assert ph["n_withheld_positives"] == 60988
    assert ph["score"] > ph["s11_e2_reference_holdout_dti"] > ph["h91_e1_reference_holdout_dti"] > ph["b0_reference_holdout_dti"]
    assert ph["paired_vs_s11_e2"]["ci_95"][0] > 0.0
    assert ph["paired_vs_s11_e2"]["prob_positive"] == 1.0

    sgmc = rc_docs["scores"]["blind_sgmc_offcatalogue_control"]
    assert sgmc["dti"] > 0.105

    uniq = rc_docs["registry_uniqueness"]
    assert uniq["uniqueness_pass"] is True
    assert uniq["rasters_checked"] >= 64
    assert uniq["max_surface_abs_rank_corr"] <= 0.90
    assert uniq["max_3px_dot_overlap"] <= 0.70
    assert uniq["max_raw_oneway_3px_le80k"] <= 0.70
    assert "lineage_predecessor_audit" in uniq
    assert "protocol_lattice_diagnostic" in uniq

    sub = rc_docs["submission"]
    assert 1 <= len(sub["recommended_form_note"]) <= 140
    assert sub["recommended_form_note_length"] == len(sub["recommended_form_note"])

    tif_path = ROOT / "docs" / "downloads" / sub["recommended_upload_file"]
    zip_path = ROOT / "docs" / "downloads" / sub["recommended_zip_download"]
    audit_path = ROOT / "docs" / "downloads" / sub["audit_json"]
    assert tif_path.is_file()
    assert zip_path.is_file()
    assert audit_path.is_file()

    tif_bytes = tif_path.read_bytes()
    assert len(tif_bytes) == sub["bytes_zeros_tif"]
    assert hashlib.sha256(tif_bytes).hexdigest() == sub["sha256_zeros_tif"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == sub["sha256_zeros_zip"]

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [sub["recommended_upload_file"]]
        assert zf.read(sub["recommended_upload_file"]) == tif_bytes

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert ds.nodata is None
        arr = ds.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) == 0.0
        assert float(arr.max()) == 1.0
        assert int((arr > 0).sum()) == sub["n_dots"]

    for html_rel in (Path("docs/s12-spac.html"), Path("docs/s12-executive-summary.html")):
        hp = ROOT / html_rel
        assert hp.is_file()
        txt = hp.read_text(encoding="utf-8")
        assert sub["candidate_id"] in txt
        assert sub["sha256_zeros_tif"] in txt
        assert sub["recommended_form_note"] in html.unescape(txt)
        for m in re.finditer(r'(?:href|src)="([^"]+)"', txt):
            target = m.group(1)
            if target.startswith(("http://", "https://", "#", "mailto:", "javascript:")):
                continue
            clean_rel = target.split("#", 1)[0].split("?", 1)[0]
            if not clean_rel:
                continue
            resolved = (hp.parent / clean_rel).resolve()
            assert resolved.exists(), f"Broken link {target!r} in {html_rel}"
            rel_to_root = resolved.relative_to(ROOT)
            ign = subprocess.run(["git", "check-ignore", "-q", str(rel_to_root)], cwd=ROOT)
            assert ign.returncode != 0, f"GitHub Pages asset {rel_to_root} is gitignored!"

