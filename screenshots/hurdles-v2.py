"""Capture les 5 patterns de haies + 3 phases de saut."""
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
        await page.evaluate("""
            document.getElementById('start-btn')?.click();
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
            STATE.lapsRun = 12; STATE.lapProgress = 0.40; STATE.gold = 5000;
            STATE.saison = 1; STATE.selectedStadiumId = 'municipal';
            if(typeof saveNow === 'function') saveNow();
        """)
        await page.wait_for_timeout(800)
        # 5 patterns de haies
        for pattern in ['single', 'double', 'triple', 'wide', 'tall']:
            await page.evaluate(f"window.RUNNER_2D.spawnHurdlePattern('{pattern}', 25);")
            await page.wait_for_timeout(300)
            await page.screenshot(path=f'D:/alchimia/screenshots/hurdle-{pattern}.png')
            print(f'OK -> hurdle-{pattern}.png')
        # 3 phases du saut : takeoff, apex, landing
        # Takeoff : vy fortement négative, y léger
        await page.evaluate("window.RUNNER_2D.setJump(-15, -350);")
        await page.wait_for_timeout(80)
        await page.screenshot(path='D:/alchimia/screenshots/jump-takeoff.png')
        print('OK -> jump-takeoff.png')
        # Apex : vy proche de 0, y au max
        await page.evaluate("window.RUNNER_2D.setJump(-85, 0);")
        await page.wait_for_timeout(80)
        await page.screenshot(path='D:/alchimia/screenshots/jump-apex.png')
        print('OK -> jump-apex.png')
        # Landing : vy positive, y descend
        await page.evaluate("window.RUNNER_2D.setJump(-15, 350);")
        await page.wait_for_timeout(80)
        await page.screenshot(path='D:/alchimia/screenshots/jump-landing.png')
        print('OK -> jump-landing.png')
        if errors:
            print('\n=== ERRORS ===')
            for e in errors[:5]: print(e)
        await browser.close()


asyncio.run(main())
