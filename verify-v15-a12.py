"""
VAGUE 15 - Agent A12 - Verification IDLE REMINDER
Init STATE._lastTapAt = performance.now() - 31000 (=> idle depuis 31s),
attendre 1.5s, vérifier que #idle-reminder existe dans le DOM.
0 erreurs console attendues.
"""
import sys, io
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

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

        # Force STATE._lastTapAt en arrière, idle de 31s
        forced = page.evaluate("""() => {
            if(!window.STATE) return {error: 'STATE not found'};
            window.STATE._lastTapAt = performance.now() - 31000;
            // Reset flag idleReminder au cas où
            window._idleReminderShown = false;
            const old = document.getElementById('idle-reminder');
            if(old) old.remove();
            return {
                lastTapAt: window.STATE._lastTapAt,
                now: performance.now(),
                diff: performance.now() - window.STATE._lastTapAt
            };
        }""")
        print(f"Forced STATE._lastTapAt -> {forced}")

        # Attendre que le tick passe (>1.5s pour être large vs setInterval ~16ms)
        page.wait_for_timeout(1500)

        # Vérifie que #idle-reminder existe
        reminder_info = page.evaluate("""() => {
            const el = document.getElementById('idle-reminder');
            return {
                exists: !!el,
                text: el ? el.innerText : null,
                visible: el ? (el.offsetWidth > 0 && el.offsetHeight > 0) : false,
                style_animation: el ? getComputedStyle(el).animationName : null,
                shown_flag: window._idleReminderShown,
            };
        }""")
        print(f"Reminder info -> {reminder_info}")

        # Screenshot
        try:
            page.screenshot(path=str(OUT / "v15-a12-idle-reminder.png"), full_page=False)
        except Exception:
            pass

        errors = 0
        if not reminder_info.get("exists"):
            print("FAIL: #idle-reminder n'existe pas")
            errors += 1
        else:
            print("OK: #idle-reminder créé dans le DOM")
        if not reminder_info.get("visible"):
            print("WARN: #idle-reminder pas visible (offsetWidth/height = 0)")
        else:
            print("OK: #idle-reminder visible")
        text = (reminder_info.get("text") or "")
        if "Toujours là" not in text and "Toujours l" not in text:
            print(f"WARN: texte inattendu: {text!r}")
        else:
            print(f"OK: texte présent: {text!r}")
        anim = reminder_info.get("style_animation") or ""
        if "idleReminderPulse" not in anim:
            print(f"WARN: animation pas idleReminderPulse (got {anim!r})")
        else:
            print(f"OK: animation idleReminderPulse appliquée")

        # Console errors
        console_errs = [m for m in console_msgs if m["type"] == "error"]
        if console_errs:
            print(f"FAIL: {len(console_errs)} erreurs console:")
            for m in console_errs[:10]:
                print(f"  - {m['text']}")
            errors += len(console_errs)
        else:
            print("OK: 0 erreurs console")

        if page_errors:
            print(f"FAIL: {len(page_errors)} page errors:")
            for e in page_errors[:10]:
                print(f"  - {e}")
            errors += len(page_errors)
        else:
            print("OK: 0 page errors")

        browser.close()
        return errors


if __name__ == "__main__":
    err = run()
    print()
    print("=== RÉSUMÉ ===")
    print(f"errors = {err}")
    if err == 0:
        print("STATUS = OK")
        sys.exit(0)
    else:
        print("STATUS = FAIL")
        sys.exit(1)
