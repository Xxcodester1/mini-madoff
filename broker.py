import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, HISTORICAL_DAYS


class AlpacaBroker:
    def __init__(self, paper: bool = True):
        self.trading = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=paper)
        self.data = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

    def get_account_info(self) -> dict:
        acct = self.trading.get_account()
        return {
            "cash": float(acct.cash),
            "portfolio_value": float(acct.portfolio_value),
            "buying_power": float(acct.buying_power),
            "day_trade_count": acct.daytrade_count,
            "pattern_day_trader": acct.pattern_day_trader,
        }

    def get_positions(self) -> list[dict]:
        positions = self.trading.get_all_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc),
                "side": p.side.value,
            }
            for p in positions
        ]

    def get_historical_bars(self, symbols: list[str], days: int = HISTORICAL_DAYS) -> dict:
        start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame.Day,
            start=start,
            feed="iex",
        )
        bars = self.data.get_stock_bars(request)
        result = {}
        for symbol in symbols:
            try:
                df = bars.df.loc[symbol].copy()
                result[symbol] = df[["open", "high", "low", "close", "volume"]].to_dict("records")
            except KeyError:
                result[symbol] = []
        return result

    def submit_order(self, symbol: str, side: str, qty: float) -> dict:
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        order = self.trading.submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,
            )
        )
        return {
            "id": str(order.id),
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side.value,
            "status": order.status.value,
        }

    def cancel_all_orders(self):
        self.trading.cancel_orders()
