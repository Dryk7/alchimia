"""Vérifie sprint juice : trail + sueur + vignette + ombrage."""
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
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true; STATE.totalTaps=200; STATE.lapsRun=15;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Test 1 : héros au repos (baseline) - pas de trail
        await page.wait_for_timeout(800)
        kmh_idle = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/JUICE-1-idle.png', clip={'x':0,'y':0,'width':540,'height':960})
        print(f'[IDLE] km/h = {kmh_idle}')

        # Test 2 : forcer un displayKmh haut pour sprint juice
        # Via hack : modifier directement la variable interne via RUNNER_2D si exposé
        # Sinon, on simule des taps massifs
        await page.evaluate('''(()=>{
            if(window.RUNNER_2D && window.RUNNER_2D._debugMode){
                // Pas de setter direct sur displayKmh, mais on peut influencer via tapCount
            }
            // Brute force : spam tap programmatique
        })()''')
        # Simule 200 taps sur le stadium en 4s
        for _ in range(80):
            await page.evaluate('''(()=>{
                const stad = document.getElementById('runner-stadium');
                if(stad){
                    const evt = new PointerEvent('pointerdown', {bubbles:true, clientX: 270, clientY: 600});
                    stad.dispatchEvent(evt);
                }
            })()''')
            await page.wait_for_timeout(50)
        kmh_sprint = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/JUICE-2-sprint.png', clip={'x':0,'y':0,'width':540,'height':960})
        print(f'[SPRINT] km/h = {kmh_sprint}')

        # Continue sprint 2s de plus
        for _ in range(40):
            await page.evaluate('''(()=>{
                const stad = document.getElementById('runner-stadium');
                if(stad) stad.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, clientX: 270, clientY: 600}));
            })()''')
            await page.wait_for_timeout(50)
        kmh_max = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/JUICE-3-max.png', clip={'x':0,'y':0,'width':540,'height':960})
        print(f'[MAX] km/h = {kmh_max}')

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
