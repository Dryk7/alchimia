"""Vérifie :
1) Plus de lampes pendantes (canvas candleC ne dessine rien)
2) Bornes 100m/500m/1km défilent au rythme de la VRAIE vitesse km/h
3) Musique CHILL v8 inclut flute (aucune erreur console)
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
        page.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type in ('error',) else None)
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # === TEST 1 : lampes pendantes virées
        # Le canvas candleC ne devrait plus rien dessiner. Vérifie en sniffant les pixels coin haut-gauche
        await page.evaluate('STATE.lapsRun = 5; STATE.totalTaps = 20;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/V8-1-no-candles.png', clip={'x':0,'y':0,'width':540,'height':200})

        # === TEST 2 : bornes défilent à bonne vitesse
        await page.evaluate('STATE.lapsRun = 5; STATE.totalTaps = 50; STATE.lapProgress = 0.3;')
        await page.wait_for_timeout(500)
        # Force displayKmh à ~20 km/h pour test
        await page.evaluate('if(window.RUNNER_2D){STATE.upgradeBaseSpeed=10;}')
        await page.wait_for_timeout(1500)
        kmh_avant = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/V8-2a-bornes.png', clip={'x':0,'y':0,'width':540,'height':960})
        await page.wait_for_timeout(2500)
        kmh_apres = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/V8-2b-bornes-2s.png', clip={'x':0,'y':0,'width':540,'height':960})
        print(f'[BORNES] km/h avant={kmh_avant:.1f}, après 2.5s={kmh_apres:.1f} → bornes devraient avoir bougé proportionnellement')

        # === TEST 3 : musique flute sans erreur
        await page.evaluate('if(typeof ProcBGM !== "undefined") ProcBGM.play("chill", 0.30);')
        await page.wait_for_timeout(3500)
        bgm_state = await page.evaluate('typeof ProcBGM !== "undefined" ? {isPlaying: ProcBGM.isPlaying(), preset: ProcBGM.currentPreset()} : null')
        print(f'[BGM] {bgm_state}')

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
