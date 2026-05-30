import json
import anthropic
from config import MODEL, LONG_TERM_WATCHLIST, SHORT_TERM_WATCHLIST
from market_data import format_market_data, format_portfolio
from agents.long_term import analyze_long_term_opportunities
from agents.short_term import analyze_short_term_opportunities
from agents.risk_manager import assess_risk

SYSTEM_PROMPT = """You are the Orchestrator of a multi-agent AI trading system for US equities.

You coordinate three specialist agents and a broker. Your job for each trading session:

1. Gather current portfolio and market data
2. Consult the Long-Term Agent for value/ETF opportunities
3. Consult the Short-Term Agent for momentum plays
4. Combine their recommendations into a proposed trade list
5. Send the proposal to the Risk Manager for approval
6. Execute only the approved/modified trades
7. Produce a session summary

Core philosophy:
- Preserve capital above all else
- Short-term profits are a funnel into long-term positions
- Never trade for the sake of trading — "do nothing" is often the right call
- Always run risk assessment before executing anything

Use the available tools in order. Be methodical. After executing trades, summarize what happened and why."""

# Tool schemas
orchestrator_tools = [
    {
        "name": "get_current_portfolio",
        "description": "Returns the current account balance and all open positions.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_long_term_watchlist_data",
        "description": "Fetches historical price and technical data for all long-term watchlist symbols.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_short_term_watchlist_data",
        "description": "Fetches historical price and technical data for all short-term watchlist symbols.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "consult_long_term_agent",
        "description": "Sends market data and portfolio to the Long-Term Value Investor agent. Returns buy/hold/sell recommendations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "market_data": {"type": "string", "description": "Formatted long-term watchlist market data"},
                "portfolio": {"type": "string", "description": "Formatted portfolio summary"},
            },
            "required": ["market_data", "portfolio"],
        },
    },
    {
        "name": "consult_short_term_agent",
        "description": "Sends market data and portfolio to the Short-Term Momentum agent. Returns buy/hold/sell recommendations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "market_data": {"type": "string", "description": "Formatted short-term watchlist market data"},
                "portfolio": {"type": "string", "description": "Formatted portfolio summary"},
            },
            "required": ["market_data", "portfolio"],
        },
    },
    {
        "name": "assess_trade_risk",
        "description": "Submits proposed trades to the Risk Manager for approval. Returns approved, modified, or rejected trades.",
        "input_schema": {
            "type": "object",
            "properties": {
                "proposed_trades": {
                    "type": "array",
                    "description": "List of proposed trades with symbol, action, qty, and source agent",
                    "items": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string"},
                            "action": {"type": "string", "enum": ["buy", "sell"]},
                            "qty": {"type": "number"},
                            "agent": {"type": "string"},
                        },
                        "required": ["symbol", "action", "qty"],
                    },
                }
            },
            "required": ["proposed_trades"],
        },
    },
    {
        "name": "execute_trade",
        "description": "Executes a single approved trade via the broker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "qty": {"type": "number", "description": "Number of shares"},
            },
            "required": ["symbol", "side", "qty"],
        },
    },
]


def _execute_tool(
    name: str,
    inputs: dict,
    broker,
    client: anthropic.Anthropic,
    dry_run: bool,
    _state: dict,
) -> str:
    if name == "get_current_portfolio":
        result = format_portfolio(broker)
        _state["portfolio_str"] = result
        _state["positions"] = broker.get_positions()
        _state["account"] = broker.get_account_info()
        return result

    elif name == "get_long_term_watchlist_data":
        result = format_market_data(broker, LONG_TERM_WATCHLIST)
        _state["lt_market_data"] = result
        return result

    elif name == "get_short_term_watchlist_data":
        result = format_market_data(broker, SHORT_TERM_WATCHLIST)
        _state["st_market_data"] = result
        return result

    elif name == "consult_long_term_agent":
        result = analyze_long_term_opportunities(
            inputs["market_data"], inputs["portfolio"], client
        )
        return json.dumps(result)

    elif name == "consult_short_term_agent":
        result = analyze_short_term_opportunities(
            inputs["market_data"], inputs["portfolio"], client
        )
        return json.dumps(result)

    elif name == "assess_trade_risk":
        result = assess_risk(
            inputs["proposed_trades"],
            _state.get("positions", []),
            _state.get("account", {}),
            client,
        )
        _state["risk_result"] = result
        return json.dumps(result)

    elif name == "execute_trade":
        symbol = inputs["symbol"]
        side = inputs["side"]
        qty = float(inputs["qty"])
        if qty <= 0:
            return json.dumps({"status": "skipped", "reason": "qty <= 0"})
        if dry_run:
            print(f"  [DRY RUN] Would {side} {qty} shares of {symbol}")
            return json.dumps({"status": "dry_run", "symbol": symbol, "side": side, "qty": qty})
        try:
            result = broker.submit_order(symbol, side, qty)
            print(f"  [ORDER] {side.upper()} {qty} {symbol} -> status: {result['status']}")
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    return json.dumps({"error": f"Unknown tool: {name}"})


def run_orchestrator(broker, client: anthropic.Anthropic, dry_run: bool = False):
    print("=== Trading Session Started ===")
    if dry_run:
        print("  (DRY RUN — no real orders will be placed)")

    _state: dict = {}
    messages = [
        {
            "role": "user",
            "content": (
                "Run today's trading session. "
                "Gather portfolio and market data, consult both agents, "
                "get risk approval, execute approved trades, then summarize the session."
            ),
        }
    ]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=8096,
            thinking={"type": "adaptive"},
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=orchestrator_tools,
            messages=messages,
        )

        # Append assistant message
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract and print the final summary
            summary = next((b.text for b in response.content if hasattr(b, "text")), "")
            print("\n=== Session Summary ===")
            print(summary)
            print("=== Session Complete ===")
            return summary

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [TOOL] {block.name}({list(block.input.keys())})")
                    result_str = _execute_tool(
                        block.name, block.input, broker, client, dry_run, _state
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason
        print(f"Unexpected stop_reason: {response.stop_reason}")
        break
