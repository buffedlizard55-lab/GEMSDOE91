#!/usr/bin/env python3
"""Refresh a bounded, auditable fleet page inventory through GitHub, not Pages.

No organizer session/score is accessed. A page author's assertions are not an
organizer receipt. Remote snapshots and all fetch failures remain in the report.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PREFIX = {1: 'GEMSDOE', **{n: f'{n}GEMSDOE' for n in
          (5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 55, 56, 57, 58, 59, 60, 61, 62)}}


def api(path, raw=False):
    command = ['gh', 'api', path]
    if raw:
        command += ['-H', 'Accept: application/vnd.github.raw']
    out = subprocess.run(command, capture_output=True, timeout=60)
    if out.returncode:
        raise RuntimeError(out.stderr.decode(errors='replace')[:400])
    return out.stdout if raw else json.loads(out.stdout)


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.text = []; self.links = []
    def handle_data(self, data):
        if data.strip(): self.text.append(data.strip())
    def handle_starttag(self, tag, attrs):
        if tag == 'a': self.links.extend(v for k, v in attrs if k == 'href')


def audit(number):
    repo = 'buffedlizard55-lab/' + PREFIX.get(number, f'GEMSDOE{number}')
    row = dict(repository=repo, status='UNVERIFIED', snapshot_commit=None,
               page=None, page_url=None, download_links=[], raster_files=0,
               raster_bytes=0, organizer_confirmed_scores=[], caveat='Page claims are not receipts.')
    try:
        commit = api(f'repos/{repo}/commits/main')['sha']
        tree = api(f'repos/{repo}/git/trees/{commit}?recursive=1')
        row['snapshot_commit'] = commit
        row['tree_truncated'] = tree.get('truncated', False)
        files = {f['path']: f for f in tree['tree'] if f['type'] == 'blob'}
        rasters = [f for p, f in files.items() if p.lower().endswith(('.tif', '.tiff'))]
        row['raster_files'] = len(rasters)
        row['raster_bytes'] = sum(f.get('size', 0) for f in rasters)
        page = next((p for p in ('docs/index.html', 'index.html') if p in files), None)
        if not page:
            row.update(status='NO_HTML_PAGE'); return row
        page_bytes = api(f'repos/{repo}/contents/{page}?ref={commit}', raw=True)
        p = Text(); p.feed(page_bytes.decode('utf-8', errors='replace'))
        text = '\n'.join(p.text)
        row.update(status='FETCHED_GITHUB_SNAPSHOT', page=page,
                   page_url=f'https://github.com/{repo}/blob/{commit}/{page}',
                   page_sha256=__import__('hashlib').sha256(page_bytes).hexdigest(),
                   download_links=[x for x in p.links if re.search(r'\.(tif|zip)([?#]|$)', x, re.I)])
        needles = ('no organiser score', 'no organizer score', 'not ok to submit',
                   'not approved', 'holdout-dti', 'organizer-confirmed', 'organiser-confirmed')
        row['evidence_excerpts'] = []
        for needle in needles:
            i = text.lower().find(needle)
            if i >= 0:
                row['evidence_excerpts'].append(text[max(0, i-60):i+220])
    except (RuntimeError, subprocess.TimeoutExpired, KeyError, ValueError) as exc:
        row['error'] = str(exc)[:500]
    return row


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=92)
    args = ap.parse_args()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(audit, range(1, args.limit + 1)))
    report = dict(checked_utc=datetime.now(timezone.utc).isoformat(),
                  method='Pinned GitHub main snapshots of supplied owner fleet; not live Pages or organizer verification',
                  complete_universal_registry=False, rows=rows)
    dest = ROOT / 'docs' / 'fleet-audit.json'
    dest.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    with (ROOT / 'docs' / 'fleet-audit.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['repository', 'status', 'snapshot_commit', 'page_url',
                                        'raster_files', 'raster_bytes', 'download_count', 'organizer_confirmed'], lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({**{k: r.get(k) for k in w.fieldnames if k not in ('download_count','organizer_confirmed')},
                        'download_count': len(r['download_links']), 'organizer_confirmed': 'NOT_VERIFIED'})
    print(f"Audited {len(rows)} repositories; {sum(r['status']=='FETCHED_GITHUB_SNAPSHOT' for r in rows)} pages fetched.")
    print('No page text has been promoted to an organizer-confirmed score.')


if __name__ == '__main__':
    main()
