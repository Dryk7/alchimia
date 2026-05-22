"""Verifie que upgradeBaseSpeed accelere reellement la vitesse passive."""
import asyncio, sys, io
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SETUP_JS = r"""
() => {
  localStorage.setItem("foulee.storySeen","1");
  localStorage.setItem("foulee.tutoV3","done");
  localStorage.setItem("foulee.activeTutoV1","done");
  localStorage.setItem("foulee.openingSeen","1");
  localStorage.setItem("foulee.dailySeen","1");
}
"""

async def measure(page, baseSpeedLvl, duration_s=4):
    """Set baseSpeedLvl, measure lapProgress delta over duration_s."""
    await page.evaluate(f"""
      () => {{
        window.STATE.lapsRun = 10;          // > 3 pour activer idle
        window.STATE.totalKm = 10;
        window.STATE.lapProgress = 0;
        window.STATE.totalTaps = 100;
        window.STATE.upgradeBaseSpeed = {baseSpeedLvl};
        window.STATE.upgradeAutoTap = 0;
        window.STATE.upgradeTapValue = 0;
        window.STATE.upgradeLapBonus = 0;
        window.STATE.upgradeCruiseControl = 0;
        window.STATE.team = {{}};
        window.STATE.saison = 1;
      }}
    """)
    # Snapshot lapProgress
    start = await page.evaluate("() => window.STATE.lapProgress")
    start_laps = await page.evaluate("() => window.STATE.lapsRun")
    # Measure also the displayKmh - read it from the HUD
    # Also test: does runnerBaseSpeed() account for upgradeBaseSpeed?
    base_speed_fn = await page.evaluate("""() => {
      try { return (typeof runnerBaseSpeed === 'function') ? runnerBaseSpeed() : null; } catch(e){ return 'ERR:'+e.message; }
    }""")
    start_kmh_text = await page.evaluate("""() => {
      // pace-pill is the displayKmh HUD; look broadly
      const pp = document.querySelector('.pace-pill, [data-pace], #pace');
      if(pp) return pp.textContent.trim();
      // Fallback : find any pill containing "km/h"
      const all = [...document.querySelectorAll('header *, .runner-hud-overlay *')];
      const kmhEl = all.find(e => e.textContent && /km\/h/i.test(e.textContent));
      return kmhEl ? kmhEl.textContent.trim() : null;
    }""")
    await page.wait_for_timeout(int(duration_s * 1000))
    end = await page.evaluate("() => window.STATE.lapProgress")
    end_laps = await page.evaluate("() => window.STATE.lapsRun")
    end_kmh_text = await page.evaluate("""() => {
      const pp = document.querySelector('.pace-pill, [data-pace], #pace');
      if(pp) return pp.textContent.trim();
      const all = [...document.querySelectorAll('header *, .runner-hud-overlay *')];
      const kmhEl = all.find(e => e.textContent && /km\/h/i.test(e.textContent));
      return kmhEl ? kmhEl.textContent.trim() : null;
    }""")
    # Account for lap completion
    delta = (end + (end_laps - start_laps)) - start
    return {
        "level": baseSpeedLvl,
        "start_lp": start,
        "end_lp": end,
        "delta": delta,
        "expected_mul": 1.10 ** baseSpeedLvl,
        "start_kmh": start_kmh_text,
        "end_kmh": end_kmh_text,
        "runner_base_speed_fn": base_speed_fn,
    }

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 412, "height": 915})
        page = await ctx.new_page()
        await page.goto("http://localhost:8770/", wait_until="domcontentloaded")
        await page.evaluate(SETUP_JS)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(800)
        try:
            await page.click("#start-btn, .start-btn, button:has-text('PRENDRE')", timeout=2500)
        except: pass
        await page.wait_for_timeout(1500)
        try:
            await page.click("body", position={"x":200,"y":400})
        except: pass
        await page.wait_for_timeout(800)

        results = []
        for lvl in [0, 5, 10]:
            r = await measure(page, lvl, duration_s=4)
            results.append(r)
            print(f"Lvl {lvl}: delta={r['delta']:.5f} (expected_mul=x{r['expected_mul']:.2f})  runnerBaseSpeed()={r['runner_base_speed_fn']}  kmh: {r['start_kmh']} -> {r['end_kmh']}")

        # Compute observed ratios vs lvl 0
        base_delta = results[0]["delta"]
        print()
        print(f"Lvl 0 baseline: {base_delta:.5f}")
        for r in results[1:]:
            obs_ratio = r["delta"] / base_delta if base_delta > 0 else 0
            exp_ratio = r["expected_mul"]
            ok = abs(obs_ratio - exp_ratio) / exp_ratio < 0.20  # 20% tolerance
            print(f"Lvl {r['level']}: observed x{obs_ratio:.2f}  expected x{exp_ratio:.2f}  {'OK' if ok else 'BUG'}")

        await browser.close()

asyncio.run(main())
