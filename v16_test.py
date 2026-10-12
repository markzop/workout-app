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
def E(w, r, tempo=None, rp=None, day='2026-10-05', deload=False):
    e = {'date': day + 'T07:00:00Z', 'type': 'normal', 'sets': [{'weight': 115, 'reps': 8}, None, {'weight': w, 'reps': r}] + ([{'weight': w, 'reps': x} for x in rp] if rp else [])}
    if tempo is not None: e['tempo'] = tempo
    if rp: e['rp'] = True
    if deload: e['deload'] = True
    return e
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True)
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, timezone_id='Asia/Jerusalem', service_workers='block')
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    ev = pg.evaluate
    pg.goto(BASE, wait_until='load')
    ev("s => { localStorage.clear(); localStorage.setItem('workoutData_v1', s); localStorage.setItem('workoutActiveProfile_v1', 'main'); }", SEED); pg.reload(wait_until='load')
    ok('workout-pwa-v17' in pg.request.get(BASE + 'sw.js').text(), 'SW cache v17')
    ev("loadResearchProgram()"); pg.wait_for_timeout(300)
    def setLogs(name, logs): ev("([n, l]) => { const d = getData(); d.logs[n] = l; saveData(d); }", [name, logs])
    def strip(x): return x.replace('\u2066', '').replace('\u2069', '')
    def stage(): return ev("readAbStage()")
    def sug():
        r = ev("n => computeSuggestion(getData().logs[n] || [], getEffectiveDef(n, {noDeload:true}))", AB)
        r['explain'] = strip(r['explain']); return r
    d = ev("n => getEffectiveDef(n, {noDeload:true})", AB)
    ok(d.get('abTempo') and d['repMin'] == 8 and d['repMax'] == 12 and d['drops'] == 2, f"main profile: ab def → tempo mode 8-12, 2 rest-pause ({d.get('repMin')}-{d.get('repMax')}, drops {d.get('drops')})")
    pdef = ev("n => getEffectiveDef(n, {noDeload:true})", PR)
    ok(not pdef.get('abTempo') and pdef['repMin'] == 8 and pdef['drops'] == 2, 'other lb machine (preacher) unaffected')
    setLogs(AB, [E(190, 15), E(190, 16, day='2026-10-07')])
    s = sug(); ok(s['weight'] == 190 and s['reps'] == 8 and s['kind'] == 'tempo' and '1-2-3' in s['explain'], f"pre-tempo history → 190 × 8 @1-2-3: {s['explain'][:60]}")
    setLogs(AB, [E(190, 10, tempo=0, rp=[5, 3])])
    s = sug(); ok(s['weight'] == 190 and s['reps'] == 11, f"stage 1, 10 reps → 11 (never more weight): {s['weight']}×{s['reps']}")
    setLogs(AB, [E(190, 6, tempo=0)]); ok(sug()['reps'] == 8, 'below range → 8')
    setLogs(AB, [E(190, 11, tempo=0)]); s = sug(); ok(s['reps'] == 12 and 'עולים שלב' in s['explain'], '11 → 12 (stage-up note)')
    # UI in a workout
    setLogs(AB, [E(190, 10, tempo=0, rp=[5, 3])])
    ev("() => { startWorkout('A'); pickAccessory('abs'); }"); pg.wait_for_timeout(300)
    meta = pg.inner_text(f'#accessory-list .exercise-item[data-name="{AB}"]').replace('\u2066', '').replace('\u2069', '')
    ok('טמפו 1-2-3' in meta and 'רסט-פאוז' in meta, f'exercise card shows tempo: {meta!r}')
    pmeta = ev("n => exerciseRowHtml(n)", PR); ok('טמפו' not in pmeta, 'preacher card: no tempo')
    pg.click(f'#accessory-list .exercise-item[data-name="{AB}"]'); pg.wait_for_timeout(300)
    T = lambda sel: pg.inner_text(sel).replace('\u2066', '').replace('\u2069', '')
    ok('טמפו 1-2-3' in T('#lbl-3') and T('#lbl-4') == 'רסט-פאוז 1/2' and T('#lbl-5') == 'רסט-פאוז 2/2', f"row labels: {T('#lbl-3')} | {T('#lbl-4')} | {T('#lbl-5')}")
    ok(ev("document.getElementById('drop-row-3').classList.contains('hidden')"), 'only 2 rest-pause rows')
    ok('1 שנ׳ למטה לכיווץ' in T('#hint-3') and 'חזה לכיוון הירכיים' in T('#hint-3') and '2 שנ׳ החזקה' in T('#hint-3') and '3 שנ׳ חזרה איטית למעלה למתיחה מלאה' in T('#hint-3') and 'עולים לכיווץ' not in T('#log-howto') and 'בלי שהסטק נוגע' in T('#hint-3') and '190 lb × 11' in T('#hint-3'), f"heavy hint: tempo + target: {T('#hint-3')[:80]}")
    ok('עד כשל' in T('#hint-4') and '15 שנ׳' in T('#hint-4') and '190 lb' in T('#hint-4'), f"rest-pause hint: {T('#hint-4')}")
    how = T('#log-howto')
    for k in ['טמפו 1-2-3', 'האגן נעול במקום', 'הישבן דבוק למושב', 'דוחף את הכריות למטה עם החזה', 'חוליה אחר חוליה', 'החזרה האיטית למעלה', 'מגלגל את עמוד השדרה למטה', 'הצלעות לאגן', 'לא מושך עם הידיים', 'מכופפי הירך', 'נושף את כל האוויר', 'חצאי חזרות', 'רסט-פאוז במקום דרופים', '1-2-5', '1-3-5', 'אתה עכשיו בשלב 1']:
        ok(k in how, f'how-to contains "{k}"')
    ok('דרופ' not in T('#log-type-label') and 'רסט-פאוז' in T('#log-type-label'), f"type label: {T('#log-type-label')}")
    ok('טמפו 1-2-3' in T('#prev-info') and 'רסט-פאוז 1' in T('#prev-info'), 'prev info: tempo + rest-pause labels')
    ok('190 lb × 11' in T('#suggestion-box'), 'suggestion box 190 × 11')
    ev("fillRecommendedWeights()"); pg.wait_for_timeout(100)
    ok(pg.input_value('#w3') == '190' and pg.input_value('#w4') == '190' and pg.input_value('#w5') == '190', 'fill recommended: 190 on heavy + rest-pause rows')
    pg.click('#hint-4 .rest-btn'); pg.wait_for_timeout(1200)
    cd = T('#rest-countdown'); ok(ev("!document.getElementById('rest-countdown').classList.contains('hidden')") and ('14' in cd or '13' in cd), f'15 s rest timer runs: {cd}')
    if SHOTS:
        ev("stopRestCountdown()"); ev("window.scrollTo(0, 0)"); pg.wait_for_timeout(1900)
        pg.screenshot(path='/workspace/shot_v16.png', full_page=True)
    ev("stopRestCountdown()")
    # save 12 clean reps → stage 2
    pg.fill('#r3', '12'); pg.fill('#r4', '4'); pg.fill('#r5', '2')
    pg.click('text=💾 שמור'); pg.wait_for_timeout(300)
    toast = ev("(document.getElementById('toast')||{}).textContent || ''")
    e = ev("n => getData().logs[n].slice(-1)[0]", AB)
    ok(e['tempo'] == 0 and e.get('rp') and [x and x['reps'] for x in e['sets'][2:5]] == [12, 4, 2], f"entry saved with tempo stage + rest-pause sets: {e.get('tempo')}")
    ok(stage() == 1 and ev("JSON.parse(localStorage.getItem('abTempoStage_v1')).stage") == 1, '12 clean reps → stage 2 stored in localStorage (main key)')
    print('  toast:', toast)
    pg.wait_for_timeout(900)
    s = sug(); ok(s['reps'] == 8 and '1-2-5' in s['explain'] and 'עלית לשלב 2' in s['explain'], f"stage 2: reset to 8 @1-2-5: {s['explain'][:70]}")
    pg.reload(wait_until='load'); ok(stage() == 1, 'stage persists after reload')
    ev("n => openLog(n)", AB); pg.wait_for_timeout(200)
    ok('1-2-5' in T('#lbl-3') and '5 שנ׳ חזרה איטית למעלה' in T('#hint-3') and 'שלב 2/3' in T('#tempo-banner'), f"UI follows stage 2: {T('#lbl-3')} / {T('#tempo-banner')[:40]}")
    # no advance cases
    ev("([n, sets]) => { currentDef = getEffectiveDef(n); return maybeAdvanceAbStage(sets, currentDef); }", [AB, [None, None, {'weight': 190, 'reps': 11}]]); ok(stage() == 1, '11 reps → no stage change')
    ev("([n, sets]) => maybeAdvanceAbStage(sets, getEffectiveDef(n))", [AB, [None, None, {'weight': 175, 'reps': 12}]]); ok(stage() == 1, '12 reps below stack max → no stage change')
    ev("([n, sets]) => maybeAdvanceAbStage(sets, Object.assign(getEffectiveDef(n), {deload: true}))", [AB, [None, None, {'weight': 190, 'reps': 12}]]); ok(stage() == 1, 'deload → no stage change')
    ev("([n, sets]) => maybeAdvanceAbStage(sets, getEffectiveDef(n))", [AB, [None, None, {'weight': 190, 'reps': 12}]]); ok(stage() == 2, '12 at 190 in stage 2 → stage 3 (1-3-5)')
    ev("([n, sets]) => maybeAdvanceAbStage(sets, getEffectiveDef(n))", [AB, [None, None, {'weight': 190, 'reps': 13}]]); ok(stage() == 2, 'stage 3 is the last')
    setLogs(AB, [E(190, 12, tempo=2, rp=[5, 3])]); s = sug(); ok(s['reps'] == 12 and 'השלב האחרון' in s['explain'] and 'חצאי חזרות' in s['explain'], 'last stage at 12: stay + half-reps tip')
    ev("n => openLog(n)", AB); pg.wait_for_timeout(200)
    pg.click('text=שלב טמפו קודם'); pg.wait_for_timeout(200); ok(stage() == 1 and '1-2-5' in T('#lbl-3'), 'manual stage button (back)')
    pg.click('text=שלב טמפו הבא'); pg.wait_for_timeout(200); ok(stage() == 2 and '1-3-5' in T('#lbl-3'), 'manual stage button (forward)')
    dd = ev("n => deloadDef(getEffectiveDef(n, {noDeload:true}))", AB)
    ok(dd['drops'] == 0 and ev("n => computeSuggestion(getData().logs[n], deloadDef(getEffectiveDef(n, {noDeload:true})), {deload:true}).kind", AB) == 'deload', 'deload week: no rest-pause, normal deload suggestion')
    # preacher UI still drops
    ev("n => openLog(n)", PR); pg.wait_for_timeout(200)
    ok(T('#lbl-4') == 'דרופ 1' and T('#lbl-3') == 'סט 3 (כבד)' and 'דרופ' in T('#hint-4') and not ev("!!document.getElementById('tempo-banner')"), 'preacher log screen unchanged (drops)')
    ev("showGuide()"); ok('1-2-3 ← 1-2-5 ← 1-3-5' in T('#guide-content') and 'למטה לכיווץ' in T('#guide-content') and 'חוליה אחר חוליה' in T('#guide-content'), 'his guide line')
    # partner profile untouched
    ev("() => localStorage.setItem('workoutActiveProfile_v1', 'p2')"); ev("createPartnerProfile('')"); pg.reload(wait_until='load')
    ok(not ev("n => isAbTempoExercise(Object.assign({}, findExerciseDef(n, RESEARCH_PROGRAM) || {name: n, type:'normal', equip:'machine_lb', stackStart:25, increment:15, stackPlates:11}))", AB), 'partner profile: never tempo mode')
    ok(ev("readAbStage()") == 0 and ev("localStorage.getItem('p2:abTempoStage_v1')") is None, 'partner stage separate (p2: key, default 0)')
    ok(not errs, f'no page errors {errs}')
    b.close()
print('FAILURES:', fails); sys.exit(1 if fails else 0)
