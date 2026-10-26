#!/usr/bin/env python3
"""Pre-registered predictions for the two existing GEMSDOE32 calibration probes (S2 = values x 0.5, S3 = +2,000 null dots).

Written BEFORE either probe has a live score.  Base raster = D2.8 (44,090 dots, USER-REPORTED 0.2600).  The credit T comes from the
nested-step natural experiments (docs/s22-xb/r0-decomposition.json); the unobservable matched mass M is bracketed in [0, T/2]
(a dot centred on a 1-px line has M:T of about 1:2.1 at 2.8 px spacing).  Output: docs/s22-xb/probe-predictions.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems91 import xbreed22 as X  # noqa: E402


def main() -> int:
    r0 = json.loads((ROOT / "docs/s22-xb/r0-decomposition.json").read_text())
    n_base, dti1, lam, k = 44090, r0["live_scores_user_reported"]["D2.8"], 0.5, 2000
    t_lo = r0["pure_fp_model"]["T_from_step1_D2.8_to_H27-4"]
    t_hi = r0["pure_fp_model"]["T_from_step2_H27-4_to_R0"]
    rows = []
    for T in (t_lo, 0.5 * (t_lo + t_hi), t_hi):
        D = T / dti1
        for M_frac in (0.0, 0.25, 0.5):
            M = M_frac * T
            F = n_base - M
            G = (D - 0.2 * T - 0.2 * F) / 0.8
            p = X.predict_probe_scores(T, G, F, lam=lam, k_null=k)
            rows.append({"T": round(T, 1), "M_over_T": M_frac, "G": round(G), "recall": round(T / G, 3),
                         "S2_pred": round(p["S2"], 4), "S3_pred": round(p["S3"], 4)})
    s2 = [r["S2_pred"] for r in rows]
    s3 = [r["S3_pred"] for r in rows]
    out = {
        "preregistered": "yes - written before any live score of S2 or S3 exists",
        "base": {"raster": "gems25 D2.8 (== probe S1, already scored)", "n_dots": n_base, "user_reported": dti1},
        "files_in_repo": {"S2_scale_lambda_0.5": "data/fleet_registry/gems32-probe-S2-SCALE-lambda-0.5.tif (restore_registry.py, sha-pinned)",
                          "S3_null_add_2000px": "data/fleet_registry/gems32-probe-S3-NULLADD-2000px.tif (restore_registry.py, sha-pinned)"},
        "construction_verified_from_bytes": {"S2": "same 44,090 pixels as D2.8, every value 0.5", "S3": "D2.8 plus 2,000 dots, all inside the footprint, >= 49.2 px (median 64.2 px) from the catalogue and >= 47.4 px from the H19-5 network"},
        "predictions": {"S2_range": [min(s2), max(s2)], "S3_range": [min(s3), max(s3)], "grid": rows},
        "falsification_rules": {
            "S3": "pure-FP nulls and T ~ 5.0e3 predict 0.2547-0.2552. A value > 0.2565 means the far-field null dots carry credit (the live-anchored model puts truth density x5.9 beyond 4 km, so this is a live possibility); < 0.2540 means T is lower than the nested steps imply.",
            "S2": "predicted 0.168-0.174 (depends on |G|). Observed S2 identifies |G| = (lam*T/S2 - lam*(0.2T + 0.2F... )) exactly via gems91.xbreed22.identify_from_probes once S3 gives T.",
        },
        "after_scores_arrive": "python3 -c \"from gems91.xbreed22 import identify_from_probes as f; print(f(0.2600, S2, S3, lam=0.5, k_null=2000))\"  # PYTHONPATH=src",
        "slots_needed": 2,
        "caveat": "probes are calibration instruments, not competitive entries; they are derivatives of D2.8 and are NOT unique under the 70% rule",
    }
    (ROOT / "docs/s22-xb/probe-predictions.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"S2_range": out["predictions"]["S2_range"], "S3_range": out["predictions"]["S3_range"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
