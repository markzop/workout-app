import json, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
SEED = open('/workspace/seed_real_shape.json', encoding='utf-8').read()
fails = []; errs = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m, flush=True)
    if not c: fails.append(m)
def E(top, bos, deload=False, day='2026-10-01'):
    e = {'date': day + 'T07:00:00Z', 'type': 'topback', 'sets': [None, None, {'weight': top, 'reps': 8}] + [{'weight': w, 'reps': r} for w, r in bos]}
    if deload: e['deload'] = True
    return e
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True)
    pg = b.new_context(viewport={'width': 390, 'height': 844}, timezone_id='Asia/Jerusalem', service_workers='block').new_page()
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    ev = pg.evaluate
    pg.goto(BASE, wait_until='load')
    ev("s => { localStorage.clear(); localStorage.setItem('workoutData_v1', s); localStorage.setItem('workoutActiveProfile_v1', 'main'); }", SEED); pg.reload(wait_until='load')
    ok('workout-pwa-v15' in pg.request.get(BASE + 'sw.js').text(), 'SW cache v15')
    ev("loadResearchProgram()"); pg.wait_for_timeout(300)
    NAME = ev("getProgram().workouts.flatMap(w => w.exercises).find(e => e.type === 'topback' && e.repMin === 6 && e.repMax === 10).name")
    print('exercise:', NAME)
    def info(logs):
        ev("([n, l]) => { const d = getData(); d.logs[n] = l; saveData(d); }", [NAME, logs])
        return ev("n => backoffDropInfo(n, getEffectiveDef(n, {noDeload:true}))", NAME)
    i = info([]); ok(i['pct'] == 12.5 and i['note'] is None, 'no history → 12.5%')
    i = info([E(125, [(110, 5), (110, 6)])]); print(' ', i['note'])
    ok(i['pct'] == 17.5 and i['note'] == 'בפעם קודמת בבק-אוף: 110×5 (מתחת לטווח) → הפעם 17.5% פחות מהטופ', '3 short → +5 → 17.5% + note text')
    i = info([E(125, [(110, 7), (110, 9)])]); print(' ', i['note']); ok(i['pct'] == 15, '1 short → +2.5 → 15%')
    i = info([E(125, [(110, 10), (110, 9)])]); print(' ', i['note']); ok(i['pct'] == 12.5 and 'בתוך הטווח' in i['note'], 'in range → keep 12.5%')
    i = info([E(125, [(110, 14), (110, 13)])]); print(' ', i['note']); ok(i['pct'] == 10 and 'מעל הטווח' in i['note'], 'above range → −2.5 → 10%')
    i = info([E(100, [(75, 4)])]); ok(i['pct'] == 25, 'clamp max 25%')
    i = info([E(100, [(92.5, 15)])]); ok(i['pct'] == 7.5, 'clamp min 7.5%')
    i = info([E(125, [(110, 5)]), E(110, [(100, 14)], deload=True, day='2026-10-03')]); ok(i['pct'] == 17.5, 'deload session ignored')
    i = info([E(125, [(110, 5)])])
    ev("n => { showProgramEditor(); goHome(); startWorkout(getProgram().workouts.find(w => w.exercises.some(e => e.name === n)).id); openLog(n); }", NAME); pg.wait_for_timeout(300)
    top = ev("currentPlan.top"); h4 = pg.inner_text('#hint-4'); how = pg.inner_text('#log-howto')
    exp = ev("t => stepBelowDef(t * 0.825, t, currentDef)", top)
    print('  top', top, '→ back-off', exp, '|', h4.replace('\n', ' / '))
    ok(f"כ-{ev('fmtKg', exp) if False else ('%g' % exp)} ק״ג" in h4 and '17.5%' in h4 and 'מתחת לטווח' in h4, 'hint under back-off rows: weight + note')
    ok('מורידים 17.5% ממשקל הטופ' in how and '10-15%' in how, 'how-to box uses adaptive %')
    pg.fill('#w3', '100'); pg.dispatch_event('#w3', 'input'); pg.wait_for_timeout(100)
    e2 = ev("stepBelowDef(82.5, 100, currentDef)")
    ok(f"כ-{'%g' % e2} ק״ג" in pg.inner_text('#hint-4'), f"typed top 100 → 82.5 snapped to grid ({e2}): {pg.inner_text('#hint-4')[:40]}")
    ev("showGuide()"); ok('אחוז הבק-אוף מותאם' in pg.inner_text('#guide-content'), 'his guide line')
    # her profile
    ev("() => localStorage.setItem('workoutActiveProfile_v1', 'p2')"); ev("createPartnerProfile('')"); pg.reload(wait_until='load')
    HT = "היפ ת'ראסט"
    ev("l => { const d = getData(); d.logs[\"היפ ת'ראסט\"] = l; saveData(d); }", [E(80, [(70, 14), (70, 13)])])
    i = ev("n => backoffDropInfo(n, getEffectiveDef(n, {noDeload:true}))", HT); print(' her:', i['note'])
    ok(i['pct'] == 10, 'her profile adaptive too (above range → 10%)')
    ev("showGuide()"); ok('האחוז מותאם לכל תרגיל' in pg.inner_text('#guide-content'), 'her guide line')
    ok(not errs, f'no page errors {errs}')
    b.close()
print('FAILURES:', fails); sys.exit(1 if fails else 0)
