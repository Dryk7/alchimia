"""Vérifie que les bornes défilent maintenant à la même vitesse que le sol."""
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
        await page.goto('http://localhost:8770', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true; STATE.totalTaps=200; STATE.lapsRun=10; STATE.upgradeBaseSpeed=10;}')
        await page.wait_for_timeout(2500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Mesure : pixAhead d'une borne entre t et t+1s
        m1 = await page.evaluate('window.RUNNER_2D?.milestones?.find(m=>m.kind==="hm")?.pixAhead')
        kmh = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        print(f'[T0] km/h={kmh:.1f}, pixAhead borne hm = {m1}')
        await page.wait_for_timeout(1500)
        m2 = await page.evaluate('window.RUNNER_2D?.milestones?.find(m=>m.kind==="hm")?.pixAhead')
        kmh2 = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        delta = (m1 - m2) if m1 is not None and m2 is not None else 'N/A'
        expected = kmh * 9.72 * 1.5  # en 1.5s
        print(f'[T1.5] km/h={kmh2:.1f}, pixAhead = {m2}, Δ = {delta} px (attendu ~{expected:.0f})')

        # Screenshot pour visuel
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/MARKERS-SYNC.png', clip={'x':0,'y':0,'width':540,'height':600})

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')
        await browser.close()

asyncio.run(main())
