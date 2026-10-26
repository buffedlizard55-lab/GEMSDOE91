"""Unit, physics-invariance, byte-integrity, and portal contract tests for Session 20 (`S20-RHTW`)."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems91 import rhtw20
from scripts import verify_s20

ROOT = Path(__file__).resolve().parents[1]


def _write_synthetic_inputs(tmp_path: Path, scramble_topo: bool = False) -> tuple[Path, Path, np.ndarray]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    h, w = 48, 52
    rng = np.random.default_rng(20261026)
    fp = np.ones((h, w), dtype=bool)
    fp[:3, :] = False
    fp[:, :3] = False

    feats_path = tmp_path / "features19.tif"
    transform = from_origin(243350.0, 4508550.0, 100.0, 100.0)
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")

    bands = np.zeros((19, h, w), dtype=np.float32)
    for b in range(19):
        bands[b] = (
            0.6 * np.sin(0.18 * xx + 0.11 * (b + 1))
            + 0.4 * np.cos(0.15 * yy - 0.07 * b)
            + 0.08 * rng.standard_normal((h, w))
        ).astype(np.float32)
    # Realistic non-negative bands
    bands[2] = np.abs(bands[2]) * 1.5  # B03 tmi_hg (nT / 200 m)
    bands[4] = np.abs(bands[4]) * 0.02  # B05 iso_grav_anom_slope
    bands[5] = np.abs(bands[5]) + 1.0  # B06 tc
    bands[9] = np.abs(bands[9]) * 5.0  # B10 deq
    bands[14] = np.abs(bands[14]) * 400.0 + 30.0  # B15 depth_to_base_surf (m)
    bands[16] = np.abs(bands[16]) + 0.1  # B17 cond_surf
    bands[18] = np.abs(bands[18]) * 4.0  # B19 det_elev_slope (deg)

    if scramble_topo:
        topo_rng = np.random.default_rng(999999)
        bands[11] = (topo_rng.uniform(-900.0, 1400.0, size=(h, w))).astype(np.float32)  # B12 det_elev (1-based 12)
        bands[18] = (topo_rng.uniform(0.0, 45.0, size=(h, w))).astype(np.float32)  # B19 det_elev_slope (1-based 19)

    bands[:, ~fp] = np.nan
    with rasterio.open(
        feats_path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=19,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
    ) as dst:
        dst.write(bands)

    gdr_csv = tmp_path / "gdr.csv"
    with gdr_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "row",
                "col",
                "temp_c",
                "geothermquartz_c",
                "geothermchalc_c",
                "geothermcat_c",
                "dist_known_fault_px",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "row": 24,
                "col": 26,
                "temp_c": "42.0",
                "geothermquartz_c": "148.0",
                "geothermchalc_c": "122.0",
                "geothermcat_c": "165.0",
                "dist_known_fault_px": "0.0" if not scramble_topo else "99999.0",
            }
        )
    return feats_path, gdr_csv, fp


def test_riesz_harmonic_gravity_reconstructs_analytic_vertical_derivative():
    """For harmonic 2D potential G(x, y) = cos(kx * x + ky * y), dG/dz at z=0 equals |k| * G(x, y)."""
    h, w = 96, 96
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")
    kx = 2.0 * math.pi / 24.0
    ky = 2.0 * math.pi / 32.0
    phase = kx * xx + ky * yy
    pot = np.cos(phase)
    gx = -kx * np.sin(phase)
    gy = -ky * np.sin(phase)
    fp = np.ones((h, w), dtype=bool)

    worms = rhtw20.riesz_harmonic_gravity_worms(gx, gy, fp)
    # Interior crop avoids reflect-padding boundary effects; note small Nyquist anti-ringing factor
    interior = slice(20, -20), slice(20, -20)
    k_mag = math.hypot(kx, ky)
    taper = math.exp(-0.35 * (k_mag / math.pi) ** 2)
    expected_gz0 = (k_mag * taper) * pot
    corr = float(np.corrcoef(worms["gz_0m"][interior].ravel(), expected_gz0[interior].ravel())[0, 1])
    rel_err = float(
        np.linalg.norm(worms["gz_0m"][interior] - expected_gz0[interior])
        / np.linalg.norm(expected_gz0[interior])
    )
    assert corr > 0.998
    assert rel_err < 0.06


def test_subsurface_specialist_bitwise_zero_dependence_on_b12_b19_and_dist_known_fault(tmp_path: Path):
    """SUB_E1_COLS (0..43) and SUB_E2_COLS (0..51) must have bitwise 0.0 diff when B12, B19, and dist_known_fault_px change."""
    f1, g1, fp1 = _write_synthetic_inputs(tmp_path / "run1", scramble_topo=False)
    f2, g2, fp2 = _write_synthetic_inputs(tmp_path / "run2", scramble_topo=True)

    X1, names1, wb1 = rhtw20.build_or_load_s20_features(f1, g1, fp1, tmp_path / "cache1")
    X2, names2, wb2 = rhtw20.build_or_load_s20_features(f2, g2, fp2, tmp_path / "cache2")

    assert names1 == names2 == rhtw20.ALL_STATIC_FEATURE_NAMES
    assert X1.shape == X2.shape == (int(fp1.sum()), 72)

    sub_diff = float(np.max(np.abs(np.asarray(X1[:, rhtw20.SUB_E2_COLS], dtype=np.float32) - np.asarray(X2[:, rhtw20.SUB_E2_COLS], dtype=np.float32))))
    wb_diff = float(np.max(np.abs(wb1 - wb2)))
    topo_diff = float(np.max(np.abs(np.asarray(X1[:, 52:72], dtype=np.float32) - np.asarray(X2[:, 52:72], dtype=np.float32))))

    assert sub_diff == 0.0, f"Subsurface columns leaked B12/B19 or dist_known_fault_px: max_diff={sub_diff}"
    assert wb_diff == 0.0, f"Subsurface worm bonus leaked B12/B19: max_diff={wb_diff}"
    assert topo_diff > 0.5, "Topographic columns failed to respond to scrambled B12/B19"


def test_fold_safe_visible_ftrs_enforces_collar_and_never_uses_hidden_faults():
    h, w = 48, 48
    fp = np.ones((h, w), dtype=bool)
    vis = np.zeros((h, w), dtype=bool)
    vis[20, 8:18] = True  # E-W visible segment
    vis[23, 22:32] = True  # En-echelon step-over visible segment
    sub_prob = np.full((h, w), 0.35, dtype=np.float32)

    f_clean = rhtw20.compute_fold_safe_visible_ftrs(vis, sub_prob, fp, collar_guard_px=2.5)
    assert f_clean.shape == (h * w, 3)
    assert np.isfinite(f_clean).all()

    # Every pixel within <= 2.5 px of visible faults must be strictly 0.0
    from scipy.ndimage import distance_transform_edt

    d_vis = distance_transform_edt(~vis).ravel()
    assert float(np.max(np.abs(f_clean[d_vis <= 2.5]))) == 0.0
    assert float(f_clean.max()) > 0.0


def test_s20_published_artifact_run_card_and_nine_sites_matrix():
    report = verify_s20.verify(with_data=(ROOT / "data/official/sample_submission.tif").is_file())
    assert report["status"] == "PASS"
    assert report["ok_to_download"] is True
    assert report["ok_to_submit"] is False
    assert report["positive_pixels"] == 37654

    matrix = json.loads((ROOT / "docs/s20_rhtw/nine_sites_forensic_matrix.json").read_text())
    expected_9_sites = {
        "GEMSDOE24",
        "GEMSDOE25",
        "GEMSDOE27",
        "GEMSDOE28",
        "GEMSDOE30",
        "GEMSDOE31",
        "GEMSDOE32",
        "GEMSDOE33",
        "GEMSDOE36",
    }
    audited_repos = {rec["repo"] for rec in matrix["forensic_rasters"]}
    assert expected_9_sites.issubset(audited_repos)
    # Strict RFC 8259 JSON check (no bare NaN/Infinity tokens)
    json.dumps(matrix, allow_nan=False)

    for html_rel in ("docs/s20-rhtw-index-src.html", "docs/s20-rhtw-exec-src.html"):
        html = (ROOT / html_rel).read_text()
        assert "OK TO DOWNLOAD: YES" in html
        assert "OK TO SUBMIT: NO" in html
        assert html.count('data-submission-ready="false"') == 1
        assert "gems91-s20-rhtw-e3-20261026T043618Z-4d501134-zeros" in html
        for site in sorted(expected_9_sites):
            assert site in html, f"{site} missing from {html_rel}"


def test_verify_s20_rejects_tampered_ok_to_submit(monkeypatch: pytest.MonkeyPatch):
    orig = verify_s20.read_json

    def tampered(rel: str):
        data = orig(rel)
        if rel == "docs/run-card-S20-RHTW.json":
            data = dict(data)
            data["ok_to_submit"] = True
        return data

    monkeypatch.setattr(verify_s20, "read_json", tampered)
    with pytest.raises(ValueError, match="Negative/unapproved candidate promoted"):
        verify_s20.verify(with_data=False)
