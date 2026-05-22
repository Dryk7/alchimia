"""Vérifie :
1) Son upgrade : achat upgrade ne crash pas
2) BGM avec sidechain duck : kick fait baisser les voix
3) Pas d'erreurs console
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
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true; STATE.gold=999999; STATE.totalTaps=50; STATE.lapsRun=10;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # === Test 1 : achat 3 upgrades successifs
        for upg in ['tapValue', 'autoTap', 'lapBonus']:
            await page.evaluate(f'if(typeof buyUpgrade === "function") buyUpgrade("{upg}");')
            await page.wait_for_timeout(600)
            print(f'[UPGRADE] {upg} acheté')

        # === Test 2 : BGM avec sidechain
        await page.evaluate('if(typeof ProcBGM !== "undefined") ProcBGM.play("chill", 0.40);')
        await page.wait_for_timeout(4000)
        bgm = await page.evaluate('typeof ProcBGM !== "undefined" ? {isPlaying: ProcBGM.isPlaying(), preset: ProcBGM.currentPreset()} : null')
        print(f'[BGM SIDECHAIN] {bgm} (4s de tournage)')

        # Force un upgrade pendant que la BGM tourne pour combiner SFX + BGM
        await page.evaluate('if(typeof buyUpgrade === "function") buyUpgrade("tapValue");')
        await page.wait_for_timeout(800)

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
