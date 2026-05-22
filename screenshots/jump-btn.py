"""Capture du bouton SAUT en action."""
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
        # Screenshot avec bouton SAUT au repos
        await page.screenshot(path='D:/alchimia/screenshots/jump-btn-idle.png')
        print('OK -> jump-btn-idle.png')
        # Force une haie qui arrive (via API exposée)
        await page.evaluate("""
            if(window.RUNNER_2D && window.RUNNER_2D.spawnHurdle){
              window.RUNNER_2D.spawnHurdle(15);
            }
        """)
        await page.wait_for_timeout(400)
        # Screenshot bouton ready (pulse)
        await page.screenshot(path='D:/alchimia/screenshots/jump-btn-ready.png')
        print('OK -> jump-btn-ready.png')
        # Force jump via API
        await page.evaluate("""
            if(window.RUNNER_2D && window.RUNNER_2D.forceJump){
              window.RUNNER_2D.forceJump();
            }
        """)
        await page.wait_for_timeout(180)
        # Screenshot pendant le saut
        await page.screenshot(path='D:/alchimia/screenshots/jump-btn-airborne.png')
        print('OK -> jump-btn-airborne.png')
        await browser.close()


asyncio.run(main())
