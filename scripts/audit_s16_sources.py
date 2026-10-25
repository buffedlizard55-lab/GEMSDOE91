#!/usr/bin/env python3
"""Evidence audit of already fetched, pinned GitHub snapshots and local rasters.

No model fits, candidate placement or organizer submissions. Source claims are
not organizer receipts. Source acquisition logs live in work/s16_sources/.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

OUT = ROOT / 'docs/s16'
WORK = ROOT / 'work/s16_sources'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def source(filename, repo, ref_file, path, claim, classification, needles):
    data = (WORK / filename).read_bytes()
    text = data.decode()
    commit = (WORK / ref_file).read_text().strip()
    excerpts = []
    for needle in needles:
        pos = text.find(needle)
        if pos < 0:
            raise ValueError(f'supporting quotation missing: {needle}')
        excerpts.append(text[max(0, pos - 40):pos + 330])
    return dict(claim=claim, classification=classification,
        url=f'https://github.com/{repo}/blob/{commit}/{path}', commit=commit,
        sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), excerpts=excerpts,
        verification='Fetched GitHub bytes at recorded commit; statements only support the scope of the quoted source.',
        organizer_receipt=False)


def main():
    sources = [
        source('official-reference.ipynb', 'drivendataorg/gems-prize-reference-solution', 'reference-sha.txt',
               'unet-mc-cv-reference-solution.ipynb',
               'Official example uses U-Net and Tversky training weights alpha 0.2 / beta 0.8. This is not an official implementation of distance-weighted scoring.',
               'OFFICIAL_REPOSITORY', ['alpha = 0.2', 'beta = 0.8', 'TverskyLoss']),
        source('gems32-index.html', 'buffedlizard55-lab/GEMSDOE32', 'gems32-sha.txt', 'docs/index.html',
               'GEMSDOE32 describes H33-2-B2 as a catalogue-flank prune and explicitly says no organizer score exists in that snapshot.',
               'OWNER_SOURCE_NOT_ORGANIZER', ['NO ORGANISER SCORE EXISTS', 'every dot at d(catalogue)']),
        source('g32-run_h33_validation.py', 'buffedlizard55-lab/GEMSDOE32', 'gems32-sha.txt', 'scripts/run_h33_validation.py',
               'The H33-2 candidate builder applies catalogue-distance exclusion buffers 2 and 3 to an existing base.',
               'OWNER_SOURCE_NOT_ORGANIZER', ['buffers=(2, 3)', 'candidates[f"H33-2-B{b}"]']),
        source('harmonica-filters.py', 'fatiando/harmonica', 'harmonica-sha.txt', 'src/harmonica/filters/_filters.py',
               'Potential-field filters are expressed in angular wavenumber; pole reduction depends on field and source magnetization directions. This is author software, not evidence of a geothermal target.',
               'AUTHOR_MAINTAINED_SCIENTIFIC_SOFTWARE', ['def derivative_upward_kernel', 'def reduction_to_pole_kernel', 'magnetization_inclination']),
    ]
    for url, claim in [
        ('https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/', 'Official competition problem, metric and format; not freshly authenticated here.'),
        ('https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/', 'Current leaderboard not verified; conflicting prompt figures must not be presented as live data.'),
        ('https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/', 'Weekly cap, account eligibility, slot use and score receipts not authenticated in this session.'),
        ('https://docs.nlr.gov/docs/fy26osti/96647.pdf', 'Official rules lead; no fresh legal/eligibility verification from this host.'),
        ('https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and', 'Official GeoDAWN source lead; mirror hashes do not prove data-use permission.'),
        ('https://gdr.openei.org/submissions/1391', 'Official geothermal well/spring data lead; not an input to S16.'),
        ('https://gbcge.org/current-projects/ingenious/', 'Institutional geothermal exploration project lead; not a verified source for historical numeric geology claims in this session.'),
    ]:
        sources.append(dict(url=url, claim=claim, classification='OFFICIAL_OR_INSTITUTIONAL_LEAD',
                            verification='NOT_FETCHED_OR_AUTHENTICATED: no fetched page or authenticated receipt is in this audit.', organizer_receipt=False))
    dump('sources.json', dict(checked_utc=datetime.now(timezone.utc).isoformat(), sources=sources,
        organizer_confirmed_scores=[], limitation='No primary source establishes why a specific hidden leaderboard score occurred.'))

    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    pins = {r['id']: r for r in manifest['files']}
    with rasterio.open(ROOT / 'data' / pins['sample_submission']['local_subpath']) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / 'data' / pins['existing_faults']['local_subpath']) as ds:
        cat = (ds.read(1) > 0) & fp
    dcat = ndi.distance_transform_edt(~cat)
    fields = {}
    records = []
    for key in ('anc_h19_5', 'anc_d2_8', 'anc_solo_d2_8', 'parent_r0_zeros'):
        pin = pins[key]; path = ROOT / 'data' / pin['local_subpath']
        if sha(path) != pin['sha256']:
            raise ValueError(f'input pin mismatch: {key}')
        with rasterio.open(path) as s:
            a = s.read(1)
            dots = (a > 0) & fp
            row = dict(id=key, sha256=sha(path), positive_support_pixels=int(dots.sum()),
                       min_catalogue_distance_px=float(dcat[dots].min()),
                       support_at_catalogue_distance_le_2px=int((dots & (dcat <= 2)).sum()),
                       binary_inside_footprint=bool(np.isin(a[fp], [0, 1]).all()))
        fields[key] = dots
        records.append(row)
    base, r0 = fields['anc_solo_d2_8'], fields['parent_r0_zeros']
    pts = np.argwhere(r0)
    distances = cKDTree(pts).query(pts, k=2)[0][:, 1]
    source_zip = WORK / 'gems32-archive.zip'
    with zipfile.ZipFile(source_zip) as z:
        zip_members = [dict(name=x.filename, uncompressed_bytes=x.file_size) for x in z.infolist()]
        valid_zip = len(zip_members) == 1 and zip_members[0]['name'].lower().endswith('.tif') and zip_members[0]['uncompressed_bytes'] > 0
    dump('gems32-forensics.json', dict(evidence_class='LOCAL_GEOMETRY_AND_ARCHIVE_AUDIT_NOT_A_SCORE',
        records=records, r0_is_exact_base_with_distance_gt_2=bool(np.array_equal(r0, base & (dcat > 2))),
        r0_added_vs_base=int((r0 & ~base).sum()), r0_removed_vs_base=int((base & ~r0).sum()),
        r0_nearest_neighbor_px=dict(min=float(distances.min()), median=float(np.median(distances))),
        advertised_zip=dict(sha256=sha(source_zip), bytes=source_zip.stat().st_size, members=zip_members,
                            single_nonempty_tif=valid_zip),
        user_reported_dti=0.2778, score_evidence_class='USER_REPORTED_UNVERIFIED_NOT_ORGANIZER_CONFIRMED',
        score_receipt=None,
        conclusion='The pruned geometry is reproducible; its hidden-score causal gain is not identifiable without organizer truth/receipts.'))

    inv = json.loads((ROOT / 'registry/s16_comparison_inventory.json').read_text())
    row = next(r for r in inv['files'] if Path(r['path']).name == 'calib_r13lattice_00904.tif')
    path = ROOT / row['path']
    if sha(path) != row['sha256']:
        raise ValueError('lattice pin mismatch')
    with rasterio.open(path) as s:
        ref = (s.read(1) > 0) & fp
    gap = int((fp & (ndi.distance_transform_edt(~ref) > 3)).sum())
    budget = 37654
    dump('registry-feasibility.json', dict(evidence_class='GEOMETRIC_CAPACITY_BOUND_NOT_A_SCORE',
        reference=row, footprint_pixels=int(fp.sum()), uncovered_pixels=gap,
        covered_fraction=1 - gap / int(fp.sum()), candidate_budget=budget,
        overlap_lower_bound=max(0, 1 - gap / budget), threshold=.70,
        feasible_at_fixed_budget=1 - gap / budget <= .70,
        calculation='At most one binary dot per uncovered cell; overlap >= (budget - uncovered_cells)/budget. Spacing can only tighten this bound.',
        policy='No reference removed or threshold changed. A source-feed inventory is not universal raster uniqueness.'))
    print('Source, parent geometry, malformed ZIP and registry feasibility audits written; no geological experiment.')


if __name__ == '__main__':
    main()
