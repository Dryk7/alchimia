"""
QA4 - Vérification du système météo (vague 20 P3)
- Cycle tous les 3 km
- HUD #hud-weather updated
- speedMul / staminaRegenMul / dropMul appliqués
- Cycle déterministe (seed-based)
"""
from playwright.sync_api import sync_playwright
import json

URL = "http://localhost:8770/"
RESULTS = {"console_errors": [], "checks": {}}


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()

        page.on("pageerror", lambda e: RESULTS["console_errors"].append(f"PAGEERROR: {e}"))
        page.on("console", lambda m: RESULTS["console_errors"].append(f"{m.type}: {m.text}")
                if m.type == "error" else None)

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        # Skip onboarding via localStorage + bypass tuto
        page.evaluate("""() => {
            try {
                localStorage.setItem('alchimia_tuto_done', '1');
                localStorage.setItem('alchimia_onboarding_done', '1');
                if(window.STATE){
                    window.STATE.tutoDone = true;
                    window.STATE.onboardingDone = true;
                }
            } catch(e){}
        }""")
        page.wait_for_timeout(500)

        # Force start the game
        page.evaluate("""() => {
            try {
                const btn = document.querySelector('[onclick*=\"startGame\"], #btn-start, .btn-start');
                if(btn) btn.click();
            } catch(e){}
            // Close any visible modal
            document.querySelectorAll('.modal.show, .overlay.show').forEach(m => m.classList.remove('show'));
        }""")
        page.wait_for_timeout(800)

        # === Q1: Cycle tous les 3 km ===
        cycle_results = []
        for km in [0, 3, 6, 9, 12, 15, 18]:
            data = page.evaluate(f"""() => {{
                window.STATE.lapsRun = {km};
                // Force re-roll : weather.endsAtKm doit être <= km pour déclencher
                if(window.STATE.weather) window.STATE.weather.endsAtKm = {km};
                window.updateWeather();
                const hudEl = document.getElementById('hud-weather');
                return {{
                    type: window.STATE.weather?.type,
                    startedAtKm: window.STATE.weather?.startedAtKm,
                    endsAtKm: window.STATE.weather?.endsAtKm,
                    hudHTML: hudEl ? hudEl.innerHTML : null,
                    hudText: hudEl ? hudEl.textContent.trim() : null,
                    speedMul: window.getWeatherMul('speedMul'),
                    staminaRegenMul: window.getWeatherMul('staminaRegenMul'),
                    dropMul: window.getWeatherMul('dropMul')
                }};
            }}""")
            cycle_results.append({"km": km, **data})
            page.wait_for_timeout(50)

        RESULTS["checks"]["cycle"] = cycle_results

        # Q1: cycles bien tous les 3 km ?
        # endsAtKm doit être startedAtKm + 3
        cycle_ok = all(c["endsAtKm"] == c["startedAtKm"] + 3 for c in cycle_results)
        RESULTS["checks"]["cycle_3km_ok"] = cycle_ok

        # Q2: HUD reflète le type ?
        hud_reflects = []
        for c in cycle_results:
            icons = {"clear": "☀", "rain": "🌧", "wind": "💨", "heat": "🔥"}
            expected_icon_substr = icons.get(c["type"], "")
            in_hud = expected_icon_substr in (c["hudHTML"] or "")
            hud_reflects.append({"km": c["km"], "type": c["type"], "in_hud": in_hud,
                                 "hud_snippet": (c["hudHTML"] or "")[:80]})
        RESULTS["checks"]["hud_reflects"] = hud_reflects
        RESULTS["checks"]["hud_ok"] = all(h["in_hud"] for h in hud_reflects)

        # === Q3: displayKmh varie selon météo ===
        # Force rain et lire un displayKmh / vitesse perçue
        speed_test = page.evaluate("""() => {
            const results = {};
            for(const type of ['clear','rain','wind','heat']){
                window.STATE.weather = { type, startedAtKm: 0, endsAtKm: 3 };
                results[type] = {
                    speedMul: window.getWeatherMul('speedMul'),
                    staminaRegenMul: window.getWeatherMul('staminaRegenMul'),
                    dropMul: window.getWeatherMul('dropMul')
                };
            }
            return results;
        }""")
        RESULTS["checks"]["multipliers"] = speed_test

        # Différence concrète clear vs rain
        clear_speed = speed_test["clear"]["speedMul"]
        rain_speed = speed_test["rain"]["speedMul"]
        wind_speed = speed_test["wind"]["speedMul"]
        speed_diff_pct = (clear_speed - rain_speed) / rain_speed * 100 if rain_speed else 0
        RESULTS["checks"]["speed_clear_vs_rain_pct"] = round(speed_diff_pct, 2)
        # devrait être 1.00/0.90 = 11.11%
        RESULTS["checks"]["speed_diff_meets_11pct"] = abs(speed_diff_pct - 11.11) < 0.5

        # Mesure réelle displayKmh in-game pour clear vs rain (laisse tourner ~2s chaque)
        # On force la vitesse via les variables internes du loop
        speed_measured = {}
        for w in ["clear", "rain", "wind"]:
            page.evaluate(f"""() => {{
                window.STATE.weather = {{ type:'{w}', startedAtKm:0, endsAtKm:3 }};
            }}""")
            page.wait_for_timeout(1500)
            # Read displayKmh via UI HUD speed if available
            kmh_val = page.evaluate("""() => {
                // Try the HUD speed counter
                const el = document.querySelector('#hud-speed, .hud-speed, [data-speed]');
                if(el){
                    const t = el.textContent || '';
                    const m = t.match(/([0-9]+\\.?[0-9]*)/);
                    return m ? parseFloat(m[1]) : null;
                }
                return null;
            }""")
            speed_measured[w] = kmh_val
        RESULTS["checks"]["measured_kmh"] = speed_measured

        # === Q4: stamina regen ralentie par heat ===
        stamina_test = page.evaluate("""() => {
            const samples = {};
            for(const t of ['clear','heat']){
                window.STATE.weather = { type: t, startedAtKm:0, endsAtKm:3 };
                samples[t] = window.getWeatherMul('staminaRegenMul');
            }
            return samples;
        }""")
        RESULTS["checks"]["stamina_regen"] = stamina_test
        RESULTS["checks"]["stamina_heat_slower"] = stamina_test["heat"] < stamina_test["clear"]

        # === Q5: Cycle déterministe ===
        det = page.evaluate("""() => {
            const results = [];
            for(const km of [3, 6, 9, 12, 15, 18, 21, 24, 30, 60, 99]){
                // First pass
                window.STATE.lapsRun = km;
                window.STATE.weather = { type:'clear', startedAtKm: km-3, endsAtKm: km };
                window.updateWeather();
                const t1 = window.STATE.weather.type;
                // Reset and re-do
                window.STATE.weather = { type:'wind', startedAtKm: km-3, endsAtKm: km };
                window.updateWeather();
                const t2 = window.STATE.weather.type;
                results.push({ km, t1, t2, deterministic: t1 === t2 });
            }
            return results;
        }""")
        RESULTS["checks"]["determinism"] = det
        RESULTS["checks"]["determinism_ok"] = all(d["deterministic"] for d in det)

        # Diversité : au moins 3 types sur 11 km tests
        types_seen = set(d["t1"] for d in det)
        RESULTS["checks"]["types_seen"] = list(types_seen)
        RESULTS["checks"]["diversity_ok"] = len(types_seen) >= 3

        # Check d'erreurs console (filtrer warnings non bloquants)
        filtered_errs = [e for e in RESULTS["console_errors"]
                         if "404" not in e and "favicon" not in e.lower()]
        RESULTS["checks"]["console_errors_count"] = len(filtered_errs)
        RESULTS["checks"]["console_errors"] = filtered_errs[:10]

        browser.close()


if __name__ == "__main__":
    import sys, io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass
    try:
        run()
    except Exception as e:
        RESULTS["fatal"] = str(e)
    out = json.dumps(RESULTS, indent=2, ensure_ascii=False, default=str)
    # Write to file as backup
    try:
        with open("D:/alchimia/screenshots/qa-vague22/qa4-weather-out.json", "w", encoding="utf-8") as f:
            f.write(out)
    except Exception:
        pass
    try:
        print(out)
    except UnicodeEncodeError:
        print(out.encode('ascii', 'replace').decode('ascii'))
