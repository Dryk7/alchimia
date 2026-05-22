"""Vérifie le Tier 6 Champion olympique :
1) Spawn forcé à km 95 → tier 6 doit apparaître
2) Capture full visuelle : médaille + drapeau + aura dorée doivent être visibles
3) Pas d'erreurs console
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
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); localStorage.setItem('fouleeDebug','1'); } catch(e){}")
        await page.goto('http://localhost:8770?debug=1', wait_until='networkidle')
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Set km 95 → distribution doit pousser des T6
        await page.evaluate('STATE.lapsRun = 95; STATE.totalTaps = 100; STATE.alchLevel = 25;')
        await page.evaluate('if(window.RUNNER_2D && window.RUNNER_2D.npcs) window.RUNNER_2D.npcs.length = 0;')

        # FORCE spawn de 3 champions T6 via debug API
        debug_avail = await page.evaluate('typeof window.RUNNER_2D?.spawnNpc === "function"')
        print(f'Debug spawnNpc API : {debug_avail}')
        if debug_avail:
            await page.evaluate('window.RUNNER_2D.spawnNpc(6); window.RUNNER_2D.spawnNpc(6); window.RUNNER_2D.spawnNpc(6);')
        # Force les NPCs à metersAhead proche de 0 pour qu'ils soient visibles à l'écran
        await page.evaluate('''(()=>{
            if(!window.RUNNER_2D || !window.RUNNER_2D.npcs) return;
            const targets = [3, 0, -3];
            window.RUNNER_2D.npcs.forEach((n, i) => {
                if(n.tier === 6) n.metersAhead = targets[i] || 0;
            });
        })()''')
        await page.wait_for_timeout(500)

        # Compte les tiers
        tier_counts = await page.evaluate('''(()=>{
            if(!window.RUNNER_2D || !window.RUNNER_2D.npcs) return null;
            const counts = [0,0,0,0,0,0,0];
            const labels = [];
            const flags = [];
            for(const n of window.RUNNER_2D.npcs){
                if(typeof n.tier === 'number' && n.tier >= 0 && n.tier <= 6){
                    counts[n.tier]++;
                    labels.push(n.tierLabel);
                    if(n.flagColors) flags.push(n.flagColors);
                }
            }
            return {counts, labels, flags, total: window.RUNNER_2D.npcs.length};
        })()''')
        print(f'[T6 KM95] {tier_counts}')

        # Capture
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/T6-km95-champion.png', clip={'x':0,'y':0,'width':540,'height':960})

        # Force re-spawn et attendre encore pour avoir plus de NPCs
        await page.wait_for_timeout(8000)
        tier_counts2 = await page.evaluate('''(()=>{
            if(!window.RUNNER_2D || !window.RUNNER_2D.npcs) return null;
            const counts = [0,0,0,0,0,0,0];
            for(const n of window.RUNNER_2D.npcs){
                if(typeof n.tier === 'number') counts[n.tier]++;
            }
            return {counts, total: window.RUNNER_2D.npcs.length};
        })()''')
        print(f'[T6 KM95 +8s] {tier_counts2}')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/T6-km95-champion-2.png', clip={'x':0,'y':0,'width':540,'height':960})

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
