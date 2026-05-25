"""
Vérification VAGUE 16ter — Block E : Buffs Bougie / Doping (helpers + UI + HUD indicator)

Lance le jeu via playwright, vérifie :
 - typeof window.buyBougie === 'function'
 - typeof window.buyDoping === 'function'
 - typeof window.getActiveBuffMul === 'function'
 - STATE.gold = 100000, eval buyBougie() → STATE.gold === 95000 + STATE.buffs.bougie > Date.now()
 - getActiveBuffMul() === 1.05
 - #hud-buff-indicator apparaît après renderStats
 - 0 erreurs console
"""
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print("[FATAL] playwright manquant :", e)
    sys.exit(1)

INDEX = Path("D:/alchimia/index.html").resolve()
URL = INDEX.as_uri()

console_errors = []

def on_console(msg):
    if msg.type == "error":
        console_errors.append(msg.text)

def main():
    results = []
    def add(label, ok, detail=""):
        tag = "OK" if ok else "FAIL"
        results.append((ok, f"[{tag}] {label}" + (f" — {detail}" if detail else "")))
        return ok

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 412, "height": 915})
        page = ctx.new_page()
        page.on("console", on_console)
        page.goto(URL)
        page.wait_for_load_state("networkidle")
        # Petit délai pour init complet
        page.wait_for_timeout(800)

        # 1. helpers exposés
        has_bougie = page.evaluate("typeof window.buyBougie === 'function'")
        has_doping = page.evaluate("typeof window.buyDoping === 'function'")
        has_mul = page.evaluate("typeof window.getActiveBuffMul === 'function'")
        add("window.buyBougie est fonction", has_bougie)
        add("window.buyDoping est fonction", has_doping)
        add("window.getActiveBuffMul est fonction", has_mul)

        # 2. buyBougie effects
        page.evaluate("STATE.gold = 100000")
        ok_call = page.evaluate("buyBougie()")
        add("buyBougie() retourne true", ok_call == True, f"retour={ok_call!r}")
        new_gold = page.evaluate("STATE.gold")
        add("STATE.gold === 95000 après buyBougie", new_gold == 95000, f"gold={new_gold}")
        bougie_active = page.evaluate("STATE.buffs && STATE.buffs.bougie > Date.now()")
        add("STATE.buffs.bougie actif (future timestamp)", bool(bougie_active))

        # 3. getActiveBuffMul == 1.05
        mul = page.evaluate("getActiveBuffMul()")
        # Tolérance flottants
        add("getActiveBuffMul() === 1.05", abs(mul - 1.05) < 1e-9, f"mul={mul}")

        # 4. HUD indicator présent après renderStats
        page.evaluate("if(typeof renderStats === 'function') renderStats();")
        page.wait_for_timeout(120)
        ind_present = page.evaluate("!!document.getElementById('hud-buff-indicator')")
        add("#hud-buff-indicator présent dans le DOM", ind_present)
        if ind_present:
            ind_text = page.evaluate("document.getElementById('hud-buff-indicator').textContent")
            add("Indicator contient l'icône bougie", "🕯️" in ind_text, f"text={ind_text!r}")

        # 5. 0 erreur console
        add("0 erreurs console", len(console_errors) == 0,
            f"errors={console_errors[:3]!r}" if console_errors else "")

        browser.close()

    print("\n=== Résultats VAGUE 16ter E ===")
    ok_count = 0
    for ok, line in results:
        print(line)
        if ok: ok_count += 1
    print(f"\nScore : {ok_count}/{len(results)}")
    if ok_count == len(results):
        print("STATUS: ALL GREEN")
        sys.exit(0)
    else:
        print("STATUS: FAIL")
        sys.exit(2)

if __name__ == "__main__":
    main()
