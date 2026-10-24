"""Preserve concurrent work without converting it into submission permission."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_parallel_outputs_are_pinned_but_quarantined():
    policy = json.loads((ROOT/'registry/artifact_policy.json').read_text())
    rows = [r for r in policy['files'] if 'gems91-denovo-' in r['path']]
    assert len(rows) == 2
    for row in rows:
        assert row['status'] == 'parallel_quarantined'
        assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest() == row['sha256']
    peer = json.loads((ROOT/'reports/run_card_20261024.json').read_text())
    assert peer['verdict'] == 'negative' and peer['submission_ready'] is False
    assert peer['historical_pre_merge_recommendation']['verdict'] == 'promote'
    page = (ROOT/'docs/denovo.html').read_text()
    assert 'data-submission-ready="false"' in page
    assert 'CURRENT POLICY: NOT OK TO SUBMIT' in page
    assert '<h2>How to submit (60 seconds)</h2>' not in page


def test_frozen_cover_counting_bound_not_a_new_raster_comparison():
    # Derive only from the previously measured diagnostic, without opening a
    # candidate/reference raster or running any scientific evaluation.
    report = json.loads((ROOT/'docs/parent-forensics.json').read_text())['novelty_protocol_diagnostic']
    uncovered = report['footprint_pixels'] - report['footprint_pixels_within3']
    assert uncovered == 6649
    assert (22163-uncovered)/22163 <= .70
    assert (22164-uncovered)/22164 > .70
    assert (32000-uncovered)/32000 > .70
    assert (37654-uncovered)/37654 > .70
