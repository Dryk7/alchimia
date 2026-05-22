"""Simule une vraie session de jeu et mesure les rythmes."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await context.new_page()
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.evaluate("""
            document.getElementById('start-btn')?.click();
            STATE.starterPackDeclined = true;
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
        """)
        await page.wait_for_timeout(1500)
        await page.evaluate("document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));")

        results = {}

        # === COÛTS DES UPGRADES (5 premiers niveaux) ===
        costs = {}
        for upg in ['tapValue', 'critChance', 'lapBonus', 'autoTap', 'baseSpeed', 'endurance']:
            await page.evaluate(f"STATE.upgrade{upg[0].upper() + upg[1:]} = 0;")
            ll = []
            for lvl in range(5):
                await page.evaluate(f"STATE['upgrade{upg[0].upper() + upg[1:]}'] = {lvl};")
                c = await page.evaluate(f"(typeof upgradeCost === 'function') ? upgradeCost('{upg}') : null")
                ll.append(c)
            costs[upg] = ll
        results['upgrade_costs_lvl_0_to_4'] = costs

        # === TEMPS POUR PREMIER KM (full tap mode) ===
        await page.evaluate("""
          STATE.lapsRun = 0; STATE.lapProgress = 0; STATE.gold = 0; STATE.totalTaps = 0;
          STATE.upgradeTapValue = 0; STATE.upgradeCritChance = 0;
        """)
        stadium_box = await page.evaluate("""
            (() => { const r = document.getElementById('runner-stadium').getBoundingClientRect();
              return { x: r.left + r.width/2, y: r.top + r.height/2 }; })()
        """)
        import time
        t_start = time.time()
        tap_count = 0
        # Tap jusqu'à ce que km 1 soit complété (max 90 sec safety)
        while time.time() - t_start < 90:
            await page.mouse.click(stadium_box['x'], stadium_box['y'])
            tap_count += 1
            await page.wait_for_timeout(120)  # 8 taps/sec (humain rapide)
            laps = await page.evaluate("STATE.lapsRun")
            if laps >= 1:
                break
        t_km1 = time.time() - t_start
        gold_after_km1 = await page.evaluate("STATE.gold")
        results['T_km1_full_tap'] = {
            'temps_sec': round(t_km1, 1),
            'taps_total': tap_count,
            'taps_par_sec': round(tap_count / t_km1, 1) if t_km1 > 0 else 0,
            'gold_obtenu': gold_after_km1,
            'ok': 30 <= t_km1 <= 180  # 30s à 3min = correct
        }

        # === COMBIEN D'UPGRADES achetables avec gold du km 1 ? ===
        first_cost = await page.evaluate("upgradeCost('tapValue')")
        upgrades_possibles = gold_after_km1 // first_cost if first_cost else 0
        results['upgrades_apres_km1'] = {
            'gold': gold_after_km1,
            'cout_premier_upgrade': first_cost,
            'nombre_achetables': upgrades_possibles,
            'ok': upgrades_possibles >= 1  # devrait pouvoir en acheter au moins 1
        }

        # === TEMPS km 5 → km 6 EN IDLE (post-débloquage AUTO-COURSE) ===
        await page.evaluate("STATE.lapsRun = 5; STATE.lapProgress = 0; STATE.runnerStamina = 1.5;")
        t_idle_start = time.time()
        while time.time() - t_idle_start < 600:  # max 10 min
            await page.wait_for_timeout(2000)
            laps = await page.evaluate("STATE.lapsRun")
            if laps >= 6:
                break
        t_km6_idle = time.time() - t_idle_start
        results['T_km5_to_km6_idle'] = {
            'temps_sec': round(t_km6_idle, 1),
            'temps_min': round(t_km6_idle / 60, 1),
            'ok': 60 <= t_km6_idle <= 600  # 1 à 10 min = correct
        }

        # === GOLD/SEC en spam tap (au km 5, sans upgrades) ===
        await page.evaluate("""
          STATE.lapsRun = 5; STATE.lapProgress = 0.1; STATE.gold = 0;
          STATE.upgradeTapValue = 0; STATE.upgradeCritChance = 0;
          STATE.runnerStamina = 1.5;
        """)
        gold_t0 = 0
        t_start = time.time()
        while time.time() - t_start < 8:
            await page.mouse.click(stadium_box['x'], stadium_box['y'])
            await page.wait_for_timeout(100)
        elapsed = time.time() - t_start
        gold_t1 = await page.evaluate("STATE.gold")
        results['gold_per_sec_spam'] = {
            'duree_test': round(elapsed, 1),
            'gold_gagne': gold_t1,
            'gold_par_sec': round(gold_t1 / elapsed, 1),
            'ok': gold_t1 / elapsed >= 5  # au moins 5 méd/sec en spam
        }

        # === STAMINA DECAY rate ===
        await page.evaluate("STATE.runnerStamina = 2.0;")
        await page.wait_for_timeout(5000)
        stam_5s = await page.evaluate("STATE.runnerStamina")
        decay_per_sec = (2.0 - stam_5s) / 5
        results['stamina_decay_rate'] = {
            'avant': 2.0,
            'apres_5s': round(stam_5s, 3),
            'decay_par_sec': round(decay_per_sec, 4),
            'temps_pour_perdre_1_unite_sec': round(1 / decay_per_sec, 1) if decay_per_sec > 0 else 'inf',
            'ok': 0.05 <= decay_per_sec <= 0.15  # ~10s pour perdre 1 unité = OK
        }

        # === RAPPORT ===
        print('\n' + '='*60)
        print('         RAPPORT BALANCE / TUNING')
        print('='*60)
        ok_count = 0
        for k, v in results.items():
            status = 'OK ' if (isinstance(v, dict) and v.get('ok')) else 'a regler'
            if isinstance(v, dict) and 'ok' in v:
                ok_count += 1 if v['ok'] else 0
            print(f'\n[{status}] {k}')
            if isinstance(v, dict):
                for kk, vv in v.items():
                    if kk != 'ok':
                        print(f'    {kk}: {vv}')
            else:
                print(f'    {v}')
        print(f'\n{ok_count} tests OK sur les tests avec critere')
        print(f'Console errors: {len(errors)}')
        for e in errors[:5]:
            print(f'  - {e[:200]}')
        await browser.close()


asyncio.run(main())
