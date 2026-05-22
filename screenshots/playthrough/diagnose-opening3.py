"""Diagnostic avec timing PRÉCIS + capture tous logs console."""
import asyncio, sys, io, time
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        all_logs = []
        page.on('console', lambda m: all_logs.append((time.time(), m.type, m.text)))
        await ctx.add_init_script("try { localStorage.removeItem('foulee.openingSeen'); } catch(e){}")
        start_t = time.time()
        await page.goto('http://localhost:8770', wait_until='domcontentloaded')

        # Sample toutes les 200ms pendant 6s
        for i in range(30):
            elapsed = int((time.time() - start_t) * 1000)
            info = await page.evaluate('''(()=>{
                const oc = document.getElementById('opening-cinematic');
                if(!oc) return null;
                const cs = getComputedStyle(oc);
                return {display: cs.display, opacity: cs.opacity};
            })()''')
            if info and (i == 0 or info['display'] == 'none' or i % 3 == 0):
                print(f'[{elapsed:5d}ms] {info}')
            if info and info['display'] == 'none' and i > 2:
                # Détecté le moment où ça passe à none — affiche les logs autour
                print('--- LOGS console ---')
                for t, typ, txt in all_logs:
                    rel = int((t - start_t) * 1000)
                    if 'opening' in txt.lower() or 'overlay' in txt.lower() or typ == 'error':
                        print(f'  [{rel:5d}ms {typ}] {txt[:250]}')
                break
            await page.wait_for_timeout(200)

        await browser.close()

asyncio.run(main())
