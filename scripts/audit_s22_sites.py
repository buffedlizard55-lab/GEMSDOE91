#!/usr/bin/env python3
"""Re-hash nine exact historical leaders; user score claims are not receipts."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import rasterio
from gems91.novelty import dot_check
from vendor.gems57 import grid


def api(path, raw=False):
    cmd = ['gh', 'api', path]
    if raw:
        cmd += ['-H', 'Accept: application/vnd.github.raw']
    b = subprocess.check_output(cmd, timeout=120)
    return b if raw else json.loads(b)


def run():
    out = ROOT / 'docs/s22'; out.mkdir(exist_ok=True)
    prior = json.loads((ROOT / 'docs/s20_rhtw/nine_sites_forensic_matrix.json').read_text())['forensic_rasters']
    # IDs from the inherited blob audit; all name the prompt's actual leaders.
    selected = [prior[i] for i in [0, 3, 6, 9, 18, 21, 23, 25, 27]]
    def fetch(r):
        repo = 'buffedlizard55-lab/' + r['repo']
        data = api(f'repos/{repo}/git/blobs/{r["git_blob"]}', raw=True)
        digest = hashlib.sha256(data).hexdigest()
        if digest != r['sha256'] or len(data) != r['bytes']:
            raise ValueError('pinned artifact mismatch')
        p = ROOT / 'data/s22-nine-sites' / (r['repo'] + '.tif')
        p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
        head = api(f'repos/{repo}/commits/main')
        return dict(site=r['repo'], filename=Path(r['rel_path']).name,
            original_path=r['rel_path'], local_path=str(p.relative_to(ROOT)),
            source_url=f'https://github.com/{repo}/blob/{r["git_blob"]}',
            blob_api_url=f'https://api.github.com/repos/{repo}/git/blobs/{r["git_blob"]}',
            artifact_git_blob=r['git_blob'], sha256=digest, bytes=len(data),
            current_main_head=head['sha'], latest_commit_utc=head['commit']['committer']['date'],
            claimed_historical_value=r['user_reported_score'], claim_source='user prompt; NOT ORGANIZER-CONFIRMED',
            organizer_confirmed_score=None, estimated_leaderboard_score=None,
            ok_to_submit=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(fetch, selected))
    g = grid.load_grid(ROOT / 'data/official')
    supports = []
    for r in rows:
        with rasterio.open(ROOT / r['local_path']) as ds:
            a = ds.read(1)
            match = ds.count == 1 and ds.shape == g.shape and ds.crs == g.crs and ds.transform == g.transform
            inside = a[g.footprint]
            r['validator'] = dict(grid_match=match, no_nan_inside_footprint=bool(np.isfinite(inside).all()),
                all_cells_finite=bool(np.isfinite(a).all()), finite_values_in_range=bool(np.all((a[np.isfinite(a)] >= 0) & (a[np.isfinite(a)] <= 1))),
                nodata=str(ds.nodata), dtype=ds.dtypes[0])
        if not match or not np.isfinite(inside).all():
            raise ValueError('nine-site raster incompatible with footprint')
        support = (a > 0) & g.footprint
        r['positive_pixels'] = int(support.sum())
        r['support_sha256'] = hashlib.sha256(np.packbits(support).tobytes()).hexdigest()
        supports.append(support.astype(np.float32))
    for i, r in enumerate(rows):
        pairwise = []
        for j, other in enumerate(rows):
            if i == j:
                continue
            d = dot_check(supports[i], supports[j], g.footprint)
            pairwise.append(dict(reference_site=other['site'], **d,
                                 exact_support_equal=bool(np.array_equal(supports[i], supports[j]))))
        worst = max(pairwise, key=lambda d: d['overlap_within_3px'])
        r['peer_comparisons'] = pairwise
        r['max_overlap_vs_other_eight'] = worst
        r['protocol_unique_among_nine'] = not any(d['status'] == 'DUPLICATE' for d in pairwise)
        # Source link must refer to a tree commit, not incorrectly use a blob as a commit.
        r['source_url'] = f'https://github.com/buffedlizard55-lab/{r["site"]}/blob/{r["current_main_head"]}/{r["original_path"]}'
        r['source_link_note'] = 'Current tree link is for navigation; pinned artifact identity is the blob API URL + SHA256.'
    result = dict(as_of_utc=datetime.now(timezone.utc).isoformat(), sites=rows,
        scope='Exact nine prompt-named historical leaders only; new candidates/private uploads not exhaustively audited',
        estimated_leaderboard_score=None, organizer_confirmed_scores=0,
        claim_ranking_best_site=max(rows, key=lambda r: r['claimed_historical_value'])['site'],
        ranking_note='Ranking user claims only, not verified organizer results')
    (out / 'nine-site-audit.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print('Nine immutable blobs hashed; pairwise supports audited; no score receipts available.')


if __name__ == '__main__':
    run()
