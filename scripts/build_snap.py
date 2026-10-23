#!/usr/bin/env python3
"""SNAP axis on R0: three matched arms that move dots <= 2 px onto a gradient crest.

Parent R0 = ``h33-h33-2-b2`` (GEMSDOE32), 37,654 unit-mass dots,
sha256 ``baeae321...`` (NaN) / ``c55bafc4...`` (zeros), CLAIM 0.2778.

Driver (sponsor-provided, no external licensing): bands 3 ``tmi_hg`` and 18
``iso_grav_anom_hg`` of the pinned GeoDAWN feature stack, each |.|-log1p'd,
nearest-filled, high-passed against a 600 m Gaussian (so only the LOCAL crest can
win), robustly scaled, smoothed at 1.5 px, and averaged.

Arms (all radius <= 2 px, count fixed, collar quarantined per IR-91-27)
-----------------------------------------------------------------------
s2c     crest mode: move only to a 3x3 local maximum of the combined driver.
        The literal "edge crest" snap; least invasive.
s2q75   window-max mode, gain threshold at the 75th percentile of per-dot window
        gain: measured 4,495 dots (11.9 %) move.
s2f     window-max mode, no threshold: every eligible dot goes to the strongest
        cell in its window. Measured 35,174 dots (93.4 %) move; pre-registered
        because the SGMC control predicts it is the worst of the three.

Usage
-----
    python3 scripts/build_snap.py --build
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import validate_raster as vr_mod  # noqa: E402
from gems91 import geom, io, proxy, release_gates as gates, relief, snap  # noqa: E402

MANIFEST_PATH = ROOT / "registry" / "data_manifest.json"
DATA = ROOT / "data"

PARENT_TAG = "h33-h33-2-b2"
PARENT_DOTS = 37654
BUILD_DATE = "20261023"
CLAIMED_LIVE = 0.2778
SHRINK = 0.5  # surrogate-to-live shrink; SGMC is a different fault population

REQUIRED_PINS = (
    "sample_submission",
    "existing_faults",
    "training_features",
    "parent_r0_zeros",
    "parent_r0_nan",
    "anc_h19_5",
    "anc_h19_4",
    "anc_h16_1",
    "anc_d2_8",
    "anc_solo_d2_8",
    "sgmc_faults_control",
)

ARMS = {
    "s2c": {
        "mode": "lmax",
        "quantile": None,
        "predicted": "+0.000",
        "range": "[-0.006,+0.006]",
        "label": "crest",
        "rationale": (
            "Snap only to a 3x3 local maximum of the combined TMI+gravity horizontal-gradient "
            "field; tests whether the dots are offset from LOCAL edge crests without pulling "
            "them along regional slopes."
        ),
    },
    "s2q75": {
        "mode": "max",
        "quantile": 0.75,
        "predicted": "-0.004",
        "range": "[-0.012,+0.005]",
        "label": "maxq75",
        "rationale": (
            "Window-max snap for the quarter of eligible dots with the largest driver gain; "
            "brackets the dose between the crest snap and the full re-layout."
        ),
    },
    "s2f": {
        "mode": "max",
        "quantile": None,
        "predicted": "-0.014",
        "range": "[-0.028,+0.004]",
        "label": "maxfull",
        "rationale": (
            "Full window-max snap, every eligible dot to the strongest cell within 2 px. "
            "Pre-registered extreme arm: the SGMC control says it is the worst locator."
        ),
    },
}


def verify_pinned_inputs() -> dict[str, Path]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in manifest["files"]}
    paths: dict[str, Path] = {}
    for fid in REQUIRED_PINS:
        entry = by_id[fid]
        p = DATA / entry["local_subpath"]
        if not p.is_file():
            raise SystemExit(f"STOP: missing pinned input {fid} at {p}; run scripts/restore_data.py")
        size = p.stat().st_size
        digest = io.sha256_file(p)
        if size != entry["bytes"] or digest != entry["sha256"]:
            raise SystemExit(
                f"STOP: pin mismatch on {fid}: got {digest} ({size} B), "
                f"expected {entry['sha256']} ({entry['bytes']} B)"
            )
        paths[fid] = p
    return paths


def verify_parent_lineage(paths: dict[str, Path], cat: np.ndarray, dcat: np.ndarray) -> dict:
    parent_nan = io.dot_mask(io.read_grid(paths["parent_r0_nan"]))
    parent_zeros = io.dot_mask(io.read_grid(paths["parent_r0_zeros"]))
    out = {
        "parent_sha256_nan": io.sha256_file(paths["parent_r0_nan"]),
        "parent_sha256_zeros": io.sha256_file(paths["parent_r0_zeros"]),
        "parent_dot_digest": io.dot_digest(parent_nan),
        "n_dots": int(parent_nan.sum()),
        "twins_identical": bool(np.array_equal(parent_nan, parent_zeros)),
        "dots_on_catalogue": int((parent_nan & cat).sum()),
        "min_catalogue_distance_px": round(float(dcat[parent_nan].min()), 6),
        "collar_2_to_3px": int((parent_nan & (dcat > 2.0) & (dcat <= 3.0)).sum()),
        "rebuilt_from": {},
    }
    for name, key in (("d2.8", "anc_d2_8"), ("solo_d2.8", "anc_solo_d2_8")):
        anc = io.dot_mask(io.read_grid(paths[key]))
        kept = anc & (dcat > geom.CATALOGUE_FLOOR_PX)
        out["rebuilt_from"][name] = {
            "n_ancestor_dots": int(anc.sum()),
            "n_after_collar": int(kept.sum()),
            "identical_to_parent": bool(np.array_equal(kept, parent_nan)),
        }
    if not (
        out["twins_identical"]
        and out["n_dots"] == PARENT_DOTS
        and out["dots_on_catalogue"] == 0
        and out["collar_2_to_3px"] == 2171
        and all(v["identical_to_parent"] for v in out["rebuilt_from"].values())
    ):
        raise SystemExit(f"STOP: parent R0 verification failed (brief section 5): {out}")
    return out


def build_drivers(paths: dict[str, Path], footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Combined local edge response; one driver shared by all three arms."""
    with rasterio.open(str(paths["training_features"])) as src:
        tmi_hg = src.read(3)
        grav_hg = src.read(18)
    d_tmi = snap.prepare_driver(tmi_hg, footprint, signed=False, high_pass_sigma_px=8.0)
    d_grav = snap.prepare_driver(grav_hg, footprint, signed=True, high_pass_sigma_px=8.0)
    smooth = 1.5
    d_tmi = np.where(
        footprint, ndi.gaussian_filter(np.where(np.isfinite(d_tmi), d_tmi, 0.0), smooth), -np.inf
    )
    d_grav = np.where(
        footprint, ndi.gaussian_filter(np.where(np.isfinite(d_grav), d_grav, 0.0), smooth), -np.inf
    )
    return {
        "tmi_hg": d_tmi.astype(np.float64),
        "iso_grav_anom_hg": d_grav.astype(np.float64),
        "combined": snap.combine_drivers([d_tmi, d_grav], footprint),
    }


def per_dot_gain(parent: np.ndarray, dcat: np.ndarray, driver: np.ndarray,
                 radius: float = 2.0) -> np.ndarray:
    """Raw best-in-window driver gain for each eligible dot (dose threshold basis)."""
    eligible = parent & (dcat > geom.CATALOGUE_FLOOR_PX)
    ys, xs = np.nonzero(eligible)
    n = int(np.ceil(radius))
    out = np.empty(len(ys), dtype=np.float64)
    h, w = parent.shape
    for k, (y, x) in enumerate(zip(ys, xs)):
        y0, y1 = max(0, y - n), min(h, y + n + 1)
        x0, x1 = max(0, x - n), min(w, x + n + 1)
        out[k] = float(driver[y0:y1, x0:x1].max()) - float(driver[y, x])
    return out


def single_feature_canary(feat_path: Path, footprint: np.ndarray, cat: np.ndarray,
                          *, stride: int = 25) -> dict[str, object]:
    """Brief section 6 leakage canary: any single band with AUC > 0.90 => stop."""
    ys = cat[footprint][::stride].astype(np.float64)
    aucs: dict[str, float] = {}
    with rasterio.open(str(feat_path)) as src:
        for b in range(1, src.count + 1):
            name = src.tags(b).get("band_name") or f"band_{b}"
            vals = src.read(b)[footprint][::stride]
            ok = np.isfinite(vals) & (vals > -1e30)
            raw = proxy._auc(vals[ok].astype(np.float64), ys[ok])
            aucs[name] = round(float(max(raw, 1.0 - raw)), 4)
    max_name = max(aucs, key=aucs.get)
    if aucs[max_name] > 0.90:
        raise SystemExit(f"STOP: leakage canary on {max_name} AUC={aucs[max_name]:.4f} > 0.90")
    return {"max_symmetric_auc": aucs[max_name], "max_feature": max_name,
            "stop_threshold": 0.90, "stride": stride,
            "n_sampled_px": int(len(ys)), "symmetric_aucs": aucs}


def update_release_manifest(new_entries: list[dict[str, object]]) -> None:
    manifest_p = ROOT / "releases" / "MANIFEST.json"
    existing = {}
    if manifest_p.is_file():
        cur = json.loads(manifest_p.read_text(encoding="utf-8"))
        for f in cur.get("files", []):
            existing[f["file"]] = f
    for f in new_entries:
        existing[f["file"]] = f
    payload = {
        "schema_version": 1,
        "generated_utc": "2026-10-23T23:30:00Z",
        "note": (
            "Releases are NOT committed (this repo does not publish derived copies of "
            "competition rasters). These hashes are the contract: rebuild with "
            "`python3 scripts/restore_data.py && python3 scripts/build_snap.py --build` "
            "and every sha256 below must reappear byte for byte. CI enforces this."
        ),
        "parent": "h33-h33-2-b2 (e5eb6e7e)",
        "files": [existing[k] for k in sorted(existing)],
    }
    manifest_p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_ledger_rows(rows: list[dict[str, object]]) -> int:
    ledger = ROOT / "ledger" / "submissions.csv"
    existing: list[dict[str, str]] = []
    newline = "\n"
    if ledger.is_file():
        raw = ledger.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            existing = list(csv.DictReader(fh))
    fieldnames = list(existing[0].keys()) if existing else list(rows[0].keys())
    for r in rows:
        for col in r:
            if col not in fieldnames:
                fieldnames.append(col)
    by_id = {r["id"]: i for i, r in enumerate(existing)}
    added = 0
    for r in rows:
        formatted = {k: str(r.get(k, "")) for k in fieldnames}
        if r["id"] in by_id:
            existing[by_id[r["id"]]] = formatted
        else:
            existing.append(formatted)
            added += 1
    with ledger.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator=newline)
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return added


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true", help="verify pins, build 3 SNAP arms, run gates")
    ap.add_argument("--skip-canary", action="store_true", help="skip the 19-band leakage canary")
    args = ap.parse_args(argv)
    if not args.build:
        print(__doc__)
        return 0

    paths = verify_pinned_inputs()
    template = io.read_grid(paths["sample_submission"])
    footprint = geom.footprint_mask(template)
    cat = geom.catalogue_mask(io.read_grid(paths["existing_faults"]))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(paths["parent_r0_nan"]))
    lineage_report = verify_parent_lineage(paths, cat, dcat)

    drivers = build_drivers(paths, footprint)
    driver = drivers["combined"]
    gains = per_dot_gain(parent, dcat, driver)

    feat_canary = (
        None if args.skip_canary else single_feature_canary(paths["training_features"], footprint, cat)
    )

    with rasterio.open(str(paths["sgmc_faults_control"])) as src:
        sgmc_off = (src.read(1) > 0) & footprint & (dcat > 3.0)
    d_sgmc = ndi.distance_transform_edt(~sgmc_off)
    r0_sgmc = relief.fast_binary_dti(parent, sgmc_off, d_truth=d_sgmc)
    r0_hr = proxy.hide_and_recover(parent, cat, footprint)

    releases_dir = ROOT / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)

    built: dict[str, dict] = {}
    manifest_entries: list[dict[str, object]] = []
    ledger_rows: list[dict[str, object]] = []

    for key, cfg in ARMS.items():
        min_gain = (
            0.0 if cfg["quantile"] is None else float(np.quantile(gains, cfg["quantile"]))
        )
        res = snap.snap_dots(
            parent, footprint, dcat, driver,
            radius=2.0, min_cat_px=3.0, min_gain=min_gain, mode=cfg["mode"],
        )
        dots = res.dots
        st = res.stats
        if st["n_dots"] != PARENT_DOTS:
            raise SystemExit(f"STOP: {key} changed the dot count: {st}")
        if st["collar_before"] != 2171 or st["collar_after"] != 2171:
            raise SystemExit(f"STOP: {key} moved collar dots (IR-91-27): {st}")
        if st["n_moved"] == 0:
            raise SystemExit(f"STOP: {key} is a no-op on this parent")
        diff = gates.parent_diff(parent, dots)

        tmp_nan = releases_dir / f"_tmp-snap-{key}-nan.tif"
        tmp_zer = releases_dir / f"_tmp-snap-{key}-zeros.tif"
        arr_nan = np.where(footprint, dots.astype(np.float32), np.nan)
        io.write_float32(tmp_nan, arr_nan, encoding="nan", template=paths["sample_submission"])
        io.write_float32(tmp_zer, arr_nan, encoding="zeros", template=paths["sample_submission"])
        sha_nan = io.sha256_file(tmp_nan)
        sha_zer = io.sha256_file(tmp_zer)
        stem = f"{PARENT_TAG}-SNAP{key}-{BUILD_DATE}-{sha_nan[:8]}"
        final_nan = releases_dir / f"{stem}.tif"
        final_zer = releases_dir / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)

        g_nan = gates.validate_release(
            final_nan, template=paths["sample_submission"], catalogue=cat,
            encoding="nan", expect_dots=PARENT_DOTS,
            ledger=ROOT / "ledger" / "submissions.csv", own_id=stem,
        )
        g_zer = gates.validate_release(
            final_zer, template=paths["sample_submission"], catalogue=cat,
            encoding="zeros", expect_dots=PARENT_DOTS,
            ledger=ROOT / "ledger" / "submissions.csv", own_id=stem,
        )
        if not (g_nan["PASS"] and g_zer["PASS"]):
            raise SystemExit(f"GATE FAIL (release_gates) {stem}: nan={g_nan['failed']} zeros={g_zer['failed']}")

        vr_nan = vr_mod.validate_raster(
            final_nan, paths["sample_submission"], catalogue=paths["existing_faults"],
            ledger_csv=ROOT / "ledger" / "submissions.csv", parent=paths["parent_r0_nan"],
        )
        vr_zer = vr_mod.validate_raster(
            final_zer, paths["sample_submission"], catalogue=paths["existing_faults"],
            ledger_csv=ROOT / "ledger" / "submissions.csv", parent=paths["parent_r0_nan"],
            allow_zeros_outside=True,
        )
        if not (vr_nan.ok and vr_zer.ok):
            raise SystemExit(f"GATE FAIL (validate_raster) {stem}:\n{vr_nan.text()}\n{vr_zer.text()}")

        sg_arm = relief.fast_binary_dti(dots, sgmc_off, d_truth=d_sgmc)
        hr_fixed = proxy.hide_and_recover(dots, cat, footprint)
        moved_mask = dots & ~parent
        dot_canary = proxy.canary(moved_mask, dots, cat)
        rel_t = (sg_arm["T"] - r0_sgmc["T"]) / r0_sgmc["T"]
        live_model = CLAIMED_LIVE * rel_t * SHRINK
        predicted = cfg["predicted"]
        note = (
            f"{PARENT_TAG}; SNAP {cfg['label']}: {st['n_moved']} dots ({st['pct_moved']:.1f}%) "
            f"moved {st['mean_displacement_px']:.2f}px mean, count fixed; pred MODEL:{predicted}"
        )
        assert len(note) <= 140, f"form_note exceeds 140 chars ({len(note)}): {note}"

        built[key] = {
            "id": stem,
            "axis": "SNAP",
            "value": key,
            "mode": cfg["mode"],
            "quantile": cfg["quantile"],
            "min_gain_used": round(min_gain, 6),
            "stats": st,
            "parent_diff": diff,
            "sha256_nan": sha_nan,
            "sha256_zeros": sha_zer,
            "bytes_nan": final_nan.stat().st_size,
            "bytes_zeros": final_zer.stat().st_size,
            "dot_set_digest": g_nan["dot_set_digest"],
            "predicted_change_MODEL": f"MODEL:{predicted}",
            "predicted_range": cfg["range"],
            "rationale": cfg["rationale"],
            "form_note": note,
            "report_only": {
                "sgmc_off_catalogue_dti": round(sg_arm["dti"], 6),
                "sgmc_delta_vs_r0": round(sg_arm["dti"] - r0_sgmc["dti"], 6),
                "sgmc_T": round(sg_arm["T"], 3),
                "sgmc_T_rel_change": round(rel_t, 6),
                "live_model_from_T_ratio": round(live_model, 5),
                "fixed_catalogue_proxy": hr_fixed,
                "proxy_delta_vs_r0": round(hr_fixed["proxy_mean_credit"] - r0_hr["proxy_mean_credit"], 6),
                "moved_dot_canary": dot_canary,
                "redundancy": proxy.redundancy(dots),
                "block_density_cv_1km": proxy.block_density_cv(dots, footprint, 10),
                "block_density_cv_5km": proxy.block_density_cv(dots, footprint, 50),
            },
            "gates_nan": {k: g_nan[k] for k in (
                "PASS", "failed", "crs_matches_template", "shape_matches_template",
                "transform_matches_template", "single_band", "dtype_float32",
                "no_nan_inside_footprint", "nan_outside_footprint", "values_within_0_1",
                "unit_mass_dots", "zero_catalogue_mass", "min_catalogue_distance_px",
                "catalogue_floor_respected", "count_matches_parent", "sha256_not_in_ledger",
            )},
            "gates_zeros": {k: g_zer[k] for k in (
                "PASS", "failed", "zeros_outside_footprint", "sha256_not_in_ledger",
            )},
            "validate_raster_14_of_14": bool(vr_nan.ok and vr_zer.ok),
        }

        manifest_entries.extend([
            {"file": final_nan.name, "sha256": sha_nan, "bytes": final_nan.stat().st_size},
            {"file": final_zer.name, "sha256": sha_zer, "bytes": final_zer.stat().st_size},
        ])
        ledger_rows.append({
            "id": stem,
            "parent": PARENT_TAG,
            "axis": "SNAP",
            "value": key,
            "n_dots": PARENT_DOTS,
            "pct_changed": f"{st['pct_moved']:.2f}",
            "pct_relocated": f"{st['pct_moved']:.2f}",
            "sha256": sha_nan,
            "sha256_zeros": sha_zer,
            "status": "BUILT",
            "predicted_change": f"MODEL:{predicted}",
            "predicted_range": cfg["range"],
            "ranking_basis": (
                "driver=0.5*z(hp600m log1p tmi_hg)+0.5*z(hp600m log1p |iso_grav_anom_hg|), "
                "smoothed 1.5px; targets d_cat>3px; collar quarantined (IR-91-27)"
            ),
            "receipt_score": "",
            "receipt_date": "",
            "date": "2026-10-23",
            "form_note": note,
            "evidence_class": "MODEL",
            "source": "SESSION 6 (arena/9b8f7d01-gemsdoe91)",
            "notes": (
                f"{cfg['mode']} mode; moved {st['n_moved']} of {st['n_eligible']} eligible "
                f"({st['pct_moved']:.2f}%, Hamming {st['pct_hamming']:.2f}%), mean displacement "
                f"{st['mean_displacement_px']:.4f}px, max {st['max_displacement_px']:.1f}px; "
                f"collar {st['collar_before']}->{st['collar_after']}; SGMC_off dDTI "
                f"{sg_arm['dti'] - r0_sgmc['dti']:+.5f} PROXY."
            ),
            "source_url": "",
        })
        print(
            f"{stem}: moved={st['n_moved']} ({st['pct_moved']:.2f}%) disp={st['mean_displacement_px']:.3f} "
            f"sgmc_dDTI={sg_arm['dti'] - r0_sgmc['dti']:+.5f} model={live_model:+.4f} pred=MODEL:{predicted}"
        )

    # Determinism: rebuilding the crest arm must give the same dot set.
    again = snap.snap_dots(parent, footprint, dcat, driver, radius=2.0,
                           min_cat_px=3.0, min_gain=0.0, mode="lmax")
    deterministic = bool(np.array_equal(again.dots, io.dot_mask(
        io.read_grid(releases_dir / f"{built['s2c']['id']}.tif"))))
    if not deterministic:
        raise SystemExit("STOP: SNAP build is not deterministic")

    added = append_ledger_rows(ledger_rows)
    update_release_manifest(manifest_entries)

    evidence = {
        "schema": "gems91.snap-evidence.v1",
        "build_date": "2026-10-23",
        "parent": PARENT_TAG,
        "driver": {
            "bands": {"tmi_hg": 3, "iso_grav_anom_hg": 18},
            "high_pass_sigma_px": 8.0,
            "smoothing_sigma_px": 1.5,
            "combination": "equal-weight mean of robust z-scores",
            "radius_px": 2.0,
            "min_catalogue_px_for_targets": 3.0,
            "collar_policy": "dots at d_cat<=3px quarantined in place (IR-91-27)",
        },
        "deterministic_rebuild": deterministic,
        "lineage": lineage_report,
        "r0_baseline": {
            "n_dots": PARENT_DOTS,
            "sgmc_off_catalogue_dti": round(r0_sgmc["dti"], 6),
            "sgmc_T": round(r0_sgmc["T"], 3),
            "sgmc_off_catalogue_n_px": int(sgmc_off.sum()),
            "fixed_catalogue_proxy": r0_hr,
            "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10),
            "block_density_cv_5km": proxy.block_density_cv(parent, footprint, 50),
            "redundancy": proxy.redundancy(parent),
        },
        "single_feature_leakage_canary": feat_canary,
        "arms": built,
    }
    ev_path = ROOT / "evidence" / f"snap_axis_{BUILD_DATE}.json"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    ev_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"\nledger new rows appended: {added}\nevidence: {ev_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
