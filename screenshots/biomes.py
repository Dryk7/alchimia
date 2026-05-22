"""Capture 4 screenshots des nouveaux biomes : désert, campagne, ville, stade."""
import asyncio
from playwright.async_api import async_playwright

SCENES = [
    {
        'name': 'biome-01-desert',
        'setup': """
            document.getElementById('start-btn')?.click();
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
            STATE.lapsRun = 0; STATE.lapProgress = 0.40; STATE.gold = 50;
            STATE.saison = 1; STATE.selectedStadiumId = 'municipal';
            if(typeof saveNow === 'function') saveNow();
        """,
    },
    {
        'name': 'biome-02-rural',
        'setup': """
            STATE.lapsRun = 5; STATE.lapProgress = 0.40;
            if(typeof saveNow === 'function') saveNow();
        """,
    },
    {
        'name': 'biome-03-urban',
        'setup': """
            STATE.lapsRun = 25; STATE.lapProgress = 0.40; STATE.gold = 5000;
            if(typeof saveNow === 'function') saveNow();
        """,
    },
    {
        'name': 'biome-04-stadium',
        'setup': """
            STATE.lapsRun = 70; STATE.lapProgress = 0.40; STATE.gold = 50000;
            if(typeof saveNow === 'function') saveNow();
        """,
    },
]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={'width': 540, 'height': 960},
            device_scale_factor=2,
        )
        page = await context.new_page()
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')

        for scene in SCENES:
            await page.evaluate(scene['setup'])
            await page.wait_for_timeout(800)
            path = f"D:/alchimia/screenshots/{scene['name']}.png"
            await page.screenshot(path=path, full_page=False)
            print(f"OK -> {path}")

        await browser.close()


asyncio.run(main())
