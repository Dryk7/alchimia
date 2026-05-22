"""Vérifie :
1) 2 boost banners activés en parallèle = empilés VERTICALEMENT, pas superposés.
2) Décor au repos (post-1er tap) défile MOINS vite qu'avant (baseline × 0.55).
"""
import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.setItem("foulee.storySeen","1"); localStorage.setItem("foulee.tutoV3","done"); localStorage.setItem("foulee.activeTutoV1","done");')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.evaluate('''
            document.getElementById("start-btn")?.click();
            if(window.STATE){
                STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;
                STATE.totalTaps = 50; STATE.lapsRun = 15;
                STATE.gold = 100000; STATE.alchLevel = 10;
            }
        ''')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Active sprint puis tailwind puis breath
        await page.evaluate('if(typeof activateSkill === "function"){ activateSkill("sprint"); }')
        await page.wait_for_timeout(300)
        await page.evaluate('if(typeof activateSkill === "function"){ activateSkill("tailwind"); }')
        await page.wait_for_timeout(300)
        await page.evaluate('if(typeof activateSkill === "function"){ activateSkill("breath"); }')
        await page.wait_for_timeout(600)

        # Snapshot positions des banners
        positions = await page.evaluate('''(()=>{
            const banners = [...document.querySelectorAll('.skill-active-banner')];
            return banners.map(b => {
                const r = b.getBoundingClientRect();
                return {
                    skill: b.dataset.skill,
                    top: Math.round(r.top),
                    bottom: Math.round(r.bottom),
                    height: Math.round(r.height),
                    visible: r.height > 0
                };
            });
        })()''')
        print('[BANNERS] Positions empilées :')
        for p in positions:
            print(f'  - {p["skill"]:10} top={p["top"]:3} bottom={p["bottom"]:3} h={p["height"]:2}')
        # Vérification : aucun banner ne doit avoir le même top qu'un autre
        tops = [p['top'] for p in positions if p['visible']]
        if len(tops) != len(set(tops)):
            print('  ❌ SUPERPOSITION DÉTECTÉE')
        else:
            print('  ✅ Tous distincts')

        await page.screenshot(path='D:/alchimia/screenshots/playthrough/BANNERS-3-stacked.png', clip={'x':0,'y':0,'width':540,'height':400})

        # Maintenant test vitesse décor : sans tap
        await page.evaluate('''(()=>{
            // Reset to fresh state but with 1 tap done
            if(window.STATE){
                STATE.totalTaps = 1;
                STATE.lapsRun = 1;
                STATE.upgradeAutoTap = 0;
                STATE.upgradeTapValue = 0;
                STATE.upgradeLapBonus = 0;
                STATE.upgradeBaseSpeed = 0;
                STATE.team = {};
            }
        })()''')
        await page.wait_for_timeout(300)
        speed_info = await page.evaluate('''(()=>({
            runnerBaseSpeed: typeof runnerBaseSpeed === 'function' ? runnerBaseSpeed() : 'N/A',
            displayKmh: window.RUNNER_2D ? 'see HUD' : 'no R2D',
        }))()''')
        kmh_text = await page.evaluate('document.getElementById("runner-pace")?.textContent || document.querySelector(".pace-pill")?.textContent || "?"')
        print(f'\n[SPEED] runnerBaseSpeed={speed_info["runnerBaseSpeed"]}')
        print(f'        visualBaseline attendu = {speed_info["runnerBaseSpeed"] * 0.55:.3f} (était {speed_info["runnerBaseSpeed"]:.3f})')
        print(f'        km/h affiché : {kmh_text}')
        await page.wait_for_timeout(800)
        kmh_after = await page.evaluate('document.getElementById("runner-pace")?.textContent || document.querySelector(".pace-pill")?.textContent || "?"')
        print(f'        km/h après 800ms : {kmh_after}')

        await browser.close()

asyncio.run(main())
