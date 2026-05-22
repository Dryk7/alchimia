"""Capture des screenshots : haies + NPCs dépassés."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await context.new_page()
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.evaluate("""
            document.getElementById('start-btn')?.click();
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
            STATE.lapsRun = 25; STATE.lapProgress = 0.40; STATE.gold = 5000;
            STATE.saison = 1; STATE.selectedStadiumId = 'municipal';
            if(typeof saveNow === 'function') saveNow();
        """)
        await page.wait_for_timeout(1000)
        # Spawn une haie devant le héros
        await page.evaluate("""
            window._hurdleSpawnTimer = 0.01;
        """)
        await page.wait_for_timeout(1500)
        await page.screenshot(path='D:/alchimia/screenshots/hurdle-incoming.png')
        print('OK -> hurdle-incoming.png')
        # Force tap pour déclencher saut
        await page.evaluate("""
            const stadium = document.getElementById('runner-stadium');
            stadium.dispatchEvent(new MouseEvent('click', {bubbles:true}));
        """)
        await page.wait_for_timeout(200)
        await page.screenshot(path='D:/alchimia/screenshots/hurdle-jump.png')
        print('OK -> hurdle-jump.png')
        await browser.close()


asyncio.run(main())
