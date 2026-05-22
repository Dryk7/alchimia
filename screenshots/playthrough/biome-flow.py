"""Vérifie le nouveau flow narratif : pas de tribune avant km 70."""
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
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.setItem("foulee.storySeen","1"); localStorage.setItem("foulee.tutoV3","done");')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); STATE.starterPackDeclined=true; STATE.starterPackClaimed=true; STATE.alchLevel=10; STATE.alchXp=999999;')
        await page.wait_for_timeout(1200)
        await page.evaluate('document.querySelectorAll(".modal.show, .modal").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        for km, label in [(1, 'km1-chantier'), (5, 'km5-route'), (15, 'km15-banlieue'), (30, 'km30-ville'), (50, 'km50-urbain'), (65, 'km65-approche'), (70, 'km70-stade-vue'), (78, 'km78-tribune'), (82, 'km82-vasque'), (90, 'km90-helico')]:
            await page.evaluate(f'STATE.lapsRun = {km}; _stageCache = {{ km: -1, result: null }};')
            await page.wait_for_timeout(400)
            await page.evaluate('document.querySelectorAll(".tier-banner, .runner-bubble").forEach(e => e.style.display="none");')
            await page.wait_for_timeout(200)
            await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/BIOME-{label}.png')
            print(f'OK -> BIOME-{label}.png')

        print(f'Errors: {len(errors)}')
        for e in errors[:3]: print(f'  - {e[:200]}')
        await browser.close()

asyncio.run(main())
