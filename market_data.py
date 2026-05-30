import math
from broker import AlpacaBroker


def _moving_average(prices: list[float], window: int) -> float | None:
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / window


def _annualized_volatility(closes: list[float]) -> float | None:
    if len(closes) < 10:
        return None
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    return math.sqrt(variance) * math.sqrt(252)


def _pct_change(closes: list[float], days: int) -> float | None:
    if len(closes) < days + 1:
        return None
    return (closes[-1] - closes[-(days + 1)]) / closes[-(days + 1)]


def format_market_data(broker: AlpacaBroker, symbols: list[str]) -> str:
    bars = broker.get_historical_bars(symbols)
    lines = []
    for symbol in symbols:
        data = bars.get(symbol, [])
        if not data:
            lines.append(f"{symbol}: no data available")
            continue
        closes = [b["close"] for b in data]
        current = closes[-1]
        ma20 = _moving_average(closes, 20)
        ma50 = _moving_average(closes, 50)
        week_chg = _pct_change(closes, 5)
        month_chg = _pct_change(closes, 21)
        vol = _annualized_volatility(closes)

        def fmt(v, pct=False):
            if v is None:
                return "N/A"
            return f"{v * 100:.1f}%" if pct else f"{v:.2f}"

        lines.append(
            f"{symbol}: price=${current:.2f} | MA20={fmt(ma20)} | MA50={fmt(ma50)} "
            f"| 1w={fmt(week_chg, True)} | 1m={fmt(month_chg, True)} | vol={fmt(vol, True)}"
        )
    return "\n".join(lines)


def format_portfolio(broker: AlpacaBroker) -> str:
    acct = broker.get_account_info()
    positions = broker.get_positions()
    lines = [
        f"Portfolio value: ${acct['portfolio_value']:,.2f}",
        f"Cash: ${acct['cash']:,.2f}",
        f"Buying power: ${acct['buying_power']:,.2f}",
        "",
        "Current positions:",
    ]
    if not positions:
        lines.append("  (none)")
    else:
        for p in positions:
            pl_pct = p["unrealized_plpc"] * 100
            lines.append(
                f"  {p['symbol']}: {p['qty']} shares @ ${p['avg_entry_price']:.2f} "
                f"| now ${p['current_price']:.2f} | P&L: ${p['unrealized_pl']:+.2f} ({pl_pct:+.1f}%)"
            )
    return "\n".join(lines)
