"""
VAGUE 14b — Verify STAMINA = vraie ressource (decay au tap, regen au repos).
Headless 540x960. Skip onboarding. Check :
  T0     : STATE.stamina === 100
  T+30   : 30 taps rapides → STATE.stamina < 50
  T+5s   : repos 5s → STATE.stamina > 80
  console errors == 0
  screenshot vague14b-stamina-hud.png (barre visible)
"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"

def main():
    report = {
        "http": None,
        "T0": None,
        "T_after_30_taps": None,
        "T_after_5s_rest": None,
        "console_errors": [],
        "console_warnings": [],
        "pageerrors": [],
        "hud_bar_present": False,
        "stamina_max": None,
        "checks": {},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()

        def on_console(msg):
            try:
                t = msg.type
                txt = msg.text
                if t == "error":
                    if len(report["console_errors"]) < 30:
                        report["console_errors"].append(txt[:400])
                elif t == "warning":
                    if len(report["console_warnings"]) < 20:
                        report["console_warnings"].append(txt[:400])
            except Exception:
                pass
        page.on("console", on_console)
        page.on("pageerror", lambda exc: report["pageerrors"].append(str(exc)[:400]))

        resp = page.goto(URL, wait_until="domcontentloaded")
        report["http"] = resp.status if resp else None

        # skip onboarding
        page.evaluate("""() => {
            try {
                localStorage.setItem('foulee.tutoV2', 'done');
                localStorage.setItem('foulee.storySeen', '1');
                localStorage.setItem('foulee.gigaTutoSeen', '1');
                localStorage.setItem('foulee.lastSeenTier', '0');
                localStorage.setItem('foulee.onboardingDone', '1');
                localStorage.setItem('foulee.openingSeen', '1');
                localStorage.setItem('foulee.cinematicSeen', '1');
            } catch(e){}
        }""")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(5500)  # splash + cinematic

        # Force close overlays
        page.evaluate("""() => {
            const ids = ['intro', 'story-intro', 'opening-credits', 'opening-overlay', 'giga-tuto'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if(el){ el.style.display = 'none'; el.classList.add('gone'); }
            });
        }""")
        page.wait_for_timeout(800)

        # === T0 : reset stamina to 100 (au cas où des taps auto auraient eu lieu)
        page.evaluate("""() => {
            if(window.STATE){
                window.STATE.staminaMax = 100 + (window.STATE.upgradeEndurance || 0) * 10;
                window.STATE.stamina = window.STATE.staminaMax;
                window.STATE._lastTapAt = 0;
            }
        }""")
        page.wait_for_timeout(120)

        t0 = page.evaluate("""() => ({
            stamina: window.STATE?.stamina,
            staminaMax: window.STATE?.staminaMax,
            hasBar: !!document.getElementById('hud-stamina-bar'),
            barWidth: document.getElementById('hud-stamina-bar')?.style.width || null
        })""")
        report["T0"] = t0
        report["hud_bar_present"] = bool(t0.get("hasBar"))
        report["stamina_max"] = t0.get("staminaMax")
        report["checks"]["T0_stamina_eq_100"] = (t0.get("stamina") == 100)

        # === T+30 taps (espaces de 90ms : confortablement >cooldown 50ms,
        # et bien <500ms du seuil regen → tous les taps comptent, pas de regen pendant)
        page.evaluate("""() => {
            return new Promise((resolve) => {
                let i = 0;
                const id = setInterval(() => {
                    if(typeof tapBoost === 'function') tapBoost();
                    else if(typeof window.tapBoost === 'function') window.tapBoost();
                    i++;
                    if(i >= 30){ clearInterval(id); resolve(); }
                }, 90);
            });
        }""")
        page.wait_for_timeout(200)
        t1 = page.evaluate("""() => ({
            stamina: window.STATE?.stamina,
            staminaMax: window.STATE?.staminaMax,
        })""")
        report["T_after_30_taps"] = t1
        report["checks"]["T1_stamina_lt_50"] = (t1.get("stamina") is not None and t1["stamina"] < 50)

        # screenshot avec stamina basse (HUD orange/rouge)
        try:
            page.screenshot(path=str(OUT / "vague14b-stamina-low.png"))
        except Exception:
            pass

        # === T+5s rest (regen 8/sec → ~40 points)
        # Le tick principal doit tourner ; on attend simplement 5s
        page.wait_for_timeout(5200)
        t2 = page.evaluate("""() => ({
            stamina: window.STATE?.stamina,
            staminaMax: window.STATE?.staminaMax,
            barWidth: document.getElementById('hud-stamina-bar')?.style.width || null
        })""")
        report["T_after_5s_rest"] = t2
        report["checks"]["T2_stamina_gt_80"] = (t2.get("stamina") is not None and t2["stamina"] > 80)

        # screenshot final (HUD vert plein)
        try:
            page.screenshot(path=str(OUT / "vague14b-stamina-hud.png"))
        except Exception:
            pass

        # === Verdict
        report["checks"]["console_clean"] = (len(report["console_errors"]) == 0 and len(report["pageerrors"]) == 0)
        report["checks"]["hud_visible"] = report["hud_bar_present"]
        all_passed = all(report["checks"].values())
        report["verdict"] = "PASS" if all_passed else "FAIL"

        browser.close()

    # Write JSON report next to screenshots
    report_path = OUT / "vague14b-stamina-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
