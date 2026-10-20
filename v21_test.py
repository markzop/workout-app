import sys, json
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
SHOTS = not (len(sys.argv) > 2 and sys.argv[2] == 'noshots')
SEED = json.load(open('/workspace/seed_real_shape.json', encoding='utf-8'))
OLD, NEW = "חתירה בטי-בר רחב", "חתירה בכבל בישיבה באחיזה רחבה"
ONE, LAT = "חתירה ביד אחת בכבל", "משיכה בפולי רחב"
fails = []; errs = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m, flush=True)
    if not c: fails.append(m)
def TB(w, r, day='2026-10-14', deload=False):
    e = {'date': day + 'T07:00:00Z', 'type': 'topback', 'sets': [{'weight': w * 0.6, 'reps': 8}, None, {'weight': w, 'reps': r}, {'weight': w * 0.85, 'reps': 9}, {'weight': w * 0.85, 'reps': 8}]}
    if deload: e['deload'] = True
    return e
def NRM(w, r, day='2026-10-14'):
    return {'date': day + 'T07:00:00Z', 'type': 'normal', 'sets': [None, None, {'weight': w, 'reps': r}, {'weight': w * 0.75, 'reps': 6}]}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True)
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, timezone_id='Asia/Jerusalem', service_workers='block')
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    ev = pg.evaluate
    pg.goto(BASE, wait_until='load')
    ok('workout-pwa-v21' in pg.request.get(BASE + 'sw.js').text(), 'SW cache v21')
    ev("s => { localStorage.clear(); localStorage.setItem('workoutData_v1', s); localStorage.setItem('workoutActiveProfile_v1', 'main'); }", json.dumps(SEED)); pg.reload(wait_until='load')
    ev("loadResearchProgram()"); pg.wait_for_timeout(200)
    # simulate a stored v20 program with the T-bar
    ev(f"""() => {{ const d = getData(); const w = d.program.workouts.find(w => w.id === 'C'); const i = w.exercises.findIndex(e => e.name === '{NEW}');
        w.exercises[i] = {{ name: '{OLD}', origName: '{OLD}', equip: 'barbell', type: 'topback', warmups: 1, backoffs: 2, repMin: 6, repMax: 10, increment: 2.5, notes: 'x' }};
        w.desc = w.desc.replace('חתירה רחבה בכבל (טופ+בק-אוף)', 'טי-בר (טופ+בק-אוף)'); delete d.wideCableRowV21; saveData(d); }}""")
    before = ev("getProgram().workouts.find(w => w.id === 'C').exercises.map(e => e.name)")
    old_n = ev(f"(getData().logs['{OLD}'] || []).length")
    pg.reload(wait_until='load')
    C = ev("getProgram().workouts.find(w => w.id === 'C')")
    names = [e['name'] for e in C['exercises']]; i = before.index(OLD)
    ok(names[i] == NEW and OLD not in names and len(names) == len(before) and i == 1, f'migrated in place (pos {i})')
    x = C['exercises'][i]
    ok(x['type'] == 'topback' and x['warmups'] == 1 and x['backoffs'] == 2 and (x['repMin'], x['repMax']) == (6, 10), 'same top+back-off scheme 6-10')
    ok(x['equip'] == 'machine' and x['increment'] == 5 and x['stack'][0] == 5 and x['stack'][-1] == 125, 'same low-row station: 5–125, step 5')
    ok('חתירה רחבה בכבל' in C['desc'] and 'טי-בר' not in C['desc'], 'workout C desc updated')
    ok(ev(f"(getData().logs['{OLD}'] || []).length") == old_n and old_n > 0 and ev(f"(getData().logs['{NEW}'] || []).length") == 0, 'T-bar history kept under old name')
    src = ev("RESEARCH_PROGRAM.workouts.find(w => w.id === 'C').exercises.map(e => e.name)"); ok(src[1] == NEW and OLD not in src, 'research program updated')
    def est(logs):
        ev("l => { const d = getData(); Object.keys(l).forEach(k => d.logs[k] = l[k]); saveData(d); }", logs)
        return ev(f"computeSuggestion(getData().logs['{NEW}'] || [], getEffectiveDef('{NEW}', {{noDeload:true}}))")
    # T-bar only
    s = est({ONE: [], LAT: [], OLD: [TB(40, 8)]})
    # e1 40x8 ≈ 50.1; ×0.65 = 32.6; load for 7+2.5 reps ≈ 32.6/1.32 ≈ 24.7 → snap down 20
    print('  T-bar only 40×8 →', s and s['weight'], round(s['raw'], 1))
    ok(s['kind'] == 'estimate' and s['weight'] == 20 and s['reps'] == 7 and 'הערכה לפי הטי-בר – תתאים בסט הראשון' in s['explain'] and 'RIR 2-3' in s['explain'], 'T-bar 40×8 → 20 kg × 7, RIR 2-3')
    s = est({OLD: [TB(40, 8), TB(60, 6, day='2026-10-16', deload=True)]}); ok(s['weight'] == 20, 'deload T-bar entry ignored')
    s = est({OLD: [TB(200, 8)]}); ok(s['weight'] <= 125, f"clamped to stack max ({s['weight']})")
    # one-arm reference preferred, T-bar shown as cross-check
    s = est({OLD: [TB(40, 8)], ONE: [NRM(30, 10)]})
    print('  one-arm 30×10 →', s['weight'], round(s['raw'], 1), '|', s['explain'][-90:])
    ok(s['source'] == ONE and s['weight'] == 50 and 'בדיקה מול: טי-בר' in s['explain'], 'one-arm row (same station) preferred: 30×10 → 50; T-bar cross-check shown')
    s = est({ONE: [], LAT: [NRM(60, 8)]}); ok(s['source'] == LAT and s['weight'] == 50, f"pulldown fallback 60×8 → {s['weight']}")
    s = est({ONE: [], LAT: [], OLD: []}); ok(s is None, 'no references → no recommendation')
    # UI with T-bar only
    est({ONE: [], LAT: [], OLD: [TB(40, 8)]})
    ev("startWorkout('C')"); pg.wait_for_timeout(300)
    pg.click(f'#exercise-list .exercise-item[data-name="{NEW}"]'); pg.wait_for_timeout(300)
    h3 = pg.inner_text('#hint-3'); ok('20 ק״ג × 7' in h3 and '(הערכה)' in h3 and 'הערכה לפי הטי-בר – תתאים בסט הראשון' in h3, f'hint-3 marks estimate: {h3}')
    ok('הערכה לפי הטי-בר – תתאים בסט הראשון' in pg.inner_text('#suggestion-box'), 'suggestion box shows estimate')
    ok('כ-10 ק״ג × 8' in pg.inner_text('#hint-1'), f"warm-up derived from estimate: {pg.inner_text('#hint-1')}")
    ok('כ-15 ק״ג' in pg.inner_text('#hint-4'), f"back-off from estimate: {pg.inner_text('#hint-4')[:40]}")
    how = pg.inner_text('#log-howto')
    for k in ['מוט רחב, אחיזה עליונה', 'יושב זקוף', 'להיטות מעט קדימה במתיחה', 'בלי נדנוד', 'לחזה התחתון', 'כ-45°', 'סוחט את השכמות שנייה אחת', '2-3 שנ׳ עד מתיחה מלאה', 'השכמות נפתחות קדימה']:
        ok(k in how, f'how-to: "{k}"')
    links = ev("[...document.querySelectorAll('#log-links a')].map(a => a.href)")
    ok(links == ['https://www.youtube.com/watch?v=YKAeU55CkVk', 'https://www.youtube.com/watch?v=e9oe5qbN0jo'], f'demo links {links}')
    if SHOTS:
        ev("window.scrollTo(0, 0)"); pg.wait_for_timeout(1900); pg.screenshot(path='/workspace/shot_v21.png', full_page=True)
    ev("fillRecommendedWeights()"); ok(pg.input_value('#w3') == '20', 'fill: estimate on top set')
    pg.fill('#r3', '10'); pg.click('text=💾 שמור'); pg.wait_for_timeout(1100)
    s = ev(f"computeSuggestion(getData().logs['{NEW}'], getEffectiveDef('{NEW}'))")
    ok(s['kind'] != 'estimate' and s['weight'] >= 25, f"after first session: normal progression ({s['kind']} {s['weight']}×{s['reps']})")
    ev(f"openLog('{NEW}')"); pg.wait_for_timeout(200); ok('הערכה' not in pg.inner_text('#hint-3') and 'הערכה לפי' not in pg.inner_text('#log-howto'), 'estimate marks gone')
    ev("showHistory()"); pg.wait_for_timeout(300)
    ok(ev(f"[...document.querySelectorAll('.history-item strong')].some(e => e.textContent === '{OLD}')"), 'T-bar history viewable')
    ev("showGuide()"); g = pg.inner_text('#guide-content'); ok('חתירה רחבה בכבל' in g and 'הערכה לפי הטי-בר' in g, 'guide line')
    ev(f"openLog('{ONE}')"); pg.wait_for_timeout(200); ok(not ev("!!document.getElementById('log-links')"), 'one-arm row unchanged')
    ev("() => localStorage.setItem('workoutActiveProfile_v1', 'p2')"); ev("createPartnerProfile('')"); pg.reload(wait_until='load')
    ok(not ev(f"isWideCableRow({{name: '{NEW}'}})") and not ev("getData().wideCableRowV21"), 'partner unchanged')
    ok(not errs, f'no page errors {errs}')
    b.close()
print('FAILURES:', fails); sys.exit(1 if fails else 0)
