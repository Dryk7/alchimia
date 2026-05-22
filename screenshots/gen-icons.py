"""Génère les 4 icônes PNG via Playwright + le canvas HTML."""
import asyncio
import base64
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('http://localhost:8770/screenshots/icon-gen.html')
        await page.wait_for_load_state('networkidle')

        for size, maskable, fname in [
            (192, False, 'icon-192.png'),
            (192, True,  'icon-192-maskable.png'),
            (512, False, 'icon-512.png'),
            (512, True,  'icon-maskable-512.png'),
            (1024, False, 'icon-1024.png'),  # bonus pour Play Store
        ]:
            data_url = await page.evaluate(f"window.__renderSize({size}, {str(maskable).lower()})")
            # data_url = "data:image/png;base64,..."
            _, b64 = data_url.split(',', 1)
            data = base64.b64decode(b64)
            out_path = f'D:/alchimia/assets/{fname}'
            with open(out_path, 'wb') as f:
                f.write(data)
            print(f'OK -> {out_path} ({len(data)} bytes)')

        await browser.close()


asyncio.run(main())
