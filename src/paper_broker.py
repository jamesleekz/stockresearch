from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from config import Settings
from strategy import PositionState, TradeDecision
from utils import ensure_directory


class AlpacaPaperTradingError(RuntimeError):
    pass


class AlpacaPaperBroker:
    def __init__(self, settings: Settings) -> None:
        self.base_url = "https://paper-api.alpaca.markets"
        self.api_key = settings.alpaca_paper_api_key
        self.api_secret = settings.alpaca_paper_api_secret
        self.notional_usd = settings.paper_trade_notional_usd

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key or "",
            "APCA-API-SECRET-KEY": self.api_secret or "",
            "Content-Type": "application/json",
        }

    def get_open_position(self, symbol: str) -> PositionState | None:
        response = requests.get(
            f"{self.base_url}/v2/positions/{symbol}",
            headers=self.headers,
            timeout=20,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        return PositionState(
            symbol=payload["symbol"],
            qty=float(payload["qty"]),
            market_value=float(payload.get("market_value") or 0.0),
            avg_entry_price=float(payload["avg_entry_price"]) if payload.get("avg_entry_price") else None,
            unrealized_plpc=float(payload["unrealized_plpc"]) if payload.get("unrealized_plpc") else None,
        )

    def market_is_open(self) -> bool:
        response = requests.get(
            f"{self.base_url}/v2/clock",
            headers=self.headers,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return bool(payload.get("is_open"))

    def submit_trade(self, decision: TradeDecision) -> TradeDecision:
        if decision.action == "HOLD":
            decision.order_status = "not_submitted"
            return decision

        if decision.action == "BUY":
            payload: dict[str, Any] = {
                "symbol": decision.symbol,
                "notional": str(self.notional_usd),
                "side": "buy",
                "type": "market",
                "time_in_force": "day",
            }
            decision.executed_side = "buy"
            decision.executed_notional_usd = self.notional_usd
        else:
            position = self.get_open_position(decision.symbol)
            if not position or position.qty <= 0:
                decision.order_status = "skipped_no_position"
                return decision
            payload = {
                "symbol": decision.symbol,
                "qty": str(position.qty),
                "side": "sell",
                "type": "market",
                "time_in_force": "day",
            }
            decision.executed_side = "sell"
            decision.executed_qty = position.qty

        response = requests.post(
            f"{self.base_url}/v2/orders",
            headers=self.headers,
            json=payload,
            timeout=20,
        )
        if response.status_code >= 400:
            raise AlpacaPaperTradingError(response.text)

        order_payload = response.json()
        decision.order_status = order_payload.get("status", "submitted")
        decision.order_id = order_payload.get("id")
        return decision


TRADE_LOG_HEADERS = [
    "timestamp",
    "symbol",
    "action",
    "confidence",
    "rationale",
    "order_status",
    "order_id",
    "executed_side",
    "executed_notional_usd",
    "executed_qty",
]

PENDING_ORDER_HEADERS = [
    "queued_at",
    "symbol",
    "action",
    "confidence",
    "rationale",
    "position_qty",
    "position_market_value",
    "position_unrealized_pl_pct",
]


def read_trade_log(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def already_traded_today(path: Path, symbol: str, action: str) -> bool:
    today = datetime.now().date().isoformat()
    for row in read_trade_log(path):
        if row.get("timestamp", "").startswith(today) and row.get("symbol") == symbol and row.get("action") == action:
            if row.get("order_status") not in {"failed", "not_submitted"}:
                return True
    return False


def append_trade_log(path: Path, decision: TradeDecision) -> None:
    ensure_directory(path.parent)
    file_exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADE_LOG_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(),
                "symbol": decision.symbol,
                "action": decision.action,
                "confidence": decision.confidence,
                "rationale": decision.rationale,
                "order_status": decision.order_status,
                "order_id": decision.order_id or "",
                "executed_side": decision.executed_side or "",
                "executed_notional_usd": decision.executed_notional_usd or "",
                "executed_qty": decision.executed_qty or "",
            }
        )


def read_pending_orders(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_pending_orders(path: Path, rows: list[dict[str, str]]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PENDING_ORDER_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def queue_pending_order(path: Path, decision: TradeDecision) -> None:
    existing_rows = read_pending_orders(path)
    for row in existing_rows:
        if row.get("symbol") == decision.symbol and row.get("action") == decision.action:
            return

    existing_rows.append(
        {
            "queued_at": datetime.now().isoformat(),
            "symbol": decision.symbol,
            "action": decision.action,
            "confidence": decision.confidence,
            "rationale": decision.rationale,
            "position_qty": str(decision.position_qty or ""),
            "position_market_value": str(decision.position_market_value or ""),
            "position_unrealized_pl_pct": str(decision.position_unrealized_pl_pct or ""),
        }
    )
    write_pending_orders(path, existing_rows)


def pending_row_to_decision(row: dict[str, str]) -> TradeDecision:
    return TradeDecision(
        symbol=row["symbol"],
        action=row["action"],
        confidence=row.get("confidence") or "low",
        rationale=row.get("rationale") or "Queued order submitted after market reopened.",
        position_qty=float(row["position_qty"]) if row.get("position_qty") else None,
        position_market_value=float(row["position_market_value"]) if row.get("position_market_value") else None,
        position_unrealized_pl_pct=float(row["position_unrealized_pl_pct"]) if row.get("position_unrealized_pl_pct") else None,
    )
