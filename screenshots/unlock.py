"""Capture la cinématique unlock auto-course."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={'width': 540, 'height': 960},
            device_scale_factor=2,
        )
        page = await context.new_page()
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.evaluate("""
            document.getElementById('start-btn')?.click();
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
        """)
        await page.wait_for_timeout(500)
        # Trigger unlock cinematic
        await page.evaluate("""
            if(typeof playUnlockCinematic === 'function'){
              playUnlockCinematic(
                'AUTO-COURSE',
                'Tu sors enfin du chantier. Ton coureur avance maintenant tout seul, même quand tu ne tapes pas.',
                'DÉBLOQUÉ'
              );
            }
        """)
        # Wait pour que le banner soit à son apogée (animation 22% = ~700ms)
        await page.wait_for_timeout(900)
        await page.screenshot(path='D:/alchimia/screenshots/unlock-cinematic.png')
        print('OK -> D:/alchimia/screenshots/unlock-cinematic.png')
        await browser.close()


asyncio.run(main())
