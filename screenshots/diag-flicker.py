"""Capture 10 frames consécutives au démarrage pour identifier les scintillements."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await context.new_page()
        errors = []
        warnings = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        page.on('console', lambda m: warnings.append(f'{m.type}:{m.text}') if m.type in ('warning', 'error') else None)
        # Clear localStorage pour first-launch experience
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.clear();')
        await page.reload()
        await page.wait_for_load_state('networkidle')

        # Capture toutes les 200ms pendant 4 sec
        for i in range(20):
            await page.screenshot(path=f'D:/alchimia/screenshots/diag-frame-{i:02d}.png')
            await page.wait_for_timeout(200)

        # Click start et continue capture
        await page.evaluate('document.getElementById("start-btn")?.click();')
        for i in range(20, 40):
            await page.screenshot(path=f'D:/alchimia/screenshots/diag-frame-{i:02d}.png')
            await page.wait_for_timeout(200)

        # Check what's visible
        visible_layers = await page.evaluate('''(() => {
            const out = {};
            ['intro', 'story-intro', 'daily-modal', 'reset-confirm-modal', 'menu-modal', 'tuto-hint', 'tier-banner', 'unlock-overlay'].forEach(id => {
              const el = document.getElementById(id);
              if(!el) return;
              const cs = getComputedStyle(el);
              out[id] = {
                display: cs.display,
                visibility: cs.visibility,
                opacity: cs.opacity,
                hasShow: el.classList.contains('show'),
                hasGone: el.classList.contains('gone'),
              };
            });
            // Check classes on html for accessibility
            out._html_classes = document.documentElement.className;
            return out;
        })()''')
        print('VISIBLE LAYERS at end:')
        for k, v in visible_layers.items():
            print(f'  {k}: {v}')

        print(f'\nERRORS: {len(errors)}')
        for e in errors[:5]: print(f'  - {e[:200]}')
        print(f'WARNINGS: {len(warnings)}')
        for w in warnings[:10]: print(f'  - {w[:200]}')
        await browser.close()


asyncio.run(main())
