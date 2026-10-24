"""The public site must fail closed when no approved candidate exists."""
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTAL_PAGES = (
    "index.html",
    "docs/index.html",
    "docs/executive-summary.html",
    "docs/submit.html",
)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(v for k, v in attrs if k == "href")


def test_portal_links_and_no_tiff_download():
    for name in PORTAL_PAGES:
        page = ROOT / name
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for href in parser.links:
            if "://" not in href and not href.startswith("#"):
                target = (page.parent / href.split("#", 1)[0]).resolve()
                assert target.is_file(), f"{name}: broken local link {href}"
            path = href.split("?", 1)[0].lower()
            assert not path.endswith((".tif", ".tiff", ".zip")), (name, href)


def test_current_pages_make_blocked_status_obvious():
    root = (ROOT / "index.html").read_text(encoding="utf-8").lower()
    landing = (ROOT / "docs/index.html").read_text(encoding="utf-8").lower()
    executive = (ROOT / "docs/executive-summary.html").read_text(encoding="utf-8").lower()
    submit = (ROOT / "docs/submit.html").read_text(encoding="utf-8").lower()
    assert "not approved" in root
    assert "do not download or submit a tiff" in root
    assert "not approved" in landing
    assert "do not download or submit a tiff" in landing
    assert "not approved" in executive
    assert "no tiff is available" in executive
    assert "not approved" in submit
    for forbidden in ("validated — ok to download", "ready to download", "submit this"):
        assert forbidden not in landing
        assert forbidden not in executive


def test_blocked_card_is_complete_and_has_no_artifact():
    card = json.loads((ROOT / "docs/run-card.json").read_text(encoding="utf-8"))
    assert card["verdict"] == "negative"
    assert card["submission_ready"] is False
    assert card["selected_for_slot"] is False
    assert card["experiments_run"] == 0
    assert card["raster_sha256"] is None
    assert card["submission_name"] is None
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["status"] == "NOT_RUN"
    assert card["holdout_dti"]["evaluator_version"] is None
    assert card["holdout_dti"]["withheld_positives"] is None
    assert card["holdout_dti"]["ci95"] is None
    assert card["registry_comparison"]["status"] == "UNVERIFIED"
    assert card["validator_output"]["status"] == "NOT_RUN"
    assert card["submission_note"] is None
    assert card["submission_note_status"] == "NOT_GENERATED_NO_CANDIDATE"
    assert card["submission_note_max_chars"] == 140
    assert len(card["run_note"]) <= 140
    downloads = ROOT / "docs/downloads"
    assert (downloads / "README.md").is_file()
    assert not list(downloads.glob("*.tif"))
    assert not list(downloads.glob("*.tiff"))
    assert not list(downloads.glob("*.zip"))


def test_master_brief_is_in_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    for text in (
        "read this readme first",
        "parallel-run protocol",
        "evaluate_holdout.py",
        "submission_writer.py",
        "holdout-dti",
        "core values",
        "maximize p(win)",
        "up to three scored submissions per week",
        "one final submission selection across both prize phases",
        "5 p.m. et",
        "reproducible code assets and documentation",
    ):
        assert text in readme
