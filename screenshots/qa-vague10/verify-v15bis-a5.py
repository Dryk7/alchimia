"""
VAGUE 15bis - Agent 5 - Verify hint contextuel stamina basse.

Skip onboarding, force STATE.stamina=5 / staminaMax=100, attendre que le HUD
update declenche le hint #tuto-hint avec un message stamina/souffle.

Verifie :
- #tuto-hint.classList contient 'show' OU
- #tuto-msg.textContent contient "stamina" ou "souffle"
- 0 erreurs console
"""
import os
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[FAIL] playwright introuvable. pip install playwright && playwright install chromium")
    sys.exit(1)

INDEX = Path("D:/alchimia/index.html").resolve()
OUT_DIR = Path("D:/alchimia/screenshots/qa-vague10")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT = OUT_DIR / "v15bis-a5-stamina-hint.png"


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

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"[FAIL] goto: {e}")
            browser.close()
            return 1

        # Laisse le temps que tout charge
        time.sleep(2.0)

        # Skip onboarding : marquer tuto fait + click start-btn si dispo
        try:
            page.evaluate(
                """() => {
                  try { localStorage.setItem('foulee.tutoSeen', '1'); } catch(e){}
                  try { localStorage.setItem('foulee.gigaTutoSeen', '1'); } catch(e){}
                  try { localStorage.setItem('foulee.storyIntroSeen', '1'); } catch(e){}
                  // Click start-btn si present
                  const b = document.getElementById('start-btn');
                  if(b) b.click();
                  // Skip giga si overlay encore la
                  const skipBtn = document.getElementById('giga-skip');
                  if(skipBtn) skipBtn.click();
                }"""
            )
        except Exception as e:
            print(f"[WARN] eval skip onboarding: {e}")

        time.sleep(2.0)

        # Force la stamina basse
        try:
            page.evaluate(
                """() => {
                  if(typeof STATE === 'undefined') return false;
                  STATE.stamina = 5;
                  STATE.staminaMax = 100;
                  // Reset le flag oneshot pour eviter une seance precedente
                  window._staminaLowHintShown = false;
                  try { localStorage.removeItem('foulee.tutoStaminaSeen'); } catch(e){}
                  return true;
                }"""
            )
        except Exception as e:
            print(f"[WARN] eval force stamina: {e}")

        # Attendre 2s que le HUD update tick et declenche le hint
        time.sleep(2.5)

        # Lire l'etat du hint
        hint_state = {}
        try:
            hint_state = page.evaluate(
                """() => {
                  const h = document.getElementById('tuto-hint');
                  const m = document.getElementById('tuto-msg');
                  return {
                    hintExists: !!h,
                    msgExists: !!m,
                    hasShowClass: h ? h.classList.contains('show') : false,
                    msgText: m ? (m.textContent || '') : '',
                    flagSet: !!window._staminaLowHintShown,
                    lsFlag: localStorage.getItem('foulee.tutoStaminaSeen') === '1',
                    staminaRatio: (STATE && STATE.stamina != null && STATE.staminaMax) ? (STATE.stamina/STATE.staminaMax) : null,
                  };
                }"""
            )
        except Exception as e:
            print(f"[WARN] eval read hint: {e}")

        try:
            page.screenshot(path=str(SCREENSHOT), full_page=False)
        except Exception as e:
            print(f"[WARN] screenshot: {e}")

        browser.close()

    # Verifications
    print("=" * 60)
    print("VAGUE 15bis - A5 - Hint stamina basse")
    print("=" * 60)
    print(f"Screenshot: {SCREENSHOT.exists()} -> {SCREENSHOT}")
    # Strip non-ascii pour les consoles Windows cp1252
    def _safe(v):
        if isinstance(v, str): return v.encode('ascii', 'replace').decode('ascii')
        return v
    safe_state = {k: _safe(v) for k, v in hint_state.items()}
    print(f"Hint state: {safe_state}")

    msg_text = (hint_state.get("msgText") or "").lower()
    has_show = bool(hint_state.get("hasShowClass"))
    msg_match = ("stamina" in msg_text) or ("souffle" in msg_text)

    checks = {
        "hint #tuto-hint exists": hint_state.get("hintExists", False),
        "msg #tuto-msg exists":   hint_state.get("msgExists", False),
        "show OR msg match":      has_show or msg_match,
        "flag oneshot set":       hint_state.get("flagSet", False),
        "localStorage flag set":  hint_state.get("lsFlag", False),
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

    final_ok = all_ok and len(console_errors) == 0
    print("=" * 60)
    print("RESULT:", "PASS" if final_ok else ("PARTIAL" if all_ok else "FAIL"))
    return 0 if final_ok else 2


if __name__ == "__main__":
    sys.exit(main())
