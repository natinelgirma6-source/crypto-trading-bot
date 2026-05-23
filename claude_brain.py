import json, anthropic, config
_client = anthropic.Anthropic(api_key=config.ANTHROPIC_KEY)
_SYS = 'You are an expert ICT/SMC trading analyst for crypto. Analyze using ICT concepts: liquidity sweeps, order blocks, fair value gaps, market structure, session context. Respond ONLY with valid JSON: {"probability": <0-100>, "reasoning": "<two sentences max>"}. No extra text.'

def analyze(symbol, direction, fvg, s_high, s_low, last_bars):
    prompt = (symbol + ' ' + direction.upper() + ' ICT setup.\nSession H=' + str(round(s_high,4)) + ' L=' + str(round(s_low,4)) + '\nFVG zone: ' + str(round(fvg.get('bottom',0),4)) + '-' + str(round(fvg.get('top',0),4)) + ' SL=' + str(round(fvg.get('sl',0),4)) + '\nRecent 5-min bars:\n' + last_bars + '\nRate this setup probability and reasoning.')
    try:
        r = _client.messages.create(model='claude-sonnet-4-6', max_tokens=200, system=_SYS, messages=[{'role':'user','content':prompt}])
        d = json.loads(r.content[0].text.strip())
        return int(d.get('probability',60)), str(d.get('reasoning','ICT setup aligned with session structure.'))
    except Exception as e:
        print('[claude] Error:', e)
        return 60, 'ICT setup aligned with session structure.'

def bars_summary(bars):
    tail = bars.tail(5)[['open','high','low','close']]
    return '\n'.join(['  ' + ts.strftime('%H:%M') + ' O=' + str(round(r['open'],4)) + ' H=' + str(round(r['high'],4)) + ' L=' + str(round(r['low'],4)) + ' C=' + str(round(r['close'],4)) for ts, r in tail.iterrows()])
