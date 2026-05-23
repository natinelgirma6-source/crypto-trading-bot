from datetime import datetime, time as dtime
import pytz
import config, data, signals, risk, alerts, claude_brain, executor

ET = pytz.timezone('America/New_York')

def get_session():
    now = datetime.now(ET).time()
    # Handle Asian session crossing midnight
    if now >= dtime(20,0) or now <= dtime(0,0):
        return 'Asian', dtime(20,0)
    for name, (start, end) in config.SESSIONS.items():
        if name != 'Asian' and start <= now <= end:
            return name, start
    return None, None

def _reset(state):
    state.update({'signal_stage': None, 'signal_direction': None, 'pending_fvg': None, 'warning_sent': False})

def check_symbol(symbol, session, session_start, state):
    bars = data.get_bars(symbol, limit=100)
    if bars is None or len(bars) < 10:
        print('[' + symbol + '] Not enough data')
        return
    price = float(bars.iloc[-1]['close'])
    s_high, s_low = signals.session_hl(bars, session_start)
    if s_high is None:
        return
    tradeable, block_reason = risk.can_trade(state)
    stage = state.get('signal_stage')
    direction = state.get('signal_direction')
    now_str = datetime.now(ET).strftime('%H:%M ET')
    print('[' + now_str + '] [' + session + '] ' + symbol + ' price=' + str(round(price,2)) + ' stage=' + str(stage))
    if stage is None:
        sweep = signals.detect_sweep(bars, s_high, s_low)
        if sweep:
            state['signal_stage'] = 'sweep'; state['signal_direction'] = sweep; state['warning_sent'] = False
    elif stage == 'sweep':
        ok, _ = signals.detect_bos(bars, direction)
        if ok:
            state['signal_stage'] = 'bos'
            if not state.get('warning_sent'):
                sent = alerts.send_warning(symbol, direction, s_high, s_low, session)
                state['warning_sent'] = sent
    elif stage == 'bos':
        fvg = signals.find_fvg(bars, direction)
        if fvg:
            state['signal_stage'] = 'fvg_formed'; state['pending_fvg'] = fvg
    elif stage == 'fvg_formed':
        fvg = state.get('pending_fvg')
        if not fvg:
            _reset(state)
        elif signals.price_in_fvg(price, fvg):
            if not tradeable:
                alerts.send_status('Blocked: ' + block_reason); _reset(state)
            else:
                trade = signals.calc_trade(price, fvg)
                if not trade or trade.get('rr',0) < config.MIN_RR:
                    _reset(state)
                else:
                    prob, reason = claude_brain.analyze(symbol, direction, fvg, s_high, s_low, claude_brain.bars_summary(bars))
                    alerts.send_entry(symbol, direction, fvg, trade, prob, reason, session)
                    ok, detail, rec = executor.place_trade(symbol, direction, price, trade['sl'], state)
                    alerts.send_order_confirm(ok, detail)
                    if ok and rec:
                        state.setdefault('pending_trades',[]).append(rec)
                    state['trades_today'] += 1; _reset(state)
    risk.save(state)

def check():
    session, session_start = get_session()
    now_str = datetime.now(ET).strftime('%H:%M ET')
    if session is None:
        print('[' + now_str + '] Outside crypto sessions.')
        return
    state = risk.load()
    if state.get('current_session') != session:
        _reset(state); state['current_session'] = session
        risk.save(state)
    for symbol in config.SYMBOLS:
        check_symbol(symbol, session, session_start, state)
        state = risk.load()
    now = datetime.now(ET)
    if now.hour == 11 and 58 <= now.minute <= 59:
        alerts.send_daily_summary(state)

if __name__ == '__main__':
    now_str = datetime.now(ET).strftime('%Y-%m-%d %H:%M ET')
    print('CRYPTO Bot | GitHub Actions | ICT BTC+ETH | ' + now_str)
    check()
    print('Done.')
