"""VAGUE 13 — Vérifie l'éradication complète de 'méd' (rename → gouttes).

Cible : daily calendar (30 jours), popups +X méd, lap rewards, km bubble.
Critère succès : document.body.innerText ne contient aucun '\\bméd\\b'.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

URL = "http://localhost:8770"
OUT = Path(__file__).parent


async def skip_onboarding(page):
    """Skippe onboarding/intro/story pour arriver au gameplay."""
    await page.evaluate("""() => {
        try {
            if(window.ActiveTuto && typeof window.ActiveTuto.skip === 'function') window.ActiveTuto.skip();
            localStorage.setItem('foulee.activeTutoV1', 'done');
            localStorage.setItem('foulee.storyShown', '1');
            localStorage.setItem('alchimia.storyShown', '1');
            const oc = document.getElementById('opening-cinematic');
            if(oc) oc.style.display = 'none';
            const splash = document.getElementById('splash');
            if(splash) splash.style.display = 'none';
        } catch(e) {}
    }""")
    try:
        btn = await page.query_selector("text=PRENDRE LE DÉPART")
        if btn:
            await btn.click()
            await page.wait_for_timeout(500)
    except Exception:
        pass
    await page.wait_for_timeout(500)


async def force_state(page):
    """Force STATE en mid-game pour révéler max d'UI."""
    await page.evaluate("""() => {
        if(window.STATE){
            window.STATE.lapsRun = 10;
            window.STATE.totalTaps = 200;
            window.STATE.gold = 50000;
        }
        if(typeof renderStats === 'function') renderStats();
        if(typeof updateRunnerHUD === 'function') updateRunnerHUD();
        if(typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
    }""")
    await page.wait_for_timeout(800)


async def find_med_in_body(page):
    """Renvoie liste des matches \\bméd\\b dans innerText du body."""
    return await page.evaluate("""() => {
        const txt = document.body.innerText || '';
        const matches = txt.match(/\\bméd\\b/gi);
        return matches || [];
    }""")


async def main():
    console_errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        page.on(
            "console",
            lambda msg: console_errors.append(f"[{msg.type}] {msg.text}")
            if msg.type == "error"
            else None,
        )
        page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc}"))

        # Clear LS pour partir d'un état neuf
        await page.goto(URL)
        await page.evaluate("() => { try { localStorage.clear(); } catch(e){} }")
        await page.reload()
        await page.wait_for_timeout(2000)

        await skip_onboarding(page)
        await page.wait_for_timeout(1500)
        await force_state(page)

        # === 1. Vérif body principal ===
        matches_main = await find_med_in_body(page)
        await page.screenshot(path=str(OUT / "vague13-med-main.png"), full_page=True)
        print(f"[Main UI] occurrences 'méd' visibles : {len(matches_main)}")
        if matches_main:
            print(f"  matches: {matches_main[:10]}")

        # === 2. Ouvrir Daily Modal ===
        opened_daily = False
        try:
            await page.evaluate("""() => {
                if(typeof openDailyModal === 'function') openDailyModal();
            }""")
            await page.wait_for_timeout(800)
            modal = await page.query_selector('#daily-modal.show')
            opened_daily = modal is not None
        except Exception as e:
            print(f"  openDailyModal error: {e}")

        await page.screenshot(path=str(OUT / "vague13-med-daily.png"), full_page=True)
        matches_daily = await find_med_in_body(page)
        print(
            f"[Daily Modal] ouvert: {opened_daily} — occurrences 'méd' visibles : {len(matches_daily)}"
        )
        if matches_daily:
            print(f"  matches: {matches_daily[:10]}")

        # === 3. Vérif HTML brut (innerHTML du daily-body) ===
        daily_html_med = await page.evaluate("""() => {
            const body = document.getElementById('daily-body');
            if(!body) return -1;
            const txt = body.textContent || '';
            const m = txt.match(/\\bméd\\b/gi);
            return m ? m.length : 0;
        }""")
        print(f"[Daily body textContent] 'méd' count : {daily_html_med}")

        # === Synthèse ===
        total = len(matches_main) + len(matches_daily)
        print("\n===== SYNTHESE VAGUE 13 - RENAME med -> gouttes =====")
        print(f"Body principal : {len(matches_main)} 'méd' restants")
        print(f"Daily modal    : {len(matches_daily)} 'méd' restants")
        print(f"Daily textContent direct : {daily_html_med}")
        print(f"TOTAL VISIBLE : {total} (objectif : 0)")
        if console_errors:
            print(f"\nERREURS CONSOLE ({len(console_errors)}):")
            for e in console_errors[:10]:
                print("  " + e)
        else:
            print("\nConsole errors: 0")

        await browser.close()


asyncio.run(main())
