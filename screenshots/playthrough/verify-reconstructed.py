"""Vérifie que le fichier reconstitué fonctionne (0 erreur console)."""
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
        page.on('console', lambda m: errors.append(f'ERR: {m.text}') if m.type == 'error' else None)
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle', timeout=15000)
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(2000)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
        await page.wait_for_timeout(1000)

        # Tente différents km pour valider
        for km in [5, 30, 75]:
            await page.evaluate(f'if(window.STATE){{STATE.lapsRun = {km}; STATE.totalTaps = 100;}}')
            await page.wait_for_timeout(800)

        await page.screenshot(path='D:/alchimia/screenshots/playthrough/RECONSTRUCT-OK.png', clip={'x':0,'y':0,'width':540,'height':960})

        print(f'Erreurs console : {len(errors)}')
        for e in errors[:10]: print(f'  {e[:250]}')

        # Check RUNNER_2D présent
        has_r2d = await page.evaluate('typeof window.RUNNER_2D === "object"')
        print(f'\nRUNNER_2D présent : {has_r2d}')

        await browser.close()

asyncio.run(main())
