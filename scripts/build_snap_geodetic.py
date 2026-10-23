#!/usr/bin/env python3
"""SNAP axis on R0 — vertical-gradient (VG) dose ladder at 1 / 2 / 3 px.

Parent R0 = h33-h33-2-b2 (GEMSDOE32), 37,654 unit-mass dots, sha256
``baeae321...c77dd`` (NaN) / ``c55bafc4...6fa9`` (zeros), CLAIM 0.2778.

Why a new field for SNAP
------------------------
Every SNAP row already in the ledger (``w2E1``/``w2S2``/``w2E2``, ``g2f35``/
``d2f35``/``d1f35``, ``ridge2px``/``pot2px``/``scarp2px``) snaps to a
*horizontal*-gradient / slope / curvature composite. No row has ever used the
vertical-gradient bands ``tmi_vg`` (Band 9) and ``iso_grav_anom_vg``
(Band 11), which are the pair whose crest sits closest to the surface trace of
a dipping sheet rather than updip of it. That is the specific failure the SNAP
axis exists to fix (GeoDAWN Area 2 was flown at 400 m line spacing, so a
lineament's position is uncertain by about the kernel radius, R = 300 m).

The edit
--------
* driver  = 0.50 * pct(|Band 9 tmi_vg|) + 0.50 * pct(|Band 11 iso_grav_anom_vg|)
            percentile-ranked inside the footprint; sign removed with |.| because
            the polarity of a VG anomaly depends on remanence / density contrast,
            while the *crest location* does not.
* each dot moves to the highest-driver cell within its own +/-r square window,
  ties broken toward the shortest displacement, r in {1, 2, 3} px;
* count fixed at 37,654; a target must be inside the footprint, unclaimed, and
  strictly more than 3.0 px from the mapped catalogue;
* **the 2,171 dots R0 already holds at 2 < d_cat <= 3 px are frozen**, not moved
  (IR-91-03). Relocating them would silently make this a PRUNE-plus-SNAP edit and
  confound the axis; freezing them holds collar drift at exactly 0, the same
  invariant the RELIEF session used;
* deterministic (row-major processing, no RNG, no seed);
* one arm per radius, so the ladder measures the dose of the same treatment.

Usage
-----
    python3 scripts/build_snap_geodetic.py --build
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

from gems91 import geom, io, proxy, release_gates as gates  # noqa: E402
from gems91 import relief as relief_mod  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import validate_raster as vr_mod  # noqa: E402

MANIFEST_PATH = ROOT / "registry" / "data_manifest.json"
DATA = ROOT / "data"

PARENT_TAG = "h33-h33-2-b2"
PARENT_DOTS = 37654
BUILD_DATE = "20261023"
MIN_CAT_PX = 3.0
VGY_BANDS = (9, 11)          # tmi_vg, iso_grav_anom_vg

REQUIRED_PINS = (
    "sample_submission",
    "existing_faults",
    "training_features",
    "parent_r0_nan",
    "parent_r0_zeros",
    "anc_d2_8",
    "anc_solo_d2_8",
    "sgmc_faults_control",
)

ARMS = {
    "vg1px": {"radius": 1, "predicted": "+0.002", "range": "[-0.004,+0.008]",
              "why": "100 m: inside the organizer's own cell-scale uncertainty, the"
                     " smallest treatment that can still correct a mis-centred dot."},
    "vg2px": {"radius": 2, "predicted": "+0.003", "range": "[-0.005,+0.011]",
              "why": "200 m: the displacement scale a 400 m flight-line geometry"
                     " actually implies for a lineament's mapped position."},
    "vg3px": {"radius": 3, "predicted": "+0.004", "range": "[-0.008,+0.016]",
              "why": "300 m = the full kernel radius R; the largest move that can"
                     " still be argued to be a *position* correction and not a"
                     " relocation to a different structure."},
}
LEDGER_COLS = ["id", "parent", "axis", "value", "n_dots", "pct_changed", "pct_relocated",
               "sha256", "sha256_zeros", "status", "predicted_change", "predicted_range",
               "ranking_basis", "receipt_score", "receipt_date", "date", "form_note",
               "evidence_class", "source", "notes", "source_url"]


def verify_pinned_inputs() -> dict[str, Path]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in manifest["files"]}
    paths: dict[str, Path] = {}
    for fid in REQUIRED_PINS:
        entry = by_id[fid]
        p = DATA / entry["local_subpath"]
        if not p.is_file():
            raise SystemExit(f"STOP: missing pinned input {fid} at {p}; run scripts/restore_data.py")
        size, digest = p.stat().st_size, io.sha256_file(p)
        if size != entry["bytes"] or digest != entry["sha256"]:
            raise SystemExit(f"STOP: pin mismatch on {fid}: got {digest} ({size} B), "
                             f"expected {entry['sha256']} ({entry['bytes']} B)")
        paths[fid] = p
        print(f"pin ok  {fid:<18} {digest[:16]} {size:>10} B")
    return paths


def pct_rank_in_footprint(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] over footprint cells; NaN outside.

    The feature stack stores -3.4028e38 as its fill sentinel, which is finite, so
    it must be removed explicitly rather than by np.isfinite.
    """
    fp = np.asarray(footprint, dtype=bool)
    a = np.asarray(arr, dtype=np.float64)
    valid = fp & np.isfinite(a) & (a > -1e30)
    if not valid.any():
        raise ValueError("band has no valid values inside the footprint")
    if np.array_equal(valid, fp):
        filled = np.where(fp, a, np.nan)
    else:
        _, idx = ndi.distance_transform_edt(~valid, return_indices=True)
        filled = np.where(fp, a[idx[0], idx[1]], np.nan)
    pct = np.full(a.shape, np.nan, dtype=np.float64)
    vals = filled[fp]
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(vals.size, dtype=np.float64)
    ranks[order] = np.arange(vals.size, dtype=np.float64) / max(1, vals.size - 1)
    pct[fp] = ranks
    return pct


def snap(parent: np.ndarray, driver: np.ndarray, footprint: np.ndarray,
         dcat: np.ndarray, radius: int, min_cat_px: float = MIN_CAT_PX,
         rng: np.random.Generator | None = None) -> dict:
    """Move each movable dot to the best cell within +/-radius; count preserved.

    ``movable`` is every dot strictly outside the catalogue collar. R0's inherited
    2 < d_cat <= 3 px dots are frozen, so the collar count is invariant by
    construction. ``rng`` is None for the deterministic local-argmax treatment; pass
    a Generator to get the null arm (a uniformly random legal cell in the same
    window, same radius, same exclusions) used only as a diagnostic.
    """
    h, w = parent.shape
    ok = footprint & (dcat > min_cat_px)
    resp = np.where(np.isfinite(driver), driver, -np.inf)
    movable = parent & (dcat > min_cat_px)
    out = np.zeros_like(parent, dtype=bool)
    # ``cnt`` counts, for every cell, how many dots (finalised OR still waiting at
    # their origin) sit in its 3x3 neighbourhood. A target is spacing-safe iff the
    # count is zero, so R0's own 2 px floor (0 pairs < 2 px, the d2.8 thinning rule)
    # survives the edit exactly. Without this the arms would silently also test
    # redundancy (S up, T saturated) - a different axis.
    cnt = np.zeros((h, w), dtype=np.int16)

    def _stamp(y: int, x: int, delta: int) -> None:
        cnt[max(0, y - 1):y + 2, max(0, x - 1):x + 2] += delta

    ys, xs = np.nonzero(parent)          # row-major, deterministic
    for y, x in zip(ys.tolist(), xs.tolist()):
        _stamp(y, x, 1)
    moved = frozen = 0
    shifts: list[float] = []
    d_before: list[float] = []
    d_after: list[float] = []
    for y, x in zip(ys.tolist(), xs.tolist()):
        _stamp(y, x, -1)                 # this dot's own reservation is released
        y0, y1 = max(0, y - radius), min(h, y + radius + 1)
        x0, x1 = max(0, x - radius), min(w, x + radius + 1)
        gy, gx = np.mgrid[y0:y1, x0:x1]
        dist = np.hypot(gy - y, gx - x)
        legal = ok[y0:y1, x0:x1] & (dist <= float(radius)) & (cnt[y0:y1, x0:x1] == 0)
        if not movable[y, x]:
            out[y, x] = True             # frozen: collared dot keeps its cell
            _stamp(y, x, 1)
            continue
        taken = None
        if rng is None:
            score = np.where(legal, resp[y0:y1, x0:x1] * 1e6 - dist, -np.inf)
            if np.isfinite(score).any():
                dy, dx = divmod(int(np.argmax(score)), score.shape[1])
                taken = (y0 + dy, x0 + dx)
        else:
            cand = np.flatnonzero(legal.ravel())
            if cand.size:
                dy, dx = divmod(int(cand[rng.integers(cand.size)]), legal.shape[1])
                taken = (y0 + dy, x0 + dx)
        if taken is None:
            taken = (y, x)               # stays put: nothing legal inside the window
            frozen += 1
        ny, nx = taken
        out[ny, nx] = True
        _stamp(ny, nx, 1)
        if np.isfinite(driver[y, x]):
            d_before.append(float(driver[y, x]))
        if np.isfinite(driver[ny, nx]):
            d_after.append(float(driver[ny, nx]))
        if (ny, nx) != (y, x):
            moved += 1
            shifts.append(float(np.hypot(ny - y, nx - x)))
    # spacing invariant must hold exactly; report the realised minimum
    yy, xx = np.nonzero(out)
    if yy.size > 1:
        from scipy.spatial import cKDTree
        pts = np.c_[yy, xx].astype(np.float64)
        dnn, _ = cKDTree(pts).query(pts, k=2)
        min_sep_after = float(dnn[:, 1].min())
    else:
        min_sep_after = float("inf")
    n_parent = int(parent.sum())
    xor = int(np.logical_xor(parent, out).sum())
    return {
        "dots": out,
        "n_parent": n_parent,
        "n_dots": int(out.sum()),
        "n_movable": int(movable.sum()),
        "moved": moved,
        "frozen_no_valid_target": frozen,
        "min_separation_after_px": round(min_sep_after, 4),
        "mean_displacement_all_px": round(float(np.sum(shifts)) / max(1, n_parent), 4),
        "mean_displacement_moved_px": round(float(np.mean(shifts)) if shifts else 0.0, 4),
        "max_displacement_px": round(float(np.max(shifts)) if shifts else 0.0, 4),
        "pct_moved": round(100.0 * moved / max(1, n_parent), 4),
        "pct_moved_of_movable": round(100.0 * moved / max(1, int(movable.sum())), 4),
        "pct_hamming": round(100.0 * xor / max(1, n_parent), 4),
        "driver_pct_before": round(float(np.mean(d_before)) if d_before else 0.0, 4),
        "driver_pct_after": round(float(np.mean(d_after)) if d_after else 0.0, 4),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--skip-proxy", action="store_true", help="skip hide-and-recover draws")
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

    # --- parent lineage: nothing is built until R0 is proven, not assumed ------
    parent_sha = io.sha256_file(paths["parent_r0_nan"])
    zeros = io.dot_mask(io.read_grid(paths["parent_r0_zeros"]))
    lineage = {
        "parent_sha256_nan": parent_sha,
        "parent_sha256_zeros": io.sha256_file(paths["parent_r0_zeros"]),
        "parent_dot_digest": io.dot_digest(parent),
        "n_dots": int(parent.sum()),
        "twins_identical": bool(np.array_equal(parent, zeros)),
        "dots_on_catalogue": int((parent & cat).sum()),
        "min_catalogue_distance_px": round(float(dcat[parent].min()), 6),
        "dots_le_3px": int((dcat[parent] <= 3.0).sum()),
        "rebuilt_from": {},
    }
    for name, key in (("d2.8", "anc_d2_8"), ("solo_d2.8", "anc_solo_d2_8")):
        anc = io.dot_mask(io.read_grid(paths[key]))
        kept = anc & (dcat > geom.CATALOGUE_FLOOR_PX)
        lineage["rebuilt_from"][name] = {
            "n_ancestor_dots": int(anc.sum()),
            "n_after_collar": int(kept.sum()),
            "identical_to_parent": bool(np.array_equal(kept, parent)),
        }
    if not (parent_sha == "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
            and lineage["twins_identical"] and lineage["n_dots"] == PARENT_DOTS
            and lineage["dots_on_catalogue"] == 0
            and all(v["identical_to_parent"] for v in lineage["rebuilt_from"].values())):
        raise SystemExit(f"STOP: parent R0 not reproduced (brief section 5): {lineage}")
    print(f"\nR0 verified: {PARENT_DOTS} dots, min d_cat {lineage['min_catalogue_distance_px']:.3f} px, "
          f"{lineage['dots_le_3px']} inherited dots at 2-3 px")

    # --- driver: vertical-gradient composite ----------------------------------
    with rasterio.open(str(paths["training_features"])) as src:
        names = {b: (src.tags(b).get("band_name") or f"band_{b}") for b in range(1, src.count + 1)}
        raw = {b: src.read(b) for b in VGY_BANDS}
        all_band_names = names
        # leakage canary needs every band, read once more per band (streamed)
        canary_aucs: dict[str, float] = {}
        y_sample = cat[footprint][::25].astype(np.float64)
        for b in range(1, src.count + 1):
            vals = src.read(b)[footprint][::25]
            good = np.isfinite(vals) & (vals > -1e30)
            if good.sum() < 10:
                continue
            raw_auc = proxy._auc(vals[good].astype(np.float64), y_sample[good])
            canary_aucs[names[b]] = round(float(max(raw_auc, 1.0 - raw_auc)), 4)
    max_name = max(canary_aucs, key=canary_aucs.get)
    max_auc = canary_aucs[max_name]
    print(f"leakage canary: max symmetric AUC {max_auc:.4f} on {max_name} (stop > 0.90)")
    if max_auc > 0.90:
        raise SystemExit(f"STOP: leakage canary {max_name}={max_auc} > 0.90 (brief section 6)")

    pct = {}
    for b in VGY_BANDS:
        mag = np.abs(raw[b].astype(np.float64))
        mag[raw[b] <= -1e30] = np.nan
        pct[b] = pct_rank_in_footprint(mag, footprint)
        print(f"driver band {b} {all_band_names[b]:<20} |.| pct mean "
              f"{np.nanmean(pct[b]):.4f} at R0 dots {np.nanmean(pct[b][parent]):.4f}")
    driver = 0.5 * np.nan_to_num(pct[VGY_BANDS[0]], nan=0.0) + \
             0.5 * np.nan_to_num(pct[VGY_BANDS[1]], nan=0.0)
    driver[~footprint] = np.nan
    print(f"composite VG driver: mean {np.nanmean(driver[footprint]):.4f}, "
          f"at R0 dots {np.nanmean(driver[parent]):.4f}")

    # --- report-only baselines ------------------------------------------------
    with rasterio.open(str(paths["sgmc_faults_control"])) as src:
        sgmc_off = (src.read(1) > 0) & footprint & (dcat > 3.0)
    d_sgmc = ndi.distance_transform_edt(~sgmc_off)
    r0_sgmc = relief_mod.fast_binary_dti(parent, sgmc_off, d_truth=d_sgmc)
    r0_hr = None if args.skip_proxy else proxy.hide_and_recover(parent, cat, footprint)

    ledger_path = ROOT / "ledger" / "submissions.csv"
    ledger_by_id: dict[str, dict] = {}
    seen_shas: dict[str, str] = {}
    if ledger_path.is_file():
        with ledger_path.open(newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                rid = (row.get("id") or "").strip()
                ledger_by_id[rid] = row
                for key in ("sha256", "sha256_zeros"):
                    sha = (row.get(key) or "").strip()
                    if sha:
                        seen_shas[sha] = rid

    releases = ROOT / "releases"
    releases.mkdir(exist_ok=True)
    evidence_arms: dict[str, dict] = {}
    manifest_entries: list[dict] = []
    ledger_rows: list[dict] = []

    for value, cfg in ARMS.items():
        r = int(cfg["radius"])
        print(f"\n=== SNAP/{value} (radius {r} px) ===")
        res = snap(parent, driver, footprint, dcat, radius=r)
        dots = res["dots"]
        diff = gates.parent_diff(parent, dots)
        print(f"moved {res['moved']} ({res['pct_moved']:.2f}% of parent, "
              f"{res['pct_moved_of_movable']:.2f}% of the {res['n_movable']} movable)  "
              f"frozen {res['frozen_no_valid_target']} "
              f"min-sep {res['min_separation_after_px']:.3f}  "
              f"mean disp {res['mean_displacement_all_px']:.3f} px "
              f"(moved {res['mean_displacement_moved_px']:.3f}, max {res['max_displacement_px']:.2f})  "
              f"driver pct {res['driver_pct_before']:.4f} -> {res['driver_pct_after']:.4f}  "
              f"collar {lineage['dots_le_3px']} -> {int((dcat[dots] <= 3.0).sum())}")

        if res["n_dots"] != PARENT_DOTS:
            raise SystemExit(f"STOP: {value} lost dots ({res['n_dots']}) - SNAP must hold the count")
        if res["min_separation_after_px"] < 2.0 - 1e-9:
            raise SystemExit(f"STOP: {value} breaks R0's 2 px spacing floor "
                             f"({res['min_separation_after_px']} px)")
        if int((dots & cat).sum()) != 0:
            raise SystemExit(f"STOP: {value} emits mass on the catalogue")

        arr_nan = np.where(footprint, dots.astype(np.float32), np.nan)
        tmp_nan = releases / f"_tmp-snapvg-{value}-nan.tif"
        tmp_zer = releases / f"_tmp-snapvg-{value}-zeros.tif"
        io.write_float32(tmp_nan, arr_nan, encoding="nan", template=paths["sample_submission"])
        io.write_float32(tmp_zer, arr_nan, encoding="zeros", template=paths["sample_submission"])
        sha_nan = io.sha256_file(tmp_nan)
        sha_zer = io.sha256_file(tmp_zer)
        stem = f"{PARENT_TAG}-SNAP{value}-{BUILD_DATE}-{sha_nan[:8]}"
        # Idempotent rebuild (CI): the same id back with the same bytes is proof, not a
        # duplicate. A different hash under a known id, or a hash already spent by a
        # DIFFERENT id, is a failure.
        idempotent = stem in ledger_by_id
        if idempotent:
            if (ledger_by_id[stem].get("sha256") or "").strip() != sha_nan:
                raise SystemExit(f"STOP: {stem} exists in the ledger with a DIFFERENT sha256 "
                                 f"- the build is not reproducible")
        else:
            for sha in (sha_nan, sha_zer):
                if sha in seen_shas and seen_shas[sha] != stem:
                    raise SystemExit(f"STOP: hash {sha[:12]} already in the ledger under "
                                     f"{seen_shas[sha]}")
        final_nan = releases / f"{stem}.tif"
        final_zer = releases / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)

        g_nan = gates.validate_release(final_nan, template=paths["sample_submission"], catalogue=cat,
                                       encoding="nan", expect_dots=PARENT_DOTS,
                                       ledger=ledger_path, own_id=stem)
        g_zer = gates.validate_release(final_zer, template=paths["sample_submission"], catalogue=cat,
                                       encoding="zeros", expect_dots=PARENT_DOTS,
                                       ledger=ledger_path, own_id=stem)
        if not (g_nan["PASS"] and g_zer["PASS"]):
            raise SystemExit(f"GATE FAIL release_gates {stem}: nan={g_nan['failed']} zeros={g_zer['failed']}")
        vr_nan = vr_mod.validate_raster(final_nan, paths["sample_submission"],
                                        catalogue=paths["existing_faults"], ledger_csv=ledger_path,
                                        parent=paths["parent_r0_nan"])
        vr_zer = vr_mod.validate_raster(final_zer, paths["sample_submission"],
                                        catalogue=paths["existing_faults"], ledger_csv=ledger_path,
                                        parent=paths["parent_r0_nan"], allow_zeros_outside=True)
        if not (vr_nan.ok and vr_zer.ok):
            raise SystemExit(f"GATE FAIL validate_raster {stem}:\n{vr_nan.text()}\n{vr_zer.text()}")
        print(f"gates PASS: release_gates 2/2 twins, validate_raster {len(vr_nan.gates)}/{len(vr_nan.gates)}")

        hr = None if args.skip_proxy else proxy.hide_and_recover(dots, cat, footprint)
        canary = proxy.canary(dots & ~parent, dots, cat)
        sgmc = relief_mod.fast_binary_dti(dots, sgmc_off, d_truth=d_sgmc)
        print(f"PROXY hide-and-recover {hr['proxy_mean_credit'] if hr else float('nan'):.6f} "
              f"(R0 {r0_hr['proxy_mean_credit'] if r0_hr else float('nan'):.6f}); "
              f"canary {canary['canary_auc']}; SGMC off-cat {sgmc['dti']:.4f} vs R0 {r0_sgmc['dti']:.4f}")

        note = (f"{PARENT_TAG}; SNAP {value}: every dot <= {r} px to the |VG| crest "
                f"(bands 9+11), count {PARENT_DOTS}; pred {cfg['predicted']} MODEL")
        assert len(note) <= 140, (len(note), note)

        evidence_arms[value] = {
            "id": stem, "axis": "SNAP", "value": value, "radius_px": r,
            "driver": "0.50*pct(|Band9 tmi_vg|) + 0.50*pct(|Band11 iso_grav_anom_vg|)",
            "n_dots": res["n_dots"], "n_movable": res["n_movable"],
            "moved": res["moved"],
            "frozen_no_valid_target": res["frozen_no_valid_target"],
            "pct_moved_of_movable": res["pct_moved_of_movable"],
            "min_separation_after_px": res["min_separation_after_px"],
            "mean_displacement_all_px": res["mean_displacement_all_px"],
            "mean_displacement_moved_px": res["mean_displacement_moved_px"],
            "max_displacement_px": res["max_displacement_px"],
            "pct_moved": res["pct_moved"], "pct_hamming": res["pct_hamming"],
            "driver_pct_before": res["driver_pct_before"],
            "driver_pct_after": res["driver_pct_after"],
            "collar_le3_before": lineage["dots_le_3px"],
            "collar_le3_after": int((dcat[dots] <= 3.0).sum()),
            "min_catalogue_distance_px": g_nan["min_catalogue_distance_px"],
            "hamming_vs_parent": diff,
            "sha256_nan": sha_nan, "sha256_zeros": sha_zer,
            "bytes_nan": final_nan.stat().st_size, "bytes_zeros": final_zer.stat().st_size,
            "dot_set_digest": g_nan["dot_set_digest"],
            "predicted_change_MODEL": f"MODEL:{cfg['predicted']}",
            "predicted_range": cfg["range"], "rationale": cfg["why"], "form_note": note,
            "report_only": {
                "hide_and_recover": hr,
                "hide_and_recover_delta_vs_r0": (None if hr is None else
                                                 round(hr["proxy_mean_credit"] - r0_hr["proxy_mean_credit"], 6)),
                "canary": canary,
                "sgmc_off_catalogue_dti": round(sgmc["dti"], 6),
                "sgmc_delta_vs_r0": round(sgmc["dti"] - r0_sgmc["dti"], 6),
                "redundancy": proxy.redundancy(dots),
                "block_density_cv_1km": proxy.block_density_cv(dots, footprint, 10),
                "block_density_cv_5km": proxy.block_density_cv(dots, footprint, 50),
            },
            "gates_nan": {k: g_nan[k] for k in (
                "PASS", "failed", "crs_matches_template", "shape_matches_template",
                "transform_matches_template", "single_band", "dtype_float32",
                "no_nan_inside_footprint", "nan_outside_footprint", "values_within_0_1",
                "unit_mass_dots", "zero_catalogue_mass", "min_catalogue_distance_px",
                "catalogue_floor_respected", "count_matches_parent", "sha256_not_in_ledger")},
            "gates_zeros": {k: g_zer[k] for k in ("PASS", "failed")},
            "validate_raster_all_pass": bool(vr_nan.ok and vr_zer.ok),
        }
        manifest_entries.extend([
            {"file": final_nan.name, "sha256": sha_nan, "bytes": final_nan.stat().st_size},
            {"file": final_zer.name, "sha256": sha_zer, "bytes": final_zer.stat().st_size},
        ])
        if idempotent:
            print(f"  {stem}: already in the ledger with the same sha256 (idempotent rebuild)")
        ledger_rows.append({
            "id": stem, "parent": PARENT_TAG, "axis": "SNAP", "value": value,
            "n_dots": PARENT_DOTS, "pct_changed": f"{res['pct_moved']:.4f}",
            "pct_relocated": f"{res['pct_moved']:.4f}",
            "sha256": sha_nan, "sha256_zeros": sha_zer, "status": "BUILT",
            "predicted_change": f"MODEL:{cfg['predicted']}", "predicted_range": cfg["range"],
            "ranking_basis": ("SNAP driver = 0.50*pct(|Band9 tmi_vg|) + 0.50*pct(|Band11 "
                              "iso_grav_anom_vg|), percentile-ranked in footprint; local argmax "
                              "inside the +/-r window; min displacement tie-break"),
            "receipt_score": "", "receipt_date": "", "date": BUILD_DATE, "form_note": note,
            "evidence_class": "MODEL",
            "source": "SESSION 6 (arena/f8d67617-gemsdoe91) SNAP-VG",
            "notes": (f"SNAP {value} radius {r}px: moved {res['moved']} "
                      f"({res['pct_moved']:.2f}% of parent, {res['pct_moved_of_movable']:.2f}% of movable), "
                      f"frozen {res['frozen_no_valid_target']}, mean displacement "
                      f"{res['mean_displacement_all_px']:.3f}px (moved-only "
                      f"{res['mean_displacement_moved_px']:.3f}px, max {res['max_displacement_px']:.2f}); "
                      f"count fixed 37,654; collar {lineage['dots_le_3px']}->{int((dcat[dots] <= 3.0).sum())}; "
                      f"hamming {res['pct_hamming']:.2f}%; driver percentile "
                      f"{res['driver_pct_before']:.4f}->{res['driver_pct_after']:.4f}; "
                      f"SGMC_off delta {sgmc['dti'] - r0_sgmc['dti']:+.4f} PROXY; pred MODEL:{cfg['predicted']}"),
            "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE91",
        })

    # --- null diagnostic (NOT a candidate: no raster, no ledger row, no slot) ---
    # Same parent, same radius-2 window, same exclusions, same count, same frozen
    # collar - the only difference is that the target is a uniformly random legal
    # cell instead of the strongest driver cell. It separates "the VG field carried
    # position information" from "shuffling 35k dots by <=2 px is itself the effect".
    null_rng = np.random.default_rng(91)
    null = snap(parent, driver, footprint, dcat, radius=2, rng=null_rng)
    null_dots = null["dots"]
    null_hr = None if args.skip_proxy else proxy.hide_and_recover(null_dots, cat, footprint)
    null_sgmc = relief_mod.fast_binary_dti(null_dots, sgmc_off, d_truth=d_sgmc)
    null_diag = {
        "label": "DIAGNOSTIC ONLY - no release, no ledger row, no slot",
        "radius_px": 2, "seed": 91, "moved": null["moved"],
        "pct_moved": null["pct_moved"],
        "mean_displacement_all_px": null["mean_displacement_all_px"],
        "collar_le3": int((dcat[null_dots] <= 3.0).sum()),
        "driver_pct_after": null["driver_pct_after"],
        "hide_and_recover": null_hr,
        "hide_and_recover_delta_vs_r0": (None if null_hr is None else
                                         round(null_hr["proxy_mean_credit"] - r0_hr["proxy_mean_credit"], 6)),
        "sgmc_off_catalogue_dti": round(null_sgmc["dti"], 6),
        "sgmc_delta_vs_r0": round(null_sgmc["dti"] - r0_sgmc["dti"], 6),
    }
    print(f"\nnull diagnostic (radius 2, random legal target): moved {null['moved']} "
          f"driver pct -> {null['driver_pct_after']:.4f}  "
          f"hide-and-recover {null_diag['hide_and_recover_delta_vs_r0']}  "
          f"SGMC {null_diag['sgmc_delta_vs_r0']}")

    # --- release manifest ------------------------------------------------------
    mp = ROOT / "releases" / "MANIFEST.json"
    existing = {}
    if mp.is_file():
        cur = json.loads(mp.read_text(encoding="utf-8"))
        existing = {f["file"]: f for f in cur.get("files", [])}
    for e in manifest_entries:
        existing[e["file"]] = e
    mp.write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": "2026-10-23T23:55:00Z",
        "note": ("Releases are NOT committed (this repo does not publish derived copies of "
                 "competition rasters). These hashes are the contract: rebuild with "
                 "`python3 scripts/restore_data.py && python3 scripts/build_snap_geodetic.py --build` "
                 "and every sha256 below must reappear byte for byte."),
        "parent": "h33-h33-2-b2 (e5eb6e7e)",
        "files": [existing[k] for k in sorted(existing)],
    }, indent=2) + "\n", encoding="utf-8")

    # --- ledger ----------------------------------------------------------------
    raw = ledger_path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    with ledger_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for c in LEDGER_COLS:
        if c not in fieldnames:
            fieldnames.append(c)
    ids = {r.get("id") for r in rows}
    hashes = {r.get("sha256") for r in rows} | {r.get("sha256_zeros") for r in rows}
    appended = 0
    for r in ledger_rows:
        if r["id"] in ids:
            continue                      # idempotent rebuild: row already recorded
        if r["sha256"] in hashes or r["sha256_zeros"] in hashes:
            raise SystemExit(f"STOP: ledger already has a hash of {r['id']}")
        rows.append({k: str(r.get(k, "")) for k in fieldnames})
        appended += 1
    with ledger_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator=newline)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    evidence = {
        "schema": "gems91.snap-vg-evidence.v1",
        "build_date": BUILD_DATE,
        "parent": PARENT_TAG,
        "lineage": lineage,
        "min_catalogue_px": MIN_CAT_PX,
        "driver": {
            "formula": "0.50*pct(|Band9 tmi_vg|) + 0.50*pct(|Band11 iso_grav_anom_vg|)",
            "percentile_scope": "footprint cells only",
            "sign_handling": "absolute value: VG polarity is remanence/density dependent, crest location is not",
        },
        "leakage_canary": {"max_symmetric_auc": max_auc, "max_feature": max_name,
                           "threshold": 0.90, "stride": 25, "all_band_aucs": canary_aucs},
        "r0_baseline": {
            "n_dots": PARENT_DOTS,
            "hide_and_recover": r0_hr,
            "sgmc_off_catalogue_dti": round(r0_sgmc["dti"], 6),
            "redundancy": proxy.redundancy(parent),
            "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10),
            "block_density_cv_5km": proxy.block_density_cv(parent, footprint, 50),
            "driver_pct_at_r0_dots": round(float(np.nanmean(driver[parent])), 4),
        },
        "arms": evidence_arms,
        "null_diagnostic": null_diag,
    }
    ev = ROOT / "evidence" / f"snap_axis_{BUILD_DATE}.json"
    ev.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"\nledger appended {appended} of {len(ledger_rows)} rows "
          f"(the rest were already recorded)\nrelease manifest {mp}\nevidence {ev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
