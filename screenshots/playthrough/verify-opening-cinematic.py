"""Vérifie l'opening cinematic à différents moments :
T=0.3s : sub-bass build, écran sombre
T=1.6s : logo apparaît avec flash
T=2.6s : strings montants
T=3.6s : tagline visible
T=5.0s : disparaît
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
        page.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type in ('error',) else None)
        # Clear localStorage AVANT tout chargement via init script
        await ctx.add_init_script("try { localStorage.removeItem('foulee.openingSeen'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='domcontentloaded')

        # Capture à T=0.3s : début (sub-bass, écran rouge naissant)
        await page.wait_for_timeout(300)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/OPENING-T0.3-build.png', clip={'x':0,'y':0,'width':540,'height':960})

        # T=1.6s : flash + logo IN
        await page.wait_for_timeout(1300)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/OPENING-T1.6-impact.png', clip={'x':0,'y':0,'width':540,'height':960})

        # T=2.6s : strings montants + rayons
        await page.wait_for_timeout(1000)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/OPENING-T2.6-rays.png', clip={'x':0,'y':0,'width':540,'height':960})

        # T=3.6s : tagline en place + sustain triomphal
        await page.wait_for_timeout(1000)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/OPENING-T3.6-tagline.png', clip={'x':0,'y':0,'width':540,'height':960})

        # T=5.5s : opening doit être disparu, splash visible
        await page.wait_for_timeout(1900)
        oc_display = await page.evaluate('''(()=>{
            const oc = document.getElementById('opening-cinematic');
            const intro = document.getElementById('intro');
            return {
                oc_exists: !!oc,
                oc_displayed: oc ? getComputedStyle(oc).display : 'none',
                oc_opacity: oc ? getComputedStyle(oc).opacity : '0',
                intro_visible: intro ? getComputedStyle(intro).display !== 'none' : false,
                seen: localStorage.getItem("foulee.openingSeen")
            };
        })()''')
        print(f'[T=5.5s] {oc_display}')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/OPENING-T5.5-splash.png', clip={'x':0,'y':0,'width':540,'height':960})

        # Test 2 : 2e visite, opening skip auto
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(400)
        oc_2nd = await page.evaluate('''(()=>{
            const oc = document.getElementById('opening-cinematic');
            return {
                oc_displayed: oc ? getComputedStyle(oc).display : 'none',
                seen: localStorage.getItem("foulee.openingSeen")
            };
        })()''')
        print(f'[2e visite] {oc_2nd}')

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
