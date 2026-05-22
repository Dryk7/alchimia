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
        page.on('pageerror', lambda e: errors.append(('PAGE', str(e))))
        page.on('console', lambda m: (
            errors.append(('CONS_ERR', m.text)) if m.type == 'error' else
            (warnings.append(m.text) if m.type == 'warning' else None)
        ))
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle', timeout=20000)
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(2500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Tester tout : modals + tous les boutons internes
        for km in [1, 8, 25, 50, 75, 100, 105]:
            print(f'--- km={km} ---', flush=True)
            await page.evaluate(f'''if(window.STATE){{
                STATE.lapsRun = {km};
                STATE.totalTaps = 200;
                STATE.alchLevel = 25;
                STATE.coins = 100000;
                STATE.gems = 500;
                STATE.runeCount = 50;
                if(STATE.cards) STATE.cards.collected = STATE.cards.collected || {{}};
            }}''')
            await page.wait_for_timeout(500)

            # Ouvrir chaque modal et cliquer sur les boutons internes
            modal_pairs = [
                ('menu-toggle', 'menu-modal'),
                ('codex-toggle', 'cards-modal'),
                ('help-toggle', 'guide-modal'),
                ('quest-toggle', 'quests-daily-modal'),
            ]
            for btn, modal in modal_pairs:
                try:
                    await page.evaluate(f'document.getElementById("{btn}")?.click()')
                    await page.wait_for_timeout(300)
                    # Cliquer tous les boutons dans le modal ouvert
                    n = await page.evaluate(f'''(() => {{
                        const m = document.getElementById("{modal}");
                        if(!m || !m.classList.contains("show")) return 0;
                        const btns = Array.from(m.querySelectorAll("button, [role=button]")).slice(0, 5);
                        let c = 0;
                        for(const b of btns){{
                            try{{ b.click(); c++; }}catch(e){{}}
                        }}
                        return c;
                    }})()''')
                    await page.wait_for_timeout(300)
                    # Fermer tout
                    await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
                    await page.wait_for_timeout(100)
                except Exception as ex:
                    print(f'  [exception {btn}] {ex}')

            # Test des fonctions globales si exposées
            await page.evaluate('''
                try { if(typeof openCards === "function") openCards(); } catch(e){}
                try { if(typeof openShop === "function") openShop(); } catch(e){}
                try { if(typeof showOffline === "function") showOffline(); } catch(e){}
            ''')
            await page.wait_for_timeout(300)
            await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Test scroll / resize
        await page.evaluate('window.scrollTo(0, 500)')
        await page.wait_for_timeout(300)

        print(f'\nERREURS: {len(errors)}')
        for e in errors[:30]: print(f'  {e}')
        print(f'\nWARNINGS: {len(warnings)}')
        for w in warnings[:20]: print(f'  {w[:300]}')
        await browser.close()

asyncio.run(main())
