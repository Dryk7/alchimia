"""Test du Rival Runner."""
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
        # Pre-set storySeen AVANT click pour skip le story intro
        await page.evaluate('localStorage.setItem("foulee.storySeen", "1");')
        await page.evaluate('''
            document.getElementById("start-btn")?.click();
            STATE.starterPackDeclined = true;
            STATE.starterPackClaimed = true;
            STATE.lapsRun = 5;
        ''')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m => m.style.display="none");')
        # Force spawn rival immédiatement
        await page.evaluate('window.RUNNER_2D.spawnRival();')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/rival-spawn.png')
        print('OK -> rival-spawn.png')
        rival_data = await page.evaluate('window.RUNNER_2D.getRival()')
        print(f'Rival data: {rival_data}')
        # Tap pour dépasser
        box = await page.evaluate('(()=>{const r=document.getElementById("runner-stadium").getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};})()')
        for i in range(30):
            await page.mouse.click(box['x'], box['y'])
            await page.wait_for_timeout(60)
        await page.wait_for_timeout(500)
        await page.screenshot(path='D:/alchimia/screenshots/rival-passing.png')
        print('OK -> rival-passing.png')
        rival_after = await page.evaluate('window.RUNNER_2D.getRival()')
        print(f'Rival apres 30 taps: {rival_after}')
        await page.wait_for_timeout(2000)  # laisse settle
        rival_settled = await page.evaluate('window.RUNNER_2D.getRival()')
        gold_final = await page.evaluate('STATE.gold')
        print(f'Rival settled: {rival_settled}, Gold final: {gold_final}')
        if errors:
            print('ERRORS:', errors[:3])
        await browser.close()


asyncio.run(main())
