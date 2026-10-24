"""Unit and end-to-end verification tests for Session 12 (`S12-BHAR`)."""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from gems91 import bhar_s12 as BH  # noqa: E402


def test_bhar_centerline_submodular_emit_eliminates_flanks_and_speckles() -> None:
    h, w = 80, 80
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    fp[:3, :] = False

    # Wide blurry range-front ridge at x=22 (sigma=3.2 px), concealed subsurface ridge at x=56,
    # plus an isolated 0-D speckle spike at (68, 40)
    surf = (
        0.82 * np.exp(-((xx - 22.0) ** 2) / (2.0 * 3.2 * 3.2))
        + 0.48 * np.exp(-((xx - 56.0) ** 2) / (2.0 * 2.0 * 2.0))
    ).astype(np.float32)
    surf[68, 40] = 0.90  # Isolated 0-D speckle far from either line

    bhar_edge = (0.88 * np.exp(-((xx - 56.0) ** 2) / 3.0)).astype(np.float32)
    conc_mask = xx >= 38

    dots = BH.bhar_centerline_submodular_emit(
        surf,
        bhar_edge,
        conc_mask,
        eligible_mask=fp,
        n_dots=28,
        gamma=1.24,
        bhar_weight=0.50,
        concealed_quota_frac=0.32,
        min_spacing_px=2.68,
        speckle_radius_px=9.0,
    )
    assert dots.shape == (h, w)
    assert dots.dtype == np.float32
    assert set(np.unique(dots)) <= {0.0, 1.0}
    assert int((dots > 0).sum()) == 28
    # Both exposed ridge (x < 38) and concealed subsurface ridge (x >= 38) receive dots
    assert int((dots[:, :38] > 0).sum()) >= 14
    assert int((dots[:, 38:] > 0).sum()) >= 7
    # Isolated 0-D speckle at (68, 40) must have been suppressed/pruned
    assert dots[68, 40] == 0.0


def test_pure_steger_and_bhar_dual_subsurface_emit() -> None:
    h, w = 80, 80
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    fp[:3, :] = False

    # Wide blurry mountain scarp at x=20 (only in p_multi, zero in p_sub!)
    # True rooted range-front fault at x=38 (in both p_multi and p_sub)
    # Blind intra-basin subsurface fault at x=60 (only in p_sub and pure_sub_edge!)
    p_multi = (
        0.75 * np.exp(-((xx - 20.0) ** 2) / (2.0 * 3.5 * 3.5))
        + 0.80 * np.exp(-((xx - 38.0) ** 2) / (2.0 * 3.0 * 3.0))
    ).astype(np.float32)
    p_sub = (
        0.72 * np.exp(-((xx - 38.0) ** 2) / (2.0 * 2.2 * 2.2))
        + 0.68 * np.exp(-((xx - 60.0) ** 2) / (2.0 * 2.0 * 2.0))
    ).astype(np.float32)
    pure_edge = (0.85 * np.exp(-((xx - 60.0) ** 2) / 3.0)).astype(np.float32)

    cr, sh = BH.pure_steger_hessian_crest(p_multi, sigma=1.15)
    assert cr[fp].mean() < 0.25  # Centerline only, never 95% of map!

    dots = BH.bhar_dual_subsurface_emit(
        p_multi,
        p_sub,
        pure_edge,
        eligible_mask=fp,
        n_dots=32,
        w_sub_blend=0.39,
        subsurface_quota_frac=0.30,
        gamma=1.20,
        min_spacing_px=2.68,
    )
    assert int((dots > 0).sum()) == 32
    assert set(np.unique(dots)) <= {0.0, 1.0}
    # Blind subsurface fault at x=60 receives Stage-2 dots despite zero signal in p_multi
    assert int((dots[:, 55:66] > 0).sum()) >= 7


def test_fold_safe_residual_basis_excludes_test_quadrant(tmp_path: Path) -> None:
    h, w = 48, 48
    fp = np.ones((h, w), dtype=bool)
    fp[0, :] = False
    n_fp = int(fp.sum())

    rng = np.random.default_rng(42)
    mm_path = tmp_path / "synth_static.dat"
    X_static = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=(n_fp, 19))
    X_static[:] = rng.normal(10.0, 2.0, size=(n_fp, 19)).astype(np.float32)
    X_static[:, 14] = np.abs(X_static[:, 14]) * 100.0  # B15 depth >= 0

    excl = np.zeros((h, w), dtype=bool)
    excl[24:, 24:] = True  # SE test quadrant

    basis1 = BH.FoldSafeResidualBasis(X_static, fp)
    out1 = basis1.compute_for_fold(excl)

    # Corrupt B13, B17, B14, B16 massively INSIDE the excluded test quadrant:
    # fitted regression coefficients must NOT change, so training-region residuals
    # far from spatial filter edges remain identical!
    X_static_corrupt = np.memmap(tmp_path / "synth_static2.dat", dtype=np.float32, mode="w+", shape=(n_fp, 19))
    X_static_corrupt[:] = X_static[:]
    excl_fp = excl[fp]
    X_static_corrupt[excl_fp, 12] += 5000.0  # B13 gravity in test region
    X_static_corrupt[excl_fp, 15] += 5000.0  # B16 seismic in test region

    basis2 = BH.FoldSafeResidualBasis(X_static_corrupt, fp)
    out2 = basis2.compute_for_fold(excl)

    # Pointwise non-convolved residuals (col 0 = g_intra_res, col 8 = log_seis_res)
    # on training interior must match to float32 precision!
    interior_train = np.zeros((h, w), dtype=bool)
    interior_train[2:16, 2:16] = True
    it_fp = interior_train[fp]
    np.testing.assert_allclose(out1[it_fp, 0], out2[it_fp, 0], rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(out1[it_fp, 8], out2[it_fp, 8], rtol=1e-5, atol=1e-5)


@pytest.mark.skipif(not (ROOT / "docs" / "run-card-S12.json").is_file(), reason="S12 run card not built yet")
def test_s12_run_card_and_certified_geotiff_artifacts() -> None:
    rc_docs = json.loads((ROOT / "docs" / "run-card-S12.json").read_text(encoding="utf-8"))
    rc_ev = json.loads((ROOT / "evidence" / "s12_run_card.json").read_text(encoding="utf-8"))
    assert rc_docs == rc_ev

    assert rc_docs["verdict"] in ("promote", "negative")
    assert rc_docs["budget"]["experiments_run"] == 3
    assert rc_docs["budget"]["wall_clock_seconds"] <= 7200
    assert rc_docs["leakage_canary"]["all_pass"] is True
    assert rc_docs["leakage_canary"]["n_features_tested"] == 92
    assert rc_docs["leakage_canary"]["worst_symmetric_auc"] <= 0.90

    ph = rc_docs["scores"]["primary_holdout"]
    assert ph["label"] == "HOLDOUT-DTI"
    assert ph["evaluator_version"] == "gems91-hide-recover-v1.0"
    assert ph["n_withheld_positives"] == 60988
    paired = ph["paired_vs_s11_e2"]
    assert paired["evidence_class"] == "HOLDOUT-DTI"
    if rc_docs["verdict"] == "promote":
        assert ph["score"] > ph["s11_e2_reference_holdout_dti"]
        assert paired["delta"] > 0.0 and paired["ci_95"][0] > 0.0

    uniq = rc_docs["registry_uniqueness"]
    assert uniq["uniqueness_pass"] is True
    assert uniq["rasters_checked"] >= 62
    assert uniq["max_surface_abs_rank_corr"] <= 0.90
    assert uniq["max_3px_dot_overlap"] <= 0.70

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

    for html_rel in (Path("docs/s12-bhar.html"), Path("docs/s12-executive-summary.html")):
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
