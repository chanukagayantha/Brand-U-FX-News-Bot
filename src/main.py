"""CLI entrypoint: `python -m src.main` (continuous) or `python -m src.main --once`."""

from __future__ import annotations

import argparse
import logging
import sys

from src.analyzer import GoldNewsAnalyzer
from src.config import Config
from src.pipeline import Pipeline
from src.providers.factory import create_backend
from src.storage import Storage


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gold market news extraction and impact analysis bot")
    parser.add_argument(
        "--once", action="store_true", help="Run a single poll cycle and exit (for cron/testing)"
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override LOG_LEVEL from config (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    config = Config.from_env()

    log_level = args.log_level or config.log_level
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("main")

    if config.analyzer_provider not in ("claude", "gemini"):
        logger.error(
            "Unknown ANALYZER_PROVIDER=%r (expected 'claude' or 'gemini')",
            config.analyzer_provider,
        )
        return 1
    if config.analyzer_provider == "claude" and not config.anthropic_api_key:
        logger.error(
            "ANALYZER_PROVIDER=claude but ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
        return 1
    if config.analyzer_provider == "gemini" and not config.gemini_api_key:
        logger.error(
            "ANALYZER_PROVIDER=gemini but GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
        return 1

    storage = Storage(config.db_path)
    analyzer = GoldNewsAnalyzer(backend=create_backend(config))
    pipeline = Pipeline(config, storage, analyzer)

    if args.once:
        pipeline.run_once()
    else:
        pipeline.run_forever()

    storage.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
