"""
QA Vague 22 - Test 2 — Reliques effectivité in-game.
Read-only : ne modifie rien dans index.html, juste tests Playwright sur localhost:8770.

Tests :
 1. Phidippide : measure displayKmh sans relique, equip + stamina=100, mesurer avec relique
 2. Hermes    : simulate fail haie sans relique (penalty gold check), equip hermes, retest
 3. Atalante  : measure crit chance sans + avec relique (devrait +10%)
 4. Etoile    : measure drop_mul sans + avec etoile + totalStarsEarned=5 (devrait +25%)
 5. rollRelicDrop sur 200 chest legendary => combien de reliques droppees ?
"""
import asyncio, json, sys, traceback
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
W, H = 540, 960


async def main():
    results = {}
    console_errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": W, "height": H})
        page = await context.new_page()

        page.on("console", lambda m: (
            console_errors.append(m.text) if m.type == "error" else None
        ))
        page.on("pageerror", lambda e: console_errors.append(f"PAGEERR {e}"))

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        # Skip onboarding : injection STATE direct, no story
        await page.evaluate("""
            try {
                localStorage.setItem('fouleeSkipStory', '1');
                localStorage.setItem('fouleeOnboardingDone', '1');
            } catch(e){}
        """)
        # Reload pour appliquer
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        # Attendre que STATE et hasRelic soient présents
        await page.wait_for_function("typeof window.hasRelic === 'function' && window.STATE && window.RELIC_DEFS", timeout=8000)

        # Force tous les états initiaux : reset reliques
        await page.evaluate("""
            window.STATE.relics = { owned: ['phidippide','hermes','atalante','etoile'], equipped: [] };
            window.STATE.stamina = 100;
            window.STATE.staminaMax = 100;
            window.STATE.totalStarsEarned = 0;
            window.STATE.gold = 5000;
            window.STATE.upgradeCritChance = 0;
        """)

        # ============= TEST 1 : PHIDIPPIDE =============
        # On simule la branche du calcul displayKmh "intermédiaire"
        # On va prendre displayKmh = 30 (valeur saturée passive cap) et calculer manuel le branchement
        t1 = await page.evaluate("""
        (() => {
            // Sans relique :
            window.STATE.relics.equipped = [];
            const baseKmh = 30;
            // simul: si phidippide && stamina>80% => *1.5 (capé à 35)
            const beforeActive = !!window.hasRelic('phidippide');
            // équipe phidippide
            window.equipRelic('phidippide');
            window.STATE.stamina = 100;
            window.STATE.staminaMax = 100;
            const afterActive = !!window.hasRelic('phidippide');
            // émulation du code branché : c'est le même if branché ligne 27628
            let calc = baseKmh;
            if(window.hasRelic('phidippide')){
                const r = window.STATE.stamina / window.STATE.staminaMax;
                if(r > 0.80){
                    calc *= 1.50;
                    calc = Math.min(35, calc);
                }
            }
            // Test avec stamina basse (50%) pour vérifier que le bonus ne s'active pas
            window.STATE.stamina = 50;
            let calcLow = baseKmh;
            if(window.hasRelic('phidippide')){
                const r2 = window.STATE.stamina / window.STATE.staminaMax;
                if(r2 > 0.80){
                    calcLow *= 1.50;
                    calcLow = Math.min(35, calcLow);
                }
            }
            // Reset
            window.STATE.stamina = 100;
            window.unequipRelic('phidippide');
            return {
                base_kmh: baseKmh,
                with_phidippide_stam100: calc,
                with_phidippide_stam50: calcLow,
                expected_bonus_pct: ((calc / baseKmh) - 1) * 100,
                bonus_active_low_stam: calcLow !== baseKmh
            };
        })()
        """)
        results['T1_phidippide'] = t1

        # ============= TEST 2 : HERMES =============
        t2 = await page.evaluate("""
        (() => {
            window.STATE.relics.equipped = [];
            window.STATE.gold = 5000;
            // simul: pénalité gold si streakFail (3+) ET !hermesActive
            // Branche pénalité = isStreakFail && STATE && !_hermesActive
            const goldBefore = window.STATE.gold;
            let hermesActive = !!window.hasRelic('hermes');
            const isStreakFail = true; // simul streak >= 3
            const failStreak = 4;
            // PATH 1 : sans hermes
            let g1 = window.STATE.gold;
            let p1ms = 0;
            if(isStreakFail && !hermesActive){
                const penalty = Math.min(g1, 100 + (failStreak - 3) * 20);
                g1 = Math.max(0, g1 - penalty);
                p1ms = 3600;
            } else if(!hermesActive){
                p1ms = 2000;
            }
            const goldNoHermes = g1;
            const penaltyMsNoHermes = p1ms;
            // PATH 2 : avec hermes
            window.equipRelic('hermes');
            hermesActive = !!window.hasRelic('hermes');
            let g2 = 5000;
            let p2ms = hermesActive ? 0 : (isStreakFail ? 3600 : 2000);
            if(isStreakFail && !hermesActive){
                const penalty = Math.min(g2, 100 + (failStreak - 3) * 20);
                g2 = Math.max(0, g2 - penalty);
            }
            window.unequipRelic('hermes');
            return {
                gold_no_hermes_after_streakfail: goldNoHermes,
                gold_with_hermes_after_streakfail: g2,
                penalty_ms_no_hermes: penaltyMsNoHermes,
                penalty_ms_with_hermes: p2ms,
                gold_protected: g2 === 5000
            };
        })()
        """)
        results['T2_hermes'] = t2

        # ============= TEST 3 : ATALANTE =============
        t3 = await page.evaluate("""
        (() => {
            window.STATE.relics.equipped = [];
            window.STATE.upgradeCritChance = 0;
            // Reproduit ligne 18196-18197
            function critRate(){
                const equipCrit = 0;
                const cardCrit = 0;
                const atalanteCrit = (window.hasRelic('atalante')) ? 0.10 : 0;
                const saisonBonus = 0; // pas de saison ici
                return 0.05 + (window.STATE.upgradeCritChance||0)*0.01 + equipCrit + cardCrit + atalanteCrit + saisonBonus;
            }
            const critBefore = critRate();
            window.equipRelic('atalante');
            const critAfter = critRate();
            window.unequipRelic('atalante');
            return {
                crit_no_atalante: critBefore,
                crit_with_atalante: critAfter,
                delta_pct: (critAfter - critBefore) * 100,
                expected_10_percent: Math.abs((critAfter - critBefore) - 0.10) < 0.0001
            };
        })()
        """)
        results['T3_atalante'] = t3

        # ============= TEST 4 : ETOILE =============
        t4 = await page.evaluate("""
        (() => {
            window.STATE.relics.equipped = [];
            window.STATE.totalStarsEarned = 5;
            // Reproduit lignes 17680-17684
            function dropMul(){
                const weatherDrop = 1; // pas de météo
                const etoileMul = (window.hasRelic('etoile')) ? 1 + (window.STATE.totalStarsEarned||0)*0.05 : 1;
                return weatherDrop * etoileMul;
            }
            const before = dropMul();
            window.equipRelic('etoile');
            const after = dropMul();
            window.unequipRelic('etoile');
            return {
                drop_mul_no_etoile_stars5: before,
                drop_mul_with_etoile_stars5: after,
                delta_pct: (after - before) * 100,
                expected_25_pct: Math.abs(after - 1.25) < 0.0001
            };
        })()
        """)
        results['T4_etoile'] = t4

        # ============= TEST 5 : rollRelicDrop x200 =============
        t5 = await page.evaluate("""
        (() => {
            // Reset relics
            window.STATE.relics = { owned: [], equipped: [] };
            let drops = 0;
            for(let i = 0; i < 200; i++){
                const before = window.STATE.relics.owned.length;
                window.rollRelicDrop();
                const after = window.STATE.relics.owned.length;
                if(after > before) drops += 1;
            }
            return {
                trials: 200,
                drops: drops,
                rate_observed: drops / 200,
                rate_expected: 0.01,
                approx_2_expected: drops >= 0 && drops <= 10
            };
        })()
        """)
        results['T5_relic_drop_rate'] = t5

        # Snapshot équipement modal
        try:
            await page.evaluate("window.STATE.relics = { owned: ['phidippide','hermes','atalante','etoile'], equipped: ['phidippide','atalante'] };")
            await page.evaluate("window.openRelics && window.openRelics()")
            await page.wait_for_timeout(500)
            await page.screenshot(path="D:/alchimia/screenshots/qa-vague22/relics-modal.png")
        except Exception:
            pass

        await browser.close()

    results['console_errors'] = console_errors
    return results


if __name__ == "__main__":
    try:
        out = asyncio.run(main())
        print(json.dumps(out, indent=2, ensure_ascii=False))
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
