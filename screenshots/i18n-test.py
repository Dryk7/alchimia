"""Test du système i18n FR/EN."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Force EN navigateur
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2, locale='en-US')
        page = await context.new_page()
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.evaluate('localStorage.clear();')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2500)
        lang = await page.evaluate('window.getLang ? window.getLang() : "?"')
        print(f'Detected lang: {lang}')
        # Capture intro EN
        await page.screenshot(path='D:/alchimia/screenshots/i18n-intro-en.png')
        print('OK -> i18n-intro-en.png')
        # Vérifier le tagline et le bouton
        tagline = await page.evaluate('document.querySelector(".tagline")?.innerHTML')
        startBtn = await page.evaluate('document.getElementById("start-btn")?.textContent')
        print(f'Tagline EN: {tagline}')
        print(f'Start button EN: {startBtn}')
        # Start the game in EN
        await page.evaluate('document.getElementById("start-btn")?.click();')
        await page.wait_for_timeout(1500)
        await page.screenshot(path='D:/alchimia/screenshots/i18n-story-en.png')
        print('OK -> i18n-story-en.png')
        story_title = await page.evaluate('document.querySelector(".story-title")?.innerHTML')
        story_go = await page.evaluate('document.getElementById("story-go")?.textContent')
        print(f'Story title EN: {story_title}')
        print(f'Story go button EN: {story_go}')
        # Switch to FR mid-game
        await page.evaluate('window.setLang("fr")')
        await page.wait_for_timeout(300)
        story_title_fr = await page.evaluate('document.querySelector(".story-title")?.innerHTML')
        story_go_fr = await page.evaluate('document.getElementById("story-go")?.textContent')
        print(f'Story title FR (apres switch): {story_title_fr}')
        print(f'Story go FR: {story_go_fr}')
        await page.screenshot(path='D:/alchimia/screenshots/i18n-story-fr.png')
        if errors:
            print('ERRORS:')
            for e in errors[:3]: print(f'  - {e[:200]}')
        await browser.close()


asyncio.run(main())
