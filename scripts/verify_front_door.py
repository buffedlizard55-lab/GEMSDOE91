#!/usr/bin/env python3
"""Verify exactly the download advertised by the canonical portal, never select it.

The OLC91 renderer remains the publication authority. The committed pointer is
checked against that authority, rather than trusted to nominate another raster.
Reference checks require the SHA-pinned competition sample and catalogue.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(root: Path = ROOT, with_data: bool = False) -> dict:
    from scripts.render_olc91_portal import front_door
    from scripts.render_portal import _raster_format

    expected = front_door(root)  # validates card, policy, TIFF and single-member ZIP
    pointer = json.loads((root / 'docs/current-run.json').read_text())
    if pointer != expected:
        raise ValueError('current-run.json differs from canonical portal; rerender before download')
    tif = root / 'docs' / expected['tif']
    _, format_ok = _raster_format(tif)
    card = json.loads((root / 'docs' / expected['run_card']).read_text())
    name, note = card.get('submission_name'), card.get('submission_note')
    problems = []
    if not format_ok:
        problems.append('single-band float32 / grid / finite [0,1] / nodata check failed')
    if not isinstance(name, str) or not name.strip():
        problems.append('missing submission name')
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        problems.append('submission note must contain 1–140 characters')
    reference_checks = 'NOT_CHECKED'
    inspection = None
    if with_data:
        # Reuse the merged shared pointer/reference inspector rather than
        # maintaining a second sample/catalogue verification implementation.
        from scripts.verify_frontdoor import verify as verify_references
        checked = verify_references(root)
        inspection = checked['validator_output']
        reference_checks = inspection['status']
        problems.extend(k for k, passed in inspection['checks'].items() if not passed)
    return {
        'scope': 'Current advertised download; technical checks only, never slot approval',
        'file': 'docs/' + expected['tif'],
        'run_card': 'docs/' + expected['run_card'],
        'sha256': expected['raster_sha256'],
        'zip_sha256': expected['zip_sha256'],
        'format_ok': not problems,
        'problems': problems,
        'reference_checks': reference_checks,
        'validator_output': inspection,
        'submission_name': name,
        'submission_note': note,
        'OK_TO_DOWNLOAD': 'YES' if not problems else 'NO',
        'OK_TO_SUBMIT': 'NO',
        'submission_ready': False,
        'why': 'Research-only publication; format validity cannot authorize a competition slot.',
    }
