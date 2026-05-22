"""Capture les 4 tiers du combo display redesigned."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await context.new_page()
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        await page.goto('http://localhost:8770?debug=1')
        await page.wait_for_load_state('networkidle')
        await page.evaluate('''
            localStorage.setItem("foulee.storySeen", "1");
            document.getElementById("start-btn")?.click();
            STATE.starterPackDeclined = true;
            STATE.starterPackClaimed = true;
            STATE.lapsRun = 5;
        ''')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show, .modal").forEach(m => { m.classList.remove("show"); m.style.display = "none"; });')

        # Force chaque tier en setting _comboCount directement
        for combo, label in [(3, 'tier1-x1.5'), (8, 'tier2-x2'), (18, 'tier3-x3'), (35, 'tier4-x5')]:
            await page.evaluate(f'_comboCount = {combo}; updateComboDisplay();')
            await page.wait_for_timeout(500)
            # Crop sur le combo display
            box = await page.evaluate('(()=>{const el = document.getElementById("combo-display"); const r = el.getBoundingClientRect(); return {x:Math.max(0,r.left-40), y:Math.max(0,r.top-30), w:r.width+80, h:r.height+60};})()')
            await page.screenshot(path=f'D:/alchimia/screenshots/combo-{label}.png', clip={'x':box['x'],'y':box['y'],'width':box['w'],'height':box['h']})
            print(f'OK -> combo-{label}.png')

        # Full screen avec combo max
        await page.evaluate('_comboCount = 50; updateComboDisplay();')
        await page.wait_for_timeout(400)
        await page.screenshot(path='D:/alchimia/screenshots/combo-max-fullscreen.png')
        print('OK -> combo-max-fullscreen.png')

        if errors:
            print('ERRORS:')
            for e in errors[:3]: print(f'  - {e[:200]}')
        await browser.close()


asyncio.run(main())
