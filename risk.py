import json, os
from datetime import date

STATE_FILE = 'state.json'
DEFAULT = {'date': str(date.today()), 'trades_today': 0, 'daily_pnl': 0.0, 'overall_pnl': 0.0, 'signal_stage': None, 'signal_direction': None, 'pending_fvg': None, 'warning_sent': False, 'current_session': None, 'pending_trades': [], 'total_trades': 0, 'winning_trades': 0}

def load():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
        if state.get('date') != str(date.today()):
            state.update({k: DEFAULT[k] for k in ['date','trades_today','daily_pnl','signal_stage','signal_direction','pending_fvg','warning_sent','current_session','pending_trades']})
            state['date'] = str(date.today())
        return state
    return dict(DEFAULT)

def save(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def can_trade(state):
    import config
    if state['trades_today'] >= config.MAX_TRADES_PER_DAY:
        return False, 'Max trades reached'
    if state['daily_pnl'] <= -(config.DAILY_LOSS_LIMIT - config.DAILY_LOSS_BUFFER):
        return False, 'Near daily loss limit'
    return True, 'ok'
