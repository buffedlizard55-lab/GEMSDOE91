#!/usr/bin/env python3
"""Post-hoc diagnostics for the S28-VFCD packaged candidate.

Reproduces the S27 diagnostics instrument exactly (same anchors, same LFI
refit recipe via scripts/run_lfi.py) and scores the new candidate:
  1) blind USGS SGMC off-catalogue DTI (>3 px and >500 m from the catalogue);
  2) LFI leaderboard-feedback inversion projections (MODEL_PROJECTION_NOT_A_SCORE).
Nine-site rows are inherited from docs/s27-osdr/diagnostics.json (same anchor
fit, set sha256 recorded there) and never re-derived here.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT)]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from evaluate_holdout import score_off_catalogue_sgmc  # noqa: E402
from gems91 import lfi as L  # noqa: E402


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    rc = json.loads((ROOT / "docs/s28-vfcd/run-card.json").read_text())
    cand_rel = rc["raster_file"]
    if sha(ROOT / cand_rel) != rc["raster_sha256"]:
        raise ValueError("Frozen S28 candidate raster drifted")

    with rasterio.open(ROOT / "data/official/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/official/existing_faults.tif") as ds:
        catalogue = ds.read(1)
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1)
    cat_bool = (np.nan_to_num(catalogue) > 0) & footprint
    dcat = ndi.distance_transform_edt(~cat_bool)
    sgmc_gt500 = np.where(dcat > 5.0, sgmc, 0)

    with rasterio.open(ROOT / cand_rel) as ds:
        pred = ds.read(1)
    sgmc_all = score_off_catalogue_sgmc(pred, sgmc, catalogue, footprint)
    sgmc_500 = score_off_catalogue_sgmc(pred, sgmc_gt500, catalogue, footprint)

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
            "theta": [fd["theta"][k] for k in pnames],
            "f": float(fd["f"]),
            "rmse_loso": fd["rmse_loso"],
            "spearman_loso": fd["spearman_loso"],
            "n_anchors": fd["n_anchors"],
            "fit_file": f"work/lfi/{fn}",
        }

    a = np.where(footprint, np.nan_to_num(pred.astype(np.float64), nan=0.0), 0.0)
    N_c, C_c = L.aggregate(a.astype(np.float32), bins, nb, cat_bool)
    lfi_row = {"name": "s28_vfcd_candidate", "path": cand_rel, "sha256": rc["raster_sha256"],
               "label_class": "MODEL_PROJECTION_NOT_A_SCORE"}
    for tag, fd in fits.items():
        y_hat, _ = L.predict(np.array(fd["theta"], dtype=np.float64), fd["f"], X, N_c[None, :], C_c[None, :], A)
        lfi_row[tag] = round(float(y_hat[0]), 5)

    s27_diag = json.loads((ROOT / "docs/s27-osdr/diagnostics.json").read_text())
    out = {
        "schema": "s28-vfcd-posthoc-diagnostics-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": "POST-HOC DIAGNOSTICS — SGMC-OFFCAT-CONTROL-DTI + LFI MODEL_PROJECTION_NOT_A_SCORE. "
                 "No ORGANIZER-CONFIRMED receipt exists for any row. Protocol Rule 3: a projection is never a score.",
        "candidate": {"path": cand_rel, "sha256": rc["raster_sha256"],
                      "sgmc_offcat_3px": sgmc_all, "sgmc_offcat_500m": sgmc_500},
        "lfi": {
            "anchor_set": {"n_used": len(used), "set_sha256": anchor_set_hash},
            "fits": {t: {k: v for k, v in f.items() if k != "theta"} for t, f in fits.items()},
            "rows": [lfi_row],
            "caveats": [
                "MODEL projection fitted to USER-REPORTED sibling scores; LOSO RMSE "
                f"{fits['ridge10']['rmse_loso']:.4f}.",
                "All 112 anchors are USER-REPORTED claims without organizer receipts.",
            ],
        },
        "inherited_nine_site_rows": {
            "source": "docs/s27-osdr/diagnostics.json",
            "anchor_set_sha256_match": s27_diag["lfi"]["anchor_set"]["set_sha256"] == anchor_set_hash,
            "lfi_rows": s27_diag["lfi"]["rows"],
            "sgmc_rows": [r for r in s27_diag.get("sgmc", {}).get("rows", [])],
        },
    }
    out_path = ROOT / "docs/s28-vfcd/diagnostics.json"
    out_path.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(f"LFI candidate: ridge1={lfi_row['ridge1']} ridge10={lfi_row['ridge10']}")
    print(f"SGMC candidate: all={sgmc_all['dti']} 500m={sgmc_500['dti']}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
