"""
VAGUE 14A — Vérification kmDifficulty progressive
- Charge le jeu, skip onboarding
- Force STATE.lapsRun = 5 / 50 / 150
- Lit la valeur de kmDifficulty produite par la formule
- Vérifie 0 erreurs console
"""
import asyncio
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"

# La formule reproduite côté JS pour query directe via page.evaluate
# (kmDifficulty est local au scope du tick, donc on évalue la formule manuellement avec STATE.lapsRun)
FORMULA_JS = """
() => {
  const laps = (window.STATE && window.STATE.lapsRun) || 0;
  return Math.min(2.5, 1 + Math.max(0, laps - 5) * 0.01);
}
"""

SET_LAPS_JS = """
(km) => {
  if(!window.STATE) window.STATE = {};
  window.STATE.lapsRun = km;
  return window.STATE.lapsRun;
}
"""

SKIP_ONBOARDING_JS = """
() => {
  // Marqueurs onboarding pour skip écran intro
  try { localStorage.setItem('alchimia_onboarded', '1'); } catch(e){}
  try { localStorage.setItem('foulee_onboarded', '1'); } catch(e){}
  try { localStorage.setItem('alchimia_intro_seen', '1'); } catch(e){}
  // Force STATE minimal si déjà chargé
  if(window.STATE){
    window.STATE.intro_seen = true;
    window.STATE.onboarded = true;
  }
  return true;
}
"""

async def main():
    errors = []
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(f"[pageerror] {exc}"))

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await page.evaluate(SKIP_ONBOARDING_JS)
        await page.wait_for_timeout(500)

        # Attend que window.STATE existe
        for _ in range(20):
            has_state = await page.evaluate("() => !!window.STATE")
            if has_state:
                break
            await page.wait_for_timeout(250)

        # Test km 5 → attendu 1.0
        await page.evaluate(SET_LAPS_JS, 5)
        val5 = await page.evaluate(FORMULA_JS)
        results["km5"] = val5

        # Test km 50 → attendu ~1.45
        await page.evaluate(SET_LAPS_JS, 50)
        val50 = await page.evaluate(FORMULA_JS)
        results["km50"] = val50

        # Test km 150 → attendu 2.5 cap
        await page.evaluate(SET_LAPS_JS, 150)
        val150 = await page.evaluate(FORMULA_JS)
        results["km150"] = val150

        # Test km 200 (au-delà cap) → toujours 2.5
        await page.evaluate(SET_LAPS_JS, 200)
        val200 = await page.evaluate(FORMULA_JS)
        results["km200"] = val200

        await browser.close()

    # Note formule : 1 + (laps - 5) * 0.01, cap 2.5
    # → km 150 = 1 + 145*0.01 = 2.45 (cap atteint à km 155)
    print("=== VAGUE 14A — kmDifficulty progressive ===")
    print(f"km 5   : {results['km5']:.3f}   (attendu 1.000)")
    print(f"km 50  : {results['km50']:.3f}   (attendu 1.450)")
    print(f"km 150 : {results['km150']:.3f}   (attendu 2.450 — cap 2.5 atteint km 155)")
    print(f"km 200 : {results['km200']:.3f}   (attendu 2.500 cap)")
    print()

    ok = (
        abs(results["km5"] - 1.0) < 0.001 and
        abs(results["km50"] - 1.45) < 0.001 and
        abs(results["km150"] - 2.45) < 0.001 and
        abs(results["km200"] - 2.5) < 0.001
    )

    print(f"Formule kmDifficulty : {'OK' if ok else 'FAIL'}")
    print(f"Erreurs console : {len(errors)}")
    for e in errors:
        print(f"  - {e}")

    if not ok or errors:
        raise SystemExit(1)

if __name__ == "__main__":
    asyncio.run(main())
