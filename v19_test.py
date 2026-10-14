import sys, datetime
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
SHOTS = not (len(sys.argv) > 2 and sys.argv[2] == 'noshots')
SEED = open('/workspace/seed_real_shape.json', encoding='utf-8').read()
ST, SE = "הרמת עקבים בעמידה", "הרמת עקבים בישיבה"
fails = []; errs = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m, flush=True)
    if not c: fails.append(m)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True)
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, timezone_id='Asia/Jerusalem', service_workers='block')
    pg = ctx.new_page()
    pg.clock.install(time=datetime.datetime(2026, 10, 11, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=3))))  # Sunday
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    ev = pg.evaluate
    pg.goto(BASE, wait_until='load')
    ev("s => { localStorage.clear(); localStorage.setItem('workoutData_v1', s); localStorage.setItem('workoutActiveProfile_v1', 'main'); }", SEED); pg.reload(wait_until='load')
    ok('workout-pwa-v19' in pg.request.get(BASE + 'sw.js').text(), 'SW cache v19')
    ev("loadResearchProgram()"); pg.wait_for_timeout(300)
    ev("() => { const d = getData(); d.logs['" + ST + "'] = [{date:'2026-10-08T07:00:00Z', type:'normal', sets:[{weight:60,reps:10},null,{weight:100,reps:11},{weight:75,reps:8},{weight:55,reps:7}]}]; saveData(d); }")
    before = ev("JSON.stringify(getProgram())")
    order = lambda: ev("[...document.querySelectorAll('#screen-workout .exercise-item')].map(e => e.dataset.name)")
    for day, wid, acc in ((11, 'A', 'calves'), (13, 'C', 'calves'), (15, 'B', 'calves'), (12, 'B', 'abs')):
        ok(ev(f"getProgram().accessoryByDay[new Date(2026, 9, {day}).getDay()]") == acc, f'day {day}: planned accessory {acc}')
    ev("startWorkout('A')"); pg.wait_for_timeout(300)
    o = order(); first_main = ev("getProgram().workouts.find(w => w.id === 'A').exercises[0].name")
    ok(o[:2] == [ST, SE] and o[2] == first_main, f'Sunday A: calves first, then main ({o[:3]})')
    ok('קודם' in pg.inner_text('#accessory-title') and ev("document.getElementById('accessory-list').nextElementSibling.id") == 'exercise-list', 'calf section rendered above the main list')
    if SHOTS:
        ev("window.scrollTo(0, 0)"); pg.wait_for_timeout(1900); pg.screenshot(path='/workspace/shot_v19.png', full_page=True)
    ok(ev("JSON.stringify(getProgram())") == before, 'program data untouched (names/ids/order same)')
    for wid in ('C', 'B'):
        ev(f"() => {{ goHome(); startWorkout('{wid}'); pickAccessory('calves'); }}"); pg.wait_for_timeout(200)
        ok(order()[:2] == [ST, SE], f'{wid} with calves: calves first')
    ev("() => { goHome(); startWorkout('B'); pickAccessory('abs'); }"); pg.wait_for_timeout(200)
    o = order(); ok(o[-2:] == ev("getProgram().accessories.find(a => a.id === 'abs').exercises.map(e => e.name)") and ev("document.getElementById('exercise-list').nextElementSibling.id") == 'accessory-title', f'abs day unchanged: abs after main ({o[-2:]})')
    # stored custom order inside calves group still applies
    ev("() => { goHome(); startWorkout('A'); writeSessionOrder('a:calves', ['" + SE + "', '" + ST + "']); startWorkout('A'); }"); pg.wait_for_timeout(200)
    ok(order()[:2] == [SE, ST], 'custom calves order respected, still first')
    ev("() => { writeSessionOrder('a:calves', null); startWorkout('A'); }")
    # history/progression intact
    pg.click(f'#accessory-list .exercise-item[data-name="{ST}"]'); pg.wait_for_timeout(300)
    ok('100' in pg.inner_text('#prev-info') and pg.inner_text('#suggestion-box').strip() != '', 'standing calf: history + suggestion intact')
    d = ev(f"getEffectiveDef('{ST}', {{noDeload:true}})"); ok(d['drops'] == 2 and '2 שנ׳ בתחתית' in (d['notes'] or ''), 'sets/drops/2s pause kept')
    h5, h4 = pg.inner_text('#hint-5'), pg.inner_text('#hint-4')
    ok('חצאי חזרות בחצי התחתון' in h5 and 'חצאי' not in h4, f'half-rep hint on last drop only: {h5}')
    ev("addDrop()"); ok('חצאי' in pg.inner_text('#hint-6') and 'חצאי' not in pg.inner_text('#hint-5'), 'hint follows the last visible drop'); ev("removeDrop()")
    how = pg.inner_text('#log-howto')
    for k in ['רק בסט האחרון', 'אין חזרה מלאה', 'העקב הכי נמוך', 'כף רגל ישרה', 'לא עד קצות האצבעות', '1-2 שנ׳', 'בלי קפיצות', 'חצי שנייה עצירה במתיחה', 'דוחף למעלה', '5-8 חצאי חזרות', 'עם הגיד']:
        ok(k in how, f'how-to: "{k}"')
    ev(f"openLog('{SE}')"); pg.wait_for_timeout(200)
    ok('חצאי חזרות' in pg.inner_text('#hint-5') and 'חצאי חזרות' in pg.inner_text('#log-howto'), 'seated calf too')
    ev("openLog('הרחקה לצדדים בכבל')"); pg.wait_for_timeout(200)
    ok(all('חצאי חזרות בחצי התחתון' not in pg.inner_text(f'#hint-{i}') for i in (4, 5, 6)), 'other drop exercises: no calf hint')
    ev("showGuide()"); g = pg.inner_text('#guide-content')
    ok('תאומים בעדיפות' in g and 'הראשונים באימון' in g and 'לא מוסיפים אימון רביעי' in g, 'guide line')
    # partner unchanged
    ev("() => localStorage.setItem('workoutActiveProfile_v1', 'p2')"); ev("createPartnerProfile('')"); pg.reload(wait_until='load')
    ok(not ev(f"isCalfPriority({{name:'{ST}', type:'normal'}})"), 'partner: no calf priority')
    ok('תאומים בעדיפות' not in (ev("showGuide(), document.getElementById('guide-content').innerText") or ''), 'partner guide unchanged')
    ok(not errs, f'no page errors {errs}')
    b.close()
print('FAILURES:', fails); sys.exit(1 if fails else 0)
