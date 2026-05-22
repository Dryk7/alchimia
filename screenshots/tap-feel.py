"""Test la réactivité du tap : simule 10 taps en 1s et capture chaque frame."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await context.new_page()
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.evaluate("""
            document.getElementById('start-btn')?.click();
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
        """)
        await page.wait_for_timeout(800)
        # Mesure le lapProgress avant taps
        before = await page.evaluate("({ lp: STATE.lapProgress, gold: STATE.gold })")
        print(f'AVANT 20 taps: lp={before["lp"]:.4f}, gold={before["gold"]}')
        # Simule 20 taps rapides sur le stade
        stadium_box = await page.evaluate("""
            (() => {
              const el = document.getElementById('runner-stadium');
              const r = el.getBoundingClientRect();
              return { x: r.left + r.width/2, y: r.top + r.height/2 };
            })()
        """)
        for i in range(20):
            await page.mouse.click(stadium_box['x'], stadium_box['y'])
            await page.wait_for_timeout(100)  # 10 taps/sec
        await page.wait_for_timeout(200)
        after = await page.evaluate("({ lp: STATE.lapProgress, gold: STATE.gold })")
        print(f'APRÈS 20 taps : lp={after["lp"]:.4f}, gold={after["gold"]}')
        delta = after["lp"] - before["lp"]
        print(f'  delta lapProgress = {delta:.4f} (attendu 0.04+ pour ressentir leffet)')
        print(f'  delta gold = {after["gold"] - before["gold"]} med')
        # Screenshot final
        await page.screenshot(path='D:/alchimia/screenshots/tap-feel-after.png')
        print('OK -> tap-feel-after.png')
        if errors:
            print('\n=== ERRORS ===')
            for e in errors[:5]: print(e)
        await browser.close()


asyncio.run(main())
