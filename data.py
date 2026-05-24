"""
Crypto market data — BTC/USD + ETH/USD via Alpaca CryptoHistoricalDataClient.
No API keys required for crypto data.
"""

from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from datetime import datetime, timedelta
import pytz
import pandas as pd

ET = pytz.timezone("America/New_York")

# No auth needed for crypto data
_client = CryptoHistoricalDataClient()


def get_bars(symbol: str = "BTC/USD", limit: int = 100) -> pd.DataFrame | None:
    """
    Fetch up to `limit` 5-minute bars for a crypto symbol.
    Crypto trades 24/7 so we look back 48h to guarantee data.
    Returns a DataFrame with columns [open, high, low, close, volume].
    """
    now   = datetime.now(ET)
    start = now - timedelta(hours=48)

    try:
        req = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame(5, TimeFrameUnit.Minute),
            start=start,
        )
        raw = _client.get_crypto_bars(req)
        df  = raw.df

        if df is None or df.empty:
            print(f"[data] No bars returned for {symbol}")
            return None

        # Handle MultiIndex (symbol, timestamp) --- flatten to just timestamp
        if isinstance(df.index, pd.MultiIndex):
            # Try both slash and no-slash versions
            for sym_key in [symbol, symbol.replace("/", "")]:
                try:
                    df = df.xs(sym_key, level=0)
                    break
                except KeyError:
                    continue
            else:
                # Fallback: just drop the symbol level
                df = df.reset_index(level=0, drop=True)

        # Normalize column names
        df.columns = [c.lower() for c in df.columns]

        # Convert index to ET timezone
        if df.index.tzinfo is None:
            df.index = pd.DatetimeIndex(df.index).tz_localize("UTC").tz_convert(ET)
        else:
            df.index = pd.DatetimeIndex(df.index).tz_convert(ET)

        df = df.sort_index()
        result = df.tail(limit)
        print(f"[data] {symbol}: {len(result)} bars fetched, latest {result.index[-1].strftime('%H:%M ET') if len(result) > 0 else 'none'}")
        return result

    except Exception as e:
        print(f"[data] Error fetching {symbol}: {e}")
        return None


def current_price(symbol: str = "BTC/USD") -> float | None:
    bars = get_bars(symbol, limit=1)
    if bars is not None and not bars.empty:
        return float(bars.iloc[-1]["close"])
    return None
