"""Test final MEGA POLISH : tribune vivante + bloom + god rays à différents km."""
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
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); localStorage.setItem('fouleeDebug','1'); } catch(e){}")
        await page.goto('http://localhost:8770?debug=1', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true; STATE.totalTaps=200; STATE.alchLevel=20;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Test à différents km
        scenarios = [
            (5, 'km05-rural'),       # rural, pas d'effets premium
            (50, 'km50-vignette'),   # vignette débute, OLA pas encore
            (70, 'km70-godrays'),    # god rays + flashs photo + tribune dense
            (95, 'km95-full'),       # tout actif : vignette intense + halos + champion
        ]
        for km, label in scenarios:
            await page.evaluate(f'STATE.lapsRun = {km};')
            # Force spawn de 2 champions à km 95 pour les voir
            if km >= 85:
                await page.evaluate('if(window.RUNNER_2D && window.RUNNER_2D.spawnNpc){ window.RUNNER_2D.spawnNpc(6); window.RUNNER_2D.spawnNpc(6); }')
            await page.wait_for_timeout(1500)
            await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/MEGA-{label}.png', clip={'x':0,'y':0,'width':540,'height':960})
            print(f'[{label}] captured')

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
