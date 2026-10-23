#!/usr/bin/env python3
"""Build the v2 AXIS=PRUNE radius-refinement experiment from exact parent R0.

This run tests three new PRUNE collar radii, each once globally per the audited
sibling ledgers: 2.60, 3.20, and 3.70 pixels. Each candidate has exactly R0's
37,654 dots. The collar is the only intervention: dots at or inside the radius
are removed and refilled from the pinned H19-5 support at greater catalogue
distance by exact greedy marginal DTI gain on the prespecified, label-free
physical corroboration field.

The script uses only registry/data_manifest.json inputs, verifies every input
SHA-256 + byte length, byte-exactly rebuilds both R0 encodings, runs the same
format validator and report-only instruments as the shared PRUNE code, and
never contacts DrivenData or Dropbox. Competition TIFFs are written under the
gitignored local releases/ directory and must not be committed or published.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_prune_variants as bpv  # noqa: E402

AXIS = "PRUNE"
PARENT = "h33-h33-2-b2"
DATE = "20261023"
RUN_VALUES = ("p2p6", "p3p2", "p3p7")
RADII = {"p2p6": 2.6, "p3p2": 3.2, "p3p7": 3.7}
PREDICTIONS = {
    "p2p6": ("+0.001", "[-0.007,+0.009]"),
    "p3p2": ("+0.002", "[-0.009,+0.013]"),
    "p3p7": ("-0.003", "[-0.013,+0.007]"),
}
CARDS = {
    "p2p6": {
        "hypothesis": "A narrow, roughly 224–260 m exclusion around already mapped faults removes near-trace magnetic/gravity shoulders that are more likely to be field or digitization halos than independent new faults; a 2.6 px constant-count replacement should be neutral to slightly positive relative to R0.",
        "mechanism": "Known catalogue pixels are masked pixel-exactly; a dot whose 300 m triangular kernel mainly overlaps the masked trace yields less new-fault credit while still adding prediction mass. The 2.6 px cutoff selectively removes the closest remaining R0 halo and replaces it with the highest exact marginal-credit H19-5 support beyond the cutoff, holding S=37,654 fixed.",
        "non_fault_mimic": "A broad, smooth potential-field shoulder or map digitization offset can create an apparent parallel ridge 200–260 m from a known fault without a second brittle slip surface.",
        "predicted_sign_size": "MODEL: +0.001 live DTI vs R0; plausible range -0.007 to +0.009. A public change with absolute size below 0.01 is no evidence under the brief.",
        "falsifier": "A live RECEIPT at least 0.01 below R0 falsifies the halo-dominated interpretation at 2.6 px and indicates that near-trace splays or offset mapped geometry contribute useful new-fault truth.",
        "external_facts": [
            "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
            "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7",
        ],
    },
    "p3p2": {
        "hypothesis": "Extending the collar just beyond the 300 m triangular-kernel radius may still help if geophysical side-lobes create redundant dots between 300 and 320 m, but the expected gain is small because the R0 collar is already near the kernel radius.",
        "mechanism": "At fixed count, remove all R0 dots with d_cat <= 3.2 px and refill from un-emitted H19-5 ridge support strictly outside 3.2 px by exact marginal DTI gain. The test isolates the 300–320 m portion of the collar while preserving mass and parent lineage.",
        "non_fault_mimic": "Normal-fault hanging-wall/down-dip potential-field gradients may peak 300–320 m from mapped surface traces without indicating a separate fault; alternatively a true antithetic splay may occur at this offset.",
        "predicted_sign_size": "MODEL: +0.002 live DTI vs R0; plausible range -0.009 to +0.013. A public change with absolute size below 0.01 is no evidence under the brief.",
        "falsifier": "A live RECEIPT at least 0.01 below R0 falsifies the hypothesis that remaining 300–320 m collar dots are mostly redundant halos and supports useful new-fault geometry in that band.",
        "external_facts": [
            "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
            "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7",
        ],
    },
    "p3p7": {
        "hypothesis": "A 300–370 m collar may begin to over-prune genuine antithetic splays and relay structures, so the incremental gain should flatten or turn negative relative to a 3.2 px cutoff.",
        "mechanism": "Remove R0's dots at d_cat <= 3.7 px and use exact marginal gain to refill from H19-5 ridge support beyond 370 m, with count fixed. Compared with 3.2 px, the only changed treatment is the additional 50 m of catalogue distance (320–370 m) removed.",
        "non_fault_mimic": "Broad alluvial-fan/piedmont edges, drainage lineaments, and hanging-wall field gradients can parallel range-front faults 320–370 m away without representing new fault planes.",
        "predicted_sign_size": "MODEL: -0.003 live DTI vs R0; plausible range -0.013 to +0.007. Predicted marginal response is lower than p3p2; a public change with absolute size below 0.01 is no evidence under the brief.",
        "falsifier": "A live RECEIPT at least 0.01 above both R0 and p3p2 falsifies the predicted turnover and indicates test faults are depleted in the 300–370 m halo, or the removed dots were predominantly redundant field shoulders.",
        "external_facts": [
            "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
            "https://community.drivendata.org/t/where-do-you-draw-the-line/11536",
            "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7",
        ],
    },
}


def _read_ledger() -> tuple[list[dict[str, str]], set[str], set[tuple[str, str, str]]]:
    path = ROOT / "ledger" / "submissions.csv"
    if not path.exists():
        return [], {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}, set()
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    hashes = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}
    pairs: set[tuple[str, str, str]] = set()
    for row in rows:
        for key in ("sha256", "sha256_zeros"):
            if row.get(key):
                hashes.add(row[key])
        if row.get("parent") and row.get("axis") and row.get("value"):
            pairs.add((row["parent"], row["axis"].upper(), row["value"]))
    return rows, hashes, pairs


def main() -> int:
    t0 = time.time()
    manifest = ROOT / "registry" / "data_manifest.json"
    verified = bpv.verify_manifest(manifest)
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot, cat, d_cat = lineage["foot"], lineage["catalogue"], lineage["d_cat"]
    h19_5, r0 = lineage["h19_5"], lineage["r0"]
    if int(r0.sum()) != 37_654:
        raise RuntimeError(f"Unexpected parent dot count: {int(r0.sum())}")
    print("START GATE PASS: 14/14 manifest SHA-256 and byte lengths; R0 exact SHA matches:")
    print(f"  zeros {lineage['rebuilt_zeros_sha256']}")
    print(f"  NaN    {lineage['rebuilt_nan_sha256']}")

    rows, existing_shas, existing_pairs = _read_ledger()
    # This pair-level gate prevents an experiment from being repeated even if a
    # previous artifact is missing. Never silently replace an experiment row.
    for value in RUN_VALUES:
        pair = (PARENT, AXIS, value)
        if pair in existing_pairs:
            raise RuntimeError(f"Repeated (parent, axis, value) experiment is prohibited: {pair}")

    print("Building label-free physical ranking field and testing the leakage canary...")
    w_field, canaries = bpv.build_physical_field_and_canaries(verified, foot, cat, h19_5)
    print(f"  canary channels: {len(canaries)}; max symmetric AUC={max(canaries.values()):.5f}")
    if max(canaries.values()) > 0.90:
        raise RuntimeError("Leakage canary > 0.90; STOP")

    releases_dir = ROOT / "releases"
    cards = ROOT / "ledger" / "mechanism_cards.json"
    cards.parent.mkdir(parents=True, exist_ok=True)
    new_rows: list[dict[str, str]] = []
    receipts: list[dict] = []
    arms: dict[str, np.ndarray] = {PARENT: r0}
    for value in RUN_VALUES:
        radius = RADII[value]
        base = r0 & (d_cat > radius)
        n_remove = int(r0.sum() - base.sum())
        if n_remove == 0 or n_remove / r0.sum() < 0.01 or n_remove / r0.sum() > 0.50:
            raise RuntimeError(f"{value} violates 1-50% change range: removed={n_remove}")
        candidates = h19_5 & ~base & (d_cat > radius)
        variant = bpv.select_exact_marginal_dti_add(
            base_mask=base,
            cand_mask=candidates,
            w=w_field,
            n_add=n_remove,
        )
        if int(variant.sum()) != int(r0.sum()):
            raise RuntimeError(f"{value}: count changed despite fixed-mass build")

        pred_delta, pred_range = PREDICTIONS[value]
        note = (
            f"R0 {PARENT}; PRUNE dcat≤{radius:.1f}px, fixed 37,654; "
            f"{pred_delta} MODEL"
        )
        rec = bpv.write_and_verify_variant(
            mask=variant,
            foot=foot,
            catalogue=cat,
            sample_path=verified["sample_submission"],
            releases_dir=releases_dir,
            parent_mask=r0,
            axis=AXIS,
            value=value,
            note_template=note,
            existing_shas=existing_shas,
            parent_id=PARENT,
            parent_sha_zeros=bpv.PARENT_SHA_ZEROS,
            parent_sha_nan=bpv.PARENT_SHA_NAN,
            date=DATE,
            min_catalogue_px=0.0,  # PRUNE is the explicit collar exception.
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])
        card = {
            **CARDS[value],
            "id": rec["id"],
            "parent": PARENT,
            "axis": AXIS,
            "value": value,
            "collar_radius_px": radius,
            "changed_parent_dots_pct": rec["parent_diff"]["pct_changed_moved"],
            "predicted_change_evidence": "MODEL",
            "predicted_change": pred_delta,
            "predicted_range": pred_range,
        }
        rec["mechanism_card"] = card
        (releases_dir / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        receipts.append(rec)
        arms[rec["id"]] = variant
        new_rows.append({
            "id": rec["id"],
            "parent": PARENT,
            "axis": AXIS,
            "value": value,
            "n_dots": str(rec["n_dots"]),
            "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
            "sha256": rec["sha256"],
            "status": "BUILT",
            "predicted_change": f"MODEL:{pred_delta} {pred_range}",
            "receipt_score": "",
            "date": "",
            "description": f"Fixed N=37,654; remove R0 dots at d_cat≤{radius:.1f}px and exact-marginal refill on H19-5 support at d_cat>{radius:.1f}px.",
        })
        print(
            f"BUILT {rec['id']} | dots={rec['n_dots']} | moved="
            f"{rec['parent_diff']['pct_changed_moved']:.2f}% | "
            f"min d_cat={rec['parent_diff']['min_dist_catalogue_px']:.4f}px | "
            f"sha256={rec['sha256']}"
        )

    print("Computing REPORT-ONLY local hide-and-recover, SGMC control, and block CV (never gates)...")
    report = bpv.evaluate_report_only_instruments(
        arms=arms,
        foot=foot,
        catalogue=cat,
        sgmc_path=verified["sgmc_faults_control"],
    )
    for rec in receipts:
        rec["report_only_diagnostics"] = report[rec["id"]]
        rec["r0_reference_diagnostics"] = report[PARENT]
        rec["leakage_canaries"] = {
            "passed": True,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        }
        (releases_dir / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")

    ledger_path = ROOT / "ledger" / "submissions.csv"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256", "status", "predicted_change", "receipt_score", "date", "description"]
    with ledger_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in [*rows, *new_rows]:
            writer.writerow({k: row.get(k, "") for k in fields})

    old_cards: dict[str, dict] = {}
    if cards.is_file():
        old_cards = json.loads(cards.read_text(encoding="utf-8"))
    for rec in receipts:
        old_cards[rec["id"]] = rec["mechanism_card"]
    cards.write_text(json.dumps(old_cards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    evidence = {
        "session_date": "2026-10-23",
        "axis": AXIS,
        "parent": PARENT,
        "parent_rebuild": {
            "n_dots": int(r0.sum()),
            "zeros_sha256": lineage["rebuilt_zeros_sha256"],
            "nan_sha256": lineage["rebuilt_nan_sha256"],
            "byte_exact": True,
        },
        "input_pin_count": len(verified),
        "input_pin_hashes_verified": True,
        "ranking": "Unmasked four-line label-free physical corroboration field; exact greedy marginal DTI operations; fixed script seed 20261023; no labels used in candidate ranking.",
        "leakage_canary": {"passed": True, "max_symmetric_auc": max(canaries.values()), "channels": canaries},
        "report_only": report,
        "variants": receipts,
        "git_sha": bpv.git_sha(),
        "elapsed_seconds": round(time.time() - t0, 2),
        "notes": "REPORT-ONLY PROXY/SGMC results are not gates and not scores. Public-chunk change below 0.01 is no evidence.",
    }
    evidence_dir = ROOT / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "prune_refinement_20261023.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("REPORT-ONLY summary:")
    for rec in receipts:
        d = report[rec["id"]]
        print(f"  {rec['value']}: hide/recover PROXY={d['holdout_proxy']['dti']:.6f} {d['holdout_proxy']['ci95']} (n={d['holdout_proxy']['withheld_positives']}); SGMC PROXY={d['sgmc_control']['dti']:.6f}; CV 12km={d['block_density_cv']['cv_12km_120px_interior']:.4f}")
    print(f"Completed in {evidence['elapsed_seconds']:.1f}s. Competition TIFFs remain untracked and gitignored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
