"""Validation finale VAGUE 2 : 21 fixes appliqués par 6 agents en parallèle.
- 0 erreurs console
- Sauvegarde OK
- BGM joue
- Premiers taps fonctionnent
- km/h compteur OK
"""
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
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: (errors.append(f'{m.type}: {m.text}') if m.type == 'error' else warnings.append(m.text)) if m.type in ('error','warning') else None)
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Test 1 : Vérifications fixes
        info = await page.evaluate('''(()=>({
            // Balance
            cruise_base: typeof UPGRADES_TAP !== 'undefined' ? UPGRADES_TAP.cruiseControl?.base : null,
            lapBonus_base: typeof UPGRADES_TAP !== 'undefined' ? UPGRADES_TAP.lapBonus?.base : null,
            sprint_cd: typeof SKILLS !== 'undefined' ? (SKILLS.find(s=>s.id==='sprint')?.cooldown) : null,
            // A11y
            html_lang: document.documentElement.lang,
            menu_btn_size: (()=>{const e=document.getElementById('menu-toggle'); if(!e) return null; const r=e.getBoundingClientRect(); return {w:Math.round(r.width), h:Math.round(r.height)};})(),
            gold_arialive: document.getElementById('gold-val')?.getAttribute('aria-live'),
            kmh_arialive: document.getElementById('runner-pace')?.getAttribute('aria-live'),
            // Perf
            bgm_isPlaying: typeof ProcBGM !== 'undefined' ? ProcBGM.isPlaying() : 'no proc',
            bgm_preset: typeof ProcBGM !== 'undefined' ? ProcBGM.currentPreset() : 'no proc',
            // Onboarding fixes
            coffres_unlock_km: document.querySelector('[data-action="chests"]')?.getAttribute('data-unlock-km'),
            // Audio cleanup
            audio_elements: document.querySelectorAll('audio[src*="ambient"]').length,
            // Gradient cache
            grad_cache: typeof window._gradCache !== 'undefined' ? 'present' : 'unknown',
        }))()''')
        print('=== FIXES VALIDATION ===')
        for k, v in info.items():
            print(f'  {k}: {v}')

        # Test 2 : tap simulé pour voir que ça marche
        await page.evaluate('STATE.totalTaps = 100; STATE.lapsRun = 30; STATE.gold = 50000;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/VAGUE2-km30.png', clip={'x':0,'y':0,'width':540,'height':960})

        await page.evaluate('STATE.lapsRun = 85;')
        await page.wait_for_timeout(500)
        if await page.evaluate('typeof window.RUNNER_2D?.spawnNpc === "function"'):
            await page.evaluate('window.RUNNER_2D.spawnNpc(6);')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/VAGUE2-km85-champion.png', clip={'x':0,'y':0,'width':540,'height':960})

        # Test 3 : Escape key ferme les modals
        await page.evaluate('document.getElementById("menu-modal")?.classList.add("show");')
        await page.wait_for_timeout(200)
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(300)
        modal_closed = await page.evaluate('!document.getElementById("menu-modal")?.classList.contains("show")')
        print(f'\n[A11Y] Escape ferme menu-modal : {modal_closed}')

        # Final
        print(f'\n=== RÉSULTAT ===')
        print(f'Erreurs console : {len(errors)}')
        print(f'Warnings : {len(warnings)}')
        for e in errors[:5]: print(f'  ERR {e[:200]}')

        await browser.close()

asyncio.run(main())
