"""Diag : qu'est-ce que l'overlay fait à T=2s ?"""
import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        await ctx.add_init_script("try { localStorage.removeItem('foulee.openingSeen'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='domcontentloaded')

        # Test à plusieurs timestamps
        for ms in [200, 500, 1000, 1500, 2000, 2500, 3500, 4500]:
            await page.wait_for_timeout(ms - (ms - 200 if ms == 200 else 0))
            info = await page.evaluate('''(()=>{
                const oc = document.getElementById('opening-cinematic');
                const intro = document.getElementById('intro');
                const cs = oc ? getComputedStyle(oc) : null;
                const ocs = intro ? getComputedStyle(intro) : null;
                const r = oc ? oc.getBoundingClientRect() : null;
                return {
                    oc_display: cs?.display,
                    oc_opacity: cs?.opacity,
                    oc_zindex: cs?.zIndex,
                    oc_position: cs?.position,
                    oc_visibility: cs?.visibility,
                    oc_w: r?.width,
                    oc_h: r?.height,
                    intro_display: ocs?.display,
                    intro_zindex: ocs?.zIndex,
                };
            })()''')
            print(f'[T~{ms}ms] {info}')
            await page.wait_for_timeout(0)
        await browser.close()

asyncio.run(main())
