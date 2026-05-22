"""Capture la tribune in-game à divers stages pour valider le nouveau rendu."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.setItem("foulee.storySeen", "1");')
        await page.evaluate('''
            document.getElementById("start-btn")?.click();
            STATE.starterPackDeclined = true;
            STATE.starterPackClaimed = true;
        ''')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show, .modal").forEach(m => { m.classList.remove("show"); m.style.display = "none"; });')

        # Capture aux différents stages
        for laps, lbl in [(5, 'km5-stade-municipal'), (12, 'km12-estrade-vip'), (25, 'km25-projecteur'), (55, 'km55-international'), (80, 'km80-vasque')]:
            await page.evaluate(f'STATE.lapsRun = {laps}; _stageCache = {{ km: -1, result: null }};')
            await page.wait_for_timeout(400)
            # Force hype élevé pour voir les bras levés
            await page.evaluate('if(typeof crowdHype !== "undefined") crowdHype = 85;')
            await page.wait_for_timeout(200)
            await page.screenshot(path=f'D:/alchimia/screenshots/tribune-{lbl}.png')
            print(f'OK -> tribune-{lbl}.png')

        if errors:
            print('ERRORS:')
            for e in errors[:3]: print(f'  - {e[:200]}')
        await browser.close()


asyncio.run(main())
