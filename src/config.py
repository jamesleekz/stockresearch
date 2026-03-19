from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
WATCHLIST_PATH = ROOT_DIR / "watchlist.csv"


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    data_dir: Path
    reports_dir: Path
    watchlist_path: Path
    report_lookback_days: int
    max_news_items: int
    openai_api_key: str | None
    openai_model: str
    openai_reasoning_effort: str
    alpaca_paper_api_key: str | None
    alpaca_paper_api_secret: str | None
    paper_trading_enabled: bool
    paper_trade_notional_usd: float
    max_position_notional_usd: float
    stop_loss_pct: float
    take_profit_pct: float
    trade_during_market_hours_only: bool


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    load_dotenv(ROOT_DIR / ".env")

    return Settings(
        root_dir=ROOT_DIR,
        data_dir=DATA_DIR,
        reports_dir=REPORTS_DIR,
        watchlist_path=WATCHLIST_PATH,
        report_lookback_days=int(os.getenv("REPORT_LOOKBACK_DAYS", "90")),
        max_news_items=int(os.getenv("MAX_NEWS_ITEMS", "5")),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low"),
        alpaca_paper_api_key=os.getenv("ALPACA_PAPER_API_KEY") or None,
        alpaca_paper_api_secret=os.getenv("ALPACA_PAPER_API_SECRET") or None,
        paper_trading_enabled=_get_bool("PAPER_TRADING_ENABLED", False),
        paper_trade_notional_usd=float(os.getenv("PAPER_TRADE_NOTIONAL_USD", "100")),
        max_position_notional_usd=float(os.getenv("MAX_POSITION_NOTIONAL_USD", "300")),
        stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", "8")),
        take_profit_pct=float(os.getenv("TAKE_PROFIT_PCT", "15")),
        trade_during_market_hours_only=_get_bool("TRADE_DURING_MARKET_HOURS_ONLY", True),
    )
