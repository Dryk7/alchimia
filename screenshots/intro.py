"""Capture l'écran d'accueil retravaillé."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await context.new_page()
        console_errors = []
        page.on('pageerror', lambda exc: console_errors.append(str(exc)))
        page.on('console', lambda msg: console_errors.append(f'console.{msg.type}: {msg.text}') if msg.type == 'error' else None)
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2500)  # Laisse les anims démarrer
        await page.screenshot(path='D:/alchimia/screenshots/intro-v2-t1.png')
        print('OK -> intro-v2-t1.png')
        await page.wait_for_timeout(1500)
        await page.screenshot(path='D:/alchimia/screenshots/intro-v2-t2.png')
        print('OK -> intro-v2-t2.png')
        if console_errors:
            print('\n=== ERRORS ===')
            for e in console_errors:
                print(e)
        else:
            print('No errors.')
        await browser.close()


asyncio.run(main())
