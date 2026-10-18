import sys, json
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
SHOTS = not (len(sys.argv) > 2 and sys.argv[2] == 'noshots')
SEED = json.load(open('/workspace/seed_real_shape.json', encoding='utf-8'))
OLD, NEW = "פשיטת מרפק מאחורי הראש עם משקולת", "פשיטת מרפק מעל הראש בכבל עם חבל"
fails = []; errs = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m, flush=True)
    if not c: fails.append(m)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True)
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, timezone_id='Asia/Jerusalem', service_workers='block')
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    ev = pg.evaluate
    pg.goto(BASE, wait_until='load')
    ok('workout-pwa-v20' in pg.request.get(BASE + 'sw.js').text(), 'SW cache v20')
    # --- migration of an existing v19 research program (stored with the old dumbbell exercise, user-tweaked drops) ---
    ev("s => { localStorage.clear(); localStorage.setItem('workoutData_v1', s); localStorage.setItem('workoutActiveProfile_v1', 'main'); }", json.dumps(SEED)); pg.reload(wait_until='load')
    ev("loadResearchProgram()"); pg.wait_for_timeout(200)
    old_logs = ev(f"(getData().logs['{OLD}'] || []).length"); ok(old_logs > 0, f'seed has dumbbell history ({old_logs})')
    ev(f"""() => {{ const d = getData(); const w = d.program.workouts.find(w => w.id === 'B'); const i = w.exercises.findIndex(e => e.name === '{NEW}');
        w.exercises[i] = Object.assign({{}}, w.exercises[i], {{ name: '{OLD}', origName: '{OLD}', equip: 'db', increment: 2, drops: 1, notes: 'old' }});
        w.desc = w.desc.replace('פשיטה מעל הראש בכבל עם חבל', 'פשיטה מאחורי הראש'); delete d.overheadRopeV20; saveData(d);
        localStorage.setItem(SESSION_ORDER_KEY, JSON.stringify({{date: toDateKey(new Date()), orders: {{'w:B': w.exercises.map(e => e.name).reverse()}}}})); }}""")
    names_before = ev("getProgram().workouts.find(w => w.id === 'B').exercises.map(e => e.name)")
    pg.reload(wait_until='load')
    B = ev("getProgram().workouts.find(w => w.id === 'B')")
    names = [e['name'] for e in B['exercises']]
    i = names_before.index(OLD)
    ok(names[i] == NEW and OLD not in names and len(names) == len(names_before), f'migrated in place (position {i})')
    x = B['exercises'][i]
    ok(x['equip'] == 'cable' and x['increment'] == 2.5 and x['origName'] == NEW and x['drops'] == 1 and x['warmups'] == 1 and x['repMin'] == 8 and x['repMax'] == 12, f"cable 2.5, same sets/reps (kept user drops=1): {x}")
    ok('חבל' in B['desc'] and 'מאחורי הראש' not in B['desc'], 'workout B desc updated')
    ok(ev(f"(getData().logs['{OLD}'] || []).length") == old_logs and ev(f"(getData().logs['{NEW}'] || []).length") == 0, 'old history kept under old name, new name starts empty')
    ok(ev("getData().overheadRopeV20") is True, 'migration flag set')
    so = ev("readSessionOrders()['w:B'] || []"); ok(NEW in so and OLD not in so, 'today custom order: name swapped')
    pg.reload(wait_until='load'); ok([e['name'] for e in ev("getProgram().workouts.find(w => w.id === 'B').exercises")] == names, 'migration idempotent')
    # fresh load of research program
    ev("loadResearchProgram()"); pg.wait_for_timeout(200)
    src = ev("RESEARCH_PROGRAM.workouts.find(w => w.id === 'B').exercises.map(e => e.name)")
    ok(NEW in src and OLD not in src and src.index(NEW) == 4, 'research program: rope cable at the old position (5th in B)')
    d = ev(f"getEffectiveDef('{NEW}', {{noDeload:true}})")
    ok(d['equip'] == 'cable' and d['increment'] == 2.5 and d['type'] == 'normal' and d['drops'] == 2 and d['warmups'] == 1 and (d['repMin'], d['repMax']) == (8, 12), 'program def: cable 2.5, 1 warm-up + heavy 8-12 + 2 drops')
    ok(ev(f"computeSuggestion(getData().logs['{NEW}'] || [], getEffectiveDef('{NEW}'))") is None, 'no weight recommendation before first session')
    # UI
    ev("() => { localStorage.removeItem(SESSION_ORDER_KEY); startWorkout('B'); }"); pg.wait_for_timeout(300)
    o = ev("[...document.querySelectorAll('#exercise-list .exercise-item')].map(e => e.dataset.name)")
    ok(o.index(NEW) == 4, f'workout list position: {o.index(NEW)}')
    pg.click(f'#exercise-list .exercise-item[data-name="{NEW}"]'); pg.wait_for_timeout(300)
    ok(pg.inner_text('#prev-info').strip() == 'אין נתונים קודמים לתרגיל זה' and ev("document.getElementById('suggestion-box').classList.contains('hidden')"), 'fresh: no previous data, no suggestion')
    ok(ev("document.getElementById('w3').value") == '' and 'ק״ג' in ev("document.getElementById('w3').placeholder"), 'no prefilled dumbbell weight, kg')
    how = pg.inner_text('#log-howto')
    for k in ['אין המלצת משקל עד הסשן הראשון', 'משקל בינוני', OLD, 'בגובה הירך או נמוך יותר', 'גב לכבל', 'עמידה מפוסקת', 'נטייה קלה קדימה', 'המרפקים ליד הראש ומצביעים קדימה', 'מאחורי הראש עד מתיחה מלאה', 'קדימה-למעלה', 'מפריד את קצוות החבל', '2-3 שנ׳', 'עד 2-3 מתוך 10', 'לא מחמיר למחרת', 'עוברים לחלופה', 'קטאנה ביד אחת בכבל', 'גלגלת נמוכה', 'מוטה מעט החוצה באלכסון']:
        ok(k in how, f'how-to: "{k}"')
    links = ev("[...document.querySelectorAll('#log-links a')].map(a => [a.href, a.target, a.textContent])")
    ok([l[0] for l in links] == ['https://www.youtube.com/watch?v=kqidUIf1eJE', 'https://www.youtube.com/watch?v=4aaSlbdMEK0'] and all(l[1] == '_blank' for l in links), f'demo links: {links}')
    if SHOTS:
        ev("window.scrollTo(0, 0)"); pg.wait_for_timeout(1900); pg.screenshot(path='/workspace/shot_v20.png', full_page=True)
    # after first session: normal progression from cable weights
    pg.fill('#w3', '15'); pg.fill('#r3', '10'); pg.click('text=💾 שמור'); pg.wait_for_timeout(1100)
    s = ev(f"computeSuggestion(getData().logs['{NEW}'], getEffectiveDef('{NEW}'))")
    ok(s and s['weight'] in (15, 17.5), f'after first session: progression from cable weight ({s and s["weight"]}×{s and s["reps"]})')
    ev(f"openLog('{NEW}')"); pg.wait_for_timeout(200); ok('אין המלצת משקל' not in pg.inner_text('#log-howto'), 'start-fresh note gone after first session')
    # old history still reachable
    ev("showHistory()"); pg.wait_for_timeout(300)
    ok(ev(f"[...document.querySelectorAll('.history-item strong')].some(e => e.textContent === '{OLD}')"), 'history list still shows the dumbbell exercise')
    ev("showGuide()"); g = pg.inner_text('#guide-content'); ok('פשיטה מעל הראש בכבל עם חבל' in g and 'קטאנה' in g, 'guide line')
    # other exercises unchanged
    ev("openLog('פשיטת מרפק בפולי')"); pg.wait_for_timeout(200); ok(not ev("!!document.getElementById('log-links')") and 'קטאנה' not in pg.inner_text('#log-howto'), 'pushdown unchanged')
    # partner untouched
    ev("() => localStorage.setItem('workoutActiveProfile_v1', 'p2')"); ev("createPartnerProfile('')"); pg.reload(wait_until='load')
    ok(not ev(f"isOverheadRope({{name: '{NEW}'}})") and 'קטאנה' not in (ev("showGuide(), document.getElementById('guide-content').innerText") or ''), 'partner unchanged')
    ok(not ev("getData().overheadRopeV20"), 'partner data not migrated')
    ok(not errs, f'no page errors {errs}')
    b.close()
print('FAILURES:', fails); sys.exit(1 if fails else 0)
