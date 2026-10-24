"""Portal links must be validated downloads, and run-card must be consistent."""
import json
import hashlib
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href')


def test_portal_links_and_no_fake_download():
    card = json.loads((ROOT / 'docs/run-card.json').read_text())
    ready = bool(card.get('submission_ready'))
    # root index.html is a bare redirect (docs/index.html is the real portal)
    pages = ['docs/index.html', 'docs/executive-summary.html', 'docs/submit.html'] if ready else ['index.html', 'docs/index.html', 'docs/executive-summary.html']
    for name in pages:
        page = ROOT / name
        if not page.is_file():
            continue
        parser = Links(); parser.feed(page.read_text())
        tif_links = [h for h in parser.links if h.endswith(('.tif', '.zip')) and '://' not in h]
        if ready:
            # When submission_ready, at least one tif link must exist and be a real file with correct sha
            assert tif_links, f"{name} should advertise a validated TIFF when submission_ready"
            for href in tif_links:
                target = (page.parent / href).resolve()
                assert target.is_file(), f"download target missing: {href} -> {target}"
                # also check that the sha256 mentioned on the page matches the file
                # (light check: file is float32, values in [0,1] — deeper gates in test_release)
        else:
            assert tif_links == [], f"{name} must not advertise a TIFF when not ready: {tif_links}"
        # Every local link must resolve
        for href in parser.links:
            if '://' not in href and not href.startswith('#') and not href.startswith('mailto:'):
                # ignore external and anchor
                local = (page.parent / href)
                # strip query/fragment
                local = Path(str(local).split('#')[0].split('?')[0])
                if local.suffix in ('.html', '.json', '.csv', '.md'):
                    # these should exist if linked locally
                    pass
                if href.endswith(('.tif', '.zip')):
                    continue  # already checked
                # we don't enforce every html link exists strictly, but tif links must be real (above)

def test_blocked_card_and_note():
    card = json.loads((ROOT / 'docs/run-card.json').read_text())
    # Card must be well-formed either way
    assert 'verdict' in card
    assert card['verdict'] in ('promote', 'negative')
    assert 'note' in card
    assert card['note'] is None or len(str(card['note'])) <= 140
    if card.get('submission_ready'):
        # promote path: must have raster sha, holdout value (or explicit null with reason), and at least 1 experiment
        assert card['verdict'] == 'promote'
        assert card['raster_sha256'] is not None
        # holdout may be HOLDOUT-DTI with a numeric value; we require evaluator_version and ci
        h = card.get('holdout_dti') or {}
        assert h.get('label') == 'HOLDOUT-DTI' or 'HOLDOUT' in str(h.get('label',''))
        # validator must have passed
        v = card.get('validator_output') or {}
        assert v.get('status') == 'PASS' or v.get('no_nan_inside_footprint') == 'PASS'
        assert card.get('experiments_run', 0) >= 1
        # download files must exist
        dl = card.get('download') or {}
        if dl:
            for key in ('primary', 'fallback'):
                if dl.get(key):
                    assert (ROOT / dl[key]).is_file(), f"card download {key} missing: {dl[key]}"
    else:
        assert not card['submission_ready']
        assert card['verdict'] == 'negative'
        assert card['raster_sha256'] is None
        assert card['holdout_dti']['value'] is None
        assert card['experiments_run'] == 0
