import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        errors = []
        warnings = []
        info_count = [0]
        page.on('pageerror', lambda e: errors.append(('PAGE', str(e))))
        page.on('console', lambda m: (
            errors.append(('CONS_ERR', m.text)) if m.type == 'error' else
            (warnings.append(m.text) if m.type == 'warning' else None)
        ))
        # PAS de localStorage preset : premier lancement total
        await page.goto('http://localhost:8770', wait_until='networkidle', timeout=20000)
        await page.wait_for_timeout(2000)
        print('=== Premier lancement (clean) ===')
        print(f'ERREURS: {len(errors)}')
        for e in errors[:30]: print(f'  {e}')
        print(f'WARNINGS: {len(warnings)}')
        for w in warnings[:20]: print(f'  {w[:300]}')

        # Cliquer start
        await page.evaluate('document.getElementById("start-btn")?.click()')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
        print(f'\n=== Apres start ===')
        print(f'ERREURS: {len(errors)}')
        print(f'WARNINGS: {len(warnings)}')

        # Test ascension (saison)
        await page.evaluate('''if(window.STATE){
            STATE.lapsRun = 110;
            STATE.totalTaps = 5000;
            STATE.alchLevel = 50;
        }''')
        await page.wait_for_timeout(500)
        await page.evaluate('document.getElementById("saison-ascend-btn")?.click()')
        await page.wait_for_timeout(800)
        print(f'\n=== Apres saison-ascend ===')
        print(f'ERREURS: {len(errors)}')
        for e in errors[:30]: print(f'  {e}')
        print(f'WARNINGS: {len(warnings)}')
        for w in warnings[:20]: print(f'  {w[:300]}')

        # Test reset
        await page.evaluate('document.getElementById("reset-confirm-modal")?.classList.add("show")')
        await page.wait_for_timeout(400)

        # Final
        print(f'\n=== FINAL ===')
        print(f'ERREURS: {len(errors)}')
        for e in errors[:30]: print(f'  {e}')
        print(f'WARNINGS: {len(warnings)}')
        for w in warnings[:20]: print(f'  {w[:300]}')

        await browser.close()

asyncio.run(main())
