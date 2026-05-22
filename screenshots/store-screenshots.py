"""Capture les 8 screenshots store HD pour Play Store.
Sélection des scènes les plus impactantes."""
import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = 'D:/alchimia/assets/store'
os.makedirs(OUT_DIR, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # 1080x1920 pour HD Play Store
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=4)
        page = await context.new_page()
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.evaluate('localStorage.clear();')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2500)

        # === SCREENSHOT 1 : INTRO LIVE (foule, banderole, soleil) ===
        await page.screenshot(path=f'{OUT_DIR}/screenshot-1.png')
        print('OK -> screenshot-1.png (intro)')

        # Start game
        await page.evaluate('''
            localStorage.setItem("foulee.storySeen", "1");
            document.getElementById("start-btn")?.click();
            STATE.starterPackDeclined = true;
            STATE.starterPackClaimed = true;
        ''')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show, .modal").forEach(m => { m.classList.remove("show"); m.style.display = "none"; });')

        # === SCREENSHOT 2 : KM 0 WASTELAND avec hint tuto ===
        await page.evaluate('STATE.lapsRun = 0; STATE.lapProgress = 0.3;')
        await page.wait_for_timeout(500)
        await page.screenshot(path=f'{OUT_DIR}/screenshot-2.png')
        print('OK -> screenshot-2.png (wasteland début)')

        # === SCREENSHOT 3 : SPRINT KM 1 (combo + speedlines) ===
        await page.evaluate('STATE.lapsRun = 1; STATE.lapProgress = 0.55;')
        box = await page.evaluate('(()=>{const r=document.getElementById("runner-stadium").getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};})()')
        for i in range(20):
            await page.mouse.click(box['x'], box['y'])
            await page.wait_for_timeout(50)
        await page.wait_for_timeout(300)
        await page.screenshot(path=f'{OUT_DIR}/screenshot-3.png')
        print('OK -> screenshot-3.png (sprint combo)')

        # === SCREENSHOT 4 : HAIE single (km 1+) ===
        await page.evaluate('STATE.lapsRun = 5; STATE.lapProgress = 0.3;')
        await page.evaluate('window.RUNNER_2D?.spawnHurdle?.(10, "single");')
        await page.wait_for_timeout(400)
        await page.screenshot(path=f'{OUT_DIR}/screenshot-4.png')
        print('OK -> screenshot-4.png (haie single)')

        # === SCREENSHOT 5 : HAIE TRIPLE (combo en vue) ===
        await page.evaluate('window.RUNNER_2D?.spawnHurdlePattern?.("triple", 20);')
        await page.wait_for_timeout(400)
        await page.screenshot(path=f'{OUT_DIR}/screenshot-5.png')
        print('OK -> screenshot-5.png (haie triple)')

        # === SCREENSHOT 6 : JUMP en l'air ===
        await page.evaluate('STATE.lapsRun = 8;')
        await page.evaluate('window.RUNNER_2D?.spawnHurdle?.(5, "single");')
        await page.evaluate('window.RUNNER_2D?.setJump?.(-50, -200);')
        await page.wait_for_timeout(50)
        await page.screenshot(path=f'{OUT_DIR}/screenshot-6.png')
        print('OK -> screenshot-6.png (saut)')

        # === SCREENSHOT 7 : RIVAL RUNNER en course ===
        await page.evaluate('STATE.lapsRun = 6; STATE.lapProgress = 0.4; window.RUNNER_2D?.spawnRival?.();')
        await page.wait_for_timeout(800)
        await page.screenshot(path=f'{OUT_DIR}/screenshot-7.png')
        print('OK -> screenshot-7.png (rival runner)')

        # === SCREENSHOT 8 : GRAND STADE km 50 ===
        await page.evaluate('STATE.lapsRun = 55; STATE.lapProgress = 0.5; STATE.gold = 50000;')
        await page.evaluate('_stageCache = { km: -1, result: null };')
        await page.wait_for_timeout(800)
        await page.screenshot(path=f'{OUT_DIR}/screenshot-8.png')
        print('OK -> screenshot-8.png (grand stade km 50)')

        await browser.close()


asyncio.run(main())
