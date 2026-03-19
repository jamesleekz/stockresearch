from __future__ import annotations

import sys

from ai_summarize import summarize_stock_with_ai
from config import load_settings
from excel_writer import write_excel_report
from fetch_data import fetch_stock_snapshot
from paper_broker import (
    AlpacaPaperBroker,
    already_traded_today,
    append_trade_log,
    pending_row_to_decision,
    queue_pending_order,
    read_pending_orders,
    write_pending_orders,
)
from report_writer import write_combined_report, write_stock_report
from strategy import PositionState, decide_trade
from summarize import summarize_stock
from utils import read_watchlist, write_json


def main() -> int:
    settings = load_settings()
    items = read_watchlist(settings.watchlist_path)
    broker = AlpacaPaperBroker(settings)
    trade_log_path = settings.data_dir / "trade_log.csv"
    pending_orders_path = settings.data_dir / "pending_orders.csv"
    market_is_open: bool | None = None
    if settings.paper_trading_enabled and broker.configured and settings.trade_during_market_hours_only:
        try:
            market_is_open = broker.market_is_open()
            if not market_is_open:
                print("Paper trading is enabled, but the U.S. market is closed. Orders will not be submitted this run.")
        except Exception as exc:
            market_is_open = None
            print(f"Could not determine market hours status: {exc}", file=sys.stderr)

    if settings.paper_trading_enabled and broker.configured and market_is_open:
        remaining_pending_orders: list[dict[str, str]] = []
        for row in read_pending_orders(pending_orders_path):
            queued_decision = pending_row_to_decision(row)
            if already_traded_today(trade_log_path, queued_decision.symbol, queued_decision.action):
                queued_decision.order_status = "skipped_duplicate_today"
                append_trade_log(trade_log_path, queued_decision)
                continue
            try:
                queued_decision = broker.submit_trade(queued_decision)
                print(f"Submitted queued {queued_decision.action} for {queued_decision.symbol}: {queued_decision.order_status}")
            except Exception as exc:
                queued_decision.order_status = "failed"
                print(f"Queued trade failed for {queued_decision.symbol}: {exc}", file=sys.stderr)
                remaining_pending_orders.append(row)
            append_trade_log(trade_log_path, queued_decision)
        write_pending_orders(pending_orders_path, remaining_pending_orders)

    snapshots = []
    summaries = []
    decisions = []
    for item in items:
        print(f"Researching {item.symbol}...")
        try:
            snapshot = fetch_stock_snapshot(item, settings)
            if settings.openai_api_key:
                try:
                    print(f"  Generating AI summary with {settings.openai_model}...")
                    summary = summarize_stock_with_ai(snapshot, settings)
                except Exception as exc:
                    print(f"  AI summary failed, falling back to rule-based summary: {exc}", file=sys.stderr)
                    summary = summarize_stock(snapshot)
            else:
                print("  No OPENAI_API_KEY found, using rule-based summary.")
                summary = summarize_stock(snapshot)
            snapshots.append(snapshot)
            summaries.append(summary)
            position: PositionState | None = None
            if broker.configured:
                try:
                    position = broker.get_open_position(item.symbol)
                except Exception as exc:
                    print(f"  Could not fetch current position: {exc}", file=sys.stderr)
            decision = decide_trade(snapshot, summary, position, settings)

            if settings.paper_trading_enabled and broker.configured and decision.action != "HOLD":
                if settings.trade_during_market_hours_only and market_is_open is False:
                    decision.order_status = "queued_market_closed"
                    queue_pending_order(pending_orders_path, decision)
                    print(f"  Queued {decision.action} for {decision.symbol}: market is closed.")
                elif already_traded_today(trade_log_path, decision.symbol, decision.action):
                    decision.order_status = "skipped_duplicate_today"
                    print(f"  Skipping {decision.action} for {decision.symbol}: already traded today.")
                else:
                    try:
                        decision = broker.submit_trade(decision)
                        print(f"  Paper trade status: {decision.order_status}")
                    except Exception as exc:
                        decision.order_status = "failed"
                        print(f"  Paper trade failed: {exc}", file=sys.stderr)
            elif decision.action != "HOLD":
                if not settings.paper_trading_enabled:
                    decision.order_status = "disabled"
                elif not broker.configured:
                    decision.order_status = "missing_credentials"

            decisions.append(decision)
            append_trade_log(trade_log_path, decision)

            raw_path = settings.data_dir / f"{item.symbol.lower()}.json"
            report_path = settings.reports_dir / f"{item.symbol.lower()}.md"

            write_json(raw_path, snapshot.to_dict())
            write_stock_report(report_path, snapshot, summary, decision)
            print(f"  Saved raw data to {raw_path}")
            print(f"  Saved report to {report_path}")
        except Exception as exc:
            print(f"  Failed to research {item.symbol}: {exc}", file=sys.stderr)

    combined_path = settings.reports_dir / "watchlist_summary.md"
    excel_path = settings.reports_dir / "watchlist.xlsx"
    write_combined_report(combined_path, summaries, decisions)
    write_excel_report(excel_path, snapshots, summaries, decisions)
    print(f"Combined summary saved to {combined_path}")
    print(f"Excel workbook saved to {excel_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
