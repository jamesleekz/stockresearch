from __future__ import annotations

from dataclasses import dataclass

from fetch_data import StockSnapshot
from utils import format_money, format_percent


@dataclass
class StockSummary:
    symbol: str
    company: str
    standout_summary: str
    key_catalyst_or_risk: str
    needs_attention_today: str


def _metric_clause(label: str, value: float | None) -> str | None:
    if value is None:
        return None
    return f"{label} {format_percent(value)}"


def summarize_stock(snapshot: StockSnapshot) -> StockSummary:
    overview = (
        f"{snapshot.company} ({snapshot.symbol}) trades near "
        f"{format_money(snapshot.current_price)} with a market cap of {format_money(snapshot.market_cap)}. "
        f"The business sits in {snapshot.sector or 'an unspecified sector'}"
        f"{f' / {snapshot.industry}' if snapshot.industry else ''}."
    )

    growth_bits = [
        _metric_clause("revenue growth is", snapshot.revenue_growth),
        _metric_clause("earnings growth is", snapshot.earnings_growth),
    ]
    growth_bits = [bit for bit in growth_bits if bit]

    momentum_sentence = "Recent momentum is limited."
    if snapshot.price_change_1m_pct is not None or snapshot.price_change_3m_pct is not None:
        parts = []
        if snapshot.price_change_1m_pct is not None:
            parts.append(f"1-month performance is {format_percent(snapshot.price_change_1m_pct)}")
        if snapshot.price_change_3m_pct is not None:
            parts.append(f"3-month performance is {format_percent(snapshot.price_change_3m_pct)}")
        momentum_sentence = ", while ".join(parts) + "."

    second_sentence = " ".join(
        part for part in [
            ("Operationally, " + " and ".join(growth_bits) + ".") if growth_bits else "Operational trend data is limited.",
            momentum_sentence,
        ] if part
    )
    standout_summary = f"{overview} {second_sentence}"

    if snapshot.recent_news:
        title = snapshot.recent_news[0].get("title") or "recent headlines"
        key_catalyst_or_risk = f"Monitor recent news flow, especially: {title}."
    elif snapshot.analyst_target_price and snapshot.current_price:
        upside = ((snapshot.analyst_target_price - snapshot.current_price) / snapshot.current_price) * 100
        key_catalyst_or_risk = (
            f"Monitor whether the stock can justify analyst upside expectations of about {format_percent(upside)}."
            if upside >= 0
            else f"Monitor whether fundamentals stabilize given analyst downside of about {format_percent(upside)}."
        )
    elif snapshot.price_change_from_52w_high_pct is not None and snapshot.price_change_from_52w_high_pct > -5:
        key_catalyst_or_risk = "The stock is near its 52-week high, so any earnings miss or guidance cut could matter."
    else:
        key_catalyst_or_risk = "Monitor the next earnings update and any change in forward guidance."

    needs_attention = False
    reasons: list[str] = []
    if snapshot.recent_news:
        needs_attention = True
        reasons.append("there are fresh headlines")
    if snapshot.price_change_1m_pct is not None and abs(snapshot.price_change_1m_pct) >= 8:
        needs_attention = True
        reasons.append("recent price movement is sizable")
    if snapshot.price_change_from_52w_high_pct is not None and snapshot.price_change_from_52w_high_pct > -3:
        needs_attention = True
        reasons.append("the stock is close to its 52-week high")

    if needs_attention:
        needs_attention_today = "Yes" + (f" - {', '.join(reasons)}." if reasons else ".")
    else:
        needs_attention_today = "No - nothing in the current snapshot suggests urgent investor action today."

    return StockSummary(
        symbol=snapshot.symbol,
        company=snapshot.company,
        standout_summary=standout_summary,
        key_catalyst_or_risk=key_catalyst_or_risk,
        needs_attention_today=needs_attention_today,
    )
