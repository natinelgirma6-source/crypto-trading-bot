import pytz
from datetime import datetime

ET = pytz.timezone('America/New_York')

def session_hl(bars, session_start):
    now = datetime.now(ET)
    today = now.date()
    import pytz
    sess_dt = ET.localize(datetime.combine(today, session_start))
    sess_bars = bars[bars.index >= sess_dt]
    if sess_bars.empty:
        return None, None
    return float(sess_bars['high'].max()), float(sess_bars['low'].min())

def detect_sweep(bars, s_high, s_low, lookback=5):
    if s_high is None or len(bars) < lookback+1:
        return None
    recent = bars.tail(lookback)
    if recent['high'].max() > s_high and bars.iloc[-1]['close'] < s_high:
        return 'bearish'
    if recent['low'].min() < s_low and bars.iloc[-1]['close'] > s_low:
        return 'bullish'
    return None

def detect_bos(bars, direction, lookback=8):
    if direction is None or len(bars) < lookback+1:
        return False, None
    recent = bars.tail(lookback)
    if direction == 'bullish':
        sh = recent['high'].max()
        if bars.iloc[-1]['close'] > sh:
            return True, sh
    else:
        sl = recent['low'].min()
        if bars.iloc[-1]['close'] < sl:
            return True, sl
    return False, None

def find_fvg(bars, direction, lookback=15):
    if direction is None or len(bars) < 3:
        return None
    recent = bars.tail(lookback)
    for i in range(len(recent)-2, 1, -1):
        c1 = recent.iloc[i-2]
        c3 = recent.iloc[i]
        if direction == 'bullish' and c1['high'] < c3['low']:
            top, bottom = c3['low'], c1['high']
            mid = (top+bottom)/2
            return {'top': top, 'bottom': bottom, 'mid': mid, 'sl': bottom-(top-bottom)*0.5, 'direction': direction}
        if direction == 'bearish' and c1['low'] > c3['high']:
            top, bottom = c1['low'], c3['high']
            mid = (top+bottom)/2
            return {'top': top, 'bottom': bottom, 'mid': mid, 'sl': top+(top-bottom)*0.5, 'direction': direction}
    return None

def price_in_fvg(price, fvg):
    return fvg and fvg['bottom'] <= price <= fvg['top']

def calc_trade(entry, fvg):
    if not fvg:
        return None
    sl = fvg['sl']
    risk = abs(entry - sl)
    if risk == 0:
        return None
    direction = fvg.get('direction', 'bullish')
    tp = entry + risk*3 if direction == 'bullish' else entry - risk*3
    return {'entry': entry, 'sl': sl, 'tp': tp, 'risk': risk, 'rr': abs(tp-entry)/risk}
