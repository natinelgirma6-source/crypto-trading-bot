"""
Telegram alert system — Crypto ICT Bot (BTC/USD + ETH/USD).
"""

import requests
import config


def _send(text: str) -> bool:
    url  = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id"   : config.TELEGRAM_CHAT_ID,
        "text"      : text,
        "parse_mode": "HTML",
    }, timeout=10)
    if not resp.ok:
        print(f"[alerts] Telegram error: {resp.text}")
    return resp.ok


def send_warning(
    direction  : str,
    s_high     : float,
    s_low      : float,
    what_next  : str,
    session    : str = "Asian",
    symbol     : str = "BTC/USD",
) -> bool:
    arrow = "🟢 BULLISH" if direction == "bullish" else "🔴 BEARISH"
    msg = (
        f"⚠️ <b>WARNING — SETUP FORMING</b>\n"
        f"{arrow} | <b>{symbol}</b> | 🕐 {session}\n\n"
        f"📊 <b>Signal:</b> Session Sweep + BOS detected\n"
        f"📍 <b>Session High:</b> ${s_high:,.2f}\n"
        f"📍 <b>Session Low:</b>  ${s_low:,.2f}\n\n"
        f"🔍 <b>Still needs:</b>\n{what_next}\n\n"
        f"<i>Not confirmed. Watching for FVG + retest...</i>"
    )
    return _send(msg)


def send_entry(
    direction  : str,
    fvg        : dict,
    trade      : dict,
    state      : dict,
    probability: int,
    reasoning  : str,
    session    : str = "Asian",
    symbol     : str = "BTC/USD",
) -> bool:
    arrow   = "🟢 LONG" if direction == "bullish" else "🔴 SHORT"
    total   = max(state.get("total_trades", 0), 1)
    wins    = state.get("winning_trades", 0)
    wr      = f"{wins}/{state.get('total_trades',0)} ({round(wins/total*100, 1)}%)"
    msg = (
        f"✅ <b>ENTRY — CONFIRMED</b>\n"
        f"{arrow} | <b>{symbol}</b> | 🕐 {session}\n\n"
        f"📊 <b>Signal:</b> Session Sweep + BOS + FVG\n"
        f"📍 <b>Entry Zone:</b> ${fvg['bottom']:,.2f} – ${fvg['top']:,.2f}\n"
        f"🛑 <b>SL:</b> ${trade['sl']:,.2f}\n"
        f"🎯 <b>TP (1:3):</b> ${trade['tp']:,.2f}\n"
        f"⚖️ <b>RR:</b> 1:{trade['rr']:.0f}\n\n"
        f"📈 <b>Daily P&amp;L:</b> ${state.get('daily_pnl', 0.0):.2f}\n"
        f"🏆 <b>Win Rate:</b> {wr}\n"
        f"🧠 <b>Probability:</b> {probability}%\n\n"
        f"💡 <b>Reason:</b> {reasoning}\n\n"
        f"<i>TP is optional — manage the trade manually.</i>"
    )
    return _send(msg)


def send_order_confirm(success: bool, detail: str, direction: str, shares_info: str) -> bool:
    if success:
        arrow = "🟢" if direction == "bullish" else "🔴"
        msg = f"📋 <b>Paper Order Placed</b> {arrow}\n{shares_info}\n<i>Stop loss set on Alpaca paper.</i>"
    else:
        msg = f"⚠️ <b>Paper Order Failed</b>\n{detail}"
    return _send(msg)


def send_daily_summary(stats: dict) -> bool:
    total = max(stats.get("total_trades", 0), 1)
    wins  = stats.get("winning_trades", 0)
    losses = stats.get("total_trades", 0) - wins
    wr    = round(wins / total * 100, 1) if stats.get("total_trades", 0) > 0 else 0
    pnl_emoji = "📈" if stats.get("daily_pnl", 0) >= 0 else "📉"

    msg = (
        f"📊 <b>CRYPTO DAILY SUMMARY</b>\n\n"
        f"{pnl_emoji} <b>Daily P&amp;L:</b> ${stats.get('daily_pnl', 0):+.2f}\n"
        f"💼 <b>Overall P&amp;L:</b> ${stats.get('overall_pnl', 0):+.2f}\n\n"
        f"📋 <b>Trades today:</b> {stats.get('trades_today', 0)}\n"
        f"🏆 <b>Win Rate:</b> {wins}W / {losses}L ({wr}%)\n\n"
        f"<i>See Alpaca paper account for full trade history.</i>"
    )
    return _send(msg)


def send_status(text: str) -> bool:
    return _send(f"ℹ️ {text}")
