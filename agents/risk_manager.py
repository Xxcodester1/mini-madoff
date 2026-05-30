import json
import re
import anthropic
from config import MODEL, MAX_POSITION_SIZE, MAX_NEW_TRADE_SIZE, STOP_LOSS_PCT, MAX_SHORT_TERM_ALLOCATION

SYSTEM_PROMPT = f"""You are the Risk Manager for a multi-agent trading system. Your job is to review proposed trades and enforce hard risk limits before any order reaches the market.

Hard rules you MUST enforce:
1. No single position may exceed {MAX_POSITION_SIZE * 100:.0f}% of total portfolio value
2. No single new trade entry may deploy more than {MAX_NEW_TRADE_SIZE * 100:.0f}% of portfolio value
3. A 5% stop loss ({STOP_LOSS_PCT * 100:.0f}%) is implied on every position — flag positions already down more than 8%
4. The short-term agent's total allocation must not exceed {MAX_SHORT_TERM_ALLOCATION * 100:.0f}% of portfolio
5. Never buy a stock that is already at or above its max position size
6. Reject any trade that would bring total invested capital above 95% of portfolio value (keep 5% cash buffer)

For each proposed trade, output one of:
- "approved" — trade meets all risk criteria
- "modified" — approved but with a reduced quantity, explain the reduction
- "rejected" — violates a hard rule, explain why

Respond with a JSON object in this exact format:
{{
  "overall_assessment": "brief risk summary",
  "reviewed_trades": [
    {{
      "symbol": "TICKER",
      "original_action": "buy" | "sell",
      "original_qty": 10,
      "decision": "approved" | "modified" | "rejected",
      "approved_qty": 10,
      "reason": "brief explanation"
    }}
  ]
}}"""


def assess_risk(
    proposed_trades: list[dict],
    portfolio: list[dict],
    account: dict,
    client: anthropic.Anthropic,
) -> dict:
    trades_str = json.dumps(proposed_trades, indent=2)
    portfolio_str = json.dumps(portfolio, indent=2)
    account_str = json.dumps(account, indent=2)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Account:\n{account_str}\n\n"
                    f"Current positions:\n{portfolio_str}\n\n"
                    f"Proposed trades:\n{trades_str}\n\n"
                    "Review each trade against the risk rules and respond with JSON."
                ),
            }
        ],
    )
    text = next((b.text for b in response.content if hasattr(b, "text")), "")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"overall_assessment": "Risk assessment failed", "reviewed_trades": []}
    return json.loads(match.group())
