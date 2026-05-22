"""Audit de cohérence graphique : capture toutes les surfaces visibles."""
import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))

        # === ÉTAPE 1 : SPLASH (premier lancement) ===
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.clear();')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-01-splash.png')

        # === ÉTAPE 2 : STORY INTRO ===
        await page.evaluate('document.getElementById("start-btn")?.click();')
        await page.wait_for_timeout(700)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-02-story.png')

        # === ÉTAPE 3 : SKIP STORY, premier vrai jeu ===
        await page.evaluate('localStorage.setItem("foulee.storySeen","1"); localStorage.setItem("foulee.tutoV3","done");')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;')
        await page.wait_for_timeout(1200)
        await page.evaluate('document.querySelectorAll(".modal.show, .modal").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
        await page.wait_for_timeout(200)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-03-game-km0.png')

        # === ÉTAPE 4 : KM 25 (urbain dense) avec rivaux ===
        await page.evaluate('STATE.lapsRun = 25; STATE.gold = 200000; STATE.alchLevel = 8; STATE.alchXp = 99999;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-04-game-km25.png')

        # === ÉTAPE 5 : KM 80 (stade olympique) ===
        await page.evaluate('STATE.lapsRun = 80; STATE.gold = 50000000; STATE.gems = 200; STATE.stars = 15; STATE.alchLevel = 25; STATE.alchXp = 999999;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-05-game-km80.png')

        # === ÉTAPE 6 : Tab UPGRADES ouvert ===
        await page.evaluate('STATE.lapsRun = 30; STATE.gold = 5000000;')
        await page.evaluate('document.querySelector("[data-tab=\\"upgrades\\"]")?.click();')
        await page.wait_for_timeout(500)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-06-tab-upgrades.png')

        # === ÉTAPE 7 : Tab ÉQUIPE ===
        await page.evaluate('document.querySelector("[data-tab=\\"team\\"]")?.click();')
        await page.wait_for_timeout(500)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-07-tab-equipe.png')

        # === ÉTAPE 8 : Tab STATS ===
        await page.evaluate('document.querySelector("[data-tab=\\"stats\\"]")?.click();')
        await page.wait_for_timeout(500)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-08-tab-stats.png')
        # Close tab
        await page.evaluate('document.querySelector(".tabbar .tab.active")?.click();')
        await page.wait_for_timeout(300)

        # === ÉTAPE 9 : DRAWER QUÊTES ===
        await page.evaluate('document.getElementById("quests")?.classList.add("open");')
        await page.wait_for_timeout(500)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-09-drawer-quetes.png')
        await page.evaluate('document.getElementById("quests")?.classList.remove("open");')

        # === ÉTAPE 10 : TIER BANNER affiché ===
        await page.evaluate('document.getElementById("tier-banner-msg").textContent = "Tribune double étage. Le bruit monte."; document.getElementById("tier-banner").style.display = "flex"; document.getElementById("tier-banner").classList.remove("out");')
        await page.wait_for_timeout(200)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-10-tier-banner.png')

        # === ÉTAPE 11 : RUNNER BUBBLE ===
        await page.evaluate('if(typeof showRunnerBubble === "function") showRunnerBubble("+500 méd");')
        await page.wait_for_timeout(300)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/COH-11-runner-bubble.png')

        if errors:
            print(f'ERRORS: {len(errors)}')
            for e in errors[:5]: print(f'  - {e[:200]}')
        else:
            print('OK 0 erreur')
        await browser.close()

asyncio.run(main())
