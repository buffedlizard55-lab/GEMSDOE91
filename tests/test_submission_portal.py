"""Research downloads may exist with a negative verdict; upload approval may not.

Contract: links resolve, file identities are verified, and the portal cannot
confuse local format validity with protocol/scientific/selector clearance.
"""
import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import pytest
from gems91.readiness import gates, submission_ready

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set(); self.text=[]; self.downloads=[]; self.states=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        if tag in ('a','link') and 'href' in a: self.links.append(a['href'])
        if tag=='script' and 'src' in a: self.links.append(a['src'])
        if tag=='a' and 'download' in a: self.downloads.append(a.get('href'))
        if 'data-submission-ready' in a: self.states.append(a['data-submission-ready'])
    def handle_data(self, data): self.text.append(data)


def load_card():
    return json.loads((ROOT/'docs/run-card.json').read_text())


def test_all_local_page_links_assets_and_fragments_resolve():
    for name in ('index.html','docs/index.html','docs/s17-cdsc.html','docs/s17-cdsc-executive-summary.html','docs/s15-scgf.html','docs/s15-scgf-executive-summary.html','docs/s15-hcpa.html','docs/s15-executive-summary.html','docs/s14-hvdc.html','docs/s14-hvdc-executive-summary.html','docs/s14-lsrg.html','docs/s14-executive-summary.html','docs/s14-ptac.html','docs/s14-ptac-executive-summary.html','docs/s13-ptha.html','docs/s13-ptha-executive-summary.html','docs/ccr91-executive-summary.html','docs/ucd91.html','docs/mtd91.html','docs/executive-summary.html','docs/research.html','docs/submit.html'):
        path=ROOT/name; parser=Page(); parser.feed(path.read_text())
        for href in parser.links:
            u=urlsplit(href)
            if u.scheme or u.netloc: continue
            target=(path.parent/unquote(u.path)).resolve() if u.path else path
            assert target.is_file(), (name,href)
            assert target.is_relative_to(ROOT)
            if u.fragment and target.suffix=='.html':
                other=Page(); other.feed(target.read_text()); assert u.fragment in other.ids


def test_negative_research_download_is_not_advertised_as_approved_submission():
    card=load_card(); a=card['artifact']
    ccr=json.loads((ROOT/'docs/run-card-CCR91.json').read_text())
    ccr_file=Path(ccr['download']).relative_to('docs').as_posix()
    ccr_zip=Path(ccr['zip_download']).relative_to('docs').as_posix()
    s13=json.loads((ROOT/'docs/run-card-S13.json').read_text())
    s13_file=Path(s13['artifact']['primary_zeros_tif']).relative_to('docs').as_posix()
    s13_zip=Path(s13['artifact']['zip_bundle']).relative_to('docs').as_posix()
    hvdc=json.loads((ROOT/'docs/run-card-S14-HVDC.json').read_text())
    hvdc_file=Path(hvdc['artifact']['primary_zeros_tif']).relative_to('docs').as_posix()
    hvdc_zip=Path(hvdc['artifact']['zip_bundle']).relative_to('docs').as_posix()
    g91_allowed=set()
    try:
        g91=json.loads((ROOT/'docs/run-card-G91.json').read_text())
        g91_file=Path(g91['download']).relative_to('docs').as_posix() if 'download' in g91 else None
        g91_zip=Path(g91['zip_download']).relative_to('docs').as_posix() if 'zip_download' in g91 else None
        if g91_file: g91_allowed.add(g91_file)
        if g91_zip: g91_allowed.add(g91_zip)
    except Exception:
        pass
    s14_allowed=set(); s14=None
    try:
        s14=json.loads((ROOT/'docs/run-card-S14.json').read_text())
        s14_allowed={s14['artifact']['file'],s14['artifact']['zip']}
    except Exception:
        pass
    ptac=json.loads((ROOT/'docs/run-card-S14-PTAC.json').read_text())
    ptac_file=Path(ptac['artifact']['primary_zeros_tif']).relative_to('docs').as_posix()
    ptac_zip=Path(ptac['artifact']['zip_bundle']).relative_to('docs').as_posix()
    s15_allowed=set(); s15=None
    try:
        s15=json.loads((ROOT/'docs/run-card-S15.json').read_text())
        s15_allowed={s15['artifact']['file'],s15['artifact']['zip']}
    except Exception:
        pass
    scgf=json.loads((ROOT/'docs/run-card-S15-SCGF.json').read_text())
    scgf_file=Path(scgf['artifact']['primary_zeros_tif']).relative_to('docs').as_posix()
    scgf_zip=Path(scgf['artifact']['zip_bundle']).relative_to('docs').as_posix()
    cdsc=json.loads((ROOT/'docs/run-card-S17-CDSC.json').read_text())
    cdsc_file=Path(cdsc['artifact']['primary_zeros_tif']).relative_to('docs').as_posix()
    cdsc_zip=Path(cdsc['artifact']['zip_bundle']).relative_to('docs').as_posix()
    allowed={a['file'],a['zip'],ccr_file,ccr_zip,s13_file,s13_zip,hvdc_file,hvdc_zip,ptac_file,ptac_zip,scgf_file,scgf_zip,cdsc_file,cdsc_zip}|g91_allowed|s14_allowed|s15_allowed
    for name in ('archive-results.html','archive-guide.html'):
        p=Page(); p.feed((ROOT/'docs'/name).read_text()); text=' '.join(p.text)
        assert p.states and all(x=='false' for x in p.states)
        assert 'NOT OK TO SUBMIT' in text
        assert 'research' in text.lower()
        assert {a['file'],a['zip'],ccr_file,ccr_zip,s13_file,s13_zip,hvdc_file,hvdc_zip,ptac_file,ptac_zip,scgf_file,scgf_zip,cdsc_file,cdsc_zip}.issubset(p.downloads)
        assert all(x in allowed for x in p.downloads)
        assert 'bff9fd21.tif' not in text

    for cdsc_page_name in ('docs/s17-cdsc.html', 'docs/s17-cdsc-executive-summary.html'):
        cp=Page(); cp.feed((ROOT/cdsc_page_name).read_text()); ctext=' '.join(cp.text)
        assert cp.states and all(x=='false' for x in cp.states)
        assert cdsc_file in cp.downloads and cdsc_zip in cp.downloads
        assert 'NOT OK TO SUBMIT' in ctext
    assert not cdsc['submission_ready'] and not submission_ready(cdsc)
    assert cdsc['verdict']=='negative' and cdsc['organizer_confirmed'] is None
    assert hashlib.sha256((ROOT/cdsc['artifact']['primary_zeros_tif']).read_bytes()).hexdigest()==cdsc['raster_sha256']

    for scgf_page_name in ('docs/s15-scgf.html', 'docs/s15-scgf-executive-summary.html'):
        sp=Page(); sp.feed((ROOT/scgf_page_name).read_text()); stext=' '.join(sp.text)
        assert sp.states and all(x=='false' for x in sp.states)
        assert scgf_file in sp.downloads and scgf_zip in sp.downloads
        assert 'NOT OK TO SUBMIT' in stext
    assert not scgf['submission_ready'] and not submission_ready(scgf)
    assert scgf['verdict']=='negative' and scgf['organizer_confirmed'] is None
    assert hashlib.sha256((ROOT/scgf['artifact']['primary_zeros_tif']).read_bytes()).hexdigest()==scgf['raster_sha256']

    for hvdc_page_name in ('docs/s14-hvdc.html', 'docs/s14-hvdc-executive-summary.html'):
        hp=Page(); hp.feed((ROOT/hvdc_page_name).read_text()); htext=' '.join(hp.text)
        assert hp.states and all(x=='false' for x in hp.states)
        assert hvdc_file in hp.downloads and hvdc_zip in hp.downloads
        assert 'OK TO SUBMIT' in htext and 'NO' in htext
    assert not hvdc['submission_ready'] and not submission_ready(hvdc)
    assert hashlib.sha256((ROOT/hvdc['artifact']['primary_zeros_tif']).read_bytes()).hexdigest()==hvdc['raster_sha256']

    for ptac_page_name in ('docs/s14-ptac.html', 'docs/s14-ptac-executive-summary.html'):
        sp=Page(); sp.feed((ROOT/ptac_page_name).read_text()); stext=' '.join(sp.text)
        assert sp.states and all(x=='false' for x in sp.states)
        assert ptac_file in sp.downloads and ptac_zip in sp.downloads
        assert 'OK TO SUBMIT: NO' in stext and '99.852%' in stext
        assert 'REVIEW-S14-PTAC-20261024.md' in sp.links or ptac_page_name.endswith('executive-summary.html')
    assert not ptac['submission_ready'] and not submission_ready(ptac)
    assert ptac['registry_comparison']['final']['status']=='STOPPED_DUPLICATE'
    assert ptac['submission']['recommended_upload_file'] is None
    assert hashlib.sha256((ROOT/ptac['artifact']['primary_zeros_tif']).read_bytes()).hexdigest()==ptac['raster_sha256']

    for s13_page_name in ('docs/s13-ptha.html', 'docs/s13-ptha-executive-summary.html'):
        sp=Page(); sp.feed((ROOT/s13_page_name).read_text()); stext=' '.join(sp.text)
        assert sp.states and all(x=='false' for x in sp.states)
        assert s13_file in sp.downloads and s13_zip in sp.downloads
        assert 'NOT OK TO SUBMIT' in stext
    assert not s13['submission_ready'] and not submission_ready(s13)
    assert hashlib.sha256((ROOT/s13['artifact']['primary_zeros_tif']).read_bytes()).hexdigest()==s13['raster_sha256']

    if s14 is not None:
        for s14_page_name in ('docs/s14-lsrg.html', 'docs/s14-executive-summary.html'):
            sp=Page(); sp.feed((ROOT/s14_page_name).read_text()); stext=' '.join(sp.text)
            assert sp.states and all(x=='false' for x in sp.states)
            assert s14['artifact']['file'] in sp.downloads and s14['artifact']['zip'] in sp.downloads
            assert 'NOT OK TO SUBMIT' in stext or 'OK TO SUBMIT: NO' in stext
        assert not s14['submission_ready'] and not submission_ready(s14)
        assert s14['organizer_confirmed'] is None
        assert hashlib.sha256((ROOT/'docs'/s14['artifact']['file']).read_bytes()).hexdigest()==s14['raster_sha256']

    if s15 is not None:
        for s15_page_name in ('docs/s15-hcpa.html', 'docs/s15-executive-summary.html'):
            sp=Page(); sp.feed((ROOT/s15_page_name).read_text()); stext=' '.join(sp.text)
            assert sp.states and all(x=='false' for x in sp.states)
            assert s15['artifact']['file'] in sp.downloads and s15['artifact']['zip'] in sp.downloads
            assert 'NOT OK TO SUBMIT' in stext or 'OK TO SUBMIT: NO' in stext
        assert not s15.get('submission_ready', False) and not submission_ready(s15)
        assert s15['organizer_confirmed'] is None
        assert hashlib.sha256((ROOT/'docs'/s15['artifact']['file']).read_bytes()).hexdigest()==s15['raster_sha256']

    page=Page(); page.feed((ROOT/'docs/ccr91-executive-summary.html').read_text())
    text=' '.join(page.text)
    assert page.states==['false']
    assert ccr_file in page.downloads and ccr_zip in page.downloads
    assert 'NOT OK TO SUBMIT' in text and '99.769%' in text
    assert not ccr['ok_to_submit'] and ccr['verdict']=='negative'
    assert hashlib.sha256((ROOT/ccr['download']).read_bytes()).hexdigest()==ccr['raster_sha256']


def test_card_is_a_measured_negative_not_an_empty_placeholder_or_fake_score():
    card=load_card(); h=card['holdout_dti']
    assert not card['submission_ready'] and not submission_ready(card)
    assert card['verdict']=='negative' and card['experiments_run']==1
    assert card['slots_used']==0 and card['organizer_confirmed'] is None
    assert h['label']=='HOLDOUT-DTI' and h['evaluator_version']=='gems57-pooled-hide-v2'
    assert h['withheld_positives']==60988
    assert h['ci95'][0] < h['value'] < h['ci95'][1]
    assert h['paired_control']['ci95'][0] < 0 < h['paired_control']['ci95'][1]
    assert 0<len(card['note'])<=140 and len(card['submission_name'])<=140
    p=ROOT/'docs'/card['artifact']['file']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==card['raster_sha256']
    assert card['registry_comparison']['final']['status']=='DUPLICATE'
    assert not gates(card)['novelty']


def test_readiness_requires_all_independent_gates_not_just_format():
    assert not submission_ready({})
    c=load_card(); c['submission_ready']=True
    assert not submission_ready(c)
    # Synthetic policy fixture, not a claimed actual promoted experiment.
    good=copy.deepcopy(c)
    good['lane']['assigned']=True
    good['registry_comparison'].update(complete_universal_registry=True,
        preplacement={'status':'PASS_WITHIN_INDEXED_SCOPE','checked':64,'not_checked_after_stop':0},
        final={'status':'PASS_WITHIN_INDEXED_SCOPE','checked':64,'not_checked_after_stop':0},
        max_measured_surface_rank_correlation=.2,
        max_measured_final_dot_rank_correlation=.2, max_measured_final_dot_overlap_within_3px=.6)
    good['comparable_prior_holdout_best']={
        'evaluator_version':'gems57-pooled-hide-v2','split_sha256':'fixture',
        'value':good['holdout_dti']['value']-.01, 'ci95':[0,.1],
        'withheld_positives':good['holdout_dti']['withheld_positives']}
    good['holdout_dti'].update(split_sha256='fixture',paired_best={'delta':.01,'ci95':[.001,.02]})
    good['selector_approval']=True
    good['selector_receipt']={'weekly_cap_verified':True,'slot_available':True}
    assert submission_ready(good)
    for mutate in (
        lambda x:x['validator_output'].update(status='UNVERIFIED'),
        lambda x:x['canaries'].update(status='LEAKAGE_SUSPECTED'),
        lambda x:x['registry_comparison']['final'].update(status='DUPLICATE'),
        lambda x:x['registry_comparison'].update(complete_universal_registry=False),
        lambda x:x['lane'].update(assigned=False),
        lambda x:x.update(comparable_prior_holdout_best=None),
        lambda x:x['holdout_dti']['paired_best'].update(ci95=[-.001,.02]),
        lambda x:x['selector_receipt'].update(slot_available=False),
    ):
        changed=copy.deepcopy(good); mutate(changed); assert not submission_ready(changed)


def test_portal_render_is_reproducible():
    names=['index.html','archive-results.html','archive-guide.html','archive-research.html','review-0a96aa96-home.html','assets/s16.css','assets/s16-support.png','s17-cdsc.html','s17-cdsc-executive-summary.html','s15-scgf.html','s15-scgf-executive-summary.html','s15-hcpa.html','s15-executive-summary.html','s14-hvdc.html','s14-hvdc-executive-summary.html','s14-lsrg.html','s14-executive-summary.html','s14-ptac.html','s14-ptac-executive-summary.html','s13-ptha.html','s13-ptha-executive-summary.html','ccr91-executive-summary.html','executive-summary.html','research.html','submit.html','assets/portal.css','assets/portal.js']
    before={n:(ROOT/'docs'/n).read_bytes() for n in names}
    subprocess.run([sys.executable,'scripts/render_portal.py'],cwd=ROOT,check=True,capture_output=True)
    assert before=={n:(ROOT/'docs'/n).read_bytes() for n in names}, 'Generated portal drift; render before committing.'


def test_download_zip_and_byte_identity_are_revalidated():
    spec=importlib.util.spec_from_file_location('artifact_check',ROOT/'scripts/verify_current_artifact.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    result=mod.verify()
    assert result['status']=='PASS' and not result['submission_ready']
    with pytest.raises(ValueError): mod.published_path('../README.md')


def test_source_register_never_treats_unfetched_page_as_organizer_receipt():
    sources=json.loads((ROOT/'docs/sources.json').read_text())
    assert len(sources)>=10
    for s in sources: assert s['url'].startswith('https://') and s['verification']
    fleet=json.loads((ROOT/'docs/fleet-audit.json').read_text())
    assert len(fleet['rows'])==92
    assert not fleet['complete_universal_registry']
    assert all(not r['organizer_confirmed_scores'] for r in fleet['rows'])
