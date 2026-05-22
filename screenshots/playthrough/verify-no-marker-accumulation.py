"""Vérifie qu'il n'y a plus d'accumulation de bornes :
- Simule lapsRun 0 → 1 → 2 → 3 → 4 → 5
- À chaque km, vérifie que <= 3 markers hm dans milestones
- Vérifie labels corrects : 250m, 500m, 750m (pas 3× '100m')
"""
import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Reset markers
        await page.evaluate('if(window.RUNNER_2D && window.RUNNER_2D.milestones) window.RUNNER_2D.milestones.length = 0;')

        # Simule lapsRun croissant SANS tap (idle pur)
        for km in [0, 1, 2, 3, 4, 5, 6]:
            await page.evaluate(f'STATE.lapsRun = {km}; STATE.totalTaps = 1;')
            await page.wait_for_timeout(700)  # laisse le tick canvas tourner
            info = await page.evaluate('''(()=>{
                if(!window.RUNNER_2D || !window.RUNNER_2D.milestones) return null;
                const hms = window.RUNNER_2D.milestones.filter(m => m.kind === 'hm');
                const kmMiles = window.RUNNER_2D.milestones.filter(m => m.kind === 'km');
                return {
                    hm_count: hms.length,
                    hm_meters: hms.map(m => m.m),
                    km_count: kmMiles.length,
                    total: window.RUNNER_2D.milestones.length
                };
            })()''')
            print(f'[KM {km}] {info}')

        # Capture visuelle au km 5 (devrait avoir 3 markers max)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/MARKERS-no-accum.png', clip={'x':0,'y':0,'width':540,'height':960})

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
