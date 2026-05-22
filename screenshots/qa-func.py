"""QA fonctionnelle : upgrades, gold, progression, save, haies bonus."""
import asyncio
import json
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
        stadium_box = await page.evaluate("""
            (() => { const r = document.getElementById('runner-stadium').getBoundingClientRect();
              return { x: r.left + r.width/2, y: r.top + r.height/2 }; })()
        """)

        # === TEST 1 : tap = gold ? ===
        before = await page.evaluate("({ gold: STATE.gold, taps: STATE.totalTaps || 0 })")
        for i in range(10):
            await page.mouse.click(stadium_box['x'], stadium_box['y'])
            await page.wait_for_timeout(110)  # 9 taps/sec
        await page.wait_for_timeout(300)
        after = await page.evaluate("({ gold: STATE.gold, taps: STATE.totalTaps || 0 })")
        results['T1_tap_gold'] = {
            'gold_avant': before['gold'], 'gold_apres': after['gold'],
            'gold_delta': after['gold'] - before['gold'],
            'taps_avant': before['taps'], 'taps_delta': after['taps'] - before['taps'],
            'ok': after['gold'] > before['gold'] and after['taps'] >= before['taps'] + 8
        }

        # === TEST 2 : upgrade tapValue achetable + applique boost ===
        await page.evaluate("STATE.gold = 100000;")  # plein de gold pour acheter
        before_tap = await page.evaluate("STATE.upgradeTapValue || 0")
        await page.evaluate("if(typeof buyUpgrade === 'function') buyUpgrade('tapValue');")
        await page.wait_for_timeout(150)
        after_tap = await page.evaluate("STATE.upgradeTapValue || 0")
        # Maintenant tap et compare gain
        gold_before = await page.evaluate("STATE.gold")
        await page.mouse.click(stadium_box['x'], stadium_box['y'])
        await page.wait_for_timeout(200)
        gold_after = await page.evaluate("STATE.gold")
        results['T2_upgrade_tap'] = {
            'tap_avant_upg': before_tap, 'tap_apres_upg': after_tap,
            'gold_gain_1tap': gold_after - gold_before,
            'ok': after_tap > before_tap and gold_after > gold_before
        }

        # === TEST 3 : upgrade lapBonus achetable ===
        await page.evaluate("STATE.gold = 100000;")
        before_lap = await page.evaluate("STATE.upgradeLapBonus || 0")
        await page.evaluate("if(typeof buyUpgrade === 'function') buyUpgrade('lapBonus');")
        await page.wait_for_timeout(150)
        after_lap = await page.evaluate("STATE.upgradeLapBonus || 0")
        results['T3_upgrade_lap'] = {
            'avant': before_lap, 'apres': after_lap,
            'ok': after_lap > before_lap
        }

        # === TEST 4 : upgrade critChance achetable ===
        await page.evaluate("STATE.gold = 100000;")
        before_crit = await page.evaluate("STATE.upgradeCritChance || 0")
        await page.evaluate("if(typeof buyUpgrade === 'function') buyUpgrade('critChance');")
        await page.wait_for_timeout(150)
        after_crit = await page.evaluate("STATE.upgradeCritChance || 0")
        results['T4_upgrade_crit'] = {
            'avant': before_crit, 'apres': after_crit,
            'ok': after_crit > before_crit
        }

        # === TEST 5 : Haie franchie = gold bonus ? ===
        await page.evaluate("STATE.lapsRun = 5; STATE.gold = 1000;")
        gold_before_h = await page.evaluate("STATE.gold")
        # Spawn haie + force saut au bon timing
        await page.evaluate("window.RUNNER_2D.spawnHurdle(3);")  # tout proche
        await page.evaluate("window.RUNNER_2D.forceJump();")
        await page.wait_for_timeout(500)
        gold_after_h = await page.evaluate("STATE.gold")
        results['T5_hurdle_bonus'] = {
            'gold_avant': gold_before_h, 'gold_apres': gold_after_h,
            'bonus': gold_after_h - gold_before_h,
            'ok': gold_after_h > gold_before_h  # bonus de min 20 attendu
        }

        # === TEST 6 : Save / Load (vérifie écriture+lecture du localStorage) ===
        # Set values, force save, vérifier immédiatement le contenu du localStorage,
        # puis simuler reload en parsant le save et vérifiant que les valeurs sont là.
        await page.evaluate("STATE.gold = 9876; STATE.lapsRun = 42;")
        await page.evaluate("if(typeof saveNow === 'function') saveNow();")
        await page.wait_for_timeout(100)
        ls_save = await page.evaluate("localStorage.getItem('alchimia.save')")
        save_parsed = json.loads(ls_save) if ls_save else None
        # Le save doit contenir exactement nos valeurs (pas de tick auto entre setter et save synchrone)
        results['T6_save_load'] = {
            'saved_gold': save_parsed.get('gold') if save_parsed else None,
            'saved_laps': save_parsed.get('lapsRun') if save_parsed else None,
            'ok': save_parsed and save_parsed.get('gold') == 9876 and save_parsed.get('lapsRun') == 42
        }

        # === TEST 7 : Progression km en idle (mode auto) ===
        await page.evaluate("STATE.lapsRun = 5; STATE.lapProgress = 0.5;")
        prog_before = await page.evaluate("STATE.lapProgress")
        await page.wait_for_timeout(3000)  # 3 sec d'idle
        prog_after = await page.evaluate("STATE.lapProgress")
        results['T7_idle_progress'] = {
            'avant': prog_before, 'apres': prog_after,
            'delta_3sec': round(prog_after - prog_before, 4),
            'ok': prog_after > prog_before
        }

        # === TEST 8 : 1er km FULL TAP (pas d'idle) ===
        await page.evaluate("STATE.lapsRun = 0; STATE.lapProgress = 0.5;")
        prog0 = await page.evaluate("STATE.lapProgress")
        await page.wait_for_timeout(3000)
        prog0_after = await page.evaluate("STATE.lapProgress")
        results['T8_fulltap_mode'] = {
            'avant': prog0, 'apres': prog0_after,
            'delta_3sec': round(prog0_after - prog0, 4),
            'ok': prog0_after - prog0 < 0.01  # progression quasi nulle attendue
        }

        # === TEST 9 : Speed kmh display réagit au tap ===
        await page.evaluate("STATE.lapsRun = 5;")
        kmh_before = await page.evaluate("window.RUNNER_2D?.getKmh?.() ?? 0")
        tapcount_before = await page.evaluate("window.RUNNER_2D?.getTapBoost?.() ?? 0")
        # Utilise dispatchEvent pour bypass tout button overlay
        await page.evaluate("""
          const el = document.getElementById('runner-stadium');
          const r = el.getBoundingClientRect();
          for(let i = 0; i < 15; i++){
            setTimeout(() => {
              el.dispatchEvent(new PointerEvent('pointerdown', {
                bubbles:true, clientX: r.left + r.width/2, clientY: r.top + r.height/2,
                pointerType:'mouse'
              }));
            }, i * 70);
          }
        """)
        await page.wait_for_timeout(1300)  # 15 * 70 + 250
        kmh_after = await page.evaluate("window.RUNNER_2D?.getKmh?.() ?? 0")
        tapcount_after = await page.evaluate("window.RUNNER_2D?.getTapBoost?.() ?? 0")
        results['T9_kmh_reactive'] = {
            'kmh_avant': round(kmh_before, 1),
            'kmh_apres': round(kmh_after, 1),
            'tapBoost_avant': round(tapcount_before, 2),
            'tapBoost_apres': round(tapcount_after, 2),
            'ok': kmh_after > kmh_before + 3
        }
        results['T9_kmh_reactive'] = {
            'kmh_avant': round(kmh_before, 1),
            'kmh_apres': round(kmh_after, 1),
            'ok': kmh_after > kmh_before + 3  # au moins +3 km/h
        }

        # === RAPPORT ===
        print('\n' + '='*60)
        print('         RAPPORT QA FONCTIONNELLE')
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
