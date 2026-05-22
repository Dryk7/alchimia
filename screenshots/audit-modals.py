"""Audit visuel : capture chaque modal du jeu pour évaluer la cohérence design."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        await page.goto('http://localhost:8770?debug=1')
        await page.evaluate('localStorage.setItem("foulee.storySeen", "1");')
        await page.evaluate('document.getElementById("start-btn")?.click(); STATE.starterPackDeclined = true; STATE.starterPackClaimed = true; STATE.lapsRun = 50; STATE.gold = 5000000; STATE.gems = 200; STATE.stars = 25; STATE.alchLevel = 30;')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m => { m.classList.remove("show"); m.style.display = "none"; });')

        # === Modal list to audit ===
        modals = [
            ('menu-modal',           'function: openModal("menu-modal")'),
            ('settings-modal',       'function: openModal("settings-modal")'),
            ('credits-modal',        'function: openModal("credits-modal")'),
            ('guide-modal',          'function: document.getElementById("help-toggle").click()'),
            ('records-modal',        'function: if(typeof openRecords === "function") openRecords()'),
            ('shop-modal',           'function: if(typeof openShopModal === "function") openShopModal()'),
            ('daily-modal',          'function: if(typeof openDailyModal === "function") openDailyModal()'),
            ('quests-daily-modal',   'function: if(typeof openQuestsModal === "function") openQuestsModal()'),
            ('stats-modal',          'function: if(typeof renderStatsBody === "function") renderStatsBody(); openModal("stats-modal")'),
            ('saison-modal',         'function: if(typeof openSaisonModal === "function") openSaisonModal()'),
            ('wardrobe-modal',       'function: if(typeof openWardrobe === "function") openWardrobe()'),
            ('equip-modal',          'function: if(typeof openEquip === "function") openEquip()'),
            ('cards-modal',          'function: if(typeof openCardCollection === "function") openCardCollection()'),
            ('chests-modal',         'function: if(typeof openChestsModal === "function") openChestsModal()'),
            ('map-stadiums-modal',   'function: if(typeof openMapStadiums === "function") openMapStadiums()'),
            ('runner-profile-modal', 'function: if(typeof openRunnerProfile === "function") openRunnerProfile()'),
        ]

        for modal_id, opener in modals:
            # Close all
            await page.evaluate('document.querySelectorAll(".modal.show").forEach(m => { m.classList.remove("show"); m.style.display = ""; });')
            await page.wait_for_timeout(150)
            # Try to open
            try:
                cmd = opener.replace('function: ', '')
                await page.evaluate(cmd)
                await page.wait_for_timeout(400)
                # Verify it opened
                is_visible = await page.evaluate(f'(()=>{{const m=document.getElementById("{modal_id}");return m && m.classList.contains("show");}})()')
                if not is_visible:
                    # Force show
                    await page.evaluate(f'document.getElementById("{modal_id}")?.classList.add("show")')
                    await page.wait_for_timeout(300)
                await page.screenshot(path=f'D:/alchimia/screenshots/audit-{modal_id}.png')
                print(f'OK -> audit-{modal_id}.png')
            except Exception as e:
                print(f'SKIP {modal_id}: {str(e)[:100]}')

        print(f'\nErrors: {len(errors)}')
        for e in errors[:3]: print(f'  - {e[:200]}')
        await browser.close()


asyncio.run(main())
