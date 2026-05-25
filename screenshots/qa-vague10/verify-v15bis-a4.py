"""
VAGUE 15bis - Agent 4 - Vérif refonte calendrier daily 30 jours.
Ouvre la modale daily, screenshot, vérifie présence des labels:
- "Item Rare" (jours 5, 12, 19, 26)
- "Item Epic" (jours 7, 14, 21, 28)
- "Cooldown reset" (jours 3, 10, 17, 24)
- "JACKPOT" (jour 30)
Compte aussi les erreurs console (cible = 0).
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
SCREENSHOT = OUT_DIR / "v15bis-a4-daily-30j.png"


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

        time.sleep(1.5)

        # Patch state pour forcer dailyAvailable=true et inspecter le tableau
        try:
            page.evaluate(
                """() => {
                  if(typeof STATE === 'undefined') return;
                  STATE.dailyLast = 0;
                  STATE.dailyStreak = 0;
                }"""
            )
        except Exception as e:
            print(f"[WARN] eval state reset: {e}")

        # Tente d'ouvrir la modale via API JS
        opened = False
        try:
            opened = page.evaluate(
                """() => {
                  if(typeof openDailyModal === 'function'){ openDailyModal(); return true; }
                  if(typeof renderDailyModal === 'function'){
                    renderDailyModal();
                    document.getElementById('daily-modal')?.classList.add('show');
                    return true;
                  }
                  return false;
                }"""
            )
        except Exception as e:
            print(f"[WARN] eval open modal: {e}")

        time.sleep(0.8)

        # Récupère le contenu textuel du body daily
        daily_text = ""
        rewards_dump = []
        try:
            daily_text = page.evaluate(
                """() => document.getElementById('daily-body')?.innerText || ''"""
            )
            rewards_dump = page.evaluate(
                """() => (typeof DAILY_REWARDS !== 'undefined') ? DAILY_REWARDS.map(r => ({d:r.day, t:r.type, l:r.label})) : []"""
            )
        except Exception as e:
            print(f"[WARN] eval daily text: {e}")

        try:
            page.screenshot(path=str(SCREENSHOT), full_page=False)
        except Exception as e:
            print(f"[WARN] screenshot: {e}")

        browser.close()

    # Vérifications
    print("=" * 60)
    print("VAGUE 15bis - A4 - Daily 30j alléchant")
    print("=" * 60)
    print(f"Modal opened: {opened}")
    print(f"Screenshot:   {SCREENSHOT.exists()} -> {SCREENSHOT}")
    print(f"DAILY_REWARDS entries: {len(rewards_dump)}")
    if rewards_dump:
        types_count = {}
        for r in rewards_dump:
            types_count[r["t"]] = types_count.get(r["t"], 0) + 1
        print(f"Types: {types_count}")

    checks = {
        "Item Rare":       "Item Rare" in daily_text,
        "Item Epic":       "Item Epic" in daily_text,
        "Cooldown reset":  "Cooldown reset" in daily_text,
        "JACKPOT":         "JACKPOT" in daily_text,
        "30 entries":      len(rewards_dump) == 30,
        "cooldown type":   any(r["t"] == "cooldown" for r in rewards_dump),
        "item type":       any(r["t"] == "item" for r in rewards_dump),
        "mega3 J30":       any(r["t"] == "mega3" and r["d"] == 30 for r in rewards_dump),
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
