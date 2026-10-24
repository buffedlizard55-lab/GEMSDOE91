"""The audit portal must not advertise an unvalidated submission."""
import json
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
    for name in ('index.html', 'docs/index.html', 'docs/executive-summary.html'):
        page = ROOT / name
        parser = Links(); parser.feed(page.read_text())
        for href in parser.links:
            if '://' not in href:
                assert (page.parent / href).is_file(), href
            assert not href.endswith(('.tif', '.zip'))


def test_blocked_card_and_note():
    card = json.loads((ROOT / 'docs/run-card.json').read_text())
    assert not card['submission_ready']
    assert card['verdict'] == 'negative'
    assert card['raster_sha256'] is None
    assert card['holdout_dti']['value'] is None
    assert card['experiments_run'] == 0
    assert len(card['note']) <= 140
