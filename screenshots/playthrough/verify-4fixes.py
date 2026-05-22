"""Test les 4 fixes :
1) upgradeBaseSpeed boost bien runnerBaseSpeed
2) tier-banner au milieu vertical (top:30%), pas en bas
3) daily-btn-float en bas-gauche (loin du HUD top)
4) runner-hud-overlay descendu sous le burger (top 44+)
5) NPC fromBehind spawn quand player inactif
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

        # === FIX 1 : upgradeBaseSpeed
        for lvl in [0, 5, 10]:
            await page.evaluate(f'STATE.totalTaps=20; STATE.lapsRun=5; STATE.upgradeBaseSpeed={lvl};')
            await page.wait_for_timeout(100)
            rb = await page.evaluate('runnerBaseSpeed()')
            print(f'[FIX1] upgradeBaseSpeed={lvl} → runnerBaseSpeed = {rb}')

        # === FIX 2 : tier-banner position
        await page.evaluate('''(()=>{
            const b = document.createElement('div');
            b.className = 'tier-banner';
            b.style.display = 'flex';
            b.innerHTML = '<span>TEST BANNER MILIEU</span>';
            document.getElementById('runner-stadium').appendChild(b);
        })()''')
        await page.wait_for_timeout(400)
        tier_pos = await page.evaluate('''(()=>{
            const b = document.querySelector('.tier-banner');
            if(!b) return null;
            const r = b.getBoundingClientRect();
            return { top: Math.round(r.top), left: Math.round(r.left), w: Math.round(r.width) };
        })()''')
        print(f'[FIX2] tier-banner position : {tier_pos} (attendu top ~30% de viewport = ~288)')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/FIX-2-tier-banner.png', clip={'x':0,'y':0,'width':540,'height':600})
        await page.evaluate('document.querySelector(".tier-banner")?.remove();')

        # === FIX 3 : daily-btn-float position
        await page.evaluate('document.getElementById("daily-btn").style.display="flex";')
        await page.wait_for_timeout(200)
        daily_pos = await page.evaluate('''(()=>{
            const b = document.getElementById('daily-btn');
            if(!b) return null;
            const r = b.getBoundingClientRect();
            const cs = getComputedStyle(b);
            return { top: Math.round(r.top), left: Math.round(r.left), bottom: Math.round(window.innerHeight - r.bottom), display: cs.display };
        })()''')
        print(f'[FIX3] daily-btn-float position : {daily_pos} (attendu left bas, pas top-right)')

        # === FIX 4 : runner-hud-overlay descendu
        overlay_pos = await page.evaluate('''(()=>{
            const o = document.querySelector('.runner-hud-overlay');
            if(!o) return null;
            const r = o.getBoundingClientRect();
            return { top: Math.round(r.top) };
        })()''')
        print(f'[FIX4] runner-hud-overlay top : {overlay_pos} (attendu ~44 pour passer sous le burger)')

        # Vérifie qu'il n'y a plus d'overlap menu-toggle vs runner-avatar
        no_overlap = await page.evaluate('''(()=>{
            const burger = document.getElementById('menu-toggle');
            const avatar = document.getElementById('runner-avatar');
            if(!burger || !avatar) return 'élément(s) manquant(s)';
            const a = burger.getBoundingClientRect();
            const b = avatar.getBoundingClientRect();
            const overlap = !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
            return {burger: {top: Math.round(a.top), bottom: Math.round(a.bottom), left: Math.round(a.left), right: Math.round(a.right)},
                    avatar: {top: Math.round(b.top), bottom: Math.round(b.bottom), left: Math.round(b.left), right: Math.round(b.right)},
                    overlap};
        })()''')
        print(f'[FIX4b] menu-toggle vs runner-avatar : {no_overlap}')

        # === FIX 5 : NPC fromBehind quand player inactif
        # Mettre le player inactif (totalTaps > 5 mais lastTapTime ancien)
        await page.evaluate('STATE.lapsRun = 5; STATE.totalTaps = 20;')
        await page.wait_for_timeout(6500) # 6.5s sans tap → devrait être détecté comme inactif
        # Vérifie les npcs spawned
        npc_info = await page.evaluate('''(()=>{
            if(window.RUNNER_2D && RUNNER_2D._debug) return RUNNER_2D._debug.npcs;
            // Fallback : check via canvas? On peut juste regarder le state.totalTaps
            return null;
        })()''')
        print(f'[FIX5] NPC debug (peut être null si pas exposé) : {npc_info}')
        # Vérifie visuellement : capture
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/FIX-5-inactive-npcs.png', clip={'x':0,'y':0,'width':540,'height':960})

        await page.screenshot(path='D:/alchimia/screenshots/playthrough/FIX-FINAL-fullscreen.png', clip={'x':0,'y':0,'width':540,'height':960})

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
