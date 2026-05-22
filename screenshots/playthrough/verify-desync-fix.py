"""Vérifie le fix desync : décor et héros doivent être SYNCHRONES.
- AVANT 1er tap : décor immobile + héros immobile.
- APRÈS 1er tap (baseline) : décor lent (proportionnel à runnerBaseSpeed) + jambes lentes.
- TAP intensif : décor rapide + jambes rapides.
"""
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
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true; STATE.totalTaps=0;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # 1) AVANT 1er TAP — decorScroll devrait quasi pas bouger
        await page.wait_for_timeout(500)
        m1 = await page.evaluate('''(()=>{
            const r2d = window.RUNNER_2D || {};
            return {
                totalTaps: window.STATE?.totalTaps || 0,
                runnerBaseSpeed: typeof runnerBaseSpeed === 'function' ? runnerBaseSpeed() : 'N/A',
            };
        })()''')
        # Sample decorScroll over 1s and see how much it changed
        d_before = await page.evaluate('window._decorSnapshot = (window.STATE?.totalTaps||0); 0')
        # Hack : we can't easily read decorScroll from outside. Snapshot via canvas pixel diff instead.
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/SYNC-1-before-tap-t0.png', clip={'x':0,'y':0,'width':540,'height':960})
        await page.wait_for_timeout(2000)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/SYNC-1-before-tap-t2s.png', clip={'x':0,'y':0,'width':540,'height':960})
        print(f'[1] AVANT tap : totalTaps={m1["totalTaps"]}, runnerBaseSpeed={m1["runnerBaseSpeed"]}')
        print('    → Compare SYNC-1-before-tap-t0.png et SYNC-1-before-tap-t2s.png : doivent être IDENTIQUES (décor immobile)')

        # 2) Donne 1 tap puis attends
        await page.evaluate('if(window.STATE){STATE.totalTaps = 1;}')
        await page.wait_for_timeout(300)
        m2 = await page.evaluate('''(()=>({
            totalTaps: window.STATE?.totalTaps || 0,
            runnerBaseSpeed: typeof runnerBaseSpeed === 'function' ? runnerBaseSpeed() : 'N/A',
        }))()''')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/SYNC-2-after-1tap-t0.png', clip={'x':0,'y':0,'width':540,'height':960})
        await page.wait_for_timeout(2000)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/SYNC-2-after-1tap-t2s.png', clip={'x':0,'y':0,'width':540,'height':960})
        print(f'[2] APRÈS 1 tap : totalTaps={m2["totalTaps"]}, runnerBaseSpeed={m2["runnerBaseSpeed"]}')
        print('    → Décor doit légèrement scroller (baseline 0.4)')

        # 3) Bursts de taps (simule rage tap)
        for _ in range(30):
            await page.evaluate('if(typeof tapBoost === "function") tapBoost(); if(window.STATE){STATE.totalTaps = (STATE.totalTaps||0)+1;}')
            await page.wait_for_timeout(40)
        await page.wait_for_timeout(200)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/SYNC-3-rage-tap-t0.png', clip={'x':0,'y':0,'width':540,'height':960})
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/SYNC-3-rage-tap-t08s.png', clip={'x':0,'y':0,'width':540,'height':960})
        print('[3] RAGE TAP : décor doit défiler RAPIDEMENT')

        await browser.close()

asyncio.run(main())
