"""Capture console logs pour identifier qui ferme l'overlay."""
import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        logs = []
        page.on('console', lambda m: logs.append(f'{m.type}: {m.text}'))
        await ctx.add_init_script("try { localStorage.removeItem('foulee.openingSeen'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='domcontentloaded')
        await page.wait_for_timeout(2500)

        for l in logs:
            if 'opening' in l.lower():
                print(l[:300])

        await browser.close()

asyncio.run(main())
