"""VISUAL AUDIT FINAL FOULÉE — 12 scénarios visuels distincts.
Capture screenshots + DOM checks (positions, overflows, invisibles) + console errors.
Génère D:/alchimia/screenshots/playthrough/VAUDIT-*.png + visual-audit-report.md
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

# Comprehensive DOM visual check :
# - off-screen visible elements (top<-20, top>970, left<-20, right>560)
# - "invisible but takes space" (opacity~0 with width/height>0 AND not in keyframe transition)
# - overlapping HUD elements
# - undefined/NaN visible text
# - z-index stacking (informational)
DOM_CHECK_JS = r"""
(()=>{
  const out = {
    offscreenVisible: [],
    invisibleNonZero: [],
    overflowX: [],
    badText: [],
    weirdPos: [],
    topZ: [],
    hudInfo: {}
  };
  const VW = 540, VH = 960;

  // Helper : detect ancestor that's intentionally off-screen (drawer not open, modal not show, etc.)
  function inHiddenContainer(el){
    let p = el;
    while(p && p !== document.body){
      const cls = (typeof p.className === 'string') ? p.className : '';
      const id = p.id || '';
      // closed drawer
      if (p.classList && p.classList.contains('drawer') && !p.classList.contains('open')) return true;
      // closed modal
      if (p.classList && p.classList.contains('modal') && !p.classList.contains('show')) return true;
      // tab pane not active
      if (p.classList && p.classList.contains('tab-pane') && !p.classList.contains('active')) return true;
      // template / cinematic / hidden helper
      if (cls.includes && (cls.includes('template') || cls.includes('hidden-helper'))) return true;
      if (id === 'opening-cinematic' || id === 'story-overlay') return true;
      p = p.parentElement;
    }
    return false;
  }

  document.querySelectorAll('body *').forEach(el => {
    if (!el || el.children.length > 200) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;

    const id = el.id || '';
    const cls = (typeof el.className === 'string') ? el.className : '';
    const tag = el.tagName;

    // skip if inside a deliberately-off-screen container (closed drawer/modal/inactive tab)
    if (inHiddenContainer(el)) return;

    // 1. visible-ish element OFF-SCREEN (top<-30 or top>VH or right<0 or left>VW)
    const op = parseFloat(cs.opacity);
    if (cs.visibility !== 'hidden' && op > 0.05) {
      if ((r.top < -40 || r.top > VH + 40 || r.right < -10 || r.left > VW + 10)
          && r.width < VW * 1.5 && r.height < VH * 1.5
          && !id.includes('cinematic')
          && !cls.includes('hidden')
          && !cls.includes('cinematic')
          && !cls.includes('toast')) {
        out.offscreenVisible.push({
          tag, id, cls: cls.toString().slice(0,40),
          top: Math.round(r.top), left: Math.round(r.left),
          w: Math.round(r.width), h: Math.round(r.height),
          op: op.toFixed(2)
        });
      }
    }

    // 2. opacity ~0 but display:block/inline with dims (probably leftover)
    if (op < 0.05 && (cs.display === 'block' || cs.display === 'inline-block' || cs.display === 'flex')
        && r.width > 10 && r.height > 10
        && r.top >= -10 && r.top < VH
        && cs.transition === 'all 0s ease 0s'  // not animating
        && !id.includes('toast') && !id.includes('banner')
        && !cls.includes('toast') && !cls.includes('banner')
        && !cls.includes('flash')) {
      out.invisibleNonZero.push({
        tag, id, cls: cls.toString().slice(0,40),
        top: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)
      });
    }

    // 3. overflow X
    if (r.right > VW + 4 && r.width > 4 && r.width < VW * 1.3 && op > 0.05) {
      out.overflowX.push({tag, id, cls: cls.toString().slice(0,40), right: Math.round(r.right), w: Math.round(r.width)});
    }

    // 4. z-index >= 1000 (informational)
    const z = parseInt(cs.zIndex, 10);
    if (!isNaN(z) && z >= 1000) {
      out.topZ.push({id: id || tag, z, cls: cls.toString().slice(0,30)});
    }
  });

  // 5. Bad text undefined/NaN visible
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  const bad = /\b(undefined|NaN|null)\b/;
  while((n = walker.nextNode())){
    const t = n.textContent;
    if(!t || !bad.test(t)) continue;
    const p = n.parentElement;
    if(!p) continue;
    const cs = getComputedStyle(p);
    if(cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = p.getBoundingClientRect();
    if(r.width === 0 || r.height === 0) continue;
    out.badText.push({
      tag: p.tagName, id: p.id || '',
      cls: (typeof p.className === 'string' ? p.className.slice(0,40) : ''),
      text: t.trim().slice(0, 80)
    });
  }

  // 6. HUD presence/positions
  ['hud-top','hud-bottom','tap-zone','runner','sky','ground','status-strip',
   'gold-display','km-display','combo-display','tap-counter'].forEach(eid => {
    const el = document.getElementById(eid);
    if (el){
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      out.hudInfo[eid] = {
        top: Math.round(r.top), left: Math.round(r.left),
        w: Math.round(r.width), h: Math.round(r.height),
        display: cs.display, op: cs.opacity, vis: cs.visibility
      };
    }
  });

  // 7. dedupe/limit
  out.offscreenVisible = out.offscreenVisible.slice(0, 12);
  out.invisibleNonZero = out.invisibleNonZero.slice(0, 8);
  out.overflowX = out.overflowX.slice(0, 8);
  out.badText = out.badText.slice(0, 8);
  out.topZ = out.topZ.sort((a,b) => b.z - a.z).slice(0, 8);

  return out;
})()
"""

REPORT = []
def log(msg=''):
    print(msg)
    REPORT.append(msg)

ERRORS = []
WARNS = []
ANOMALIES = {}  # scn_id -> list

async def screenshot(page, name):
    await page.screenshot(path=f'{OUT_DIR}/VAUDIT-{name}.png', clip={'x':0,'y':0,'width':540,'height':960})

async def setup_state(page, **kwargs):
    js = ''
    for k, v in kwargs.items():
        js += f'STATE["{k}"] = {json.dumps(v)};'
    js += CLOSE_MODALS_JS
    await page.evaluate(js)

async def goto_clean(page):
    await page.goto(URL, wait_until='domcontentloaded')
    await page.evaluate(SETUP_LS)
    await page.reload()
    await page.wait_for_load_state('networkidle')
    await page.wait_for_timeout(500)
    try:
        await page.evaluate('document.getElementById("start-btn")?.click();')
        await page.wait_for_timeout(400)
    except Exception:
        pass
    await page.evaluate(CLOSE_MODALS_JS)
    await page.wait_for_timeout(250)

def record(scn_id, dom, err_before):
    items = []
    for o in dom.get('offscreenVisible', []):
        items.append(f"OFFSCREEN {o['tag']}#{o['id']}.{o['cls']} top={o['top']} left={o['left']} {o['w']}x{o['h']} op={o['op']}")
    for o in dom.get('invisibleNonZero', []):
        items.append(f"INVIS-NONZERO {o['tag']}#{o['id']}.{o['cls']} top={o['top']} {o['w']}x{o['h']}")
    for o in dom.get('overflowX', []):
        items.append(f"OVERFLOW-X {o['tag']}#{o['id']}.{o['cls']} right={o['right']} w={o['w']}")
    for o in dom.get('badText', []):
        items.append(f"BAD-TEXT {o['tag']}#{o['id']}: '{o['text']}'")
    new_err = (len(ERRORS) + len(WARNS)) - err_before
    if new_err > 0:
        items.append(f"+{new_err} console errors/warnings")
    ANOMALIES[scn_id] = items
    return items

async def scenario(page, scn_id, title, setup_kw, post_js=None, wait_ms=600):
    log(f'\n=== {scn_id} : {title} ===')
    err_before = len(ERRORS) + len(WARNS)
    await setup_state(page, **setup_kw)
    if post_js:
        try:
            await page.evaluate(post_js)
        except Exception as e:
            log(f'  post_js err: {str(e)[:140]}')
    await page.wait_for_timeout(wait_ms)
    await screenshot(page, scn_id)
    try:
        dom = await page.evaluate(DOM_CHECK_JS)
    except Exception as e:
        log(f'  DOM err: {str(e)[:160]}')
        dom = {}
    items = record(scn_id, dom, err_before)
    if items:
        log(f'  {len(items)} anomalies:')
        for it in items[:8]:
            log(f'    - {it}')
        if len(items) > 8:
            log(f'    (+{len(items)-8} more)')
    else:
        log('  OK')
    # log HUD info snapshot for posterity (1-line)
    if dom.get('hudInfo'):
        hud = dom['hudInfo']
        if 'hud-top' in hud:
            h = hud['hud-top']
            log(f'  hud-top: top={h["top"]} {h["w"]}x{h["h"]} disp={h["display"]} op={h["op"]}')
    await page.evaluate(CLOSE_MODALS_JS)
    await page.wait_for_timeout(150)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        page.on('pageerror', lambda e: ERRORS.append(str(e)[:240]))
        page.on('console', lambda m: WARNS.append(f'{m.type}:{m.text[:200]}') if m.type in ('error','warning') else None)

        await goto_clean(page)

        # 12 scenarios
        await scenario(page, 'V01', 'km 0 fresh (totalTaps=0)',
            setup_kw={'lapsRun': 0, 'lapProgress': 0, 'totalTaps': 0, 'gold': 0, 'gems': 0, 'alchLevel': 1})

        await scenario(page, 'V02', 'km 1 (warm up, totalTaps=50)',
            setup_kw={'lapsRun': 1, 'lapProgress': 100, 'totalTaps': 50, 'gold': 200, 'gems': 0, 'alchLevel': 1})

        await scenario(page, 'V03', 'km 3 (AUTO-COURSE unlock)',
            setup_kw={'lapsRun': 3, 'lapProgress': 80, 'totalTaps': 150, 'gold': 1500, 'gems': 5, 'alchLevel': 2})

        await scenario(page, 'V04', 'km 8 (1ere haie / hurdles)',
            setup_kw={'lapsRun': 8, 'lapProgress': 60, 'totalTaps': 350, 'gold': 5000, 'gems': 10, 'alchLevel': 3})

        await scenario(page, 'V05', 'km 15 (banlieue active)',
            setup_kw={'lapsRun': 15, 'lapProgress': 100, 'totalTaps': 600, 'gold': 15000, 'gems': 20, 'alchLevel': 5})

        await scenario(page, 'V06', 'km 30 (urbain dense)',
            setup_kw={'lapsRun': 30, 'lapProgress': 200, 'totalTaps': 1500, 'gold': 80000, 'gems': 50, 'alchLevel': 8})

        await scenario(page, 'V07', 'km 50 (route vers stade)',
            setup_kw={'lapsRun': 50, 'lapProgress': 150, 'totalTaps': 3000, 'gold': 500000, 'gems': 100, 'alchLevel': 12})

        await scenario(page, 'V08', 'km 70 (stade visible)',
            setup_kw={'lapsRun': 70, 'lapProgress': 200, 'totalTaps': 6000, 'gold': 3000000, 'gems': 200, 'alchLevel': 16})

        await scenario(page, 'V09', 'km 85 (champion T6)',
            setup_kw={'lapsRun': 85, 'lapProgress': 250, 'totalTaps': 9000, 'gold': 20000000, 'gems': 350, 'alchLevel': 20})

        await scenario(page, 'V10', 'km 95 (god rays + halo)',
            setup_kw={'lapsRun': 95, 'lapProgress': 300, 'totalTaps': 11000, 'gold': 60000000, 'gems': 500, 'alchLevel': 23})

        await scenario(page, 'V11', 'km 100 (avant ascension)',
            setup_kw={'lapsRun': 100, 'lapProgress': 50, 'totalTaps': 13000, 'gold': 120000000, 'gems': 700, 'alchLevel': 25})

        await scenario(page, 'V12', 'km 105 (chapitre 2 lunaire)',
            setup_kw={'lapsRun': 105, 'lapProgress': 200, 'totalTaps': 16000, 'gold': 250000000, 'gems': 900, 'alchLevel': 28, 'chapter': 2})

        await ctx.close()
        await browser.close()

    # Summary
    log('\n\n========== SUMMARY ==========')
    total = len(ANOMALIES)
    ok = sum(1 for v in ANOMALIES.values() if not v)
    log(f'Scenarios OK: {ok}/{total}')

    # Aggregate counts
    counts = {'OFFSCREEN':0, 'INVIS-NONZERO':0, 'OVERFLOW-X':0, 'BAD-TEXT':0, 'console':0}
    for v in ANOMALIES.values():
        for it in v:
            for k in counts:
                if k in it:
                    counts[k] += 1
                    break
            else:
                if 'console' in it:
                    counts['console'] += 1
    log(f'Counts: {counts}')
    log(f'Total console errors: {len(ERRORS)} pageerror, {len(WARNS)} warn/error')

    # Write report
    lines = []
    lines.append('# VISUAL AUDIT FOULÉE — 12 scénarios')
    lines.append('')
    lines.append(f'**Score: {ok}/{total} scénarios sans anomalie**')
    lines.append('')
    lines.append('## Récap par scénario')
    for sid in sorted(ANOMALIES.keys()):
        v = ANOMALIES[sid]
        lines.append(f'### {sid} ({len(v)} anomalies)')
        if not v:
            lines.append('- OK')
        else:
            for it in v[:15]:
                lines.append(f'- {it}')
        lines.append('')
    lines.append('## Erreurs console top 10')
    for e in (ERRORS[:6] + WARNS[:6])[:10]:
        lines.append(f'- `{e[:240]}`')
    lines.append('')
    lines.append(f'**Aggregated**: {counts}')

    with open(f'{OUT_DIR}/visual-audit-report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    log(f'\n[DONE] {OUT_DIR}/visual-audit-report.md')

asyncio.run(main())
