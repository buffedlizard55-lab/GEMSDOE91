#!/usr/bin/env python3
"""S27 post-hoc diagnostics (computed strictly AFTER the S27-CVDC raster was frozen).

1) Blind USGS SGMC off-catalogue DTI (total + >500 m far-field) via shared
   scripts/evaluate_holdout.score_off_catalogue_sgmc. Report-only proxy control.
2) LFI leaderboard-feedback inversion REFITTED in this session on the 108
   restored USER-REPORTED anchors (scripts/run_lfi.py aggregate x2 + fit,
   ridge 1 and 10). Every output is strictly labeled MODEL_PROJECTION_NOT_A_SCORE.
3) Descriptive radial dot-geography profile (distance to catalogue, distance to
   H19-5 multiline network, LFI consensus votes) testing whether stitched 4-fold
   v3-buffered OOF emission eliminated S25-FABRIC's in-sample [3, 10] px halo bug.
4) Fresh nine-focus-site + GEMSDOE92 byte/HEAD/uniqueness audit (docs/s27-osdr/nine-site-audit.json).

Outputs: docs/s27-osdr/diagnostics.json, docs/s27-osdr/dot-profile.json, docs/s27-osdr/nine-site-audit.json.
Creates NO candidate and spends ZERO weekly submission slots.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT)]

import numpy as np
import rasterio
from scipy import ndimage as ndi

from evaluate_holdout import score_off_catalogue_sgmc
from gems91 import lfi as L
from gems91.novelty import dot_check

SITES = [
    "GEMSDOE24",
    "GEMSDOE25",
    "GEMSDOE27",
    "GEMSDOE28",
    "GEMSDOE30",
    "GEMSDOE31",
    "GEMSDOE32",
    "GEMSDOE33",
    "GEMSDOE36",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def gh_head(repo: str) -> tuple[str, str]:
    out = subprocess.check_output(
        ["gh", "api", f"repos/buffedlizard55-lab/{repo}/commits/main"],
        timeout=60,
    )
    j = json.loads(out)
    return j["sha"], j["commit"]["committer"]["date"]


def main() -> int:
    rc = json.loads((ROOT / "docs/s27-osdr/run-card.json").read_text())
    cand_rel = rc["raster_file"]
    if sha(ROOT / cand_rel) != rc["raster_sha256"]:
        raise ValueError("Frozen S27 candidate raster drifted")

    man = {
        r["id"]: r
        for r in json.loads((ROOT / "registry/data_manifest.json").read_text())["files"]
    }
    for rid in ("sample_submission", "existing_faults", "sgmc_faults_control", "parent_r0_zeros"):
        p = ROOT / "data" / man[rid]["local_subpath"]
        if sha(p) != man[rid]["sha256"]:
            raise ValueError(f"Pinned input drift: {rid}")

    with rasterio.open(ROOT / "data/official/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
        ref_crs = str(ds.crs)
        ref_transform = ds.transform
    with rasterio.open(ROOT / "data/official/existing_faults.tif") as ds:
        catalogue = ds.read(1)
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1)

    cat_bool = (np.nan_to_num(catalogue) > 0) & footprint
    dcat = ndi.distance_transform_edt(~cat_bool)
    sgmc_gt500 = np.where(dcat > 5.0, sgmc, 0)

    targets = [
        ("s27_cvdc_e2_candidate", cand_rel),
        (
            "s25_fabric_e2_candidate",
            "docs/downloads/gems91-s25-fabric-e2-37654dots-20261028T115403Z-3188f6e6-zeros.tif",
        ),
        (
            "s21_pdwc_e3",
            "docs/downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif",
        ),
        (
            "s24_cckm_e2",
            "docs/downloads/gems91-s24-cckm-e2-37654dots-20261027T190354Z-d69650bd-zeros.tif",
        ),
        (
            "gemsdoe92_lbmc1",
            "data/s27_refs/gemsdoe92-lbmc1-35801dots-20261027-89a660f6-zeros.tif",
        ),
        ("parent_r0_gemsdoe32", "data/" + man["parent_r0_zeros"]["local_subpath"]),
    ]

    nine_s22 = {
        s["site"]: s
        for s in json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]
    }
    for site in SITES:
        s = nine_s22[site]
        if sha(ROOT / s["local_path"]) != s["sha256"]:
            raise ValueError(f"Nine-site leader drift: {site}")
        targets.append((f"nine_{site.lower()}", s["local_path"]))

    def read_pred(rel: str) -> np.ndarray:
        with rasterio.open(ROOT / rel) as ds:
            if ds.shape != footprint.shape or str(ds.crs) != ref_crs or ds.count != 1:
                raise ValueError(f"Grid mismatch: {rel}")
            return ds.read(1)

    # 1) Blind USGS SGMC off-catalogue DTI (total + >500 m)
    sgmc_rows = []
    preds = {}
    for name, rel in targets:
        pred = read_pred(rel)
        preds[name] = pred
        res_all = score_off_catalogue_sgmc(pred, sgmc, catalogue, footprint)
        res_500 = score_off_catalogue_sgmc(pred, sgmc_gt500, catalogue, footprint)
        sgmc_rows.append(
            {
                "name": name,
                "path": rel,
                "sha256": sha(ROOT / rel),
                "n_positive_pixels_inside": int(((np.nan_to_num(pred) > 0) & footprint).sum()),
                "dti_gt500m": float(res_500["dti"]),
                **res_all,
            }
        )
        print(
            f"SGMC all={res_all['dti']:.6f}  >500m={res_500['dti']:.6f}  {name}",
            flush=True,
        )

    # 2) LFI refit in this session on restored 108 anchors
    work = ROOT / "work/lfi"
    py = sys.executable
    if not (work / "fit_r10.0_fNone.json").is_file() or not (work / "cons_votes.npy").is_file():
        run([py, "scripts/run_lfi.py", "aggregate"])
        (work / "anchors_base.json").write_bytes((work / "anchors.json").read_bytes())
        run([py, "scripts/run_lfi.py", "aggregate"])
        run([py, "scripts/run_lfi.py", "fit", "--ridge", "1"])
        run([py, "scripts/run_lfi.py", "fit", "--ridge", "10"])

    meta = json.loads((work / "anchors.json").read_text())
    used = [r for r in meta["rows"] if r.get("used")]
    anchor_set_hash = hashlib.sha256(
        "\n".join(sorted(f"{r['name']}|{r['sha256']}" for r in used)).encode()
    ).hexdigest()
    z = np.load(work / "agg.npz")
    A, Lm = z["A"], z["L"]
    bins = np.load(work / "bins.npy")
    nb = int(meta["n_bins"])
    pnames = meta["param_names"]
    X = np.hstack([np.ones((Lm.shape[0], 1)), Lm])

    fits = {}
    for tag, fn in (("ridge1", "fit_r1.0_fNone.json"), ("ridge10", "fit_r10.0_fNone.json")):
        fd = json.loads((work / fn).read_text())
        fits[tag] = {
            "theta": np.array([fd["theta"][k] for k in pnames], dtype=np.float64),
            "f": float(fd["f"]),
            "rmse_loso": fd["rmse_loso"],
            "spearman_loso": fd["spearman_loso"],
            "pearson_loso": fd["pearson_loso"],
            "n_anchors": fd["n_anchors"],
            "fit_file": f"work/lfi/{fn}",
        }

    lfi_rows = []
    for name, rel in targets:
        a = np.where(footprint, np.nan_to_num(preds[name].astype(np.float64), nan=0.0), 0.0)
        N_c, C_c = L.aggregate(a.astype(np.float32), bins, nb, cat_bool)
        row = {
            "name": name,
            "path": rel,
            "sha256": sha(ROOT / rel),
            "label_class": "MODEL_PROJECTION_NOT_A_SCORE",
        }
        for tag, fd in fits.items():
            y_hat, _ = L.predict(fd["theta"], fd["f"], X, N_c[None, :], C_c[None, :], A)
            row[tag] = round(float(y_hat[0]), 5)
        lfi_rows.append(row)
        print(f"LFI {name}: ridge1={row['ridge1']} ridge10={row['ridge10']}", flush=True)

    diag = {
        "schema": "s27-posthoc-diagnostics-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "label": "POST-HOC DIAGNOSTICS — SGMC proxy control + LFI MODEL_PROJECTION_NOT_A_SCORE. No ORGANIZER-CONFIRMED receipt exists for any row.",
        "candidate": {
            "name": "s27_cvdc_e2_candidate",
            "tif": cand_rel,
            "sha256": rc["raster_sha256"],
            "organizer_confirmed_score": None,
        },
        "sgmc": {
            "label": "SGMC-OFFCAT-CONTROL-DTI (report-only; never a selection gate or leaderboard estimate)",
            "evaluator": "scripts/evaluate_holdout.score_off_catalogue_sgmc",
            "input_sha256": man["sgmc_faults_control"]["sha256"],
            "rows": sorted(sgmc_rows, key=lambda r: -r["dti"]),
        },
        "lfi": {
            "label_class": "MODEL_PROJECTION_NOT_A_SCORE",
            "anchor_set": {
                "n_used": len(used),
                "n_rows": len(meta["rows"]),
                "set_sha256": anchor_set_hash,
            },
            "fits": {
                k: {
                    kk: v[kk]
                    for kk in ("f", "rmse_loso", "spearman_loso", "pearson_loso", "n_anchors", "fit_file")
                }
                for k, v in fits.items()
            },
            "caveats": [
                "Protocol Rule 3: A model projection is NEVER a score and must never be written as an expected live score.",
                "S27-CVDC was designed, selected, and packaged strictly on HOLDOUT-DTI without viewing LFI or SGMC; by contrast, GEMSDOE92 lbmc1 directly maximized a 123-anchor leaderboard model (projecting 0.3322 MODEL vs 0.2784 USER-REPORTED live, +0.0538 optimizer's-curse inflation).",
                "All 108 LFI anchors are USER-REPORTED claims from sibling sites without organizer receipts.",
            ],
            "rows": sorted(lfi_rows, key=lambda r: -r["ridge1"]),
        },
    }
    (ROOT / "docs/s27-osdr/diagnostics.json").write_text(json.dumps(diag, indent=2, allow_nan=False) + "\n")

    # 3) Descriptive radial dot-geography profile
    net = (
        np.nan_to_num(
            read_pred("data/fleet_registry/19GEMSDOE__h19-5-powerlaw-budget-multiline.tif")
        )
        > 0
    ) & footprint
    dnet = ndi.distance_transform_edt(~net)
    votes = np.load(work / "cons_votes.npy")
    dcat_edges = [(0, 3), (3, 5), (5, 10), (10, 20), (20, 40), (40, float("inf"))]
    dnet_edges = [(0, 1.5), (1.5, 3), (3, 6), (6, float("inf"))]

    def hist(v: np.ndarray, edges) -> dict:
        return {f"({lo},{hi}]": round(float(((v > lo) & (v <= hi)).mean()), 4) for lo, hi in edges}

    prof_rows = []
    for name in (
        "s27_cvdc_e2_candidate",
        "s25_fabric_e2_candidate",
        "s21_pdwc_e3",
        "s24_cckm_e2",
        "gemsdoe92_lbmc1",
        "parent_r0_gemsdoe32",
    ):
        rel = dict(targets)[name]
        dots = (np.nan_to_num(preds[name]) > 0) & footprint
        dc, dn, vt = dcat[dots], dnet[dots], votes[dots]
        prof_rows.append(
            {
                "name": name,
                "path": rel,
                "sha256": sha(ROOT / rel),
                "n_dots": int(dots.sum()),
                "dcat_px_median": round(float(np.median(dc)), 3),
                "dcat_px_hist": hist(dc, dcat_edges),
                "dnet_px_median": round(float(np.median(dn)), 3),
                "dnet_px_hist": hist(dn, dnet_edges),
                "cons_votes_hist": {
                    "0": round(float((vt == 0).mean()), 4),
                    "1": round(float((vt == 1).mean()), 4),
                    "2": round(float((vt == 2).mean()), 4),
                    ">=3": round(float((vt >= 3).mean()), 4),
                },
            }
        )
        print(
            f"PROFILE {name:24s}: median_dcat={prof_rows[-1]['dcat_px_median']:6.2f}px  "
            f"frac_(3,10]px={prof_rows[-1]['dcat_px_hist']['(3,5]'] + prof_rows[-1]['dcat_px_hist']['(5,10]']:.4f}  "
            f"frac_>20px={prof_rows[-1]['dcat_px_hist']['(20,40]'] + prof_rows[-1]['dcat_px_hist']['(40,inf]']:.4f}",
            flush=True,
        )

    (ROOT / "docs/s27-osdr/dot-profile.json").write_text(
        json.dumps(
            {
                "schema": "s27-dot-profile-v1",
                "label": "DESCRIPTIVE DOT GEOGRAPHY PROFILE (not a score)",
                "rows": prof_rows,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )

    # 4) Nine-site + GEMSDOE92 fresh audit (precomputed 3-px EDT halos per site -> <4s)
    cand_dots = (np.nan_to_num(preds["s27_cvdc_e2_candidate"]) > 0) & footprint
    site_dots = {
        site: (np.nan_to_num(preds[f"nine_{site.lower()}"]) > 0) & footprint
        for site in SITES
    }
    site_halo3 = {
        site: ndi.distance_transform_edt(~site_dots[site]) <= 3.0
        for site in SITES
    }
    nine_rows = []
    for site in SITES:
        s = nine_s22[site]
        head_sha, head_date = gh_head(site)
        sd = site_dots[site]
        n_sd = int(sd.sum())
        peer_ovs = []
        for other in SITES:
            if other == site:
                continue
            ov = float(site_halo3[other][sd].mean()) if n_sd > 0 else 0.0
            peer_ovs.append(
                {
                    "peer": other,
                    "overlap_within_3px": round(ov, 6),
                    "status": "DUPLICATE" if ov > 0.70 else "UNIQUE",
                }
            )
        max_peer = max(peer_ovs, key=lambda x: x["overlap_within_3px"])
        s27_ov = float(site_halo3[site][cand_dots].mean())
        nine_rows.append(
            {
                "site": site,
                "site_url": f"https://buffedlizard55-lab.github.io/{site}/",
                "best_claimed_file": s["filename"],
                "original_path": s.get("original_path"),
                "sha256": s["sha256"],
                "bytes": s["bytes"],
                "positive_pixels": n_sd,
                "user_reported_public_dti": s.get("claimed_historical_value"),
                "score_evidence_class": "USER-REPORTED (NOT ORGANIZER-CONFIRMED; no DrivenData receipt)",
                "organizer_confirmed_score": None,
                "current_main_head": head_sha,
                "current_main_head_date": head_date,
                "max_3px_overlap_among_nine": max_peer["overlap_within_3px"],
                "closest_peer_among_nine": max_peer["peer"],
                "unique_within_nine_at_70pct": bool(max_peer["overlap_within_3px"] <= 0.70),
                "s27_candidate_3px_overlap_vs_site": round(s27_ov, 6),
                "s27_candidate_status_vs_site": "DUPLICATE" if s27_ov > 0.70 else "UNIQUE",
            }
        )

    head_92, date_92 = gh_head("GEMSDOE92")
    lbmc_dots = (np.nan_to_num(preds["gemsdoe92_lbmc1"]) > 0) & footprint
    lbmc_halo3 = ndi.distance_transform_edt(~lbmc_dots) <= 3.0
    s27_vs_92_ov = float(lbmc_halo3[cand_dots].mean())
    lbmc_vs_32_ov = float(site_halo3["GEMSDOE32"][lbmc_dots].mean())

    nine_audit = {
        "schema": "s27-nine-site-plus-gems92-audit-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "organizer_complete_registry": False,
        "nine_focus_sites": sorted(nine_rows, key=lambda r: -(r["user_reported_public_dti"] or 0.0)),
        "gemsdoe92_context": {
            "site": "GEMSDOE92",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE92/",
            "best_claimed_file": "gemsdoe92-lbmc1-35801dots-20261027-89a660f6-zeros.tif",
            "sha256": sha(ROOT / "data/s27_refs/gemsdoe92-lbmc1-35801dots-20261027-89a660f6-zeros.tif"),
            "positive_pixels": int(lbmc_dots.sum()),
            "user_reported_public_dti": 0.2784,
            "run_card_holdout_dti": 0.019698,
            "run_card_model_projection_not_a_score": 0.332224,
            "score_evidence_class": "USER-REPORTED (NOT ORGANIZER-CONFIRMED; GEMSDOE92 README marks DO NOT SUBMIT)",
            "current_main_head": head_92,
            "current_main_head_date": date_92,
            "overlap_3px_vs_gemsdoe32": round(lbmc_vs_32_ov, 6),
            "s27_candidate_3px_overlap_vs_gemsdoe92": round(s27_vs_92_ov, 6),
            "s27_candidate_status_vs_gemsdoe92": "DUPLICATE" if s27_vs_92_ov > 0.70 else "UNIQUE",
        },
    }
    (ROOT / "docs/s27-osdr/nine-site-audit.json").write_text(
        json.dumps(nine_audit, indent=2, allow_nan=False) + "\n"
    )
    print("Wrote docs/s27-osdr/diagnostics.json, dot-profile.json, nine-site-audit.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
