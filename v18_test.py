import json, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
SHOTS = not (len(sys.argv) > 2 and sys.argv[2] == 'noshots')
SEED = open('/workspace/seed_real_shape.json', encoding='utf-8').read()
AB = "כפיפת בטן במכשיר"; PR = "כפיפה בפריצ'ר"
fails = []; errs = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m, flush=True)
    if not c: fails.append(m)
strip = lambda x: (x or '').replace('\u2066', '').replace('\u2069', '')
def OLD(w, r, day='2026-10-05'):
    return {'date': day + 'T07:00:00Z', 'type': 'normal', 'sets': [{'weight': 115, 'reps': 8}, None, {'weight': w, 'reps': r}, {'weight': w, 'reps': 4}]}
def NEW(w, reps, day='2026-10-08', deload=False):
    e = {'date': day + 'T07:00:00Z', 'type': 'simple', 'sets': [{'weight': w, 'reps': r} for r in reps]}
    if deload: e['deload'] = True
    return e
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True)
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, timezone_id='Asia/Jerusalem', service_workers='block')
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    ev = pg.evaluate
    pg.goto(BASE, wait_until='load')
    ev("s => { localStorage.clear(); localStorage.setItem('workoutData_v1', s); localStorage.setItem('workoutActiveProfile_v1', 'main'); localStorage.setItem('abTempoStage_v1', '{\"stage\":1}'); }", SEED); pg.reload(wait_until='load')
    ok('workout-pwa-v18' in pg.request.get(BASE + 'sw.js').text(), 'SW cache v18')
    ok(ev("localStorage.getItem('abTempoStage_v1')") is None, 'old v16 tempo-stage key cleaned up')
    ok(all(ev(f"typeof window['{n}'] === 'undefined'") for n in ['readAbStage', 'startRestCountdown', 'changeAbStage', 'maybeAdvanceAbStage', 'AB_TEMPO_STAGES']), 'tempo-stage / rest-pause / countdown code removed')
    ok(not ev("!!document.getElementById('rest-countdown')"), 'no countdown element')
    ev("loadResearchProgram()"); pg.wait_for_timeout(300)
    def setLogs(name, logs): ev("([n, l]) => { const d = getData(); d.logs[n] = l; saveData(d); }", [name, logs])
    def sug():
        r = ev("n => computeSuggestion(getData().logs[n] || [], getEffectiveDef(n, {noDeload:true}))", AB)
        if r: r['explain'] = strip(r['explain'])
        return r
    d = ev("n => getEffectiveDef(n, {noDeload:true})", AB)
    ok(d.get('abStraight') and d['type'] == 'simple' and d['setCount'] == 3 and d['repMin'] == 12 and d['repMax'] == 20 and d['rir'] == '0-1' and d['warmups'] == 2, f"ab def: 3 straight sets 12-20 RIR 0-1 + warm-up ({d.get('type')} {d.get('setCount')} {d.get('repMin')}-{d.get('repMax')} {d.get('rir')})")
    pdef = ev("n => getEffectiveDef(n, {noDeload:true})", PR)
    ok(not pdef.get('abStraight') and pdef['type'] == 'normal' and pdef['drops'] == 2, 'preacher unaffected')
    setLogs(AB, []); s = sug(); ok(s['weight'] is None and s['reps'] == 15 and '15 חזרות' in s['explain'], 'no history: pick ~15-rep weight')
    starts = {}
    for r in [6, 8, 10, 12]:
        setLogs(AB, [OLD(190, r)]); s = sug(); starts[r] = s['weight']
    print('  start weights from old 190×r:', starts)
    ok(all(130 <= w <= 145 for w in starts.values()) and all(w in (130, 145) for w in starts.values()), 'old 190 × 6-12 → start 130-145 lb (snapped)')
    setLogs(AB, [OLD(190, 10)]); s = sug(); ok(s['weight'] == 145 and s['reps'] == 15 and 'שיטה חדשה' in s['explain'], f"190×10 → 145 × 15: {s['explain'][:70]}")
    setLogs(AB, [NEW(145, [16, 14, 13])]); s = sug(); ok(s['weight'] == 145 and s['reps'] == 14, f'double progression: min 13 → 14 same weight ({s["weight"]}×{s["reps"]})')
    setLogs(AB, [NEW(145, [20, 20, 19])]); s = sug(); ok(s['weight'] == 145 and s['reps'] == 20, 'not all at 20 → stay')
    setLogs(AB, [NEW(145, [21, 20, 20])]); s = sug(); ok(s['weight'] == 160 and s['reps'] == 12 and s['kind'] == 'up', 'all sets 20 → +1 plate (160)')
    setLogs(AB, [NEW(175, [20, 20, 20])]); s = sug(); ok(s['weight'] == 190, 'cap: 175 → 190')
    setLogs(AB, [NEW(190, [20, 20, 22])]); s = sug(); ok(s['weight'] == 190 and s['kind'] == 'stackmax' and 'פלטה/משקולת ליד' in s['explain'], 'at 190 all 20 → stack-max tips, no more weight')
    setLogs(AB, [NEW(160, [10, 9, 8])]); s = sug(); ok(s['weight'] == 145 and s['kind'] == 'down', 'below 12 → plate down')
    setLogs(AB, [NEW(160, [15, 14, 13]), NEW(145, [10, 10, 10], day='2026-10-10', deload=True)]); s = sug(); ok(s['weight'] == 160 and s['reps'] == 14, 'deload entry ignored for progression')
    dd = ev("n => deloadDef(getEffectiveDef(n, {noDeload:true}))", AB); ok(dd['setCount'] == 2, 'deload: fewer sets')
    # UI
    setLogs(AB, [OLD(190, 10)])
    ev("() => { startWorkout('A'); pickAccessory('abs'); }"); pg.wait_for_timeout(300)
    meta = strip(pg.inner_text(f'#accessory-list .exercise-item[data-name="{AB}"]'))
    ok('3×12-20 עד כשל' in meta and '1-1-2/3' in meta, f'card: {meta!r}')
    pg.click(f'#accessory-list .exercise-item[data-name="{AB}"]'); pg.wait_for_timeout(300)
    T = lambda sel: strip(pg.inner_text(sel))
    ok(ev("dynamicSetCount") == 3 and ev("document.getElementById('normal-sets').classList.contains('hidden')"), '3 straight-set rows, no heavy/drop/rest-pause rows')
    ok('רסט-פאוז' not in T('#screen-log') and 'שלב טמפו' not in T('#screen-log') and 'דרופ' not in T('#log-type-label'), 'no rest-pause / stage UI')
    ok('145 lb × 15' in T('#dhint-1') and 'RIR\xa00-\u20601' in T('#dhint-1') and '1 שנ׳ למטה לכיווץ' in T('#dhint-1') and '2-3 שנ׳ חזרה מבוקרת למעלה למתיחה מלאה' in T('#dhint-1') and 'בלי שהסטק נוגע' in T('#dhint-1'), f"set 1 hint: target + tempo: {T('#dhint-1')[:90]}")
    ok('עד כשל מלא + 5-8 חצאי חזרות' in T('#dhint-3') and 'חצאי' not in T('#dhint-2'), 'last set: failure + 5-8 half-reps')
    ok('1-1-2/3' in T('#tempo-banner') and '3×12-20' in T('#tempo-banner'), f"tempo banner: {T('#tempo-banner')[:50]}")
    how = T('#log-howto')
    for k in ['2 סטי חימום', 'כ-70 lb × 12 ← כ-115 lb × 6-8', 'רחוק מכשל', '3 סטים ישרים וקשים', 'חצאי חזרות בחצי העליון', 'הישבן דבוק למושב', 'דוחף את הכריות למטה עם החזה', 'חוליה אחר חוליה', 'נושף את כל האוויר', 'קרבה לכשל', 'טווח תנועה מלא', 'לא טמפו קיצוני', 'מוסיפים פלטה']:
        ok(k in how, f'how-to contains "{k}"')
    ok('עולים לכיווץ' not in how, 'no "up into crunch" wording')
    ok('145 lb × 15' in T('#suggestion-box'), 'suggestion box 145 × 15')
    ok(not ev("document.getElementById('ab-warm').classList.contains('hidden')"), 'warm-up rows shown')
    ok(T('#ab-warm-row-1 .set-label') == 'חימום 1' and T('#ab-warm-row-2 .set-label') == 'חימום 2', 'warm-up labels')
    ok('כ-70 lb × 12' in T('#awhint-1') and 'רחוק מכשל' in T('#awhint-1') and 'לומד את התנועה' in T('#awhint-1'), f"warm 1: ~50% × 12 + purpose: {T('#awhint-1')}")
    ok('כ-115 lb × 6-8' in T('#awhint-2') and 'לאט ובשליטה' in T('#awhint-2'), f"warm 2: ~75% × 6-8: {T('#awhint-2')}")
    mw = ev("abWarmWeight(40, 0.5, getEffectiveDef('" + AB + "'))"); ok(mw == 25, f'warm-up snapped to stack min 25 ({mw})')
    ev("fillRecommendedWeights()"); pg.wait_for_timeout(100)
    ok([pg.input_value(f'#dw{i}') for i in (1, 2, 3)] == ['145'] * 3, 'fill recommended: 145 on all 3 sets')
    ok(pg.input_value('#aw1') == '70' and pg.input_value('#aw2') == '115', 'fill recommended: warm-ups 70 / 115')
    pg.fill('#ar1', '12'); pg.fill('#ar2', '7')
    if SHOTS:
        ev("window.scrollTo(0, 0)"); pg.wait_for_timeout(1900)
        pg.screenshot(path='/workspace/shot_v18.png', full_page=True)
    for i, r in ((1, 16), (2, 14), (3, 12)): pg.fill(f'#dr{i}', str(r))
    pg.click('text=💾 שמור'); pg.wait_for_timeout(1100)
    e = ev("n => getData().logs[n].slice(-1)[0]", AB)
    ok(e['type'] == 'simple' and [x['reps'] for x in e['sets']] == [16, 14, 12] and all(x['weight'] == 145 for x in e['sets']), 'saved as 3 straight sets')
    ok(e.get('warm') == [{'weight': 70, 'reps': 12}, {'weight': 115, 'reps': 7}], f"warm-ups saved separately: {e.get('warm')}")
    s = sug(); ok(s['weight'] == 145 and s['reps'] == 13, 'next: 145 × 13')
    ev("n => openLog(n)", PR); pg.wait_for_timeout(200)
    ok(ev("document.getElementById('ab-warm').classList.contains('hidden')") and T('#lbl-4') == 'דרופ 1' and T('#lbl-3') == 'סט 3 (כבד)' and not ev("!!document.getElementById('tempo-banner')"), 'preacher log screen unchanged (drops)')
    ev("showGuide()"); g = T('#guide-content')
    ok('3 סטים ישרים וקשים של 12-20' in g and '5-8 חצאי חזרות' in g and 'למטה לכיווץ' in g and 'חוליה אחר חוליה' in g and 'קרבה לכשל' in g and '1-2-3 ← 1-2-5' not in g, 'his guide updated')
    ev("() => localStorage.setItem('workoutActiveProfile_v1', 'p2')"); ev("createPartnerProfile('')"); pg.reload(wait_until='load')
    ok(not ev("n => isAbStraightExercise({name: n, type:'normal', equip:'machine_lb', stackStart:25, increment:15, stackPlates:11})", AB), 'partner profile: never ab straight-set mode')
    ok('קרבה לכשל' not in (ev("showGuide(), document.getElementById('guide-content').innerText") or ''), 'partner guide unchanged')
    ok(not errs, f'no page errors {errs}')
    b.close()
print('FAILURES:', fails); sys.exit(1 if fails else 0)
