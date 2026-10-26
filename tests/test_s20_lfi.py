"""S20-LFI: the published file, run card, gates and portal must agree; the verdict must stay fail-closed."""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "docs/run-card-S20-LFI.json").read_text())


def test_download_bytes_match_card_and_are_valid_without_repo_code():
    s = CARD["submission"]
    raw = (ROOT / s["file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == s["sha256"]
    with tifffile.TiffFile(ROOT / s["file"]) as t:
        assert len(t.pages) == 1
        a = t.pages[0].asarray()
        tags = {x.name: x.value for x in t.pages[0].tags.values()}
    assert a.dtype == np.float32 and a.shape == (3730, 3292)
    assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
    assert int((a > 0).sum()) == s["n_dots"]
    assert "GDAL_NODATA" not in tags
    assert tuple(tags["ModelTiepointTag"])[3:5] == (243350.0, 4508550.0)
    with zipfile.ZipFile(ROOT / s["zip"]) as z:
        assert z.namelist() == [Path(s["file"]).name] and z.read(z.namelist()[0]) == raw
    assert 0 < len(s["note"]) <= 140 and s["note_chars"] == len(s["note"])


def test_verdict_is_derived_from_gates_and_stays_fail_closed():
    G = CARD["gates"]
    assert CARD["ok_to_download"] == (G["G1_format"] and G["G2_uniqueness"])
    assert CARD["s20_preregistered_gates_all_pass"] == all(G.values())
    # Standing rule: a slot needs a measured win on the spatially-blocked holdout; G5 can't waive it.
    beats = CARD["evidence"]["holdout_dti_hide_v2"]["paired_vs_r0"]["ci95"][0] > 0
    assert CARD["standing_rule_beats_spatially_blocked_holdout_best"] == beats
    assert CARD["ok_to_submit"] == (all(G.values()) and beats)
    assert CARD["slots_used"] == 0


def test_g4_matches_preregistered_rule():
    proj = CARD["evidence"]["projection_G4"]
    lb = sum(v["boot_delta_ci95"][0] > 0 for v in proj.values())
    p_ok = all(v["p_delta_gt0"] >= 0.95 for v in proj.values())
    assert CARD["gates"]["G4_surrogate_projection"] == (lb >= 2 and p_ok)


def test_uniqueness_evidence_refers_to_this_file():
    for f in ("docs/lfi/registry-check.json", "docs/lfi/sibling-check.json"):
        r = json.loads((ROOT / f).read_text())
        assert r["candidate_sha256"] == CARD["submission"]["sha256"]
        assert r["verdict"] == "UNIQUE" and r["duplicates"] == []
        sparse = [x for x in r["rows"] if not x["dense"]]
        assert max(x["within_3px_literal"] for x in sparse) <= 0.70


def test_portal_banner_matches_card():
    page = (ROOT / "docs/s20-lfi-executive-summary.html").read_text()
    assert page.count('data-submission-ready="') == 1
    assert f'data-submission-ready="{str(CARD["ok_to_submit"]).lower()}"' in page
    assert Path(CARD["submission"]["file"]).name in page and CARD["submission"]["sha256"] in page
    guide = (ROOT / "docs/s20-lfi-executive-summary.html").read_text()
    assert "How to submit" in guide and CARD["submission"]["note"] in guide
    if not CARD["ok_to_submit"]:
        assert "NOT OK TO SUBMIT" in page and "NOT OK TO SUBMIT" in guide


def test_instrument_validity_numbers_are_reproduced_from_rows():
    from scipy.stats import spearmanr
    e2 = json.loads((ROOT / "docs/lfi/holdout-e2.json").read_text())
    live = [a["live"] for a in e2["anchors"]]
    hv = [a["hide_v2"] for a in e2["anchors"]]
    rho = spearmanr(hv, live).statistic
    assert abs(rho - e2["instrument_validity"]["spearman_hide_v2_vs_live"]) < 1e-9
    assert CARD["gates"]["G5_instrument_rule"] is True
