"""
VAGUE 15bis - Agent A6 - Vérif toast notification "NOUVEAU : X débloqué !"
quand un upgrade passe de hidden -> visible (transition de seuil km).

Étapes :
1. Skip onboarding (storySeen + activeTuto)
2. Force STATE.lapsRun = 0 + appel applyProgressiveDisclosure -> rien révélé
3. Force STATE.lapsRun = 3 + appel applyProgressiveDisclosure
4. Vérifie qu'un élément [id^="unlock-toast"] existe
5. Compte erreurs console (cible = 0)
"""
import sys
import time
import io
from pathlib import Path

# Force UTF-8 stdout for emojis dans logs
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[FAIL] playwright introuvable. pip install playwright && playwright install chromium")
    sys.exit(1)

INDEX = Path("D:/alchimia/index.html").resolve()
OUT_DIR = Path("D:/alchimia/screenshots/qa-vague10")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT = OUT_DIR / "v15bis-a6-unlock-toast.png"


def main():
    if not INDEX.exists():
        print(f"[FAIL] {INDEX} introuvable")
        return 1

    url = INDEX.as_uri()
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 414, "height": 896})
        page = ctx.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(f"PAGEERROR: {err}"))

        # Skip story/tutos pour boot rapide
        page.add_init_script("""
            try{
              localStorage.setItem('storySeen','1');
              localStorage.setItem('foulee.activeTutoV1', JSON.stringify({done:true}));
            }catch(e){}
        """)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"[FAIL] goto: {e}")
            browser.close()
            return 1

        time.sleep(1.5)

        # Étape A : force lapsRun=0 et applique disclosure
        baseline = page.evaluate("""() => {
            if(!window.STATE) return {error: 'STATE not found'};
            window.STATE.lapsRun = 0;
            window._revealedUnlocks = new Set();
            if(typeof applyProgressiveDisclosure === 'function'){
                applyProgressiveDisclosure();
            }
            const initial = document.querySelectorAll('[id^="unlock-toast"]').length;
            return { laps: window.STATE.lapsRun, toasts: initial };
        }""")
        print(f"Baseline (lapsRun=0): {baseline}")

        time.sleep(1.0)

        # Étape B : passe à lapsRun=3, applique disclosure -> doit déclencher toast(s)
        triggered = page.evaluate("""() => {
            if(!window.STATE) return {error: 'STATE not found'};
            window.STATE.lapsRun = 3;
            if(typeof applyProgressiveDisclosure === 'function'){
                applyProgressiveDisclosure();
            }
            const nodes = document.querySelectorAll('[id^="unlock-toast"]');
            return {
                laps: window.STATE.lapsRun,
                count: nodes.length,
                ids: Array.from(nodes).map(n => n.id),
                texts: Array.from(nodes).map(n => n.textContent),
                revealedSize: (window._revealedUnlocks && window._revealedUnlocks.size) || 0
            };
        }""")
        print(f"After lapsRun=3: {triggered}")

        time.sleep(1.0)

        try:
            page.screenshot(path=str(SCREENSHOT), full_page=False)
        except Exception as e:
            print(f"[WARN] screenshot: {e}")

        # Vérifie aussi qu'une seconde application ne re-trigger pas le même toast
        idempotent = page.evaluate("""() => {
            const sizeBefore = (window._revealedUnlocks && window._revealedUnlocks.size) || 0;
            if(typeof applyProgressiveDisclosure === 'function'){
                applyProgressiveDisclosure();
            }
            const sizeAfter = (window._revealedUnlocks && window._revealedUnlocks.size) || 0;
            return { before: sizeBefore, after: sizeAfter, same: sizeBefore === sizeAfter };
        }""")
        print(f"Idempotency check: {idempotent}")

        browser.close()

    # Vérifications
    print("=" * 60)
    print("VAGUE 15bis - A6 - Unlock toast notification")
    print("=" * 60)

    has_toast = isinstance(triggered, dict) and triggered.get("count", 0) > 0
    revealed = isinstance(triggered, dict) and triggered.get("revealedSize", 0) > 0
    baseline_clean = isinstance(baseline, dict) and baseline.get("toasts", 99) == 0
    no_console_errors = len(console_errors) == 0
    idempotent_ok = isinstance(idempotent, dict) and idempotent.get("same", False)

    checks = {
        "Baseline 0 toast at lapsRun=0":   baseline_clean,
        "Toast(s) created at lapsRun=3":   has_toast,
        "_revealedUnlocks tracks items":   revealed,
        "Idempotent re-apply":             idempotent_ok,
        "0 console errors":                no_console_errors,
    }

    print("-" * 60)
    all_ok = True
    for k, v in checks.items():
        flag = "OK " if v else "FAIL"
        print(f"  [{flag}] {k}")
        if not v:
            all_ok = False

    print("-" * 60)
    print(f"Console errors: {len(console_errors)}")
    for e in console_errors[:5]:
        print(f"  - {e}")

    print("=" * 60)
    print("RESULT:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
