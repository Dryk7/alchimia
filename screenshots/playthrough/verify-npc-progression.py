"""Vérifie distribution NPC par km :
- km 0-2 : majorité promeneurs (T0)
- km 70+ : majorité semi-pros/pros (T4-T5)
Et capture des screenshots visuels.
"""
import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DIST_BY_KM = [
    (1,    [0.80, 0.20, 0,    0,    0,    0   ]),
    (10,   [0.40, 0.45, 0.13, 0.02, 0,    0   ]),
    (20,   [0.15, 0.35, 0.30, 0.18, 0.02, 0   ]),
    (40,   [0.05, 0.15, 0.30, 0.30, 0.18, 0.02]),
    (60,   [0,    0.05, 0.15, 0.30, 0.35, 0.15]),
    (80,   [0,    0,    0.05, 0.20, 0.40, 0.35]),
    (95,   [0,    0,    0,    0.10, 0.30, 0.60]),
    (110,  [0,    0,    0,    0,    0.20, 0.80]),
]
TIER_NAMES = ['promeneur', 'jogger', 'jogger sérieux', 'amateur', 'semi-pro', 'pro']

def expected_top_tier(dist):
    return TIER_NAMES[max(range(6), key=lambda i: dist[i])]

print('=== DISTRIBUTION ATTENDUE PAR KM ===')
for km, dist in DIST_BY_KM:
    top = expected_top_tier(dist)
    bars = ''.join(['█' * int(p * 20) + ' ' for p in dist])
    print(f'  km{km:3d} : dominant={top:18s} | {dist}')

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

        # Pour chaque km clé : set state, laisse 12s pour quelques spawns, capture + count tiers visibles
        for km, label in [(1, 'km01-promeneur'), (20, 'km20-mixed'), (60, 'km60-semipro'), (95, 'km95-pros')]:
            await page.evaluate(f'STATE.lapsRun = {km}; STATE.totalTaps = 50; STATE.alchLevel = 5;')
            # Vide les NPCs existants pour avoir un état propre
            await page.evaluate('if(window.RUNNER_2D && window.RUNNER_2D.npcs) window.RUNNER_2D.npcs.length = 0;')
            await page.wait_for_timeout(7000)  # 7s pour laisser quelques spawns naturels
            # Compte les tiers présents
            tier_counts = await page.evaluate('''(()=>{
                if(!window.RUNNER_2D || !window.RUNNER_2D.npcs) return null;
                const counts = [0,0,0,0,0,0];
                for(const n of window.RUNNER_2D.npcs){
                    if(typeof n.tier === 'number' && n.tier >= 0 && n.tier <= 5){
                        counts[n.tier]++;
                    }
                }
                return {counts, total: window.RUNNER_2D.npcs.length, labels: window.RUNNER_2D.npcs.map(n => n.tierLabel)};
            })()''')
            print(f'\n[KM {km}] NPCs visibles : {tier_counts}')
            await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/NPC-{label}.png', clip={'x':0,'y':0,'width':540,'height':960})

        print(f'\nErreurs console : {len(errors)}')
        for e in errors[:5]: print(f'  {e[:200]}')

        await browser.close()

asyncio.run(main())
