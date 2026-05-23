import os as _os
from datetime import time as _t

TELEGRAM_TOKEN   = _os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = _os.environ.get('TELEGRAM_CHAT_ID', '')
ALPACA_KEY       = _os.environ.get('ALPACA_KEY', '')
ALPACA_SECRET    = _os.environ.get('ALPACA_SECRET', '')
ANTHROPIC_KEY    = _os.environ.get('ANTHROPIC_KEY', '')

SYMBOLS          = ['BTC/USD', 'ETH/USD']
PRIMARY          = 'BTC/USD'
ACCOUNT_SIZE     = 5000.0
RISK_PER_TRADE   = 0.01
MIN_RR           = 3.0
MAX_TRADES_PER_DAY = 6
DAILY_LOSS_LIMIT = 200.0
DAILY_LOSS_BUFFER = 50.0

SESSIONS = {
    'Asian'   : (_t(20, 0), _t(23, 59)),
    'London'  : (_t(3,  0), _t(7,  59)),
    'NewYork' : (_t(8,  0), _t(11, 59)),
}
