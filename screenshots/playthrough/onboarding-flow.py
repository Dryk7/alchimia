"""Test l'expérience d'un VRAI nouveau joueur (pas de localStorage)."""
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
        await page.evaluate('localStorage.clear();')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/ONBOARD-01-splash.png')
        print('OK 01 splash')

        # Click PRENDRE LE DÉPART
        await page.evaluate('document.getElementById("start-btn")?.click();')
        await page.wait_for_timeout(1500)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/ONBOARD-02-story.png')
        print('OK 02 story affichée')

        # Click JE SUIS PRÊT
        await page.evaluate('document.getElementById("story-go")?.click();')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/ONBOARD-03-active-tuto-step1.png')
        print('OK 03 ActiveTuto step 1 (BIENVENUE)')

        # Click COMMENCER
        await page.evaluate('document.getElementById("tuto-next")?.click();')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/ONBOARD-04-active-tuto-step2.png')
        print('OK 04 ActiveTuto step 2 (TAP)')

        # Simule 1 tap
        await page.evaluate('document.getElementById("runner-stadium")?.click();')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/ONBOARD-05-after-1tap.png')
        print('OK 05 après 1 tap')

        # 5 taps de plus pour valider step 2 (6 taps total)
        for _ in range(6):
            await page.evaluate('document.getElementById("runner-stadium")?.click();')
            await page.wait_for_timeout(100)
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/ONBOARD-06-after-6taps.png')
        print('OK 06 après 6 taps')

        # Forcer 1 km pour passer plus loin dans le tuto
        await page.evaluate('STATE.lapsRun = 1;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/ONBOARD-07-1km.png')
        print('OK 07 1km')

        print(f'\nErrors: {len(errors)}')
        for e in errors[:5]: print(f'  - {e[:200]}')
        await browser.close()

asyncio.run(main())
