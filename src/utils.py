from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WatchlistItem:
    symbol: str
    company: str
    notes: str


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_slug(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.strftime("%Y%m%d_%H%M%S")


def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_").lower()


def read_watchlist(path: Path) -> list[WatchlistItem]:
    if not path.exists():
        raise FileNotFoundError(f"Watchlist not found: {path}")

    items: list[WatchlistItem] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        normalized_fieldnames = [name.strip().lower() for name in (reader.fieldnames or [])]
        if "symbol" not in normalized_fieldnames:
            raise ValueError("watchlist.csv must include a 'symbol' column")

        for row in reader:
            normalized_row = {(key or "").strip().lower(): (value or "") for key, value in row.items()}
            symbol = normalized_row.get("symbol", "").strip().upper()
            if not symbol:
                continue
            items.append(
                WatchlistItem(
                    symbol=symbol,
                    company=normalized_row.get("company", "").strip(),
                    notes=normalized_row.get("notes", "").strip(),
                )
            )

    if not items:
        raise ValueError("watchlist.csv does not contain any stock symbols")

    return items


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def format_money(value: float | None) -> str:
    if value is None:
        return "N/A"

    magnitude = abs(value)
    if magnitude >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if magnitude >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if magnitude >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.2f}"


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
