"""Unit tests for Session 17 (`S17-LFTG`) 3-D Laplace Full-Tensor Gravity,
flight-line notch destriping, accommodation-zone reversal, sentinel safety, and
bitwise Band 12/19 invariance.
"""

from __future__ import annotations

import sys
from pathlib import Path

from affine import Affine
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from gems91 import dd_vtc_pu as DD  # noqa: E402
from gems91 import lftg17 as L17  # noqa: E402
from gems91 import mhtr_coda as MC  # noqa: E402
from gems91 import ptha as PTHA  # noqa: E402
from gems91 import scgf15 as SCGF  # noqa: E402


def test_laplace_full_tensor_step_amplitude_invariance_and_plug_rejection():
    h, w = 160, 160
    fp = np.ones((h, w), dtype=bool)
    yy, xx = np.indices((h, w), dtype=np.float32)

    # Oblique N27E strike-extended 2-D step buried under smooth kernel
    coord = (xx - 80.0) * np.cos(0.45) + (yy - 80.0) * np.sin(0.45)
    step_strong = ndi.gaussian_filter((coord > 0).astype(np.float32) * 20.0, sigma=3.0)
    step_weak = step_strong * np.float32(0.10)  # 10x weaker amplitude (deeply buried analogue)

    g_strong = L17.compute_laplace_full_tensor_gravity(step_strong, fp, pad=32, workers=1)
    g_weak = L17.compute_laplace_full_tensor_gravity(step_weak, fp, pad=32, workers=1)

    for g in (g_strong, g_weak):
        for arr in g.values():
            assert arr.dtype == np.float32
            assert np.isfinite(arr).all()

    interior_mask = (yy > 35) & (yy < 125) & (xx > 35) & (xx < 125)
    on_fault = (np.abs(coord) < 1.5) & interior_mask
    off_fault = (np.abs(coord) > 18.0) & interior_mask
    # Wijns cos(theta_G) peaks on the fault for BOTH strong and 10x-weaker steps
    assert float(g_strong["cos_theta_200m"][on_fault].mean()) > 0.85
    assert float(g_weak["cos_theta_200m"][on_fault].mean()) > 0.85
    assert float(g_weak["cos_theta_200m"][on_fault].mean()) > float(
        g_weak["cos_theta_200m"][off_fault].mean() + 0.30
    )

    # Circular 3-D volcanic plug (axisymmetric Gaussian anomaly) vs 2-D fault step:
    # Pedersen-Rasmussen Q_2D = (1 - |I|) * cos_theta suppresses 3-D axisymmetric center/ring
    r2 = (xx - 80.0) ** 2 + (yy - 80.0) ** 2
    plug_3d = (25.0 * np.exp(-r2 / (2.0 * 6.0 * 6.0))).astype(np.float32)
    g_plug = L17.compute_laplace_full_tensor_gravity(plug_3d, fp, pad=32, workers=1)
    plug_ring = (np.sqrt(r2) > 4.5) & (np.sqrt(r2) < 7.5)
    q2d_ratio_step = float(
        g_strong["q2d_purity"][on_fault].mean()
        / (g_strong["cos_theta_200m"][on_fault].mean() + 1e-6)
    )
    q2d_ratio_plug = float(
        g_plug["q2d_purity"][plug_ring].mean()
        / (g_plug["cos_theta_200m"][plug_ring].mean() + 1e-6)
    )
    assert q2d_ratio_step > 0.90
    assert q2d_ratio_step > q2d_ratio_plug + 0.15


def test_cardinal_flightline_destriping_preserves_oblique_fault():
    h, w = 160, 160
    yy, xx = np.indices((h, w), dtype=np.float32)
    oblique_fault = np.tanh(((xx - 80.0) * 0.82 + (yy - 80.0) * 0.57) / 2.5).astype(np.float32) * 8.0
    stripes = (
        3.5 * np.sin(2.0 * np.pi * yy / 6.0) + 2.5 * np.cos(2.0 * np.pi * xx / 8.0)
    ).astype(np.float32)
    noisy = (oblique_fault + stripes).astype(np.float32)

    clean, removed = L17.destripe_cardinal_flightlines(noisy, pad=32, workers=1)
    interior = (slice(24, 136), slice(24, 136))
    err_before = float(np.mean((noisy[interior] - oblique_fault[interior]) ** 2))
    err_after = float(np.mean((clean[interior] - oblique_fault[interior]) ** 2))
    assert err_after < 0.12 * err_before
    assert np.isfinite(clean).all() and np.isfinite(removed).all()


def test_accommodation_dip_reversal_peaks_at_scissor_hinge():
    h, w = 140, 140
    fp = np.ones((h, w), dtype=bool)
    yy, xx = np.indices((h, w), dtype=np.float32)
    # North-striking structure whose throw flips sign across y = 70
    polarity = np.tanh((yy - 70.0) / 3.0)
    scissor = (polarity * np.tanh((xx - 70.0) / 2.5) * 10.0).astype(np.float32)
    rev = L17.compute_accomm_dip_reversal(scissor, fp)
    hinge = (np.abs(yy - 70.0) <= 3.0) & (np.abs(xx - 70.0) <= 4.0)
    flank = (np.abs(yy - 35.0) <= 5.0) & (np.abs(xx - 70.0) <= 4.0)
    assert float(rev[hinge].mean()) > 4.0 * float(rev[flank].mean() + 1e-4)


def test_lftg17_memmap_sentinel_safe_and_bitwise_b12_b19_invariant(tmp_path: Path):
    h, w = 96, 96
    fp = np.ones((h, w), dtype=bool)
    fp[:4, :] = False
    rng = np.random.default_rng(1701)
    bands = rng.normal(0.0, 5.0, size=(19, h, w)).astype(np.float32)
    # Inject -3.4028235e+38 sentinels inside the active footprint (matching real GeoDAWN cube)
    bands[:, 20:23, 30:33] = np.float32(-3.4028235e38)

    def _write_cube(path: Path, arr: np.ndarray) -> None:
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=h,
            width=w,
            count=19,
            dtype="float32",
            crs="EPSG:32611",
            transform=Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
        ) as dst:
            dst.write(arr)

    tif_a = tmp_path / "cube_a.tif"
    tif_b = tmp_path / "cube_b.tif"
    _write_cube(tif_a, bands)

    bands_corrupted = bands.copy()
    # Corrupt Band 12 (idx 11) and Band 19 (idx 18) massively
    bands_corrupted[11] = rng.uniform(-1e5, 1e5, size=(h, w)).astype(np.float32)
    bands_corrupted[18] = rng.uniform(-1e5, 1e5, size=(h, w)).astype(np.float32)
    bands_corrupted[11, 40, 40] = np.float32(-3.4028235e38)
    _write_cube(tif_b, bands_corrupted)

    mm_a, names_a, _ = L17.build_or_load_lftg17_feature_memmap(
        features_tif=tif_a, footprint=fp, cache_dir=tmp_path / "ca", workers=1
    )
    mm_b, names_b, _ = L17.build_or_load_lftg17_feature_memmap(
        features_tif=tif_b, footprint=fp, cache_dir=tmp_path / "cb", workers=1
    )
    assert names_a == names_b == L17.S17_LFTG_FEATURE_NAMES
    assert mm_a.shape == (int(fp.sum()), 20)
    assert np.isfinite(mm_a).all()
    assert np.array_equal(np.asarray(mm_a), np.asarray(mm_b))

    # Verify Pure-Subsurface column selector excludes all STRICT_TOPO_FEATURE_NAMES
    sub_static = L17.select_subsurface_cols(L17.CLEAN_STATIC_COLS, DD.ALL_STATIC_FEATURE_NAMES)
    sub_s11 = L17.select_subsurface_cols(L17.CLEAN_S11_COLS, MC.S11_MHTR_FEATURE_NAMES)
    sub_ptha = L17.select_subsurface_cols(L17.CLEAN_PTHA_COLS, PTHA.PTHA_FEATURE_NAMES)
    sub_lftg = L17.select_subsurface_cols(L17.ALL_LFTG17_COLS, L17.S17_LFTG_FEATURE_NAMES)
    assert len(sub_lftg) == 20
    chosen_names = (
        [DD.ALL_STATIC_FEATURE_NAMES[c] for c in sub_static]
        + [MC.S11_MHTR_FEATURE_NAMES[c] for c in sub_s11]
        + [PTHA.PTHA_FEATURE_NAMES[c] for c in sub_ptha]
        + [L17.S17_LFTG_FEATURE_NAMES[c] for c in sub_lftg]
    )
    assert not (set(chosen_names) & set(SCGF.STRICT_TOPO_FEATURE_NAMES))


def test_bayes_prior_calibration_exact_roundtrip():
    fp = np.ones((2, 3), dtype=bool)
    p = np.array([[0.0, 0.05, 0.25], [0.50, 0.85, 1.0]], dtype=np.float32)
    cal = PTHA.prior_shift_calibrate_surface(p, footprint=fp, pi_true=0.022, pi_sample=0.50)
    back = PTHA.prior_shift_calibrate_surface(cal, footprint=fp, pi_true=0.50, pi_sample=0.022)
    assert cal.dtype == np.float32
    assert np.isfinite(cal).all()
    assert float(cal.min()) >= 0.0 and float(cal.max()) <= 1.0
    assert np.allclose(back.ravel()[1:-1], p.ravel()[1:-1], atol=1e-4)


def test_s17_preregistration_and_runcard_invariants():
    import hashlib
    import json
    from gems91 import readiness as RD

    prereg = ROOT / "docs" / "HYPOTHESES_S17_LFTG.md"
    card_path = ROOT / "docs" / "run-card-S17-LFTG.json"
    ev_path = ROOT / "evidence" / "s17_lftg_20261025.json"
    assert prereg.is_file() and card_path.is_file() and ev_path.is_file()

    prereg_sha = hashlib.sha256(prereg.read_bytes()).hexdigest()
    assert prereg_sha == "951a49b1f94b8a78f7b244d51efcb19dec86eadd449ac43feeab55e0d1806eef"

    card = json.loads(card_path.read_text(encoding="utf-8"))
    ev = json.loads(ev_path.read_text(encoding="utf-8"))
    assert card == ev
    assert card["lane"]["preregistration_sha256"] == prereg_sha
    assert card["budget"]["experiments_run"] == 3 <= card["budget"]["max_experiments"]
    assert card["budget"]["elapsed_seconds"] <= card["budget"]["max_seconds"] == 7200.0
    assert card["organizer_confirmed_score"] is None
    assert len(card["submission_note"]) <= 140
    assert card["verdict"] == "negative"
    assert card["ok_to_download_research"] is True
    assert card["ok_to_submit"] is False
    assert card["submission_ready"] is False

    h = card["holdout_dti"]
    assert h["label"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["withheld_positives"] == 60988
    assert h["ci95"][0] <= h["value"] <= h["ci95"][1]
    for arm in h["all_arms"].values():
        assert arm["label"] == "HOLDOUT-DTI"
        assert arm["ci95"][0] <= arm["dti"] <= arm["ci95"][1]

    g = RD.gates(card)
    # Preserve the recorded six historical gates while enforcing the new
    # independent buffered-context gate on this pre-correction receipt.
    assert {k: v for k, v in g.items() if k != "buffered_context"} == card["shared_readiness_gates"]
    assert g["buffered_context"] is False
    assert g["format"] is True
    assert g["canary"] is True
    assert RD.submission_ready(card) is False


def test_s17_geotiff_and_zip_automated_validation():
    import hashlib
    import json
    import stat
    import zipfile

    card = json.loads((ROOT / "docs" / "run-card-S17-LFTG.json").read_text(encoding="utf-8"))
    tif_path = ROOT / "docs" / card["artifact"]["file"]
    zip_path = ROOT / "docs" / card["artifact"]["zip"]
    assert tif_path.is_file() and zip_path.is_file()

    # World-readable (0o004) required for GitHub Pages static tarball deployment
    for p in (tif_path, zip_path):
        mode = stat.S_IMODE(p.stat().st_mode)
        assert mode & stat.S_IROTH, f"{p} is not world-readable: {oct(mode)}"

    tif_bytes = tif_path.read_bytes()
    assert hashlib.sha256(tif_bytes).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["artifact"]["zip_sha256"]

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert zf.read(names[0]) == tif_bytes

    with rasterio.open(tif_path) as src:
        assert src.count == 1
        assert src.dtypes == ("float32",)
        assert str(src.crs) == "EPSG:32611"
        assert (src.height, src.width) == (3730, 3292)
        assert tuple(src.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert src.nodata is None
        arr = src.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        uniq = np.unique(arr)
        assert np.array_equal(uniq, np.array([0.0, 1.0], dtype=np.float32))
        assert int((arr == 1.0).sum()) == 37654


def test_s17_portal_pages_and_local_links():
    import json
    import re

    card = json.loads((ROOT / "docs" / "run-card-S17-LFTG.json").read_text(encoding="utf-8"))
    for name in ("s17-lftg.html", "s17-lftg-executive-summary.html"):
        page_path = ROOT / "docs" / name
        assert page_path.is_file()
        html = page_path.read_text(encoding="utf-8")
        assert "OK TO DOWNLOAD: YES" in html
        assert "OK TO SUBMIT: NO" in html
        assert "NOT OK TO SUBMIT" in html
        assert html.count('data-submission-ready="false"') == 1
        assert 'data-submission-ready="true"' not in html
        assert card["artifact"]["file"] in html
        assert card["artifact"]["zip"] in html
        assert card["raster_sha256"] in html

        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            clean = href.split("#", 1)[0]
            assert (ROOT / "docs" / clean).exists(), f"Dead local link {href} in {name}"

