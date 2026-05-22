"""Zoom sur le bouton SAUT pour vérifier le texte."""
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
            STATE.starterPackDeclined = true;
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
            STATE.lapsRun = 5;
        """)
        await page.wait_for_timeout(1500)
        # Crop to SAUT button area
        jump_btn = page.locator('#jump-btn')
        await jump_btn.screenshot(path='D:/alchimia/screenshots/saut-zoom-idle.png')
        print('OK -> saut-zoom-idle.png')
        # Trigger ready state
        await page.evaluate("window.RUNNER_2D.spawnHurdle(15);")
        await page.wait_for_timeout(300)
        await jump_btn.screenshot(path='D:/alchimia/screenshots/saut-zoom-ready.png')
        print('OK -> saut-zoom-ready.png')
        await browser.close()


asyncio.run(main())
