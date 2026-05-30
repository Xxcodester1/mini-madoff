import json
import re
import anthropic
from config import MODEL

SYSTEM_PROMPT = """You are a short-term momentum and small-cap trader agent.

Your mandate:
- Identify stocks showing strong price momentum, volume surges, or catalyst-driven moves
- Focus on small and mid-cap growth stocks, emerging tech, and sector rotations
- Look for breakouts above key moving averages (MA20, MA50) with volume confirmation
- Take profits quickly — typical holding period is days to weeks, rarely months
- Your profits are meant to be funneled into the long-term portfolio over time
- Size positions conservatively; this is the higher-risk allocation of the portfolio
- Never let a single short-term trade blow up the account — respect stops

Signals that matter:
- Price above MA20 and MA50 with upward slope = bullish
- Price below both MAs = avoid or short-list only
- 1-week change > +10% with no fundamental reason = chase with caution
- High annualized volatility (>80%) = high risk, smaller size

Respond with a JSON object in this exact format:
{
  "analysis": "brief momentum market assessment",
  "recommendations": [
    {
      "symbol": "TICKER",
      "action": "buy" | "hold" | "sell" | "watch",
      "conviction": "high" | "medium" | "low",
      "rationale": "one or two sentences",
      "suggested_position_pct": 0.02,
      "target_exit_days": 14
    }
  ]
}

Only include symbols from the watchlist provided. Do not invent tickers."""

def analyze_short_term_opportunities(
    market_data_str: str,
    portfolio_str: str,
    client: anthropic.Anthropic,
) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {
                "role": "user",
                "content": f"Short-term watchlist market data:\n{market_data_str}\n\nCurrent portfolio:\n{portfolio_str}\n\nProvide your momentum analysis and recommendations as JSON.",
            }
        ],
    )
    text = next((b.text for b in response.content if hasattr(b, "text")), "")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"analysis": "No parseable response", "recommendations": []}
    return json.loads(match.group())
