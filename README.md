# Brand-U-FX-News-Bot

A near-real-time gold market (XAU/USD) news bot. It polls financial RSS feeds
and an economic calendar feed, filters for gold-relevant items, uses Claude to
analyze each item's likely market impact, and stores short trader-facing
summaries. There is no distribution channel yet — this is the extraction and
analysis pipeline that a future Telegram/email layer will read from.

## Architecture

```
fetch (RSS + economic calendar)
  -> dedupe against SQLite (URL for news, pending/released status for calendar events)
  -> cheap keyword prefilter (cuts LLM calls by an estimated 85-95%)
  -> Claude analysis (relevance, direction, impact level, short summary)
  -> store in SQLite
  -> print/log a formatted summary for anything relevant
```

Repeats every `POLL_INTERVAL_MINUTES` (default 5), or run once with `--once`.

Calendar events are handled specially: an event is analyzed once when first
seen (to assess potential impact), and again exactly once when its `actual`
value is released (to assess realized impact vs. forecast) — never on an
unchanged repeat poll.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY
```

For development (adds pytest):

```bash
pip install -r requirements-dev.txt
```

## Configuration

All variables are optional except `ANTHROPIC_API_KEY`; everything else has a
built-in default so the bot runs out of the box.

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `ANALYZER_MODEL` | `claude-sonnet-5` | Claude model used for impact analysis |
| `POLL_INTERVAL_MINUTES` | `5` | Seconds between poll cycles, in minutes |
| `RSS_FEEDS` | Kitco, FXStreet, Investing.com, ForexLive, MarketWatch | Comma-separated RSS feed URLs |
| `CALENDAR_URL` | Forex Factory weekly calendar JSON | Economic calendar feed URL |
| `DB_PATH` | `data/gold_news.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Usage

```bash
# Continuous polling loop (Ctrl+C to stop)
python -m src.main

# Single pass — useful for cron or manual testing
python -m src.main --once --log-level DEBUG
```

## Data & storage

SQLite database at `DB_PATH` with four tables: `news_items`, `news_analysis`,
`calendar_events`, `calendar_analysis`. Every analysis row has a
`distributed_at` column (`NULL` today) — this is the seam a future
distribution layer uses to claim unsent items without touching this schema.

Inspect the database directly:

```bash
sqlite3 data/gold_news.db "SELECT title, direction, impact_level, summary FROM news_items JOIN news_analysis ON news_items.id = news_analysis.news_item_id ORDER BY analyzed_at DESC LIMIT 10;"
```

## Testing

```bash
pytest
```

All tests run without a live `ANTHROPIC_API_KEY` or network access — HTTP
calls are mocked against local fixtures, and the Claude client is fully
mocked in `tests/test_analyzer.py`.

## Cost notes

The keyword prefilter is the primary cost control — most fetched items never
reach the LLM. Analysis calls use `claude-sonnet-5` with `effort: "low"` and
thinking disabled (a bounded classification task), and the system prompt is
cached (`cache_control: ephemeral`) so repeated calls within the cache TTL are
cheap.

## Roadmap

- Distribution layer (Telegram bot, email digest) consuming
  `Storage.get_unsent_analyses()` and the shared formatting functions in
  `src/output.py`.

## Disclaimer

This tool produces automated market commentary for informational purposes
only. It is not financial advice.
