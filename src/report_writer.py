from __future__ import annotations

from pathlib import Path

from fetch_data import StockSnapshot
from strategy import TradeDecision
from summarize import StockSummary
from utils import ensure_directory, format_money, format_percent


def _stock_report_markdown(snapshot: StockSnapshot, summary: StockSummary, decision: TradeDecision) -> str:
    lines = [
        f"# {summary.company} ({summary.symbol})",
        "",
        "## What Stands Out",
        summary.standout_summary,
        "",
        "## Key Metrics",
        f"- Current price: {format_money(snapshot.current_price)} {snapshot.currency or ''}".strip(),
        f"- Previous close: {format_money(snapshot.previous_close)} {snapshot.currency or ''}".strip(),
        f"- Market cap: {format_money(snapshot.market_cap)}",
        f"- Trailing P/E: {snapshot.trailing_pe:.2f}" if snapshot.trailing_pe is not None else "- Trailing P/E: N/A",
        f"- Forward P/E: {snapshot.forward_pe:.2f}" if snapshot.forward_pe is not None else "- Forward P/E: N/A",
        f"- Dividend yield: {format_percent(snapshot.dividend_yield)}",
        f"- Revenue growth: {format_percent(snapshot.revenue_growth)}",
        f"- Earnings growth: {format_percent(snapshot.earnings_growth)}",
        "",
        "## Monitor",
        f"- {summary.key_catalyst_or_risk}",
        "",
        "## Attention Today",
        f"- {summary.needs_attention_today}",
        "",
        "## Paper Trading",
        f"- Signal: {decision.action}",
        f"- Confidence: {decision.confidence}",
        f"- Rationale: {decision.rationale}",
        f"- Order status: {decision.order_status}",
        f"- Current position qty: {decision.position_qty if decision.position_qty is not None else 'N/A'}",
        f"- Current position market value: {format_money(decision.position_market_value)}",
        f"- Current position unrealized P/L: {format_percent(decision.position_unrealized_pl_pct)}",
    ]

    if snapshot.recent_news:
        lines.extend(["", "## Recent News"])
        for item in snapshot.recent_news:
            title = item.get("title") or "Untitled"
            publisher = item.get("publisher") or "Unknown publisher"
            url = item.get("url") or ""
            if url:
                lines.append(f"- [{title}]({url}) ({publisher})")
            else:
                lines.append(f"- {title} ({publisher})")

    if snapshot.business_summary:
        lines.extend(["", "## Business Summary", snapshot.business_summary])

    return "\n".join(lines) + "\n"


def _combined_report_markdown(summaries: list[StockSummary], decisions: list[TradeDecision]) -> str:
    lines = [
        "# Watchlist Summary",
        "",
    ]

    if not summaries:
        lines.extend(
            [
                "No stock summaries were generated for this run.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend([
        "## Quick View",
    ])

    decisions_by_symbol = {decision.symbol: decision for decision in decisions}
    for summary in summaries:
        decision = decisions_by_symbol.get(summary.symbol)
        signal = decision.action if decision else "N/A"
        lines.append(f"- **{summary.symbol}**: {summary.standout_summary} Signal: {signal}.")

    lines.extend(["", "## Highlights"])
    for summary in summaries:
        decision = decisions_by_symbol.get(summary.symbol)
        lines.append(
            f"- **{summary.symbol}**: Monitor: {summary.key_catalyst_or_risk} Attention today: {summary.needs_attention_today} "
            f"Paper trade: {(decision.action if decision else 'N/A')}."
        )

    return "\n".join(lines) + "\n"


def write_stock_report(path: Path, snapshot: StockSnapshot, summary: StockSummary, decision: TradeDecision) -> None:
    ensure_directory(path.parent)
    path.write_text(_stock_report_markdown(snapshot, summary, decision), encoding="utf-8")


def write_combined_report(path: Path, summaries: list[StockSummary], decisions: list[TradeDecision]) -> None:
    ensure_directory(path.parent)
    path.write_text(_combined_report_markdown(summaries, decisions), encoding="utf-8")
