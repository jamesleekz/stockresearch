from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import yfinance as yf

from config import Settings
from utils import WatchlistItem, safe_float, utc_now


@dataclass
class StockSnapshot:
    symbol: str
    company: str
    notes: str
    fetched_at: str
    currency: str | None
    sector: str | None
    industry: str | None
    business_summary: str | None
    current_price: float | None
    previous_close: float | None
    market_cap: float | None
    trailing_pe: float | None
    forward_pe: float | None
    dividend_yield: float | None
    analyst_target_price: float | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    revenue_growth: float | None
    earnings_growth: float | None
    recommendation_key: str | None
    price_change_1m_pct: float | None
    price_change_3m_pct: float | None
    price_change_from_52w_high_pct: float | None
    price_change_from_52w_low_pct: float | None
    average_volume: float | None
    recent_news: list[dict[str, Any]]
    history: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _history_to_records(history: pd.DataFrame) -> list[dict[str, Any]]:
    if history.empty:
        return []

    records: list[dict[str, Any]] = []
    for index, row in history.reset_index().iterrows():
        dt_value = row.get("Date")
        records.append(
            {
                "date": dt_value.strftime("%Y-%m-%d") if hasattr(dt_value, "strftime") else str(dt_value),
                "open": safe_float(row.get("Open")),
                "high": safe_float(row.get("High")),
                "low": safe_float(row.get("Low")),
                "close": safe_float(row.get("Close")),
                "volume": safe_float(row.get("Volume")),
            }
        )
    return records


def _percent_change(start: float | None, end: float | None) -> float | None:
    if start in (None, 0) or end is None:
        return None
    return ((end - start) / start) * 100


def _extract_news(ticker: yf.Ticker, max_items: int) -> list[dict[str, Any]]:
    items = getattr(ticker, "news", None) or []
    news_items: list[dict[str, Any]] = []
    for item in items[:max_items]:
        content = item.get("content") or {}
        news_items.append(
            {
                "title": content.get("title") or item.get("title"),
                "summary": content.get("summary"),
                "publisher": content.get("provider", {}).get("displayName") or item.get("publisher"),
                "published_at": content.get("pubDate") or item.get("providerPublishTime"),
                "url": content.get("canonicalUrl", {}).get("url") or item.get("link"),
            }
        )
    return news_items


def fetch_stock_snapshot(item: WatchlistItem, settings: Settings) -> StockSnapshot:
    ticker = yf.Ticker(item.symbol)
    info = ticker.info or {}
    history = ticker.history(period=f"{settings.report_lookback_days}d", interval="1d", auto_adjust=False)

    current_price = safe_float(info.get("currentPrice")) or safe_float(info.get("regularMarketPrice"))
    previous_close = safe_float(info.get("previousClose"))
    market_cap = safe_float(info.get("marketCap"))
    trailing_pe = safe_float(info.get("trailingPE"))
    forward_pe = safe_float(info.get("forwardPE"))
    analyst_target_price = safe_float(info.get("targetMeanPrice"))
    fifty_two_week_high = safe_float(info.get("fiftyTwoWeekHigh"))
    fifty_two_week_low = safe_float(info.get("fiftyTwoWeekLow"))
    average_volume = safe_float(info.get("averageVolume"))
    revenue_growth = safe_float(info.get("revenueGrowth"))
    earnings_growth = safe_float(info.get("earningsGrowth"))
    dividend_yield = None
    raw_dividend_yield = safe_float(info.get("dividendYield"))
    if raw_dividend_yield is not None:
        dividend_yield = raw_dividend_yield * 100

    history_records = _history_to_records(history)
    close_prices = [record["close"] for record in history_records if record["close"] is not None]

    price_change_1m_pct = None
    price_change_3m_pct = None
    if len(close_prices) >= 22:
        price_change_1m_pct = _percent_change(close_prices[-22], close_prices[-1])
    if len(close_prices) >= 63:
        price_change_3m_pct = _percent_change(close_prices[-63], close_prices[-1])

    price_change_from_52w_high_pct = _percent_change(fifty_two_week_high, current_price)
    price_change_from_52w_low_pct = _percent_change(fifty_two_week_low, current_price)

    return StockSnapshot(
        symbol=item.symbol,
        company=item.company or info.get("longName") or info.get("shortName") or item.symbol,
        notes=item.notes,
        fetched_at=utc_now().isoformat(),
        currency=info.get("currency"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        business_summary=info.get("longBusinessSummary"),
        current_price=current_price,
        previous_close=previous_close,
        market_cap=market_cap,
        trailing_pe=trailing_pe,
        forward_pe=forward_pe,
        dividend_yield=dividend_yield,
        analyst_target_price=analyst_target_price,
        fifty_two_week_high=fifty_two_week_high,
        fifty_two_week_low=fifty_two_week_low,
        revenue_growth=(revenue_growth * 100) if revenue_growth is not None else None,
        earnings_growth=(earnings_growth * 100) if earnings_growth is not None else None,
        recommendation_key=info.get("recommendationKey"),
        price_change_1m_pct=price_change_1m_pct,
        price_change_3m_pct=price_change_3m_pct,
        price_change_from_52w_high_pct=price_change_from_52w_high_pct,
        price_change_from_52w_low_pct=price_change_from_52w_low_pct,
        average_volume=average_volume,
        recent_news=_extract_news(ticker, settings.max_news_items),
        history=history_records,
    )

