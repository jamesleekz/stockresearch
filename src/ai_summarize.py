from __future__ import annotations

import json

from openai import OpenAI

from config import Settings
from fetch_data import StockSnapshot
from summarize import StockSummary


def _snapshot_for_prompt(snapshot: StockSnapshot) -> dict[str, object]:
    return {
        "symbol": snapshot.symbol,
        "company": snapshot.company,
        "notes": snapshot.notes,
        "currency": snapshot.currency,
        "sector": snapshot.sector,
        "industry": snapshot.industry,
        "business_summary": snapshot.business_summary,
        "current_price": snapshot.current_price,
        "previous_close": snapshot.previous_close,
        "market_cap": snapshot.market_cap,
        "trailing_pe": snapshot.trailing_pe,
        "forward_pe": snapshot.forward_pe,
        "dividend_yield": snapshot.dividend_yield,
        "analyst_target_price": snapshot.analyst_target_price,
        "fifty_two_week_high": snapshot.fifty_two_week_high,
        "fifty_two_week_low": snapshot.fifty_two_week_low,
        "revenue_growth": snapshot.revenue_growth,
        "earnings_growth": snapshot.earnings_growth,
        "recommendation_key": snapshot.recommendation_key,
        "price_change_1m_pct": snapshot.price_change_1m_pct,
        "price_change_3m_pct": snapshot.price_change_3m_pct,
        "price_change_from_52w_high_pct": snapshot.price_change_from_52w_high_pct,
        "price_change_from_52w_low_pct": snapshot.price_change_from_52w_low_pct,
        "average_volume": snapshot.average_volume,
        "recent_news": snapshot.recent_news,
    }


def summarize_stock_with_ai(snapshot: StockSnapshot, settings: Settings) -> StockSummary:
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        reasoning={"effort": settings.openai_reasoning_effort},
        text={
            "format": {
                "type": "json_schema",
                "name": "stock_summary",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "standout_summary": {"type": "string"},
                        "key_catalyst_or_risk": {"type": "string"},
                        "needs_attention_today": {"type": "string"},
                    },
                    "required": [
                        "standout_summary",
                        "key_catalyst_or_risk",
                        "needs_attention_today",
                    ],
                },
            }
        },
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are an investment research assistant. "
                            "Use only the provided company snapshot. "
                            "Do not invent numbers or facts. "
                            "Keep the tone concise, factual, and balanced. "
                            "If the data is limited, say so. "
                            "The output must be valid JSON matching the schema."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Given the stock data below, produce: "
                            "1. a two-sentence summary of what stands out "
                            "2. one key catalyst or risk to monitor "
                            "3. whether the stock needs investor attention today.\n\n"
                            f"Stock snapshot:\n{json.dumps(_snapshot_for_prompt(snapshot), indent=2)}"
                        ),
                    }
                ],
            },
        ],
    )

    payload = json.loads(response.output_text)
    return StockSummary(
        symbol=snapshot.symbol,
        company=snapshot.company,
        standout_summary=payload["standout_summary"],
        key_catalyst_or_risk=payload["key_catalyst_or_risk"],
        needs_attention_today=payload["needs_attention_today"],
    )
