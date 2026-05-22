"""Vérif visuelle propre — capture absolue à T=0.6, 2.0, 3.0, 4.0s"""
import asyncio, sys, io, time
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        await ctx.add_init_script("try { localStorage.removeItem('foulee.openingSeen'); } catch(e){}")
        start_t = time.time()
        await page.goto('http://localhost:8770', wait_until='domcontentloaded')

        targets = [
            (0.6, 'T0.6-build'),
            (1.7, 'T1.7-impact'),   # logo doit être visible (animation finit à 2.6s)
            (2.8, 'T2.8-rays'),     # logo en place + rayons + tagline en cours
            (3.5, 'T3.5-tagline'),  # tagline + sustain
            (4.6, 'T4.6-fadeout'),  # début fade out
        ]
        for target_sec, label in targets:
            wait_ms = int(target_sec * 1000 - (time.time() - start_t) * 1000)
            if wait_ms > 0:
                await page.wait_for_timeout(wait_ms)
            elapsed = int((time.time() - start_t) * 1000)
            await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/OPENING2-{label}.png', clip={'x':0,'y':0,'width':540,'height':960})
            print(f'[{elapsed}ms] OPENING2-{label}.png captured')

        await browser.close()

asyncio.run(main())
