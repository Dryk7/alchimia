"""Vérifie :
1) maybeDropItem() donne Bois au km normal, Argent au km 5, Légendaire au km 25/50/75/100
2) UPGRADES_TAP contient eagleEye (nouvelle upgrade)
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
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Test 1 : km 1 → bois, km 5 → argent, km 25 → légendaire
        for km in [1, 5, 25, 50, 75, 100]:
            await page.evaluate(f'STATE.lapsRun = {km}; STATE.chests = {{wood:0,iron:0,gold:0,legendary:0}}; if(typeof maybeDropItem === "function") maybeDropItem();')
            chests = await page.evaluate('STATE.chests')
            print(f'[km{km:3d}] coffre obtenu : {chests}')

        # Test 2 : upgrade eagleEye existe
        upg_info = await page.evaluate('''(()=>({
            has_eagleEye: typeof UPGRADES_TAP !== "undefined" && !!UPGRADES_TAP.eagleEye,
            cost_lvl_0: typeof UPGRADES_TAP !== "undefined" ? UPGRADES_TAP.eagleEye?.base : null,
            descKey: typeof UPGRADES_TAP !== "undefined" ? UPGRADES_TAP.eagleEye?.nameKey : null,
        }))()''')
        print(f'[UPGRADE] {upg_info}')

        # Test 3 : i18n traduction Vision d'Aigle
        i18n = await page.evaluate('typeof t === "function" ? {name: t("upg_eagleEye"), desc: t("upg_desc_eagleEye")} : null')
        print(f'[I18N] {i18n}')

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
