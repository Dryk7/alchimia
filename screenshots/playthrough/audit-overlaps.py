"""
FOULÉE — Audit superpositions visuelles
Visite 6 états (km 0, 3, 10, 30, 70, 105 lunar) et identifie les éléments
HUD qui se chevauchent visuellement.
"""
import asyncio
import json
import sys
import io
from pathlib import Path
from playwright.async_api import async_playwright

# Force UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

STATES = [
    {"name": "km00",        "lapsRun": 0,   "totalKm": 0,    "chapter": 1, "extra": {}},
    {"name": "km03",        "lapsRun": 3,   "totalKm": 3,    "chapter": 1, "extra": {"upgradeAutoTap": 1}},
    {"name": "km10",        "lapsRun": 10,  "totalKm": 10,   "chapter": 1, "extra": {"upgradeAutoTap": 3, "upgradeTapValue": 4, "upgradeBaseSpeed": 2}},
    {"name": "km30",        "lapsRun": 30,  "totalKm": 30,   "chapter": 1, "extra": {"upgradeCruiseControl": 1, "upgradeAutoTap": 5, "upgradeBaseSpeed": 5}},
    {"name": "km70",        "lapsRun": 70,  "totalKm": 70,   "chapter": 1, "extra": {"upgradeCruiseControl": 8, "upgradeBaseSpeed": 10}},
    {"name": "km105_lunar", "lapsRun": 105, "totalKm": 105,  "chapter": 2, "extra": {"upgradeCruiseControl": 15, "upgradeBaseSpeed": 15}},
]

OVERLAP_JS = r"""
() => {
  const sels = [
    'header *',
    '.runner-hud-overlay *',
    '.tabs-strip *',
    '#skills-bar *',
    '.runner-bubble',
    '.tier-banner',
    '.skill-active-banner',
    '.jump-btn-float',
    '.daily-btn-float',
    '#boost-banner',
    '.save-toast',
    '.floating-pop',
    '.pace-pill',
    '.km-pill',
    '.gold-pill',
    '#runner-2d',
    '.idle-arrow',
    '.tap-hint',
    '.combo-display',
    '.runner-bottom-bar',
    '.dot-nav',
    '.stamina-bar',
    '.km-popup',
    '.skill-btn',
  ];
  const all = new Set();
  for(const s of sels){
    try { document.querySelectorAll(s).forEach(el => all.add(el)); } catch(e){}
  }
  const vw = window.innerWidth, vh = window.innerHeight;
  const visibles = [...all].filter(el => {
    const cs = getComputedStyle(el);
    if(cs.display === 'none' || cs.visibility === 'hidden') return false;
    if(parseFloat(cs.opacity) <= 0.3) return false;
    const r = el.getBoundingClientRect();
    if(r.width <= 5 || r.height <= 5) return false;
    if(r.bottom <= 0 || r.right <= 0 || r.top >= vh || r.left >= vw) return false;
    // Skip the giant canvas itself (always overlaps everything in front)
    if(el.tagName === 'CANVAS') return false;
    return true;
  });
  const tag = (el) => {
    let s = el.tagName.toLowerCase();
    if(el.id) s += '#' + el.id;
    if(el.className && typeof el.className === 'string'){
      const cls = el.className.split(/\s+/).filter(x=>x).slice(0,2).join('.');
      if(cls) s += '.' + cls;
    }
    return s;
  };
  const overlaps = [];
  for(let i = 0; i < visibles.length; i++){
    for(let j = i+1; j < visibles.length; j++){
      const a = visibles[i], b = visibles[j];
      if(a.contains(b) || b.contains(a)) continue;
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const overlap = !(ra.right <= rb.left || ra.left >= rb.right || ra.bottom <= rb.top || ra.top >= rb.bottom);
      if(!overlap) continue;
      const ox = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const oy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      const area = ox * oy;
      if(area <= 30) continue;
      const areaA = ra.width * ra.height;
      const areaB = rb.width * rb.height;
      const minArea = Math.min(areaA, areaB);
      const pct = minArea > 0 ? Math.round(100 * area / minArea) : 0;
      overlaps.push({
        a: tag(a),
        b: tag(b),
        area: Math.round(area),
        pct,
        a_rect: {x:Math.round(ra.x),y:Math.round(ra.y),w:Math.round(ra.width),h:Math.round(ra.height)},
        b_rect: {x:Math.round(rb.x),y:Math.round(rb.y),w:Math.round(rb.width),h:Math.round(rb.height)},
        a_text: (a.textContent || '').trim().slice(0, 30),
        b_text: (b.textContent || '').trim().slice(0, 30),
      });
    }
  }
  return overlaps.sort((x,y) => y.area - x.area).slice(0, 12);
}
"""

SETUP_JS = r"""
() => {
  localStorage.setItem("foulee.storySeen","1");
  localStorage.setItem("foulee.tutoV3","done");
  localStorage.setItem("foulee.activeTutoV1","done");
  localStorage.setItem("foulee.openingSeen","1");
  localStorage.setItem("foulee.dailySeen","1");
  localStorage.setItem("foulee.introSeen","1");
}
"""

async def apply_state(page, st):
    # Inject state directly
    extra_json = json.dumps(st["extra"])
    laps = st["lapsRun"]
    total = st["totalKm"]
    chap = st["chapter"]
    js = f"""
    () => {{
      if(!window.STATE) return false;
      window.STATE.lapsRun = {laps};
      window.STATE.totalKm = {total};
      window.STATE.lapProgress = 0;
      window.STATE.gold = 50000;
      window.STATE.totalTaps = 100;
      window.STATE.chapter = {chap};
      window.STATE.saison = {chap};
      const extra = {extra_json};
      for(const k in extra){{ window.STATE[k] = extra[k]; }}
      // Force redraw HUD
      try {{ if(typeof updateRunnerHUD === 'function') updateRunnerHUD(); }} catch(e){{}}
      try {{ if(typeof refreshKmHud === 'function') refreshKmHud(); }} catch(e){{}}
      return true;
    }}
    """
    return await page.evaluate(js)

async def close_modals(page):
    try:
        await page.evaluate("""() => {
          document.querySelectorAll('.modal-overlay, .modal-backdrop, [data-modal], .overlay-open').forEach(m => {
            m.style.display = 'none';
            m.classList.remove('open','visible','show','active');
          });
          document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
          // Close buttons
          document.querySelectorAll('button.close, .modal-close, [data-close]').forEach(b => {
            try { b.click(); } catch(e){}
          });
        }""")
    except Exception:
        pass

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 412, "height": 915})
        page = await ctx.new_page()

        # Console errors capture
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        # Pre-set localStorage by going to page, setting, then reload
        await page.goto("http://localhost:8770/", wait_until="domcontentloaded")
        await page.evaluate(SETUP_JS)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(800)

        # Try to click start button if present
        try:
            await page.click("#start-btn, .start-btn, button:has-text('PRENDRE')", timeout=2500)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        # Close any opening cinematic
        try:
            await page.evaluate("() => { if(window.OPENING_CINEMATIC) window.OPENING_CINEMATIC.skip && window.OPENING_CINEMATIC.skip(); }")
        except Exception:
            pass
        # Click to skip splash
        try:
            await page.click("body", position={"x": 200, "y": 400})
        except Exception:
            pass
        await page.wait_for_timeout(1200)

        all_results = {}
        for st in STATES:
            ok = await apply_state(page, st)
            await page.wait_for_timeout(600)
            await close_modals(page)
            await page.wait_for_timeout(400)
            # Trigger a fake "next tick" so canvas redraws + HUD updates
            await page.evaluate("""() => {
              try { if(window.dispatchEvent) window.dispatchEvent(new Event('resize')); } catch(e){}
            }""")
            await page.wait_for_timeout(500)

            overlaps = await page.evaluate(OVERLAP_JS)
            all_results[st["name"]] = {
                "applied": ok,
                "overlaps": overlaps,
            }
            shot_path = OUT_DIR / f"AUDIT-{st['name']}.png"
            await page.screenshot(path=str(shot_path), full_page=False)
            print(f"[{st['name']}] applied={ok}  overlaps={len(overlaps)}  -> {shot_path.name}")
            for o in overlaps[:5]:
                print(f"   {o['area']:>6}px2 ({o['pct']}%)  {o['a']}  <->  {o['b']}")
                if o.get("a_text"): print(f"      a_text: {o['a_text']!r}")
                if o.get("b_text"): print(f"      b_text: {o['b_text']!r}")

        # Save full JSON
        report_path = OUT_DIR / "AUDIT-overlaps.json"
        report_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport saved: {report_path}")
        if errors:
            print("\nConsole errors:")
            for e in errors[:5]:
                print(f"   ! {e[:200]}")

        await browser.close()
        return all_results

if __name__ == "__main__":
    results = asyncio.run(main())
    # Aggregate top overlaps
    print("\n========== TOP OVERLAPS (cross-state) ==========")
    flat = []
    for state, data in results.items():
        for o in data["overlaps"]:
            flat.append((state, o))
    flat.sort(key=lambda t: t[1]["area"], reverse=True)
    for state, o in flat[:8]:
        print(f"[{state}] {o['area']:>6}px2  {o['a']}  <->  {o['b']}")
