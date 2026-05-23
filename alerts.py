import requests, config
API = 'https://api.telegram.org/bot' + config.TELEGRAM_TOKEN

def _send(text):
    try:
        r = requests.post(API + '/sendMessage', json={'chat_id': config.TELEGRAM_CHAT_ID, 'text': text}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print('[alerts]', e); return False

def send_warning(symbol, direction, s_high, s_low, session):
    arrow = 'BULLISH' if direction == 'bullish' else 'BEARISH'
    return _send('CRYPTO WARNING - ' + symbol + ' ' + arrow + '\nSession: ' + session + '\nH: ' + str(round(s_high,2)) + '  L: ' + str(round(s_low,2)) + '\nWatching for FVG entry...')

def send_entry(symbol, direction, fvg, trade, prob, reason, session):
    side = 'LONG' if direction == 'bullish' else 'SHORT'
    return _send('CRYPTO ENTRY - ' + symbol + ' ' + side + '\nSession: ' + session + '\nAI: ' + str(prob) + '% - ' + reason + '\nEntry: ' + str(round(trade['entry'],2)) + '  SL: ' + str(round(trade['sl'],2)) + '  TP: ' + str(round(trade['tp'],2)) + '\nRR: 1:' + str(round(trade['rr'],1)))

def send_order_confirm(ok, detail):
    return _send('CRYPTO ORDER ' + ('PLACED' if ok else 'FAILED') + '\n' + str(detail))

def send_status(msg):
    return _send('CRYPTO BOT\n' + msg)

def send_daily_summary(state):
    tt = max(state.get('total_trades',1),1)
    wr = round(state.get('winning_trades',0)/tt*100)
    return _send('CRYPTO DAILY SUMMARY\nDaily PnL: $' + str(state.get('daily_pnl',0)) + '\nTrades: ' + str(state.get('trades_today',0)) + '\nWin rate: ' + str(wr) + '%')
