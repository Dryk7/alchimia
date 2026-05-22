"""Capture story intro + vitesse progressive."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await context.new_page()
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.evaluate('localStorage.clear();')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click();')
        await page.wait_for_timeout(1200)  # laisse l'intro story s'afficher
        await page.screenshot(path='D:/alchimia/screenshots/story-intro.png')
        print('OK -> story-intro.png')
        # Click "JE SUIS PRÊT"
        await page.click('#story-go', force=True)  # animation peut être en cours, force le click
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/after-story.png')
        print('OK -> after-story.png')
        # Verify vitesse progressive : tape 15x au km 0
        await page.evaluate('STATE.starterPackDeclined = true; STATE.starterPackClaimed = true;')
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m => m.style.display="none");')
        box = await page.evaluate('(()=>{const r=document.getElementById("runner-stadium").getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};})()')
        for i in range(15):
            await page.mouse.click(box['x'], box['y'])
            await page.wait_for_timeout(80)
        await page.wait_for_timeout(300)
        kmh_km0 = await page.evaluate('window.RUNNER_2D?.getKmh?.() ?? 0')
        print(f'kmh apres 15 taps a km 0: {round(kmh_km0, 1)}')
        # Force km 3 et re-tape
        await page.evaluate('STATE.lapsRun = 3;')
        await page.wait_for_timeout(100)
        for i in range(15):
            await page.mouse.click(box['x'], box['y'])
            await page.wait_for_timeout(80)
        await page.wait_for_timeout(300)
        kmh_km3 = await page.evaluate('window.RUNNER_2D?.getKmh?.() ?? 0')
        print(f'kmh apres 15 taps a km 3: {round(kmh_km3, 1)}')
        await page.screenshot(path='D:/alchimia/screenshots/km3-fast.png')
        if errors:
            print('ERRORS:', errors[:3])
        await browser.close()


asyncio.run(main())
