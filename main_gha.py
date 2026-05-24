"""
GitHub Actions entry point — Crypto ICT Trading Bot.
Runs every 5 minutes via GHA cron. Single-run, then exits.
State persisted via actions/cache (state.json).
Covers: Asian (8pm-midnight ET) | London (3am-8am ET) | NewYork (8am-noon ET)
Symbols: BTC/USD, ETH/USD
"""

import sys
from datetime import datetime, time as dtime, date
import pytz

import config
import data
import signals
import risk
import alerts
import claude_brain
import executor

ET = pytz.timezone("America/New_York")


def get_session():
    """Return (session_name, session_start) or (None, None) if outside sessions."""
    now = datetime.now(ET).time()
    # Asian session crosses midnight: 8pm to 11:59pm
    if now >= dtime(20, 0):
        return "Asian", dtime(20, 0)
    # Other sessions
    for name, (start, end) in config.SESSIONS.items():
        if name != "Asian" and start <= now <= end:
            return name, start
    return None, None


def _reset_signal(state):
    state["signal_stage"]     = None
    state["signal_direction"] = None
    state["pending_fvg"]      = None
    state["warning_sent"]     = False


def _invalidated(bars, direction, s_high, s_low):
    price  = float(bars.iloc[-1]["close"])
    spread = s_high - s_low
    if direction == "bullish" and price < s_low - spread * 0.5:
        return True
    if direction == "bearish" and price > s_high + spread * 0.5:
        return True
    return False


def check_symbol(symbol: str, session: str, session_start: dtime, state: dict):
    """Run the full ICT signal pipeline for one symbol."""
    now_str = datetime.now(ET).strftime("%H:%M ET")
    sym_key = symbol.replace("/", "")  # BTC/USD → BTCUSD for state keys

    bars = data.get_bars(symbol=symbol, limit=100)
    if bars is None or len(bars) < 10:
        print(f"[{sym_key}] Not enough data ({len(bars) if bars is not None else 0} bars)")
        return

    price         = float(bars.iloc[-1]["close"])
    s_high, s_low = signals.session_hl(bars, session_start)
    if s_high is None:
        print(f"[{sym_key}] Could not determine session H/L")
        return

    tradeable, block_reason = risk.can_trade(state)
    stage     = state.get(f"{sym_key}_stage")
    direction = state.get(f"{sym_key}_direction")

    print(f"[{now_str}] [{session}] {symbol}  price=${price:,.2f}  "
          f"H=${s_high:,.2f}  L=${s_low:,.2f}  stage={stage}")

    # Invalidation
    if stage and direction and _invalidated(bars, direction, s_high, s_low):
        print(f"[{sym_key}] Setup invalidated — resetting.")
        state[f"{sym_key}_stage"]     = None
        state[f"{sym_key}_direction"] = None
        state[f"{sym_key}_fvg"]       = None
        state[f"{sym_key}_warned"]    = False
        stage = None

    # STAGE 0 — looking for sweep
    if stage is None:
        sweep_dir = signals.detect_sweep(bars, s_high, s_low)
        if sweep_dir:
            print(f"[{sym_key}] Sweep detected: {sweep_dir}")
            state[f"{sym_key}_stage"]     = "sweep"
            state[f"{sym_key}_direction"] = sweep_dir
            state[f"{sym_key}_warned"]    = False

    # STAGE 1 — sweep found, looking for BOS
    elif stage == "sweep":
        bos_ok, bos_level = signals.detect_bos(bars, direction)
        if bos_ok:
            print(f"[{sym_key}] BOS confirmed: {direction}  level=${bos_level:,.2f}")
            state[f"{sym_key}_stage"] = "bos"
            if not state.get(f"{sym_key}_warned"):
                what = (
                    f"• FVG to form in {direction} direction\n"
                    f"• Price to pull back into FVG zone\n"
                    f"• RR must be >= 1:3"
                )
                sent = alerts.send_warning(direction, s_high, s_low, what, session, symbol=symbol)
                state[f"{sym_key}_warned"] = sent

    # STAGE 2 — BOS confirmed, looking for FVG
    elif stage == "bos":
        fvg = signals.find_fvg(bars, direction)
        if fvg:
            print(f"[{sym_key}] FVG found: {fvg}")
            state[f"{sym_key}_stage"] = "fvg_formed"
            state[f"{sym_key}_fvg"]   = fvg

    # STAGE 3 — FVG formed, waiting for price to enter
    elif stage == "fvg_formed":
        fvg = state.get(f"{sym_key}_fvg")
        if not fvg:
            state[f"{sym_key}_stage"] = None
        elif signals.price_in_fvg(price, fvg):
            print(f"[{sym_key}] Price entered FVG at ${price:,.2f}")

            if not tradeable:
                print(f"[{sym_key}] Trade blocked: {block_reason}")
                alerts.send_status(f"⛔ {symbol} setup valid but blocked: {block_reason}")
                state[f"{sym_key}_stage"] = None
            else:
                trade = signals.calc_trade(price, fvg)
                if not trade or trade.get("rr", 0) < config.MIN_RR:
                    print(f"[{sym_key}] RR too low — skipping.")
                    state[f"{sym_key}_stage"] = None
                else:
                    summary      = claude_brain.bars_summary(bars)
                    prob, reason = claude_brain.analyze(
                        symbol, direction, fvg, s_high, s_low, summary
                    )
                    sent = alerts.send_entry(
                        direction, fvg, trade, state, prob, reason, session, symbol=symbol
                    )
                    print(f"[{sym_key}] ENTRY sent: {sent}  prob={prob}%")

                    ok, detail, trade_record = executor.place_trade(
                        symbol, direction, price, trade["sl"], state
                    )
                    alerts.send_order_confirm(ok, detail, direction, detail)
                    print(f"[{sym_key}] Paper order: {ok} — {detail}")

                    if ok and trade_record:
                        pending = state.get("pending_trades", [])
                        pending.append(trade_record)
                        state["pending_trades"] = pending

                    state["trades_today"] = state.get("trades_today", 0) + 1
                    state[f"{sym_key}_stage"] = None


def check():
    session, session_start = get_session()
    now     = datetime.now(ET)
    now_str = now.strftime("%H:%M ET")
    today   = now.strftime("%Y-%m-%d")

    if session is None:
        print(f"[{now_str}] Outside trading sessions — nothing to do.")
        return

    state = risk.load()

    # ── Session-open notification ─────────────────────────────────────────────
    # Key: "session_notified_<SessionName>_<date>" — fires once per session per day
    notif_key = f"session_notified_{session}_{today}"
    if not state.get(notif_key):
        msg = (
            f"🚀 CRYPTO BOT — {session} Session Open\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Scanning: BTC/USD + ETH/USD\n"
            f"🕐 Time: {now_str}\n"
            f"💰 Daily PnL: ${state.get('daily_pnl', 0.0):.2f}\n"
            f"📊 Trades today: {state.get('trades_today', 0)}"
        )
        alerts.send_status(msg)
        state[notif_key] = True
        risk.save(state)
        print(f"[{now_str}] Session-open notification sent for {session}")

    # ── Session change: reset per-symbol signal states ────────────────────────
    if state.get("current_session") != session:
        print(f"[{now_str}] New session: {session} — resetting signal states.")
        for sym in config.SYMBOLS:
            sym_key = sym.replace("/", "")
            state[f"{sym_key}_stage"]     = None
            state[f"{sym_key}_direction"] = None
            state[f"{sym_key}_fvg"]       = None
            state[f"{sym_key}_warned"]    = False
        state["current_session"] = session
        risk.save(state)

    # ── Daily reset at midnight ───────────────────────────────────────────────
    if state.get("last_reset_date") != today:
        state["trades_today"]     = 0
        state["daily_pnl"]        = 0.0
        state["last_reset_date"]  = today
        risk.save(state)

    # ── Scan each symbol ─────────────────────────────────────────────────────
    for symbol in config.SYMBOLS:
        check_symbol(symbol, session, session_start, state)

    risk.save(state)


if __name__ == "__main__":
    now_str = datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")
    print("=" * 55)
    print("  CRYPTO Bot | GitHub Actions | ICT BTC+ETH")
    print(f"  {now_str}")
    print("=" * 55)
    check()
    print("Done.")
