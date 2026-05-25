"""
QA Vague 10 — Mid-game playthrough (km 30-50)
Force STATE simulant un joueur progressé, dump STATE complet à chaque palier.
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright

OUT = os.path.dirname(os.path.abspath(__file__))
URL = "http://localhost:8770/index.html"
PALIERS = [30, 40, 45, 49, 50]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
            user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0",
        )
        page = await context.new_page()

        # Skip onboarding
        await page.add_init_script("""
            try {
                localStorage.setItem('alchimia.onboarded', '1');
                localStorage.setItem('foulee.onboarded', '1');
                localStorage.setItem('foulee_introSeen', '1');
                localStorage.setItem('alchimia.introSeen', '1');
                localStorage.setItem('foulee.tutorialDone', '1');
            } catch(e){}
        """)
        console_msgs = []
        page.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text}"))

        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(2500)

        # Forcer demarrage du jeu (skip intro si besoin)
        await page.evaluate("""() => {
            try {
                // tente de cliquer 'PRENDRE LE DÉPART' ou autre bouton de start
                const buttons = document.querySelectorAll('button, .btn, [role="button"]');
                for(const b of buttons){
                    const t = (b.textContent || '').toUpperCase();
                    if(t.includes('DÉPART') || t.includes('DEPART') || t.includes('JOUER') || t.includes('START') || t.includes('SUIVANT')){
                        b.click();
                        break;
                    }
                }
                // Ferme tout overlay daily-reward / onboarding
                document.querySelectorAll('.modal .modal-close, .modal-close, .cinematic-close').forEach(el => {
                    try { el.click(); } catch(e){}
                });
            } catch(e){}
        }""")
        await page.wait_for_timeout(1500)

        # Force STATE initial mid-game
        await page.evaluate("""() => {
            if(!window.STATE) return;
            STATE.totalTaps = 2000;
            STATE.gold = 100000;
            STATE.lapsRun = 0;       // sera bumpe par palier
            STATE.lapProgress = 0;
            STATE.bestKmh = 30;
            STATE.runnerStamina = 2.0;
            // Modeste investissement upgrades pour realisme
            STATE.upgradeTapValue = 8;
            STATE.upgradeCritChance = 5;
            STATE.upgradeLapBonus = 6;
            STATE.upgradeEndurance = 4;
            STATE.upgradeAutoTap = 2;
            STATE.upgradeBaseSpeed = 3;
            STATE.upgradeEagleEye = 3;
            // Rebuild quetes pour totaux coherents
            if(typeof rebuildQuests === 'function'){ try { rebuildQuests(); } catch(e){} }
        }""")
        await page.wait_for_timeout(500)

        results = {}

        for km in PALIERS:
            # Bump lapsRun et trigger les hooks de "km bouclé"
            # On simule le saut comme si le joueur venait de boucler le km
            await page.evaluate("""(targetKm) => {
                const prev = STATE.lapsRun || 0;
                STATE.lapsRun = targetKm;
                STATE.lapProgress = 0;
                // Trigger achievements + chest drop pour chaque km traverse
                for(let k = prev + 1; k <= targetKm; k++){
                    STATE.lapsRun = k;
                    try { if(typeof maybeDropItem === 'function') maybeDropItem(); } catch(e){}
                    try { if(typeof checkAchievements === 'function') checkAchievements(); } catch(e){}
                    try { if(typeof onLapCompleted === 'function') onLapCompleted(); } catch(e){}
                }
                STATE.lapsRun = targetKm;
                try { if(typeof renderAll === 'function') renderAll(); } catch(e){}
                try { if(typeof updateChestBadge === 'function') updateChestBadge(); } catch(e){}
                try { if(typeof refreshQuests === 'function') refreshQuests(); } catch(e){}
                // Trigger spawn de palier eventuel (km 50 etc.)
                try { if(typeof onKmReached === 'function') onKmReached(targetKm); } catch(e){}
            }""", km)

            await page.wait_for_timeout(2000)  # laisser pop-up / cinematic apparaitre

            # Dump STATE complet
            dump = await page.evaluate("""() => {
                const s = window.STATE || {};
                const upgKeys = ['upgradeTapValue','upgradeCritChance','upgradeLapBonus',
                                'upgradeAutoTap','upgradeEndurance','upgradeEagleEye',
                                'upgradeBaseSpeed','upgradeCruiseControl'];
                const upgrades = {};
                for(const k of upgKeys){ upgrades[k] = s[k] || 0; }
                // Costs courants des upgrades
                const costs = {};
                if(typeof upgradeCost === 'function'){
                    for(const id of ['tapValue','critChance','lapBonus','autoTap','endurance','eagleEye','baseSpeed','cruiseControl']){
                        try { costs[id] = upgradeCost(id); } catch(e){ costs[id] = null; }
                    }
                }
                // Pop-ups / modals visibles
                const visibleModals = [];
                document.querySelectorAll('.modal, .cinematic-overlay, .drop-toast, .chest-modal').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    if(rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden'){
                        visibleModals.push({
                            id: el.id || '',
                            classes: el.className,
                            text: (el.textContent || '').trim().slice(0, 200)
                        });
                    }
                });
                // Skills/menu items unlocked
                const menuItems = [];
                document.querySelectorAll('[data-unlock-km]').forEach(el => {
                    const unlockKm = parseInt(el.dataset.unlockKm) || 0;
                    const isUnlocked = (s.lapsRun || 0) >= unlockKm;
                    const visible = !el.classList.contains('hidden') && el.offsetParent !== null;
                    menuItems.push({
                        action: el.dataset.action || el.dataset.upgrade || el.getAttribute('aria-label') || '',
                        unlockKm,
                        unlocked: isUnlocked,
                        visible
                    });
                });
                return {
                    gold: s.gold,
                    totalTaps: s.totalTaps,
                    lapsRun: s.lapsRun,
                    lapProgress: s.lapProgress,
                    bestKmh: s.bestKmh,
                    runnerStamina: s.runnerStamina,
                    upgrades,
                    upgradeCosts: costs,
                    chests: s.chests || {},
                    ownedSkins: s.ownedSkins || {},
                    equippedSkin: s.equippedSkin || null,
                    equipment: s.equipment || {},
                    activeBoosts: s.activeBoosts || {},
                    achievements: Object.keys(s.achievements || {}),
                    achievementsCount: Object.keys(s.achievements || {}).length,
                    visibleModals,
                    menuItems
                };
            }""")
            results[f"km{km}"] = dump

            shot_path = os.path.join(OUT, f"palier-km{km:02d}.png")
            await page.screenshot(path=shot_path, full_page=False)
            print(f"[OK] km {km}: gold={dump['gold']} chests={dump['chests']} modals={len(dump['visibleModals'])}")

        # Test specifique : pop-up coffre legendaire au km 50 ?
        # Verification visuelle plus poussee
        await page.evaluate("""() => {
            // Trigger explicite chest drop pour km 50 si pas deja fait
            if(typeof maybeDropItem === 'function'){
                try { maybeDropItem(); } catch(e){}
            }
            // Trigger pop-up legendaire si possible
            try { if(typeof showLegendaryChest === 'function') showLegendaryChest(); } catch(e){}
        }""")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=os.path.join(OUT, "km50-postchest.png"))

        # Test : est-ce que cruiseControl reste cher a km 50 ?
        cruiseCheck = await page.evaluate("""() => {
            const cost = (typeof upgradeCost === 'function') ? upgradeCost('cruiseControl') : null;
            const lvl = STATE.upgradeCruiseControl || 0;
            const gold = STATE.gold || 0;
            return { cost, lvl, gold, affordable: gold >= cost };
        }""")
        results["cruiseCheck"] = cruiseCheck

        # Capture les hauts faits debloqués
        results["achievementsUnlockedAtKm50"] = await page.evaluate("""() => {
            const list = [];
            if(typeof ACHIEVEMENTS !== 'undefined'){
                for(const a of ACHIEVEMENTS){
                    if(STATE.achievements && STATE.achievements[a.id]){
                        list.push({ id: a.id, name: a.name, reward: a.reward });
                    }
                }
            }
            return list;
        }""")

        results["consoleErrors"] = [m for m in console_msgs if '[error]' in m.lower()][:20]
        results["consoleWarns"] = [m for m in console_msgs if '[warning]' in m.lower()][:10]

        out_json = os.path.join(OUT, "results.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        print("\n=== RESULTS ===")
        print(json.dumps(results, indent=2, default=str, ensure_ascii=False)[:8000])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
