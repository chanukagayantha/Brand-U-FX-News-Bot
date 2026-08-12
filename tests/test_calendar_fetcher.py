import json
import os
from unittest.mock import MagicMock, patch

from src.fetchers.calendar_fetcher import fetch_calendar_events

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample_calendar.json")


def _load_fixture() -> list:
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@patch("src.fetchers.calendar_fetcher.requests.get")
def test_fetch_calendar_events_parses_entries(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = _load_fixture()
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    events = fetch_calendar_events("https://example.com/calendar.json")

    assert len(events) == 3
    cpi = events[0]
    assert cpi.title == "CPI m/m"
    assert cpi.status == "pending"

    gdp = events[2]
    assert gdp.status == "released"


@patch("src.fetchers.calendar_fetcher.requests.get")
def test_fetch_calendar_events_returns_empty_on_failure(mock_get):
    mock_get.side_effect = ConnectionError("boom")

    events = fetch_calendar_events("https://example.com/calendar.json")

    assert events == []
