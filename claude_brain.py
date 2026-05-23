import json, anthropic, config
_client = anthropic.Anthropic(api_key=config.ANTHROPIC_KEY)
_SYS = 'You are a concise ICT crypto analyst. Respond ONLY with valid JSON: {"probability": <0-100>, "reasoning": "<one sentence>"}. No extra text.'

def analyze(symbol, direction, fvg, s_high, s_low, last_bars):
    prompt = symbol + ' ' + direction.upper() + ' ICT setup. H=' + str(round(s_high,2)) + ' L=' + str(round(s_low,2)) + '. FVG=' + str(round(fvg.get('bottom',0),2)) + '-' + str(round(fvg.get('top',0),2)) + '. Bars:\n' + last_bars
    try:
        r = _client.messages.create(model='claude-haiku-4-5-20251001', max_tokens=120, system=_SYS, messages=[{'role':'user','content':prompt}])
        d = json.loads(r.content[0].text.strip())
        return int(d.get('probability',60)), str(d.get('reasoning','ICT setup aligned.'))
    except:
        return 60, 'ICT structure aligned with session.'

def bars_summary(bars):
    tail = bars.tail(5)[['open','high','low','close']]
    return '\n'.join(['  ' + str(ts.strftime('%H:%M')) + ' O=' + str(round(r['open'],2)) + ' C=' + str(round(r['close'],2)) for ts, r in tail.iterrows()])
