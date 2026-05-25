"""
VAGUE 15 - Agent A1 - Verification FOULÉE (drawRunner v15-a1)
Force STATE.stamina=10, STATE.staminaMax=100, STATE.lapsRun=20 puis screenshot.
Verifie 0 erreur console + visuels haletant <30% stamina + trail colore selon effort.
"""
import json, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"

def run():
    console_msgs = []
    page_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()

        page.on("console", lambda msg: console_msgs.append({"type": msg.type, "text": msg.text}))
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        # Skip story for faster boot
        page.add_init_script("try{localStorage.setItem('storySeen','1')}catch(e){}")

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Démarrer la course si bouton présent
        try:
            page.evaluate("""() => {
                const btn = document.getElementById('start-run-btn') || document.querySelector('[data-action=\"start-run\"]');
                if(btn) btn.click();
            }""")
        except Exception:
            pass
        page.wait_for_timeout(1500)

        # Force STATE values pour tester haletant + trail color
        forced = page.evaluate("""() => {
            if(!window.STATE) return {error: 'STATE not found'};
            window.STATE.stamina = 10;
            window.STATE.staminaMax = 100;
            window.STATE.lapsRun = 20;
            // Force aussi un effort/sprint visible si dispo
            if(window.STATE.upgradeTapValue !== undefined){
                window.STATE.upgradeTapValue = window.STATE.upgradeTapValue || 0;
            }
            return {
                stamina: window.STATE.stamina,
                staminaMax: window.STATE.staminaMax,
                lapsRun: window.STATE.lapsRun,
                ratio: window.STATE.stamina / window.STATE.staminaMax
            };
        }""")

        # Tape un peu pour activer effort (trail)
        try:
            for _ in range(10):
                page.evaluate("""() => {
                    const stadium = document.getElementById('runner-stadium');
                    if(!stadium) return;
                    const rect = stadium.getBoundingClientRect();
                    const e = new PointerEvent('pointerdown', {
                        bubbles: true, cancelable: true,
                        clientX: rect.left + rect.width/2,
                        clientY: rect.top + rect.height/2,
                        pointerType: 'touch'
                    });
                    stadium.dispatchEvent(e);
                }""")
                page.wait_for_timeout(80)
        except Exception:
            pass

        # Re-force stamina basse APRÈS taps (les taps peuvent regen)
        page.evaluate("""() => {
            if(window.STATE){
                window.STATE.stamina = 10;
                window.STATE.staminaMax = 100;
                window.STATE.lapsRun = 20;
            }
        }""")
        page.wait_for_timeout(600)

        shot = OUT / "verify-v15-a1.png"
        page.screenshot(path=str(shot))

        report = {
            "forced_state": forced,
            "screenshot": str(shot),
            "console_msgs": console_msgs[-30:],
            "page_errors": page_errors,
            "console_errors_count": sum(1 for m in console_msgs if m["type"] == "error"),
            "pass": len(page_errors) == 0 and sum(1 for m in console_msgs if m["type"] == "error") == 0,
        }
        (OUT / "verify-v15-a1.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))

        browser.close()
        return 0 if report["pass"] else 1

if __name__ == "__main__":
    sys.exit(run())
