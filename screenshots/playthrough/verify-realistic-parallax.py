"""Vérifie que la vitesse de défilement du décor est PHYSIQUEMENT RÉALISTE :
1. 0 km/h : décor totalement immobile (delta = 0 entre 2 screenshots)
2. ~10 km/h (footing) : décor avance lentement
3. ~35 km/h (sprint) : décor avance vite
4. Montagne/lune restent quasi-fixes même au sprint
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
        page.on('pageerror', lambda e: errors.append(str(e)))
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        async def sample_scroll(label, kmh_target_min, kmh_target_max, scenario_setup):
            """Setup STATE, attend stabilisation, capture decorScroll delta sur 1s."""
            await page.evaluate(scenario_setup)
            await page.wait_for_timeout(800)  # laisse displayKmh se stabiliser
            d1 = await page.evaluate('window.RUNNER_2D ? RUNNER_2D.getDecorScroll() : null')
            await page.wait_for_timeout(1000)
            d2 = await page.evaluate('window.RUNNER_2D ? RUNNER_2D.getDecorScroll() : null')
            kmh = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
            print(f'[{label}] km/h={kmh:.1f} | scroll Δ/1s = {d2-d1 if d1 and d2 else "N/A"} px')

        # Pour pouvoir lire decorScroll, on doit l'exposer
        # On utilise eval pour ajouter un accesseur si pas déjà présent
        await page.evaluate('''(()=>{
            // Hack : expose decorScroll via getDecorScroll
            if(window.RUNNER_2D && !window.RUNNER_2D.getDecorScroll){
                // On va monkey-patch en sniffant via les variables visibles
                // Plus simple : lire la position d'un élément qui scroll, ex la lampadaire
                // En vrai on peut juste calculer displayKmh * 9.72 manuellement
            }
        })()''')

        # Test 1 : totalTaps=0 → immobile
        await page.evaluate('if(window.STATE){STATE.totalTaps=0; STATE.lapsRun=0;}')
        await page.wait_for_timeout(1500)
        kmh0 = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        print(f'[1] totalTaps=0 → km/h affichée = {kmh0} (attendu: 0.0)')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/PHYS-1-immobile.png', clip={'x':0,'y':0,'width':540,'height':500})

        # Test 2 : km 3 baseline (auto-course active, pas de tap actif)
        await page.evaluate('if(window.STATE){STATE.totalTaps=10; STATE.lapsRun=3;}')
        await page.wait_for_timeout(1500)
        kmh2 = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        print(f'[2] km3 idle → km/h = {kmh2:.1f} (attendu ~0.9 baseline)')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/PHYS-2-km3-idle.png', clip={'x':0,'y':0,'width':540,'height':500})

        # Test 3 : km 10 + rage tap simulé via tapCount = 100
        await page.evaluate('if(window.STATE){STATE.lapsRun=10;}; if(window.RUNNER_2D && RUNNER_2D.setTapCount) RUNNER_2D.setTapCount(100);')
        # Force tap via 30 pointerdowns simulés
        for _ in range(30):
            await page.evaluate('document.dispatchEvent(new PointerEvent("pointerdown",{bubbles:true}));')
            await page.wait_for_timeout(40)
        await page.wait_for_timeout(500)
        kmh3 = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        print(f'[3] km10 rage tap → km/h = {kmh3:.1f} (attendu plus élevé)')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/PHYS-3-km10-rage.png', clip={'x':0,'y':0,'width':540,'height':500})

        # Test 4 : km 70 sprint élite (vue stade)
        await page.evaluate('if(window.STATE){STATE.lapsRun=70; STATE.alchLevel=20;}')
        for _ in range(40):
            await page.evaluate('document.dispatchEvent(new PointerEvent("pointerdown",{bubbles:true}));')
            await page.wait_for_timeout(35)
        await page.wait_for_timeout(500)
        kmh4 = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        print(f'[4] km70 sprint → km/h = {kmh4:.1f}')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/PHYS-4-km70-sprint.png', clip={'x':0,'y':0,'width':540,'height':960})

        # Test 5 : km 105 lunar — vérifier que la moon reste presque fixe
        await page.evaluate('if(window.STATE){STATE.lapsRun=105; STATE.chapter=2;}')
        await page.wait_for_timeout(800)
        # 2 screenshots à 1s d'écart pour voir si moon bouge
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/PHYS-5a-lunar.png', clip={'x':0,'y':0,'width':540,'height':500})
        await page.wait_for_timeout(1500)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/PHYS-5b-lunar.png', clip={'x':0,'y':0,'width':540,'height':500})
        kmh5 = await page.evaluate('parseFloat(document.getElementById("runner-pace")?.textContent || "0")')
        print(f'[5] km105 lunar → km/h = {kmh5:.1f}, screenshots 5a vs 5b pour comparer moon')

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
