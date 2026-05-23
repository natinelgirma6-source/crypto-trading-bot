from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import config

_client = CryptoHistoricalDataClient()

def get_bars(symbol=None, limit=100):
    symbol = symbol or config.PRIMARY
    req = CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame(5, TimeFrameUnit.Minute), limit=limit)
    try:
        bars = _client.get_crypto_bars(req).df
    except Exception as e:
        print('[data] Error:', e)
        return None
    if bars is None or bars.empty:
        return None
    if hasattr(bars.index, 'levels'):
        try:
            bars = bars.xs(symbol, level=0)
        except:
            bars = bars.reset_index(level=0, drop=True)
    bars.columns = [c.lower() for c in bars.columns]
    return bars.sort_index().tail(limit)

def current_price(symbol=None):
    bars = get_bars(symbol, limit=2)
    return float(bars.iloc[-1]['close']) if bars is not None and len(bars) > 0 else None
