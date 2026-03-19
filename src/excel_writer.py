from __future__ import annotations

from pathlib import Path

import pandas as pd

from fetch_data import StockSnapshot
from strategy import TradeDecision
from summarize import StockSummary


OVERVIEW_COLUMNS = [
    "symbol",
    "company",
    "fetched_at",
    "currency",
    "sector",
    "industry",
    "current_price",
    "previous_close",
    "market_cap",
    "trailing_pe",
    "forward_pe",
    "dividend_yield_pct",
    "analyst_target_price",
    "revenue_growth_pct",
    "earnings_growth_pct",
    "price_change_1m_pct",
    "price_change_3m_pct",
    "price_vs_52w_high_pct",
    "price_vs_52w_low_pct",
    "recommendation_key",
    "notes",
    "standout_summary",
    "key_catalyst_or_risk",
    "needs_attention_today",
    "trade_action",
    "trade_confidence",
    "trade_rationale",
    "trade_order_status",
    "trade_order_id",
    "position_qty",
    "position_market_value",
    "position_unrealized_pl_pct",
]

NEWS_COLUMNS = [
    "symbol",
    "company",
    "published_at",
    "publisher",
    "title",
    "summary",
    "url",
]


def _overview_rows(
    snapshots: list[StockSnapshot],
    summaries: list[StockSummary],
    decisions: list[TradeDecision],
) -> list[dict[str, object]]:
    summary_by_symbol = {summary.symbol: summary for summary in summaries}
    decision_by_symbol = {decision.symbol: decision for decision in decisions}
    rows: list[dict[str, object]] = []

    for snapshot in snapshots:
        summary = summary_by_symbol.get(snapshot.symbol)
        decision = decision_by_symbol.get(snapshot.symbol)
        rows.append(
            {
                "symbol": snapshot.symbol,
                "company": snapshot.company,
                "fetched_at": snapshot.fetched_at,
                "currency": snapshot.currency,
                "sector": snapshot.sector,
                "industry": snapshot.industry,
                "current_price": snapshot.current_price,
                "previous_close": snapshot.previous_close,
                "market_cap": snapshot.market_cap,
                "trailing_pe": snapshot.trailing_pe,
                "forward_pe": snapshot.forward_pe,
                "dividend_yield_pct": snapshot.dividend_yield,
                "analyst_target_price": snapshot.analyst_target_price,
                "revenue_growth_pct": snapshot.revenue_growth,
                "earnings_growth_pct": snapshot.earnings_growth,
                "price_change_1m_pct": snapshot.price_change_1m_pct,
                "price_change_3m_pct": snapshot.price_change_3m_pct,
                "price_vs_52w_high_pct": snapshot.price_change_from_52w_high_pct,
                "price_vs_52w_low_pct": snapshot.price_change_from_52w_low_pct,
                "recommendation_key": snapshot.recommendation_key,
                "notes": snapshot.notes,
                "standout_summary": summary.standout_summary if summary else None,
                "key_catalyst_or_risk": summary.key_catalyst_or_risk if summary else None,
                "needs_attention_today": summary.needs_attention_today if summary else None,
                "trade_action": decision.action if decision else None,
                "trade_confidence": decision.confidence if decision else None,
                "trade_rationale": decision.rationale if decision else None,
                "trade_order_status": decision.order_status if decision else None,
                "trade_order_id": decision.order_id if decision else None,
                "position_qty": decision.position_qty if decision else None,
                "position_market_value": decision.position_market_value if decision else None,
                "position_unrealized_pl_pct": decision.position_unrealized_pl_pct if decision else None,
            }
        )

    return rows


def _overview_df(
    snapshots: list[StockSnapshot],
    summaries: list[StockSummary],
    decisions: list[TradeDecision],
) -> pd.DataFrame:
    return pd.DataFrame(_overview_rows(snapshots, summaries, decisions), columns=OVERVIEW_COLUMNS)


def _news_rows(snapshots: list[StockSnapshot]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for snapshot in snapshots:
        for item in snapshot.recent_news:
            rows.append(
                {
                    "symbol": snapshot.symbol,
                    "company": snapshot.company,
                    "published_at": item.get("published_at"),
                    "publisher": item.get("publisher"),
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "url": item.get("url"),
                }
            )
    return rows


def _news_df(snapshots: list[StockSnapshot]) -> pd.DataFrame:
    return pd.DataFrame(_news_rows(snapshots), columns=NEWS_COLUMNS)


def _read_existing_sheet(path: Path, sheet_name: str, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)

    try:
        existing_df = pd.read_excel(path, sheet_name=sheet_name)
    except ValueError:
        return pd.DataFrame(columns=columns)

    return existing_df.reindex(columns=columns)


def write_excel_report(
    path: Path,
    snapshots: list[StockSnapshot],
    summaries: list[StockSummary],
    decisions: list[TradeDecision],
) -> None:
    overview_df = _overview_df(snapshots, summaries, decisions)
    news_df = _news_df(snapshots)

    existing_history_df = _read_existing_sheet(path, "History", OVERVIEW_COLUMNS)
    existing_news_history_df = _read_existing_sheet(path, "NewsHistory", NEWS_COLUMNS)

    history_df = pd.concat([existing_history_df, overview_df], ignore_index=True)
    news_history_df = pd.concat([existing_news_history_df, news_df], ignore_index=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        overview_df.to_excel(writer, index=False, sheet_name="Overview")
        news_df.to_excel(writer, index=False, sheet_name="News")
        history_df.to_excel(writer, index=False, sheet_name="History")
        news_history_df.to_excel(writer, index=False, sheet_name="NewsHistory")
