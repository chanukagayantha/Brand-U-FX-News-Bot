# Brand-U-FX-News-Bot

A near-real-time gold market (XAU/USD) news bot. It polls financial RSS feeds
and an economic calendar feed, filters for gold-relevant items, uses an LLM
(Gemini or Claude, configurable) to analyze each item's likely market impact,
and stores short trader-facing summaries. There is no distribution channel
yet — this is the extraction and analysis pipeline that a future
Telegram/email layer will read from.

## Architecture

```
fetch (RSS + economic calendar)
  -> dedupe against SQLite (URL for news, pending/released status for calendar events)
  -> cheap keyword prefilter (cuts LLM calls by an estimated 85-95%)
  -> LLM analysis (relevance, direction, impact level, short summary) via Gemini or Claude
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
# edit .env: set ANALYZER_PROVIDER (defaults to "gemini") and the matching API key
# (GEMINI_API_KEY for gemini, ANTHROPIC_API_KEY for claude)
```

For development (adds pytest):

```bash
pip install -r requirements-dev.txt
```

## Configuration

`ANALYZER_PROVIDER` picks the LLM backend; only the matching API key is
required. Everything else has a built-in default so the bot runs out of the
box.

| Variable | Default | Description |
|---|---|---|
| `ANALYZER_PROVIDER` | `gemini` | Which LLM backend to use: `gemini` or `claude` |
| `GEMINI_API_KEY` | *(required if provider=gemini)* | Your Gemini API key |
| `GEMINI_MODEL` | `gemini-flash-latest` | Gemini model used for impact analysis. A rolling alias, not a dated model — Google occasionally sunsets specific dated models (e.g. `gemini-2.5-flash` can 404 for new API keys even though it's still listed by `client.models.list()`); `run list_gemini_models.py` to see what your key can actually call if you want to pin a specific version instead |
| `ANTHROPIC_API_KEY` | *(required if provider=claude)* | Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-5` | Claude model used for impact analysis |
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

All tests run without a live API key or network access — HTTP calls are
mocked against local fixtures, and both provider clients are fully mocked in
`tests/test_claude_backend.py` and `tests/test_gemini_backend.py` (the
provider-agnostic logic in `src/analyzer.py` is tested separately in
`tests/test_analyzer.py` against a fake backend). CI (`.github/workflows/tests.yml`)
runs the same suite on every push/PR to `main` — no secrets required.

## Cost notes

The keyword prefilter is the primary cost control — most fetched items never
reach the LLM. Both backends run as bounded, low-effort classification calls:
Claude uses `effort: "low"` with thinking disabled; Gemini uses
`gemini-flash-latest` with `thinking_budget: 0`. Claude's system prompt is also
cached (`cache_control: ephemeral`) so repeated calls within the cache TTL are
cheaper — Gemini has an equivalent context-caching feature that isn't wired
up yet (see Roadmap).

## Roadmap

- Distribution layer (Telegram bot, email digest) consuming
  `Storage.get_unsent_analyses()` and the shared formatting functions in
  `src/output.py`.
- Gemini context caching, to match Claude's prompt-caching cost savings.

## Disclaimer

This tool produces automated market commentary for informational purposes
only. It is not financial advice.
