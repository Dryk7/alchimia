"""AUDIT FINAL FOULÉE — 17 scénarios distincts + opening cinematic check.
Génère D:/alchimia/screenshots/playthrough/AUDIT-*.png + audit-final-report.md
"""
import asyncio, io, sys, time, json
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OUT_DIR = 'D:/alchimia/screenshots/playthrough'
URL = 'http://localhost:8770'

SETUP_LS = """
localStorage.setItem("foulee.storySeen","1");
localStorage.setItem("foulee.tutoV3","done");
localStorage.setItem("foulee.activeTutoV1","done");
localStorage.setItem("foulee.openingSeen","1");
"""

CLOSE_MODALS_JS = """
document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="";});
try { STATE.starterPackDeclined = true; STATE.starterPackClaimed = true; } catch(e){}
"""

DOM_CHECK_JS = r"""
(()=>{
  const out = {overflows:[], badText:[], stuckModals:[], hidden:[], topZ:[]};
  const docW = document.documentElement.clientWidth;
  // 1. Overflows
  document.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.right > docW + 4 && r.width > 0 && r.height > 0) {
      const cs = getComputedStyle(el);
      if (cs.visibility !== 'hidden' && cs.display !== 'none') {
        out.overflows.push({
          tag: el.tagName,
          id: el.id || '',
          cls: (typeof el.className === 'string' ? el.className.slice(0, 50) : ''),
          right: Math.round(r.right),
          width: Math.round(r.width)
        });
      }
    }
  });
  out.overflows = out.overflows.slice(0, 10);
  // 2. Bad text (undefined/NaN/null visibles)
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  const bad = /\b(undefined|NaN|null)\b/;
  while((node = walker.nextNode())){
    const t = node.textContent;
    if(!t || !bad.test(t)) continue;
    const parent = node.parentElement;
    if(!parent) continue;
    const cs = getComputedStyle(parent);
    if(cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = parent.getBoundingClientRect();
    if(r.width === 0 || r.height === 0) continue;
    out.badText.push({
      tag: parent.tagName,
      id: parent.id || '',
      cls: (typeof parent.className === 'string' ? parent.className.slice(0,40) : ''),
      text: t.trim().slice(0, 80)
    });
  }
  out.badText = out.badText.slice(0, 10);
  // 3. Modals stuck
  document.querySelectorAll('.modal.show').forEach(m => {
    out.stuckModals.push({id: m.id || '?', display: getComputedStyle(m).display});
  });
  // 4. Hidden display:block opacity:0 in HUD
  document.querySelectorAll('#hud-top *, #hud-bottom *, .hud *').forEach(el => {
    const cs = getComputedStyle(el);
    if(cs.display === 'block' && parseFloat(cs.opacity) < 0.05){
      out.hidden.push({tag: el.tagName, id: el.id || '', cls: (typeof el.className==='string'?el.className.slice(0,40):'')});
    }
  });
  out.hidden = out.hidden.slice(0, 6);
  // 5. Top z-index (just info)
  document.querySelectorAll('*').forEach(el => {
    const z = parseInt(getComputedStyle(el).zIndex, 10);
    if(!isNaN(z) && z >= 1000){
      out.topZ.push({id: el.id || el.tagName, z, cls: (typeof el.className==='string'?el.className.slice(0,30):'')});
    }
  });
  out.topZ = out.topZ.sort((a,b)=>b.z-a.z).slice(0, 8);
  return out;
})()
"""

REPORT = []
def log(msg=''):
    print(msg)
    REPORT.append(msg)

ERRORS = []
WARNS = []

async def screenshot(page, name):
    await page.screenshot(path=f'{OUT_DIR}/AUDIT-{name}.png', clip={'x':0,'y':0,'width':540,'height':960})

async def setup_state(page, **kwargs):
    """Pousse des valeurs dans STATE.* (lapsRun, gold, totalTaps, chapter, etc.) + recalcule lapProgress."""
    js = ''
    for k, v in kwargs.items():
        if isinstance(v, str):
            js += f'STATE["{k}"] = "{v}";'
        else:
            js += f'STATE["{k}"] = {json.dumps(v)};'
    js += CLOSE_MODALS_JS
    await page.evaluate(js)

async def goto_clean(page):
    await page.goto(URL, wait_until='domcontentloaded')
    await page.evaluate(SETUP_LS)
    await page.reload()
    await page.wait_for_load_state('networkidle')
    await page.wait_for_timeout(400)
    # Click start if visible
    try:
        await page.evaluate('document.getElementById("start-btn")?.click();')
        await page.wait_for_timeout(400)
    except Exception:
        pass
    await page.evaluate(CLOSE_MODALS_JS)
    await page.wait_for_timeout(200)

ANOMALIES = {}  # scenario_id -> list of strings

def record_anomalies(scn_id, dom, console_count_before, console_count_after):
    items = []
    if dom['overflows']:
        for o in dom['overflows']:
            items.append(f"OVERFLOW {o['tag']}#{o['id']}.{o['cls']} right={o['right']}px")
    if dom['badText']:
        for b in dom['badText']:
            items.append(f"BAD-TEXT in {b['tag']}#{b['id']}.{b['cls']}: '{b['text']}'")
    # stuckModals : informational only — flag only if we expected them closed
    if dom['stuckModals']:
        for m in dom['stuckModals']:
            items.append(f"MODAL-OPEN {m['id']}")
    if dom['hidden']:
        for h in dom['hidden']:
            items.append(f"HUD-HIDDEN display:block opacity~0 — {h['tag']}#{h['id']}.{h['cls']}")
    new_console = console_count_after - console_count_before
    if new_console > 0:
        items.append(f"+{new_console} console errors/warnings during scenario")
    ANOMALIES[scn_id] = items
    return items

OPENING_OBS = []  # observations T2/T3/T4

async def scenario_run(page, scn_id, title, setup_kw, post_js=None, open_overlay=None):
    log(f'\n=== {scn_id} : {title} ===')
    err_before = len(ERRORS) + len(WARNS)
    await setup_state(page, **setup_kw)
    if post_js:
        try:
            await page.evaluate(post_js)
        except Exception as e:
            log(f'  post_js err: {str(e)[:120]}')
    await page.wait_for_timeout(600)
    if open_overlay:
        try:
            await page.evaluate(open_overlay)
        except Exception as e:
            log(f'  open_overlay err: {str(e)[:120]}')
        await page.wait_for_timeout(400)
    await screenshot(page, scn_id)
    try:
        dom = await page.evaluate(DOM_CHECK_JS)
    except Exception as e:
        log(f'  DOM check err: {str(e)[:200]}')
        dom = {'overflows':[],'badText':[],'stuckModals':[],'hidden':[],'topZ':[]}
    items = record_anomalies(scn_id, dom, err_before, len(ERRORS) + len(WARNS))
    if not items:
        log(f'  OK — no anomaly')
    else:
        log(f'  {len(items)} anomalies:')
        for it in items:
            log(f'    - {it}')
    # Close any stuck overlay before next scenario
    await page.evaluate(CLOSE_MODALS_JS)
    await page.wait_for_timeout(150)

async def opening_cinematic_check(p):
    log('\n=== OPENING CINEMATIC CHECK (fresh localStorage) ===')
    ctx = await p.chromium.launch()
    bctx = await ctx.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
    page2 = await bctx.new_page()
    errs2 = []
    page2.on('pageerror', lambda e: errs2.append(str(e)))
    # Strip openingSeen BEFORE first load
    await bctx.add_init_script("try { localStorage.clear(); } catch(e){}")
    t0 = time.time()
    await page2.goto(URL, wait_until='domcontentloaded')

    # Capture at T=2.0, 3.0, 4.0s and inspect logo state
    targets = [2.0, 3.0, 4.0]
    obs_local = []
    for sec in targets:
        wait_ms = int(sec * 1000 - (time.time() - t0) * 1000)
        if wait_ms > 0:
            await page2.wait_for_timeout(wait_ms)
        elapsed = (time.time() - t0)
        try:
            info = await page2.evaluate(r"""
              (() => {
                const el = document.querySelector('.oc-logo');
                if(!el) return {present: false};
                const cs = getComputedStyle(el);
                const r = el.getBoundingClientRect();
                const overlay = document.getElementById('opening-cinematic');
                return {
                  present: true,
                  text: (el.textContent || '').trim(),
                  opacity: cs.opacity,
                  display: cs.display,
                  visibility: cs.visibility,
                  transform: cs.transform,
                  width: Math.round(r.width),
                  height: Math.round(r.height),
                  overlayDisplay: overlay ? getComputedStyle(overlay).display : 'no-overlay',
                  overlayOpacity: overlay ? getComputedStyle(overlay).opacity : '?'
                };
              })()
            """)
        except Exception as e:
            info = {'err': str(e)[:120]}
        obs_local.append({'t': round(elapsed, 2), 'info': info})
        await page2.screenshot(path=f'{OUT_DIR}/AUDIT-OPENING-T{int(sec*10)}.png', clip={'x':0,'y':0,'width':540,'height':960})

    for o in obs_local:
        i = o['info']
        log(f'  T={o["t"]}s : ' + (
            'no .oc-logo' if not i.get('present', False) else
            f'text="{i.get("text","?")[:20]}" opacity={i.get("opacity","?")} '
            f'display={i.get("display","?")} vis={i.get("visibility","?")} '
            f'size={i.get("width","?")}x{i.get("height","?")} '
            f'overlay_disp={i.get("overlayDisplay","?")} overlay_op={i.get("overlayOpacity","?")}'
        ))
    OPENING_OBS.extend(obs_local)

    # Verdict
    visible_count = 0
    for o in obs_local:
        try:
            if o['info'].get('present') and float(o['info'].get('opacity', '0')) > 0.5 \
               and o['info'].get('display') != 'none' \
               and o['info'].get('width', 0) > 20:
                visible_count += 1
        except Exception:
            pass
    OPENING_OBS.append({'verdict_visible_count': visible_count, 'total': len(obs_local)})
    log(f'  Verdict logo : visible (opacity>0.5) at {visible_count}/{len(obs_local)} sample times')

    await bctx.close()
    await ctx.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        page.on('pageerror', lambda e: ERRORS.append(str(e)))
        page.on('console', lambda m: WARNS.append(f'{m.type}:{m.text[:160]}') if m.type in ('error','warning') else None)

        # ===== AUD01 : fresh load (with opening cinematic) — use SEPARATE context =====
        log('\n=== AUD01 : 1er load fresh (opening + splash) ===')
        ctx2 = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page1 = await ctx2.new_page()
        page1.on('pageerror', lambda e: ERRORS.append(str(e)))
        await ctx2.add_init_script("try { localStorage.clear(); } catch(e){}")
        await page1.goto(URL, wait_until='domcontentloaded')
        await page1.wait_for_timeout(1200)  # mid-cinematic
        await page1.screenshot(path=f'{OUT_DIR}/AUDIT-AUD01.png', clip={'x':0,'y':0,'width':540,'height':960})
        try:
            dom01 = await page1.evaluate(DOM_CHECK_JS)
        except Exception:
            dom01 = {'overflows':[],'badText':[],'stuckModals':[],'hidden':[],'topZ':[]}
        items = record_anomalies('AUD01', dom01, 0, 0)
        if items:
            for it in items: log(f'  - {it}')
        else:
            log('  OK — no anomaly')
        await ctx2.close()

        # ===== Setup main page (opening dismissed, story dismissed) =====
        await goto_clean(page)

        # ===== AUD02..17 =====
        await scenario_run(page, 'AUD02', 'km 0, totalTaps=0',
            setup_kw={'lapsRun': 0, 'lapProgress': 0, 'totalTaps': 0, 'gold': 0})

        await scenario_run(page, 'AUD03', 'km 0, totalTaps=10',
            setup_kw={'lapsRun': 0, 'lapProgress': 0, 'totalTaps': 10, 'gold': 50})

        await scenario_run(page, 'AUD04', 'km 3 (AUTO-COURSE unlock)',
            setup_kw={'lapsRun': 3, 'lapProgress': 50, 'totalTaps': 100, 'gold': 1000})

        await scenario_run(page, 'AUD05', 'km 10 (banlieue)',
            setup_kw={'lapsRun': 10, 'lapProgress': 200, 'totalTaps': 400, 'gold': 8000})

        await scenario_run(page, 'AUD06', 'km 30 (urbain)',
            setup_kw={'lapsRun': 30, 'lapProgress': 200, 'totalTaps': 1500, 'gold': 80000})

        await scenario_run(page, 'AUD07', 'km 55 (approche stade)',
            setup_kw={'lapsRun': 55, 'lapProgress': 200, 'totalTaps': 4000, 'gold': 1000000, 'gems': 100, 'alchLevel': 15})

        await scenario_run(page, 'AUD08', 'km 70 (stade en vue)',
            setup_kw={'lapsRun': 70, 'lapProgress': 200, 'totalTaps': 7000, 'gold': 5000000, 'gems': 200})

        await scenario_run(page, 'AUD09', 'km 95 (halo héros + godrays)',
            setup_kw={'lapsRun': 95, 'lapProgress': 300, 'totalTaps': 10000, 'gold': 50000000, 'gems': 500})

        await scenario_run(page, 'AUD10', 'km 100 (avant ascension)',
            setup_kw={'lapsRun': 100, 'lapProgress': 0, 'totalTaps': 12000, 'gold': 100000000})

        await scenario_run(page, 'AUD11', 'km 105 chapitre 2 lunaire',
            setup_kw={'lapsRun': 105, 'lapProgress': 300, 'totalTaps': 15000, 'chapter': 2, 'gold': 200000000})

        # Reset chapter for next scenarios
        await page.evaluate('STATE.chapter = 1; STATE.lapsRun = 10; STATE.lapProgress = 100;')
        await page.wait_for_timeout(300)

        await scenario_run(page, 'AUD12', 'Skills bar SPRINT actif (1 banner)',
            setup_kw={'lapsRun': 10, 'lapProgress': 100, 'totalTaps': 500},
            post_js="if(typeof activateSkill==='function'){ activateSkill('sprint'); }"
        )

        await scenario_run(page, 'AUD13', 'Skills bar SPRINT + VENT (2 banners empilés)',
            setup_kw={'lapsRun': 10, 'lapProgress': 100, 'totalTaps': 500},
            post_js="""
              if(typeof activateSkill==='function'){
                STATE.skillsLastUsed = {};
                activateSkill('sprint');
                setTimeout(()=>activateSkill('tailwind'), 100);
              }
            """
        )
        # Need more wait for second skill
        await page.wait_for_timeout(400)
        await screenshot(page, 'AUD13')  # re-screenshot after delay
        try:
            dom13 = await page.evaluate(DOM_CHECK_JS)
        except Exception:
            dom13 = {'overflows':[],'badText':[],'stuckModals':[],'hidden':[],'topZ':[]}
        # Also probe banner count
        banner_info = await page.evaluate(r"""
          (() => {
            const list = [...document.querySelectorAll('.skill-active-banner')].map(b => {
              const cs = getComputedStyle(b);
              const r = b.getBoundingClientRect();
              return {top: cs.top, right: cs.right, skill: b.getAttribute('data-skill'), y: Math.round(r.top), h: Math.round(r.height)};
            });
            return {count: list.length, banners: list};
          })()
        """)
        log(f'  banners visibles : {banner_info["count"]}')
        for b in banner_info['banners']:
            log(f'    - {b["skill"]} top={b["top"]} y={b["y"]} h={b["h"]}')
        if banner_info['count'] < 2:
            ANOMALIES.setdefault('AUD13', []).append(f'EXPECTED 2 banners, got {banner_info["count"]}')

        await scenario_run(page, 'AUD14', 'Drawer team ouvert (menu-modal)',
            setup_kw={'lapsRun': 20, 'lapProgress': 100},
            open_overlay='document.getElementById("menu-toggle")?.click();'
        )

        await scenario_run(page, 'AUD15', 'Drawer profile ouvert',
            setup_kw={'lapsRun': 20, 'lapProgress': 100},
            open_overlay='if(typeof openRunnerProfile==="function") openRunnerProfile(); else document.getElementById("runner-profile-modal")?.classList.add("show");'
        )

        await scenario_run(page, 'AUD16', 'Lapin spawned',
            setup_kw={'lapsRun': 10, 'lapProgress': 100},
            post_js="if(typeof window.SPAWN_RABBIT==='function') window.SPAWN_RABBIT();"
        )

        await scenario_run(page, 'AUD17', 'Lievre spawned',
            setup_kw={'lapsRun': 20, 'lapProgress': 100},
            post_js="if(typeof window.SPAWN_HARE==='function') window.SPAWN_HARE();"
        )

        await ctx.close()

        # ===== Opening cinematic special check =====
        await opening_cinematic_check(p)

        await browser.close()

    # ===== WRITE REPORT =====
    ok_count = sum(1 for k, v in ANOMALIES.items() if not v)
    total = len(ANOMALIES)

    # Top 5 console errors/warnings
    console_top = (ERRORS[:5] + WARNS[:5])[:5]

    lines = []
    lines.append('# AUDIT FINAL FOULÉE — 17 scénarios')
    lines.append('')
    lines.append(f'**Score : {ok_count}/{total} scénarios OK**')
    lines.append('')
    lines.append('## Récap par scénario')
    lines.append('')
    for sid in sorted(ANOMALIES.keys()):
        items = ANOMALIES[sid]
        status = 'OK' if not items else f'{len(items)} anomalies'
        lines.append(f'### {sid} — {status}')
        if items:
            for it in items:
                lines.append(f'  - {it}')
        lines.append('')

    lines.append('## Top erreurs console')
    lines.append('')
    if console_top:
        for e in console_top:
            lines.append(f'- `{e[:240]}`')
    else:
        lines.append('- (aucune erreur capturée)')
    lines.append('')

    lines.append(f'**Total console errors capturés** : {len(ERRORS)} pageerrors + {len(WARNS)} console.warn/error')
    lines.append('')

    lines.append('## Verdict logo opening cinematic')
    lines.append('')
    visible_count = 0
    total_samples = 3
    for o in OPENING_OBS:
        if 'verdict_visible_count' in o:
            visible_count = o['verdict_visible_count']
            total_samples = o['total']
            break
    verdict = 'OK' if visible_count >= 2 else ('BUG CONFIRMÉ' if visible_count == 0 else 'partiel')
    lines.append(f'**Verdict : {verdict}** — logo visible (opacity > 0.5, display!=none, width>20) à {visible_count}/{total_samples} samples')
    lines.append('')
    for o in OPENING_OBS:
        if 'verdict_visible_count' in o:
            continue
        i = o['info']
        if not i.get('present', False):
            lines.append(f'- T={o["t"]}s : pas de `.oc-logo` dans le DOM')
        else:
            lines.append(f'- T={o["t"]}s : text="{i.get("text","")[:20]}" opacity={i.get("opacity","?")} display={i.get("display","?")} size={i.get("width","?")}x{i.get("height","?")}')
    lines.append('')

    # Recommandations
    lines.append('## Recommandations prioritaires')
    lines.append('')
    recs = []
    # Look for systematic overflows
    overflow_count = sum(1 for v in ANOMALIES.values() for it in v if 'OVERFLOW' in it)
    badtxt_count = sum(1 for v in ANOMALIES.values() for it in v if 'BAD-TEXT' in it)
    modal_stuck = sum(1 for v in ANOMALIES.values() for it in v if 'MODAL-OPEN' in it)
    if visible_count < 2:
        recs.append('FIX opening logo : `.oc-logo` invisible — vérifier @keyframes ocLogoIn opacity finale + animation-fill-mode forwards.')
    if overflow_count > 0:
        recs.append(f'FIX overflows horizontaux ({overflow_count} occurrences) — ajouter `max-width:100%` ou `overflow-x:hidden` sur les conteneurs incriminés.')
    if badtxt_count > 0:
        recs.append(f'FIX undefined/NaN/null visibles ({badtxt_count}) — `?? "0"` ou guard `typeof v === "undefined"` autour des templates.')
    if modal_stuck > 3:
        recs.append(f'FIX modals stuck ({modal_stuck} occurrences) — auditer les .modal.show qui restent ouvertes entre scénarios.')
    if not recs:
        recs.append('RAS — pas de bug majeur détecté, audit OK.')
    for r in recs[:3]:
        lines.append(f'1. {r}')
    lines.append('')

    with open(f'{OUT_DIR}/audit-final-report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    log(f'\n[DONE] Report écrit : {OUT_DIR}/audit-final-report.md')
    log(f'Score : {ok_count}/{total} OK')

asyncio.run(main())
