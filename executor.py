from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import config

_client = TradingClient(config.ALPACA_KEY, config.ALPACA_SECRET, paper=True)

def place_trade(symbol, direction, entry, sl, state):
    try:
        acct = _client.get_account()
        equity = float(acct.equity)
        risk_amt = equity * config.RISK_PER_TRADE
        risk_per_unit = abs(entry - sl)
        if risk_per_unit <= 0:
            return False, 'Invalid SL', None
        qty = round(risk_amt / risk_per_unit, 4)
        qty = max(qty, 0.001)
        side = OrderSide.BUY if direction == 'bullish' else OrderSide.SELL
        req = MarketOrderRequest(symbol=symbol.replace('/', ''), qty=qty, side=side, time_in_force=TimeInForce.GTC)
        order = _client.submit_order(req)
        record = {'order_id': str(order.id), 'symbol': symbol, 'direction': direction, 'entry': entry, 'sl': sl, 'qty': qty, 'equity_before': equity}
        return True, 'Order placed: ' + str(order.id)[:8], record
    except Exception as e:
        return False, str(e), None
