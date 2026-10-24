"""The generated preflight snapshot must not contradict its own readiness inputs."""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_preflight_verdict_and_axis_readiness_are_consistent():
    snapshot = json.loads((ROOT / "registry/preflight.json").read_text(encoding="utf-8"))
    ready_axes = snapshot["ready_axes"]
    required_missing = snapshot["missing"]
    expected = "BUILD ALLOWED" if ready_axes and not required_missing else "BUILD BLOCKED"
    assert snapshot["verdict"] == expected
    for axis, state in snapshot["axis_readiness"].items():
        assert state["ready"] is (not state["missing"]), axis
        assert (axis in ready_axes) is state["ready"]
    checked = snapshot["checked_utc"]
    parsed = datetime.fromisoformat(checked.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
