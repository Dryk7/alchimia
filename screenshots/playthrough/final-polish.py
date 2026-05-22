"""Force différents weather pour vérifier le polish final."""
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

        # Force WINDY at km 30
        await page.evaluate('STATE.lapsRun=30; if(window.RUNNER_2D) RUNNER_2D.setWeather && RUNNER_2D.setWeather("windy"); _stageCache = {km:-1, result:null};')
        await page.wait_for_timeout(1500)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/FINAL-windy.png')
        print('OK windy km30')

        # Force RAINY at km 30
        await page.evaluate('if(window.RUNNER_2D) RUNNER_2D.setWeather && RUNNER_2D.setWeather("rainy");')
        await page.wait_for_timeout(1200)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/FINAL-rainy.png')
        print('OK rainy km30')

        # Camera shake test : trigger km 100 milestone
        await page.evaluate('STATE.lapsRun = 99; _stageCache={km:-1,result:null};')
        await page.wait_for_timeout(500)
        await page.evaluate('STATE.lapsRun = 100; _stageCache={km:-1,result:null};')
        await page.wait_for_timeout(150)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/FINAL-km100-shake.png')
        print('OK km100 shake')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/FINAL-km100-magic.png')
        print('OK km100 magic')

        await browser.close()

asyncio.run(main())
