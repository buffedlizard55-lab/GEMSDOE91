"""Preflight tests: an unpinned or absent input must block the build."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import make_fixture, preflight


def _manifest(tmp_path, fx, *, pin=True, expected=None):
    entries = {
        "sample_submission": fx["sample_submission"],
        "R0_parent": fx["parent_R0"],
        "catalogue_mask": fx["catalogue_mask"],
        "km_prior": fx["prior_kmscale"],
    }
    inputs = []
    for key, path in entries.items():
        inputs.append({
            "id": key, "path": str(path), "kind": "competition",
            "sha256": preflight.sha256_file(Path(path)) if pin else None,
            "required_by": ["CONCENTRATION"],
        })
    inputs[1]["parent_sha256_expected"] = expected or (
        preflight.sha256_file(Path(entries["R0_parent"])) if pin else None
    )
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"schema": "test", "inputs": inputs}))
    return p


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    out = tmp_path_factory.mktemp("pf")
    return {k: Path(v) for k, v in make_fixture.make(out, seed=5, n_dots=200).items()}


def test_pinned_present_inputs_clear_the_build(tmp_path, fx):
    ok, results = preflight.check("CONCENTRATION", _manifest(tmp_path, fx), quiet=True)
    assert ok, [r for r in results if not r["ok"]]


def test_unpinned_input_blocks(tmp_path, fx):
    ok, results = preflight.check("CONCENTRATION", _manifest(tmp_path, fx, pin=False), quiet=True)
    assert not ok
    assert any("UNPINNED" in r["detail"] for r in results)


def test_missing_input_blocks(tmp_path, fx):
    p = _manifest(tmp_path, fx)
    man = json.loads(p.read_text())
    for entry in man["inputs"]:
        if entry["id"] == "km_prior":
            entry["path"] = str(tmp_path / "absent.tif")
    p.write_text(json.dumps(man))
    ok, results = preflight.check("CONCENTRATION", p, quiet=True)
    assert not ok
    assert any("missing on disk" in r["detail"] for r in results)


def test_wrong_expected_parent_hash_blocks(tmp_path, fx):
    ok, results = preflight.check("CONCENTRATION", _manifest(tmp_path, fx, expected="0" * 64), quiet=True)
    assert not ok
    assert any(r["item"] == "R0 identity" and "differs" in r["detail"] for r in results)


def test_axis_without_pinned_inputs_blocks(tmp_path, fx):
    ok, results = preflight.check("SNAP", _manifest(tmp_path, fx), quiet=True)
    assert not ok
    assert any("tmi_gradient" in r["item"] for r in results)


def test_real_repository_manifest_is_blocked_today():
    """Guard on the actual repo state: no pinned inputs => nothing may be built."""
    ok, results = preflight.check("CONCENTRATION", preflight.MANIFEST, quiet=True)
    assert not ok
    assert all(r["detail"] for r in results if not r["ok"])


def test_cli_exit_code_is_2_when_blocked(tmp_path, fx, capsys):
    assert preflight.main(["--axis", "CONCENTRATION", "--manifest", str(tmp_path / "nope.json")]) == 2
