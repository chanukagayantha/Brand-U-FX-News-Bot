import os
from unittest.mock import MagicMock, patch

from src.fetchers.rss_fetcher import fetch_rss_items

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample_feed.xml")


def _load_fixture_bytes() -> bytes:
    with open(FIXTURE_PATH, "rb") as f:
        return f.read()


@patch("src.fetchers.rss_fetcher.requests.get")
def test_fetch_rss_items_parses_entries(mock_get):
    mock_response = MagicMock()
    mock_response.content = _load_fixture_bytes()
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    items = fetch_rss_items(["https://example.com/feed.xml"])

    assert len(items) == 2
    assert items[0].title == "Gold prices surge as Fed signals rate cuts amid CPI miss"
    # tracking param stripped
    assert "utm_source" not in items[0].url
    assert items[1].title == "Local bakery wins regional pastry award"


@patch("src.fetchers.rss_fetcher.requests.get")
def test_fetch_rss_items_one_broken_feed_does_not_abort(mock_get):
    def side_effect(url, timeout, headers):
        if "broken" in url:
            raise ConnectionError("boom")
        mock_response = MagicMock()
        mock_response.content = _load_fixture_bytes()
        mock_response.raise_for_status = MagicMock()
        return mock_response

    mock_get.side_effect = side_effect

    items = fetch_rss_items(["https://example.com/broken.xml", "https://example.com/ok.xml"])

    assert len(items) == 2
