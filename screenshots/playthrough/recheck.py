"""Re-capture les écrans critiques après les fixes."""
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
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.setItem("foulee.storySeen","1"); localStorage.setItem("foulee.tutoV3","done");')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); STATE.starterPackDeclined=true; STATE.starterPackClaimed=true; STATE.lapsRun = 50; STATE.gold = 5000000; STATE.gems = 200; STATE.stars = 15; STATE.alchLevel = 25; STATE.alchXp = 999999;')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show, .modal").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
        await page.wait_for_timeout(300)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/AFTER-km50.png')
        print('OK -> AFTER-km50.png')

        # Tester modals critiques (le fix)
        for mid, opener in [
            ('settings-modal', 'document.getElementById("settings-modal").classList.add("show")'),
            ('credits-modal',  'document.getElementById("credits-modal").classList.add("show")'),
            ('stats-modal',    'if(typeof renderStatsBody === "function") renderStatsBody(); document.getElementById("stats-modal").classList.add("show")'),
            ('records-modal',  'if(typeof openRecords === "function") openRecords()'),
            ('shop-modal',     'if(typeof openShopModal === "function") openShopModal()'),
            ('profile-modal','if(typeof openRunnerProfile === "function") openRunnerProfile()'),
            ('equip-modal',    'if(typeof openEquip === "function") openEquip()'),
            ('cards-modal',    'if(typeof openCardCollection === "function") openCardCollection()'),
            ('map-stadiums-modal','if(typeof openMapStadiums === "function") openMapStadiums()'),
            ('menu-modal',     'document.getElementById("menu-modal").classList.add("show")'),
            ('guide-modal',    'document.getElementById("help-toggle")?.click()'),
        ]:
            await page.evaluate('document.querySelectorAll(".modal.show, .modal").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
            await page.evaluate(f'document.getElementById("{mid}")?.style && (document.getElementById("{mid}").style.display="");')
            await page.wait_for_timeout(120)
            try:
                await page.evaluate(opener)
                await page.wait_for_timeout(400)
                await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/AFTER-{mid}.png')
                print(f'OK -> AFTER-{mid}.png')
            except Exception as e:
                print(f'SKIP {mid}: {str(e)[:80]}')

        print(f'\nErrors: {len(errors)}')
        for e in errors[:5]: print(f'  - {e[:200]}')
        await browser.close()

asyncio.run(main())
