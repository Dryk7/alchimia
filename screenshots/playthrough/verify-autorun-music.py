"""Vérifie :
1) Avant km 3 : runnerBaseSpeed = 0 même après tap (pas d'AUTO-COURSE)
2) Au km 3 : runnerBaseSpeed = 0.4 baseline (AUTO-COURSE débloquée)
3) Musique CHILL démarre sans erreur (counter-melody + shaker présents)
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
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.setItem("foulee.storySeen","1"); localStorage.setItem("foulee.tutoV3","done"); localStorage.setItem("foulee.activeTutoV1","done");')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true; STATE.totalTaps=0; STATE.lapsRun=0;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # === 1) totalTaps=0 → baseline 0 (immobile)
        r0 = await page.evaluate('runnerBaseSpeed()')
        print(f'[1] totalTaps=0 lapsRun=0  → runnerBaseSpeed = {r0} (attendu: 0)')

        # === 2) 1 tap, km 0 → toujours baseline 0 (AUTO-COURSE pas active avant km 3)
        await page.evaluate('STATE.totalTaps = 1; STATE.lapsRun = 0;')
        r1 = await page.evaluate('runnerBaseSpeed()')
        print(f'[2] totalTaps=1 lapsRun=0  → runnerBaseSpeed = {r1} (attendu: 0 — AUTO-COURSE non débloquée)')

        # === 3) 10 taps, km 1 → toujours baseline 0
        await page.evaluate('STATE.totalTaps = 10; STATE.lapsRun = 1;')
        r2 = await page.evaluate('runnerBaseSpeed()')
        print(f'[3] totalTaps=10 lapsRun=1 → runnerBaseSpeed = {r2} (attendu: 0)')

        # === 4) km 2 (encore avant km 3) → baseline 0
        await page.evaluate('STATE.lapsRun = 2;')
        r3 = await page.evaluate('runnerBaseSpeed()')
        print(f'[4] totalTaps=10 lapsRun=2 → runnerBaseSpeed = {r3} (attendu: 0)')

        # === 5) km 3 → baseline 0.4 (AUTO-COURSE débloquée !)
        await page.evaluate('STATE.lapsRun = 3;')
        r4 = await page.evaluate('runnerBaseSpeed()')
        print(f'[5] totalTaps=10 lapsRun=3 → runnerBaseSpeed = {r4} (attendu: 0.4 — WOW moment)')

        # === 6) Avec upgrade autoTap niveau 1 (avant km 3) → baseline = 0.15 (upgrade rend qqch)
        await page.evaluate('STATE.lapsRun = 1; STATE.upgradeAutoTap = 1;')
        r5 = await page.evaluate('runnerBaseSpeed()')
        print(f'[6] km=1 + upgrade autoTap=1 → runnerBaseSpeed = {r5} (attendu: 0.15 — l\'upgrade donne déjà du baseline)')

        # === 7) Vérifier la musique
        await page.evaluate('STATE.totalTaps = 100; STATE.lapsRun = 10; STATE.upgradeAutoTap = 0;')
        bgm_info = await page.evaluate('''(()=>({
            isPlaying: typeof ProcBGM !== 'undefined' ? ProcBGM.isPlaying() : 'no proc',
            preset: typeof ProcBGM !== 'undefined' ? ProcBGM.currentPreset() : 'no proc',
        }))()''')
        print(f'[7] BGM état : {bgm_info}')

        # Force la musique chill
        await page.evaluate('if(typeof ProcBGM !== "undefined") ProcBGM.play("chill", 0.30);')
        await page.wait_for_timeout(3000)  # laisser tourner 3s pour vérifier qu'aucune erreur ne survient
        bgm_after = await page.evaluate('''(()=>({
            isPlaying: typeof ProcBGM !== 'undefined' ? ProcBGM.isPlaying() : 'no proc',
            preset: typeof ProcBGM !== 'undefined' ? ProcBGM.currentPreset() : 'no proc',
        }))()''')
        print(f'[8] BGM après 3s : {bgm_after}')
        print(f'[9] Erreurs console : {len(errors)}')
        for e in errors[:5]: print(f'    {e[:200]}')

        await browser.close()

asyncio.run(main())
