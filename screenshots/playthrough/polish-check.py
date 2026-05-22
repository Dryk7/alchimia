"""Vérifie le polish visuel : km 70/85/95/100 + dust + halo."""
import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.setItem("foulee.storySeen","1"); localStorage.setItem("foulee.tutoV3","done"); localStorage.setItem("foulee.activeTutoV1","done");')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        for km, label in [(70, 'km70-stadium'), (85, 'km85-golden'), (95, 'km95-rays'), (99, 'km99-halo'), (100, 'km100-magic')]:
            await page.evaluate(f'STATE.lapsRun = {km}; STATE.alchLevel = 25; STATE.runnerStamina = 1; _stageCache = {{ km: -1, result: null }};')
            await page.wait_for_timeout(800)
            await page.evaluate('document.querySelectorAll(".tier-banner, .runner-bubble").forEach(e => e.style.display="none");')
            await page.wait_for_timeout(200)
            await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/POLISH-{label}.png')
            print(f'OK -> POLISH-{label}.png')

        await browser.close()

asyncio.run(main())
