"""Capture une galerie de screenshots du jeu FOULÉE en PNG sur disque."""
import asyncio
from playwright.async_api import async_playwright

SCENES = [
    {
        'name': '01-splash',
        'setup': None,  # Just splash
        'title': 'Splash',
    },
    {
        'name': '02-debut-5km',
        'setup': """
            document.getElementById('start-btn')?.click();
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
            STATE.lapsRun = 5; STATE.lapProgress = 0.30; STATE.gold = 500;
            STATE.saison = 1; STATE.selectedStadiumId = 'municipal';
            if(typeof saveNow === 'function') saveNow();
        """,
        'title': 'Stade municipal 5 km',
    },
    {
        'name': '03-mid-35km',
        'setup': """
            STATE.lapsRun = 35; STATE.lapProgress = 0.30; STATE.gold = 15000;
            STATE.upgradeTapValue = 5; STATE.upgradeCritChance = 3;
            if(typeof saveNow === 'function') saveNow();
            if(typeof renderStats === 'function') renderStats();
        """,
        'title': 'Écran géant 35 km',
    },
    {
        'name': '04-helico-65km',
        'setup': """
            STATE.lapsRun = 65; STATE.lapProgress = 0.30; STATE.gold = 50000;
            if(typeof saveNow === 'function') saveNow();
        """,
        'title': 'Hélico TV 65 km',
    },
    {
        'name': '05-vasque-80km',
        'setup': """
            STATE.lapsRun = 80; STATE.lapProgress = 0.30; STATE.gold = 80000;
            if(typeof saveNow === 'function') saveNow();
        """,
        'title': 'Vasque olympique 80 km',
    },
    {
        'name': '06-apotheose-99km',
        'setup': """
            STATE.lapsRun = 99; STATE.lapProgress = 0.30; STATE.gold = 150000;
            if(typeof saveNow === 'function') saveNow();
        """,
        'title': 'Apothéose 99 km',
    },
    {
        'name': '07-sunset',
        'setup': """
            STATE.saison = 5; STATE.selectedStadiumId = 'sunset';
            STATE.lapsRun = 40; STATE.lapProgress = 0.40;
            if(typeof saveNow === 'function') saveNow();
        """,
        'title': 'Saison Sunset',
    },
    {
        'name': '08-cosmic',
        'setup': """
            STATE.saison = 8; STATE.selectedStadiumId = 'cosmic';
            STATE.lapsRun = 60; STATE.lapProgress = 0.40;
            if(typeof saveNow === 'function') saveNow();
        """,
        'title': 'Saison Cosmic',
    },
    {
        'name': '09-upgrades',
        'setup': """
            STATE.saison = 1; STATE.selectedStadiumId = 'municipal';
            STATE.lapsRun = 25; STATE.lapProgress = 0.50; STATE.gold = 5000;
            STATE.upgradeTapValue = 5; STATE.upgradeCritChance = 3;
            if(typeof saveNow === 'function') saveNow();
            const upgTab = document.querySelector('[data-tab="upgrades"]');
            if(upgTab) upgTab.click();
        """,
        'title': 'Onglet Upgrades',
    },
    {
        'name': '10-menu',
        'setup': """
            document.getElementById('menu-toggle')?.click();
        """,
        'title': 'Menu hamburger',
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
            if scene['setup']:
                await page.evaluate(scene['setup'])
                await page.wait_for_timeout(800)
            else:
                await page.wait_for_timeout(400)

            path = f"D:/alchimia/screenshots/{scene['name']}.png"
            await page.screenshot(path=path, full_page=False)
            print(f"OK: {scene['title']} -> {path}")

        await browser.close()
        print("\nDone. Open D:/alchimia/screenshots/")


asyncio.run(main())
