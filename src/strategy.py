from __future__ import annotations

from dataclasses import dataclass

from config import Settings
from fetch_data import StockSnapshot
from summarize import StockSummary


@dataclass
class PositionState:
    symbol: str
    qty: float = 0.0
    market_value: float = 0.0
    avg_entry_price: float | None = None
    unrealized_plpc: float | None = None


@dataclass
class TradeDecision:
    symbol: str
    action: str
    confidence: str
    rationale: str
    score: float = 0.0
    order_status: str = "not_submitted"
    order_id: str | None = None
    executed_side: str | None = None
    executed_notional_usd: float | None = None
    executed_qty: float | None = None
    position_qty: float | None = None
    position_market_value: float | None = None
    position_unrealized_pl_pct: float | None = None


def decide_trade(
    snapshot: StockSnapshot,
    summary: StockSummary,
    position: PositionState | None,
    settings: Settings,
) -> TradeDecision:
    buy_score = 0
    sell_score = 0
    buy_reasons: list[str] = []
    sell_reasons: list[str] = []
    held_position = position if position and position.qty > 0 else None

    position_qty = held_position.qty if held_position else 0.0
    position_market_value = held_position.market_value if held_position else 0.0
    position_unrealized_pl_pct = (
        held_position.unrealized_plpc * 100
        if held_position and held_position.unrealized_plpc is not None
        else None
    )

    if snapshot.revenue_growth is not None and snapshot.revenue_growth > 8:
        buy_score += 1
        buy_score += min(snapshot.revenue_growth / 20, 2)
        buy_reasons.append("revenue growth is healthy")
    if snapshot.earnings_growth is not None and snapshot.earnings_growth > 8:
        buy_score += 1
        buy_score += min(snapshot.earnings_growth / 20, 2)
        buy_reasons.append("earnings growth is healthy")
    if snapshot.price_change_1m_pct is not None and snapshot.price_change_1m_pct > 5:
        buy_score += 1
        buy_score += min(snapshot.price_change_1m_pct / 10, 1.5)
        buy_reasons.append("1-month momentum is positive")
    if snapshot.price_change_3m_pct is not None and snapshot.price_change_3m_pct > 10:
        buy_score += 1
        buy_score += min(snapshot.price_change_3m_pct / 15, 1.5)
        buy_reasons.append("3-month momentum is positive")

    if snapshot.revenue_growth is not None and snapshot.revenue_growth < 0:
        sell_score += 1
        sell_score += min(abs(snapshot.revenue_growth) / 20, 2)
        sell_reasons.append("revenue is contracting")
    if snapshot.earnings_growth is not None and snapshot.earnings_growth < 0:
        sell_score += 1
        sell_score += min(abs(snapshot.earnings_growth) / 20, 2)
        sell_reasons.append("earnings are contracting")
    if snapshot.price_change_1m_pct is not None and snapshot.price_change_1m_pct < -7:
        sell_score += 1
        sell_score += min(abs(snapshot.price_change_1m_pct) / 10, 1.5)
        sell_reasons.append("1-month momentum is weak")
    if snapshot.price_change_3m_pct is not None and snapshot.price_change_3m_pct < -12:
        sell_score += 1
        sell_score += min(abs(snapshot.price_change_3m_pct) / 15, 1.5)
        sell_reasons.append("3-month momentum is weak")

    if held_position and held_position.unrealized_plpc is not None:
        pnl_pct = held_position.unrealized_plpc * 100
        if pnl_pct <= -settings.stop_loss_pct:
            return TradeDecision(
                symbol=snapshot.symbol,
                action="SELL",
                confidence="high",
                rationale=f"Stop-loss triggered at {pnl_pct:.2f}% versus the {settings.stop_loss_pct:.2f}% threshold.",
                score=-10.0,
                position_qty=position_qty,
                position_market_value=position_market_value,
                position_unrealized_pl_pct=position_unrealized_pl_pct,
            )
        if pnl_pct >= settings.take_profit_pct:
            return TradeDecision(
                symbol=snapshot.symbol,
                action="SELL",
                confidence="high",
                rationale=f"Take-profit triggered at {pnl_pct:.2f}% versus the {settings.take_profit_pct:.2f}% threshold.",
                score=10.0,
                position_qty=position_qty,
                position_market_value=position_market_value,
                position_unrealized_pl_pct=position_unrealized_pl_pct,
            )

    if held_position and held_position.market_value >= settings.max_position_notional_usd:
        return TradeDecision(
            symbol=snapshot.symbol,
            action="HOLD",
            confidence="medium",
            rationale="Hold signal because the current position is already at or above the max position size limit.",
            score=buy_score - sell_score,
            position_qty=position_qty,
            position_market_value=position_market_value,
            position_unrealized_pl_pct=position_unrealized_pl_pct,
        )

    if buy_score >= 3 and sell_score == 0:
        return TradeDecision(
            symbol=snapshot.symbol,
            action="BUY",
            confidence="medium",
            rationale="Buy signal triggered because " + ", ".join(buy_reasons[:4]) + ".",
            score=buy_score - sell_score,
            position_qty=position_qty,
            position_market_value=position_market_value,
            position_unrealized_pl_pct=position_unrealized_pl_pct,
        )

    if sell_score >= 2:
        return TradeDecision(
            symbol=snapshot.symbol,
            action="SELL",
            confidence="medium",
            rationale="Sell signal triggered because " + ", ".join(sell_reasons[:4]) + ".",
            score=buy_score - sell_score,
            position_qty=position_qty,
            position_market_value=position_market_value,
            position_unrealized_pl_pct=position_unrealized_pl_pct,
        )

    return TradeDecision(
        symbol=snapshot.symbol,
        action="HOLD",
        confidence="low",
        rationale="Hold signal because the current snapshot does not provide a strong enough edge for a trade.",
        score=buy_score - sell_score,
        position_qty=position_qty,
        position_market_value=position_market_value,
        position_unrealized_pl_pct=position_unrealized_pl_pct,
    )
