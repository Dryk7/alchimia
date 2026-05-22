"""Vérifie les mécaniques de challenge ajoutées."""
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

        # === T1 : Drift haie scale avec km ===
        # Mesure le drift à km 1 vs km 20
        await page.evaluate("STATE.lapsRun = 1;")
        await page.evaluate("window.RUNNER_2D.spawnHurdle(80, 'single'); window.RUNNER_2D.getHurdles().length = 1;")
        await page.wait_for_timeout(1000)
        drift_km1 = await page.evaluate("80 - (window.RUNNER_2D?.getHurdles?.()?.[0]?.metersAhead ?? 80)")
        # Reset puis km 20
        await page.evaluate("window.RUNNER_2D.getHurdles().length = 0;")
        await page.evaluate("STATE.lapsRun = 20;")
        await page.evaluate("window.RUNNER_2D.spawnHurdle(80, 'single');")
        await page.wait_for_timeout(1000)
        drift_km20 = await page.evaluate("80 - (window.RUNNER_2D?.getHurdles?.()?.[0]?.metersAhead ?? 80)")
        results['T1_hurdle_speed_scale'] = {
            'drift_km1_en_1s': round(drift_km1, 1),
            'drift_km20_en_1s': round(drift_km20, 1),
            'ratio': round(drift_km20 / max(drift_km1, 0.01), 2),
            'ok': drift_km20 > drift_km1 * 1.3  # au moins +30% plus rapide
        }

        # === T2 : Stamina réduit la vitesse ===
        # Stam haute = full speed
        await page.evaluate("STATE.runnerStamina = 1.5;")
        await page.wait_for_timeout(500)
        kmh_full = await page.evaluate("window.RUNNER_2D?.getKmh?.() ?? 0")
        # Stam basse = vitesse réduite
        await page.evaluate("STATE.runnerStamina = 0.31;")
        await page.wait_for_timeout(500)
        kmh_tired = await page.evaluate("window.RUNNER_2D?.getKmh?.() ?? 0")
        results['T2_stamina_speed'] = {
            'kmh_stam_1_5': round(kmh_full, 1),
            'kmh_stam_0_3': round(kmh_tired, 1),
            'ok': kmh_tired < kmh_full  # ralenti
        }

        # === T3 : Streak de 3 fails déclenche sanction ===
        await page.evaluate("STATE.lapsRun = 5; STATE.gold = 1000;")
        # Vide haies + spawn 3 successivement, force pas de saut
        await page.evaluate("window.RUNNER_2D.getHurdles().length = 0;")
        await page.evaluate("window.RUNNER_2D.spawnHurdle(2, 'single');")
        await page.wait_for_timeout(800)  # haie passe sans saut → fail #1
        await page.evaluate("window.RUNNER_2D.spawnHurdle(2, 'single');")
        await page.wait_for_timeout(800)  # fail #2
        gold_before_streak = await page.evaluate("STATE.gold")
        await page.evaluate("window.RUNNER_2D.spawnHurdle(2, 'single');")
        await page.wait_for_timeout(800)  # fail #3 → sanction
        gold_after_streak = await page.evaluate("STATE.gold")
        results['T3_streak_penalty'] = {
            'gold_avant_3e_fail': gold_before_streak,
            'gold_apres_3e_fail': gold_after_streak,
            'penalty': gold_before_streak - gold_after_streak,
            'ok': gold_after_streak < gold_before_streak  # gold perdu
        }

        # === Screenshot stamina low ===
        await page.evaluate("STATE.runnerStamina = 0.32;")
        await page.wait_for_timeout(400)
        await page.screenshot(path='D:/alchimia/screenshots/challenge-stamina-low.png')

        # === RAPPORT ===
        print('\n' + '='*60)
        print('         QA CHALLENGE')
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
