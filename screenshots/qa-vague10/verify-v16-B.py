"""
VAGUE 16 - Verification economie B : durcissement courbe upgrades.

Verifie :
  1. upgradeCost('tapValue') a lvl 0 -> base 80
  2. cost a lvl 5 -> ~80 * 1.55^5 ~= 700
  3. cost a lvl 25 -> applique soft cap x10
  4. cost a lvl 30 -> applique soft cap x100
  5. buyUpgrade refuse au-dela de lvl 50 (hard cap)
  6. Toutes les autres upgrades : factors mis a jour

Output : OK/FAIL par check + 0 erreurs console.
"""
import json, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"

# Reference factors apres refonte
EXPECTED_FACTORS = {
    'tapValue': 1.55,
    'critChance': 1.60,
    'lapBonus': 1.55,
    'autoTap': 1.65,
    'endurance': 1.60,
    'eagleEye': 1.55,
    'baseSpeed': 1.65,
    'cruiseControl': 1.55,
}

def main():
    results = {"checks": [], "console_errors": [], "summary": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()

        # Capture erreurs console
        page.on("pageerror", lambda exc: results["console_errors"].append({"type": "pageerror", "msg": str(exc)}))
        page.on("console", lambda msg: results["console_errors"].append({"type": "consoleerror", "msg": msg.text}) if msg.type == "error" else None)

        page.goto(URL, wait_until="networkidle")
        time.sleep(1.0)

        # Skip story si presente
        try:
            page.evaluate("""() => {
                if(window.STATE) window.STATE.storySeen = true;
                const s = document.getElementById('story-intro');
                if(s){ s.style.display='none'; s.classList.add('gone'); }
            }""")
        except Exception:
            pass

        # === CHECK 1 : factors UPGRADES_TAP corrects
        try:
            actual_factors = page.evaluate("""() => {
                const out = {};
                for(const k in window.UPGRADES_TAP){ out[k] = window.UPGRADES_TAP[k].factor; }
                return out;
            }""")
            all_ok = True
            mismatch = {}
            for k, expected in EXPECTED_FACTORS.items():
                got = actual_factors.get(k)
                if got is None or abs(got - expected) > 0.001:
                    all_ok = False
                    mismatch[k] = {"expected": expected, "got": got}
            results["checks"].append({
                "id": 1, "name": "factors", "ok": all_ok,
                "factors": actual_factors, "mismatch": mismatch
            })
        except Exception as e:
            results["checks"].append({"id": 1, "name": "factors", "ok": False, "error": str(e)})

        # === CHECK 2 : cost lvl 0 = base 80
        try:
            cost_lvl0 = page.evaluate("""() => {
                window.STATE.upgradeTapValue = 0;
                return window.upgradeCost('tapValue');
            }""")
            ok = cost_lvl0 == 80
            results["checks"].append({"id": 2, "name": "cost_lvl_0", "ok": ok, "cost": cost_lvl0, "expected": 80})
        except Exception as e:
            results["checks"].append({"id": 2, "name": "cost_lvl_0", "ok": False, "error": str(e)})

        # === CHECK 3 : cost lvl 5 ~= 80 * 1.55^5 ~= 706
        try:
            cost_lvl5 = page.evaluate("""() => {
                window.STATE.upgradeTapValue = 5;
                return window.upgradeCost('tapValue');
            }""")
            expected_lvl5 = int(80 * (1.55 ** 5))  # ~ 706
            ok = abs(cost_lvl5 - expected_lvl5) <= 5  # tolerance floor
            results["checks"].append({
                "id": 3, "name": "cost_lvl_5", "ok": ok,
                "cost": cost_lvl5, "expected_approx": expected_lvl5
            })
        except Exception as e:
            results["checks"].append({"id": 3, "name": "cost_lvl_5", "ok": False, "error": str(e)})

        # === CHECK 4 : cost lvl 25 inclut soft cap x10
        try:
            data_lvl25 = page.evaluate("""() => {
                window.STATE.upgradeTapValue = 25;
                return {
                    cost: window.upgradeCost('tapValue'),
                    raw_no_cap: Math.floor(80 * Math.pow(1.55, 25))
                };
            }""")
            cost_lvl25 = data_lvl25["cost"]
            raw_lvl25 = data_lvl25["raw_no_cap"]
            expected_with_cap = int(80 * (1.55 ** 25) * 10)
            ratio = cost_lvl25 / raw_lvl25 if raw_lvl25 else 0
            ok = 9.5 < ratio < 10.5  # x10 soft cap
            results["checks"].append({
                "id": 4, "name": "soft_cap_lvl_25", "ok": ok,
                "cost": cost_lvl25, "raw_no_cap": raw_lvl25,
                "ratio_to_raw": ratio, "expected_ratio": 10
            })
        except Exception as e:
            results["checks"].append({"id": 4, "name": "soft_cap_lvl_25", "ok": False, "error": str(e)})

        # === CHECK 5 : cost lvl 30 inclut soft cap x100
        try:
            data_lvl30 = page.evaluate("""() => {
                window.STATE.upgradeTapValue = 30;
                return {
                    cost: window.upgradeCost('tapValue'),
                    raw_no_cap: Math.floor(80 * Math.pow(1.55, 30))
                };
            }""")
            cost_lvl30 = data_lvl30["cost"]
            raw_lvl30 = data_lvl30["raw_no_cap"]
            ratio = cost_lvl30 / raw_lvl30 if raw_lvl30 else 0
            ok = 95 < ratio < 105  # x100 soft cap
            results["checks"].append({
                "id": 5, "name": "soft_cap_lvl_30", "ok": ok,
                "cost": cost_lvl30, "raw_no_cap": raw_lvl30,
                "ratio_to_raw": ratio, "expected_ratio": 100
            })
        except Exception as e:
            results["checks"].append({"id": 5, "name": "soft_cap_lvl_30", "ok": False, "error": str(e)})

        # === CHECK 6 : hard cap a lvl 50 -> buyUpgrade refuse
        try:
            hard_cap_test = page.evaluate("""() => {
                window.STATE.upgradeTapValue = 50;
                window.STATE.gold = 1e20;  // assez de gold pour ne pas etre bloque par cost
                const lvl_before = window.STATE.upgradeTapValue;
                window.buyUpgrade('tapValue');
                const lvl_after = window.STATE.upgradeTapValue;
                return { lvl_before: lvl_before, lvl_after: lvl_after, blocked: lvl_after === lvl_before };
            }""")
            ok = hard_cap_test["blocked"] is True
            results["checks"].append({
                "id": 6, "name": "hard_cap_50", "ok": ok,
                "data": hard_cap_test
            })
        except Exception as e:
            results["checks"].append({"id": 6, "name": "hard_cap_50", "ok": False, "error": str(e)})

        # Resume
        ok_count = sum(1 for c in results["checks"] if c.get("ok"))
        total = len(results["checks"])
        results["summary"] = {
            "passed": ok_count, "total": total,
            "console_errors_count": len(results["console_errors"])
        }

        # Save
        out_json = OUT / "verify-v16-B-report.json"
        out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        # Output lisible
        print("=" * 60)
        print("VAGUE 16 - VERIFY ECONOMIE B (durcir upgrades)")
        print("=" * 60)
        for c in results["checks"]:
            mark = "OK" if c.get("ok") else "FAIL"
            print(f"  [{mark}] check #{c['id']} {c['name']}")
            if not c.get("ok"):
                print(f"          details: {json.dumps(c, ensure_ascii=False)}")
        print("-" * 60)
        print(f"  passed {ok_count}/{total} - console_errors: {len(results['console_errors'])}")
        for e in results["console_errors"][:10]:
            print(f"    ERR: {e}")
        print("=" * 60)
        print(f"  report -> {out_json}")

        browser.close()

    # Exit non-zero si echec
    if ok_count < total or results["console_errors"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
