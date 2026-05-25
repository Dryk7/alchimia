"""VAGUE 12 — Vérifie le déblocage progressif des upgrades + boutons cachés"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

URL = "http://localhost:8770"
OUT = Path(__file__).parent

async def count_visible_upgs(page):
    """Compte les upgrades non lockés (data-locked != '1')"""
    return await page.evaluate("""() => {
        return document.querySelectorAll('.upg-btn:not([data-locked="1"])').length;
    }""")

async def force_km(page, km):
    """Force STATE.lapsRun et déclenche applyProgressiveDisclosure"""
    await page.evaluate(f"""() => {{
        if(window.STATE) window.STATE.lapsRun = {km};
        if(typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
    }}""")
    await page.wait_for_timeout(800)

async def skip_onboarding(page):
    """Skippe onboarding/intro/story pour arriver au gameplay"""
    await page.evaluate("""() => {
        try {
            // Skip tuto actif
            if(window.ActiveTuto && typeof window.ActiveTuto.skip === 'function') window.ActiveTuto.skip();
            localStorage.setItem('foulee.activeTutoV1', 'done');
            localStorage.setItem('foulee.storyShown', '1');
            localStorage.setItem('alchimia.storyShown', '1');
            // Dismiss opening cinematic
            const oc = document.getElementById('opening-cinematic');
            if(oc) oc.style.display='none';
            const splash = document.getElementById('splash');
            if(splash) splash.style.display='none';
        } catch(e) {}
    }""")
    # Click PRENDRE LE DÉPART si présent
    try:
        btn = await page.query_selector("text=PRENDRE LE DÉPART")
        if btn:
            await btn.click()
            await page.wait_for_timeout(500)
    except: pass
    await page.wait_for_timeout(500)

async def open_upgrades_drawer(page):
    """Ouvre le drawer/panel upgrades"""
    await page.evaluate("""() => {
        // Le panel .tap-upgrades-v2 est dans la page principale (pas un drawer modal séparé)
        // Scroll vers lui pour qu'il soit visible
        const panel = document.querySelector('.tap-upgrades-v2');
        if(panel) panel.scrollIntoView({behavior:'instant', block:'center'});
    }""")
    await page.wait_for_timeout(300)

async def main():
    console_errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc}"))

        # Clear LS pour partir d'un état neuf
        await page.goto(URL)
        await page.evaluate("() => { try { localStorage.clear(); } catch(e){} }")
        await page.reload()
        await page.wait_for_timeout(2000)

        await skip_onboarding(page)
        await page.wait_for_timeout(1500)
        await open_upgrades_drawer(page)

        # ===== KM 0 =====
        await force_km(page, 0)
        c0 = await count_visible_upgs(page)
        empty_visible = await page.evaluate("""() => {
            const m = document.getElementById('upg-empty-msg');
            return m && m.style.display !== 'none';
        }""")
        await page.screenshot(path=str(OUT / "vague12-km0-empty.png"), full_page=True)
        print(f"KM 0 — visible upgrades: {c0} (expect 0), empty msg shown: {empty_visible}")

        # ===== KM 1 =====
        await force_km(page, 1)
        c1 = await count_visible_upgs(page)
        await page.screenshot(path=str(OUT / "vague12-km1.png"), full_page=True)
        print(f"KM 1 — visible: {c1} (expect 1 = tapValue)")

        # ===== KM 5 =====
        await force_km(page, 5)
        c5 = await count_visible_upgs(page)
        await page.screenshot(path=str(OUT / "vague12-km5.png"), full_page=True)
        print(f"KM 5 — visible: {c5} (expect 3 = tapValue + lapBonus + critChance)")

        # ===== KM 12 =====
        await force_km(page, 12)
        c12 = await count_visible_upgs(page)
        print(f"KM 12 — visible: {c12} (expect 5 = + eagleEye + endurance)")

        # ===== KM 30 =====
        await force_km(page, 30)
        c30 = await count_visible_upgs(page)
        await page.screenshot(path=str(OUT / "vague12-km30-all.png"), full_page=True)
        print(f"KM 30 — visible: {c30} (expect 8 = all)")

        # Synthèse
        print("\n===== SYNTHESE =====")
        print(f"KM 0: {c0}/0  KM 1: {c1}/1  KM 5: {c5}/3  KM 12: {c12}/5  KM 30: {c30}/8")
        if console_errors:
            print(f"\nERREURS CONSOLE ({len(console_errors)}):")
            for e in console_errors[:10]:
                print("  " + e)
        else:
            print("\nConsole errors: 0")

        await browser.close()

asyncio.run(main())
