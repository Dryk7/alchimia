"""
QA Lunar - Playthrough post-ascension km 100+ (chapitre 2 / biome lunaire).
Tests :
  - Forcer STATE post-ascension (km 105/130/150)
  - Capturer visuels biome lunaire
  - Comparer aux paliers stade km 50, 80, 99
  - Inspecter NPCs spawnés
  - Mesurer drop rate coffres
  - Vérifier achievements post-100
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
OUT = "D:/alchimia/screenshots/qa-vague10"

LOCALSTORAGE_SETUP = """
() => {
  // marque onboarding done (tuto + active tuto)
  localStorage.setItem('foulee.activeTutoV1', 'done');
  localStorage.setItem('foulee.tutoV3', JSON.stringify({skip:true}));
  localStorage.setItem('foulee.introSeen', '1');
  localStorage.setItem('foulee.openingShown', '1');
  localStorage.setItem('foulee.introSplashShown', '1');
  localStorage.removeItem('alchimia.save'); // clean
  return true;
}
"""

FORCE_STATE = """
(km) => {
  if(!window.STATE){ return {err: 'no STATE'}; }
  window.STATE.gold = 1e9;
  window.STATE.lapsRun = km;
  window.STATE.ascensions = 1;
  window.STATE.totalStars = 10;
  window.STATE.stars = 10;
  window.STATE.saison = 2; // 2e saison post-ascension
  window.STATE.chapter = 2;
  window.STATE.alchLevel = 25;
  window.STATE.runnerStamina = 1.5;
  window.STATE.lapProgress = 0;
  // chest counters pour vérifier drop post-100
  if(!window.STATE.chests) window.STATE.chests = {wood:0, iron:0, gold:0, legendary:0};
  return {ok:true, km: window.STATE.lapsRun, saison: window.STATE.saison, biome: (typeof currentBiome === 'function') ? currentBiome() : 'NO_FN'};
}
"""

INSPECT_STATE = """
() => {
  const s = window.STATE || {};
  const rd = window.RUNNER_2D || {};
  let stageBiome = null;
  try { stageBiome = (typeof currentBiome === 'function') ? currentBiome() : null; } catch(e){}
  // NPCs spawnés
  let npcInfo = null;
  try {
    const npcsArr = (rd._dbg && rd._dbg.npcs) || (typeof getNpcs === 'function' ? getNpcs() : null);
    if(npcsArr && npcsArr.length){
      npcInfo = npcsArr.map(n => ({tier:n.tier, label:n.tierLabel, flagColors: n.flagColors ? 'YES' : null}));
    }
  } catch(e){ npcInfo = 'err:' + e.message; }
  // Coffres
  const chests = s.chests || {};
  // Cinematic flags
  return {
    km: s.lapsRun,
    saison: s.saison,
    chapter: s.chapter,
    biome: stageBiome,
    gold: s.gold,
    stars: s.stars,
    ascensions: s.ascensions,
    chests: chests,
    upgradeTapValue: s.upgradeTapValue,
    achievements: Object.keys(s.achievements || {}).length,
  };
}
"""

GET_BGM_PRESET = """
() => {
  if(!window.ProcBGM) return null;
  return window.ProcBGM.currentPreset ? window.ProcBGM.currentPreset() : null;
}
"""

# Force le re-render du canvas en simulant un tap silencieux
TRIGGER_RENDER = """
() => {
  // Trigger un updateRunnerHUD et renderStats pour push state
  try { if(typeof updateRunnerHUD === 'function') updateRunnerHUD(); } catch(e){}
  try { if(typeof renderStats === 'function') renderStats(); } catch(e){}
  // Force scroll decor pour debug : pousse decorScroll
  if(window.RUNNER_2D && window.RUNNER_2D.resize) window.RUNNER_2D.resize();
  return true;
}
"""

CHECK_LUNAR_OBSTACLES = """
() => {
  // Inspecte les hurdles en cours pour voir si pattern 'crater' apparaît
  let pattern = null;
  try {
    const arr = (window.RUNNER_2D && window.RUNNER_2D.getHurdles) ? window.RUNNER_2D.getHurdles() : null;
    if(arr) pattern = arr.map(h => h.kind);
  } catch(e){}
  return { hurdles: pattern };
}
"""

TAP_STADIUM = """
async (n) => {
  const stage = document.getElementById('runner-stadium');
  if(!stage) return false;
  const rect = stage.getBoundingClientRect();
  const cx = rect.left + rect.width/2;
  const cy = rect.top + rect.height/2;
  // Dispatch pointerdown events directement
  for(let i=0; i<n; i++){
    const ev = new PointerEvent('pointerdown', {clientX: cx, clientY: cy, bubbles: true, pointerType:'touch'});
    stage.dispatchEvent(ev);
    await new Promise(r => setTimeout(r, 100));
  }
  return true;
}
"""

async def main():
    os.makedirs(OUT, exist_ok=True)
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = await ctx.new_page()

        # Capture console errors
        console_errors = []
        page.on('console', lambda msg: console_errors.append(f'[{msg.type}] {msg.text}') if msg.type in ('error', 'warning') else None)
        page.on('pageerror', lambda err: console_errors.append(f'[pageerror] {err}'))

        # Boot
        await page.goto(URL, wait_until='networkidle')
        await page.evaluate(LOCALSTORAGE_SETUP)
        await page.reload(wait_until='networkidle')

        # Wait for STATE to be available
        await page.wait_for_function("window.STATE !== undefined", timeout=10000)
        # Dismiss intro if blocking
        await page.evaluate("""
          () => {
            const intro = document.getElementById('intro');
            if(intro) intro.style.display = 'none';
            const opening = document.getElementById('opening-cinematic');
            if(opening) opening.style.display = 'none';
            const splash = document.getElementById('intro-splash');
            if(splash) splash.style.display = 'none';
          }
        """)

        await asyncio.sleep(1.0)

        # === Test 1 : km 50 (baseline urban→stadium) pour comparaison
        out = await page.evaluate(FORCE_STATE, 50)
        await page.evaluate(TRIGGER_RENDER)
        await asyncio.sleep(2.0)
        bgm50 = await page.evaluate(GET_BGM_PRESET)
        state50 = await page.evaluate(INSPECT_STATE)
        await page.screenshot(path=f"{OUT}/01-km50-baseline-stadium.png")
        results.append({'km': 50, 'state': state50, 'bgm': bgm50})

        # === Test 2 : km 99 — apothéose vasque
        await page.evaluate(FORCE_STATE, 99)
        await page.evaluate(TRIGGER_RENDER)
        await asyncio.sleep(2.0)
        bgm99 = await page.evaluate(GET_BGM_PRESET)
        state99 = await page.evaluate(INSPECT_STATE)
        await page.screenshot(path=f"{OUT}/02-km99-vasque.png")
        results.append({'km': 99, 'state': state99, 'bgm': bgm99})

        # === Test 3 : km 105 — début lunaire
        await page.evaluate(FORCE_STATE, 105)
        await page.evaluate(TRIGGER_RENDER)
        await asyncio.sleep(3.0)
        bgm105 = await page.evaluate(GET_BGM_PRESET)
        state105 = await page.evaluate(INSPECT_STATE)
        await page.screenshot(path=f"{OUT}/03-km105-lunar-debut.png", full_page=False)
        # Tap quelques fois pour spawner des NPC et hurdles
        await page.evaluate(TAP_STADIUM, 20)
        await asyncio.sleep(3.0)
        await page.screenshot(path=f"{OUT}/03b-km105-after-taps.png")
        state105b = await page.evaluate(INSPECT_STATE)
        results.append({'km': 105, 'state': state105, 'state_after_taps': state105b, 'bgm': bgm105})

        # === Test 4 : km 130 — exploration profonde lunar
        await page.evaluate(FORCE_STATE, 130)
        await page.evaluate(TRIGGER_RENDER)
        await asyncio.sleep(3.0)
        state130 = await page.evaluate(INSPECT_STATE)
        await page.screenshot(path=f"{OUT}/04-km130-lunar-mid.png")
        await page.evaluate(TAP_STADIUM, 30)
        await asyncio.sleep(3.0)
        await page.screenshot(path=f"{OUT}/04b-km130-after-taps.png")
        # Check hurdle patterns
        hurdleInfo = await page.evaluate(CHECK_LUNAR_OBSTACLES)
        results.append({'km': 130, 'state': state130, 'hurdles': hurdleInfo})

        # === Test 5 : km 150 — lunar bien avancé
        await page.evaluate(FORCE_STATE, 150)
        await page.evaluate(TRIGGER_RENDER)
        await asyncio.sleep(3.0)
        state150 = await page.evaluate(INSPECT_STATE)
        await page.screenshot(path=f"{OUT}/05-km150-lunar-deep.png")
        await page.evaluate(TAP_STADIUM, 30)
        await asyncio.sleep(4.0)
        await page.screenshot(path=f"{OUT}/05b-km150-after-taps.png")
        # Check ascension modal / saison modal
        await page.evaluate("""
          () => {
            const btn = document.querySelector('[data-menu="saison"]') || document.querySelector('#saison-btn');
            if(btn) btn.click();
          }
        """)
        await asyncio.sleep(1.0)
        await page.screenshot(path=f"{OUT}/06-saison-modal-km150.png")
        # Close
        await page.evaluate("""
          () => {
            const m = document.getElementById('saison-modal');
            if(m) m.classList.remove('show');
          }
        """)
        results.append({'km': 150, 'state': state150})

        # === Test 6 : km 200 — vérifier que rien casse loin dans le chapitre
        await page.evaluate(FORCE_STATE, 200)
        await page.evaluate(TRIGGER_RENDER)
        await asyncio.sleep(2.5)
        state200 = await page.evaluate(INSPECT_STATE)
        await page.screenshot(path=f"{OUT}/07-km200-lunar-far.png")
        results.append({'km': 200, 'state': state200})

        # === Test 7 : check menus accessibles
        await page.evaluate(FORCE_STATE, 130)
        await asyncio.sleep(0.5)
        # Open chest modal
        await page.evaluate("""
          () => {
            if(typeof openChestsModal === 'function') openChestsModal();
          }
        """)
        await asyncio.sleep(1.0)
        await page.screenshot(path=f"{OUT}/08-chests-km130.png")
        await page.evaluate("""
          () => {
            document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
          }
        """)
        await asyncio.sleep(0.5)
        # achievement modal
        await page.evaluate("""
          () => {
            const btn = document.querySelector('[data-menu="profile"]');
            if(btn) btn.click();
            else if(typeof openRunnerProfile === 'function') openRunnerProfile();
          }
        """)
        await asyncio.sleep(1.0)
        await page.screenshot(path=f"{OUT}/09-profile-km130.png")

        # === FINAL : dump full result
        with open(f"{OUT}/qa-lunar-results.json", 'w', encoding='utf-8') as f:
            json.dump({'results': results, 'console': console_errors[:50]}, f, indent=2, default=str, ensure_ascii=False)

        await browser.close()

    print("=== QA LUNAR RESULTS ===")
    for r in results:
        print(json.dumps(r, indent=2, default=str, ensure_ascii=False))
    print("\n=== CONSOLE ERRORS ===")
    for e in console_errors[:30]:
        print(e)

if __name__ == '__main__':
    asyncio.run(main())
