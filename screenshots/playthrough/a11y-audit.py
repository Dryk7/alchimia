"""AUDIT A11Y FOULÉE — screenshots a11y-dark, a11y-large, contraste, tab-order.
Génère D:/alchimia/screenshots/playthrough/A11Y-*.png + a11y-report.json
"""
import asyncio, io, sys, json
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

# Contraste relatif WCAG
CONTRAST_JS = r"""
(()=>{
  function lum(rgb){
    const [r,g,b] = rgb.map(c => {
      c = c/255;
      return c <= 0.03928 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4);
    });
    return 0.2126*r + 0.7152*g + 0.0722*b;
  }
  function parseRGB(s){
    const m = s.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    return m ? [+m[1], +m[2], +m[3]] : null;
  }
  function ratio(c1, c2){
    const L1 = lum(c1), L2 = lum(c2);
    const a = Math.max(L1,L2), b = Math.min(L1,L2);
    return (a+0.05)/(b+0.05);
  }
  // Trouver bg réel (remonte parents jusqu'à trouver un opaque)
  function effectiveBG(el){
    let cur = el;
    while(cur){
      const cs = getComputedStyle(cur);
      const c = parseRGB(cs.backgroundColor);
      const al = cs.backgroundColor.includes('rgba') ? parseFloat(cs.backgroundColor.split(',')[3]) : 1;
      if(c && al > 0.5) return c;
      cur = cur.parentElement;
    }
    return [255,255,255];
  }

  const targets = [
    {sel:'#gold-val', desc:'HUD Gouttes value'},
    {sel:'#stars-val', desc:'HUD Stars value'},
    {sel:'.stat-lbl', desc:'HUD label (8-9px)'},
    {sel:'#runner-pace', desc:'Runner pace number'},
    {sel:'.tab-btn', desc:'Tab button (inactive)'},
    {sel:'.tab-btn.active', desc:'Tab button (active)'},
    {sel:'.jump-btn-float span', desc:'Jump btn label SAUT'},
    {sel:'.modal-close', desc:'Modal close X'},
    {sel:'.upg-name', desc:'Upgrade button name'},
    {sel:'.upg-cost', desc:'Upgrade cost label'},
    {sel:'.skill-btn::after', desc:'Skill btn label (7px)', skipPseudo:true},
    {sel:'.skill-btn.cooldown', desc:'Skill cooldown state', cdState:true},
  ];

  const out = [];
  for(const t of targets){
    const el = document.querySelector(t.sel.replace('::after',''));
    if(!el){ out.push({...t, found:false}); continue; }
    const cs = getComputedStyle(el);
    const fg = parseRGB(cs.color);
    const bg = effectiveBG(el);
    if(!fg){ out.push({...t, found:true, fg:cs.color, bg:'?', ratio:null}); continue; }
    const r = ratio(fg, bg);
    const fs = parseFloat(cs.fontSize);
    const fw = cs.fontWeight;
    const isLarge = fs >= 18 || (fs >= 14 && parseInt(fw)>=700);
    const requirement = isLarge ? 3.0 : 4.5;
    out.push({
      desc: t.desc,
      sel: t.sel,
      found: true,
      color: cs.color,
      bg: 'rgb('+bg.join(',')+')',
      fontSize: cs.fontSize,
      fontWeight: cs.fontWeight,
      ratio: Math.round(r*100)/100,
      requiredAA: requirement,
      passAA: r >= requirement,
      passAAA: r >= (isLarge ? 4.5 : 7.0),
    });
  }
  return out;
})()
"""

# Audit boutons taille touch
TOUCH_JS = r"""
(()=>{
  const sels = [
    '#menu-toggle',
    '.modal-close',
    '#jump-btn',
    '#daily-btn',
    '#boost-btn',
    '.tab-btn',
    '.skill-btn',
    '.upg-btn',
    '.menu-item',
    '#stat-gold',
    '#stat-gems',
    '#stat-stars',
    '#runner-avatar',
  ];
  const out = [];
  for(const sel of sels){
    const els = document.querySelectorAll(sel);
    for(const el of els){
      const r = el.getBoundingClientRect();
      if(r.width === 0 && r.height === 0) continue;
      out.push({
        sel,
        w: Math.round(r.width),
        h: Math.round(r.height),
        passGoogle48: r.width >= 48 && r.height >= 48,
        passAppleHIG44: r.width >= 44 && r.height >= 44,
      });
      break;
    }
  }
  return out;
})()
"""

# Audit ARIA / focus
ARIA_JS = r"""
(()=>{
  const buttons = document.querySelectorAll('button, [role="button"]');
  let total = 0, withAria = 0, withText = 0, withNeither = [];
  buttons.forEach(b => {
    if(getComputedStyle(b).display === 'none') return;
    total++;
    const al = b.getAttribute('aria-label');
    const txt = b.textContent.trim();
    if(al) withAria++;
    if(txt.length > 0) withText++;
    if(!al && txt.length === 0){
      withNeither.push((b.id||b.className||b.tagName).slice(0,60));
    }
  });
  // Modals
  const modals = document.querySelectorAll('.modal, .drawer');
  let modalsTotal = 0, modalsWithRole = 0, modalsLabelled = 0;
  modals.forEach(m => {
    modalsTotal++;
    if(m.getAttribute('role') === 'dialog') modalsWithRole++;
    if(m.getAttribute('aria-labelledby') || m.getAttribute('aria-label')) modalsLabelled++;
  });
  // aria-live
  const live = document.querySelectorAll('[aria-live]').length;
  // Focusable elements (tab order check)
  const focusables = document.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  let visibleFocusable = 0;
  focusables.forEach(f => {
    const cs = getComputedStyle(f);
    if(cs.display !== 'none' && cs.visibility !== 'hidden') visibleFocusable++;
  });
  return {
    buttonsTotal: total,
    buttonsWithAria: withAria,
    buttonsWithText: withText,
    buttonsWithoutAccessibleName: withNeither.length,
    sampleNoName: withNeither.slice(0, 10),
    modalsTotal,
    modalsWithRoleDialog: modalsWithRole,
    modalsLabelled,
    ariaLiveRegions: live,
    visibleFocusable,
  };
})()
"""

# Tab navigation : on tape Tab N fois et on note les focus
TAB_ORDER_JS = r"""
(()=>{
  // Trigger un focus visible diagnostic
  const focused = [];
  const all = document.querySelectorAll('button, [role="button"], a, input, select, textarea, [tabindex]');
  let n = 0;
  all.forEach(el => {
    const cs = getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden') return;
    if(el.disabled) return;
    n++;
    if(n <= 25){
      const r = el.getBoundingClientRect();
      focused.push({
        idx: n,
        tag: el.tagName,
        id: el.id||'',
        cls: (typeof el.className==='string'?el.className:'').slice(0,40),
        aria: el.getAttribute('aria-label')||'',
        x: Math.round(r.left), y: Math.round(r.top),
        w: Math.round(r.width), h: Math.round(r.height),
      });
    }
  });
  return { total: n, first25: focused };
})()
"""

REDUCED_MOTION_JS = r"""
(()=>{
  // Cherche les keyframes définies
  const animatedEls = [];
  document.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    if(cs.animationName && cs.animationName !== 'none'){
      animatedEls.push(cs.animationName);
    }
  });
  const unique = [...new Set(animatedEls)];
  return {
    animationsRunning: animatedEls.length,
    uniqueAnimations: unique.length,
    sample: unique.slice(0, 15),
  };
})()
"""

async def main():
    report = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={'width':390,'height':844},
            device_scale_factor=2,
        )
        page = await ctx.new_page()
        await page.add_init_script(SETUP_LS)
        await page.goto(URL, wait_until='networkidle')
        await page.wait_for_timeout(2000)
        await page.evaluate(CLOSE_MODALS_JS)
        await page.wait_for_timeout(500)

        # 1. Baseline screenshot
        await page.screenshot(path=f'{OUT_DIR}/A11Y-01-baseline.png', full_page=False)
        print('[OK] baseline')

        # 2. Aria audit
        report['aria'] = await page.evaluate(ARIA_JS)
        print('[OK] aria audit')

        # 3. Touch targets
        report['touch'] = await page.evaluate(TOUCH_JS)
        print('[OK] touch targets')

        # 4. Contraste baseline
        report['contrast_baseline'] = await page.evaluate(CONTRAST_JS)
        print('[OK] contrast baseline')

        # 5. Tab order
        report['tab_order'] = await page.evaluate(TAB_ORDER_JS)
        print('[OK] tab order')

        # 6. Reduced motion check
        report['motion'] = await page.evaluate(REDUCED_MOTION_JS)
        print('[OK] motion check')

        # 7. a11y-dark
        await page.evaluate('Accessibility.set("dark", true)')
        await page.wait_for_timeout(800)
        await page.screenshot(path=f'{OUT_DIR}/A11Y-02-dark.png', full_page=False)
        report['contrast_dark'] = await page.evaluate(CONTRAST_JS)
        print('[OK] a11y-dark')

        # 8. a11y-large (cumul avec dark)
        await page.evaluate('Accessibility.set("large", true)')
        await page.wait_for_timeout(500)
        await page.screenshot(path=f'{OUT_DIR}/A11Y-03-dark-large.png', full_page=False)
        print('[OK] a11y-large')

        # 9. Reset, juste a11y-large pour comparer
        await page.evaluate('Accessibility.set("dark", false)')
        await page.wait_for_timeout(500)
        await page.screenshot(path=f'{OUT_DIR}/A11Y-04-large-only.png', full_page=False)
        print('[OK] large-only')

        # 10. a11y-cb (color-blind) — ouvrir une zone avec hurdle markers si possible
        await page.evaluate('Accessibility.set("cb", true)')
        await page.wait_for_timeout(500)
        await page.screenshot(path=f'{OUT_DIR}/A11Y-05-cb.png', full_page=False)
        print('[OK] a11y-cb')

        # 11. Test Escape sur modal (ouvrir menu modal)
        await page.evaluate('Accessibility.set("large", false); Accessibility.set("cb", false);')
        await page.wait_for_timeout(300)
        # Ouvrir le menu modal
        try:
            menuOpened = await page.evaluate("""
              (()=>{
                const m = document.getElementById('menu-modal');
                if(m){ m.classList.add('show'); return true; }
                return false;
              })()
            """)
            if menuOpened:
                await page.wait_for_timeout(500)
                # Tester Escape
                escapeBefore = await page.evaluate("document.getElementById('menu-modal').classList.contains('show')")
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(400)
                escapeAfter = await page.evaluate("document.getElementById('menu-modal').classList.contains('show')")
                report['escape_closes_modal'] = {'before':escapeBefore, 'after':escapeAfter, 'works':(escapeBefore and not escapeAfter)}
                # screenshot if still open
                if escapeAfter:
                    await page.screenshot(path=f'{OUT_DIR}/A11Y-06-modal-no-escape.png', full_page=False)
                print(f"[OK] escape: works={report['escape_closes_modal']['works']}")
        except Exception as e:
            report['escape_closes_modal'] = {'error': str(e)}

        # 12. Tab key navigation — vérifier que un focus visible apparaît
        await page.evaluate("document.querySelectorAll('.modal.show').forEach(m=>m.classList.remove('show'))")
        await page.wait_for_timeout(300)
        await page.keyboard.press('Tab')
        await page.wait_for_timeout(200)
        firstFocus = await page.evaluate("""
          (()=>{
            const a = document.activeElement;
            if(!a) return null;
            return {tag:a.tagName, id:a.id, cls:(typeof a.className==='string'?a.className:'').slice(0,40), aria:a.getAttribute('aria-label')||''};
          })()
        """)
        # outline visible ?
        focusOutline = await page.evaluate("""
          (()=>{
            const a = document.activeElement;
            if(!a) return null;
            const cs = getComputedStyle(a);
            return {outline:cs.outline, outlineWidth:cs.outlineWidth, boxShadow:cs.boxShadow.slice(0,80)};
          })()
        """)
        report['tab_first_focus'] = firstFocus
        report['focus_visible_style'] = focusOutline
        await page.screenshot(path=f'{OUT_DIR}/A11Y-07-tab-focus.png', full_page=False)
        print(f"[OK] tab focus: {firstFocus}")

        await browser.close()

    # save report
    with open(f'{OUT_DIR}/a11y-report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print('\n=== REPORT saved ===')
    print(json.dumps({
        'aria': report.get('aria'),
        'escape': report.get('escape_closes_modal'),
        'tab_first': report.get('tab_first_focus'),
        'focus_style': report.get('focus_visible_style'),
        'motion_total': report.get('motion',{}).get('animationsRunning'),
    }, indent=2, ensure_ascii=False))

asyncio.run(main())
