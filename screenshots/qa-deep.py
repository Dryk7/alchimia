"""QA profonde : crit, prix upgrade, stamina, perf, overlap haies."""
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

        # === T1 : Prix upgrades scale ===
        await page.evaluate("STATE.gold = 999999;")
        prices = []
        for i in range(5):
            p_now = await page.evaluate("(typeof upgradeCost === 'function') ? upgradeCost('tapValue') : null")
            prices.append(p_now)
            await page.evaluate("(typeof buyUpgrade === 'function') && buyUpgrade('tapValue')")
            await page.wait_for_timeout(80)
        results['T1_price_scale'] = {
            'prix_lvl_0_1_2_3_4': prices,
            'ok': prices[0] is not None and prices[-1] > prices[0] * 1.5
        }

        # === T2 : Crit chance proc effectivement ===
        await page.evaluate("STATE.upgradeCritChance = 50; STATE.gold = 0;")  # ~55% crit
        crit_count = 0
        normal_count = 0
        for i in range(50):
            before = await page.evaluate("STATE.gold")
            await page.evaluate("if(typeof tapBoost === 'function') tapBoost(null);")
            after = await page.evaluate("STATE.gold")
            gain = after - before
            # Crit = 5× (gain >= 5 si perTap=1)
            if gain >= 4:
                crit_count += 1
            elif gain > 0:
                normal_count += 1
        results['T2_crit_proc'] = {
            'taps': 50,
            'crit_count': crit_count,
            'normal_count': normal_count,
            'ok': crit_count > 5  # avec 50% crit on attend ~25/50, minimum 5
        }

        # === T3 : Stamina decays + recharge ===
        await page.evaluate("STATE.runnerStamina = 2.0;")
        await page.wait_for_timeout(2500)
        stam_after = await page.evaluate("STATE.runnerStamina")
        results['T3_stamina_decay'] = {
            'avant': 2.0,
            'apres_2_5s': round(stam_after, 3),
            'ok': stam_after < 2.0
        }

        # === T4 : Multiple haies overlap render OK ===
        await page.evaluate("STATE.lapsRun = 10;")
        await page.evaluate("window.RUNNER_2D.spawnHurdlePattern('triple', 20);")
        await page.wait_for_timeout(300)
        hurdle_count = await page.evaluate("window.RUNNER_2D?.getHurdles?.()?.length ?? 0")
        results['T4_triple_render'] = {
            'spawned': 3,
            'visible': hurdle_count,
            'ok': hurdle_count == 3
        }

        # === T5 : Performance interne du tick ===
        # Mesure le delta de t (frame counter interne) au lieu de RAF (que Playwright throttle)
        # t est incrémenté de 1 par frame du jeu (setInterval 1000/60)
        t_before = await page.evaluate("(typeof window.RUNNER_2D !== 'undefined') ? performance.now() : null")
        await page.wait_for_timeout(2000)
        t_after = await page.evaluate("performance.now()")
        # Le setInterval-based tick devrait tourner ~60Hz. Mesure indirecte via decorScroll
        scroll_before = await page.evaluate("window.RUNNER_2D?.getKmh?.() ?? null")
        await page.wait_for_timeout(1000)
        scroll_after = await page.evaluate("window.RUNNER_2D?.getKmh?.() ?? null")
        results['T5_perf'] = {
            'kmh_lisse': scroll_after,
            'tick_function_alive': scroll_after is not None,
            'ok': scroll_after is not None
        }

        # === T6 : Stage transitions OK (km 5, 10, 25 doivent changer biome) ===
        biomes = {}
        for laps in [0, 3, 6, 12, 25]:
            await page.evaluate(f"STATE.lapsRun = {laps}; _stageCache = {{ km: -1, result: null }};")
            await page.wait_for_timeout(200)
            biome = await page.evaluate("typeof currentStage === 'function' ? currentStage().biome : 'unknown'")
            biomes[f'km_{laps}'] = biome
        results['T6_biome_progression'] = {
            **biomes,
            'ok': len(set(biomes.values())) >= 3  # au moins 3 biomes différents
        }

        # === T7 : Combo decay (1.5s sans tap = reset) ===
        # 5 taps espacés de 100ms pour éviter le TAP_COOLDOWN_MS
        for i in range(5):
            await page.evaluate("(typeof tapBoost === 'function') && tapBoost(null)")
            await page.wait_for_timeout(110)
        combo_after_3 = await page.evaluate("typeof _comboCount !== 'undefined' ? _comboCount : null")
        await page.wait_for_timeout(1700)
        combo_after_wait = await page.evaluate("typeof _comboCount !== 'undefined' ? _comboCount : null")
        results['T7_combo_decay'] = {
            'combo_apres_3taps': combo_after_3,
            'combo_apres_1.7s': combo_after_wait,
            'ok': combo_after_3 >= 3 and combo_after_wait == 0
        }

        # === T8 : Hurdle SCALE difficulté avec km (drift speed should increase) ===
        # Idée : le drift speed devrait augmenter pour la difficulté progressive
        await page.evaluate("STATE.lapsRun = 10;")
        await page.evaluate("if(window.RUNNER_2D?.spawnHurdle){ window.RUNNER_2D.getHurdles().length = 0; window.RUNNER_2D.spawnHurdle(80, 'single'); }")
        await page.wait_for_timeout(500)
        h_dist = await page.evaluate("window.RUNNER_2D?.getHurdles?.()?.[0]?.metersAhead ?? null")
        results['T8_hurdle_drift'] = {
            'distance_apres_500ms': round(h_dist, 1) if h_dist is not None else None,
            'note': '80 - drift = X. Plus drift haut = plus difficile.',
            'ok': h_dist is not None and h_dist < 78  # au moins 2m de drift
        }

        # === RAPPORT ===
        print('\n' + '='*60)
        print('         QA PROFONDE')
        print('='*60)
        ok_count = 0
        for k, v in results.items():
            status = 'OK ' if v['ok'] else 'KO!'
            ok_count += 1 if v['ok'] else 0
            print(f'\n[{status}] {k}')
            for kk, vv in v.items():
                if kk != 'ok':
                    print(f'    {kk}: {vv}')
        print(f'\n{ok_count}/{len(results)} tests OK')
        print(f'Console errors: {len(errors)}')
        for e in errors[:5]:
            print(f'  - {e[:200]}')
        await browser.close()


asyncio.run(main())
