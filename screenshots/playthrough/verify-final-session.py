"""Validation finale TOUTES VAGUES (28 agents) :
- 0 erreur console à tous les km
- Screenshots biomes pour preuve visuelle
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
        page.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        for km, label in [(1, 'wasteland'), (5, 'rural'), (20, 'urban'), (75, 'stadium'), (105, 'lunar')]:
            await page.evaluate(f'STATE.lapsRun = {km}; STATE.totalTaps = 100;')
            await page.wait_for_timeout(1200)
            await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/FINAL-{label}-km{km}.png', clip={'x':0,'y':0,'width':540,'height':960})
            print(f'[FINAL km{km} {label}] captured')

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')
        await browser.close()

asyncio.run(main())
