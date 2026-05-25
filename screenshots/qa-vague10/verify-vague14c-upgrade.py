"""
VAGUE 14c — Verify UPGRADE ITEM BY GOUTTES.
Headless 540x960. Skip onboarding. Check:
  T0   : inject STATE.gold = 100000 + STATE.equipment.shoes uncommon NIV1
  T1   : upgradeItem('shoes') → level === 2 && gold === 99500
  T2   : 4x upgradeItem → level === 5 (cap)
  T3   : canUpgradeItem(...) === false (cap)
  T4   : ascendItem('shoes') → rarityId === 'rare' && level === 1
  console_errors == 0
  screenshot vague14c-upgrade-ui.png (modale equip si possible)
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"

def main():
    report = {
        "http": None,
        "T0_initial": None,
        "T1_after_1_upgrade": None,
        "T2_after_5_upgrades": None,
        "T3_can_upgrade_at_cap": None,
        "T4_after_ascend": None,
        "console_errors": [],
        "console_warnings": [],
        "pageerrors": [],
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
        page.wait_for_timeout(5500)

        # Force close overlays
        page.evaluate("""() => {
            const ids = ['intro', 'story-intro', 'opening-credits', 'opening-overlay', 'giga-tuto'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if(el){ el.style.display = 'none'; el.classList.add('gone'); }
            });
        }""")
        page.wait_for_timeout(500)

        # === T0 : seed state
        t0 = page.evaluate("""() => {
            if(!window.STATE) return {error: 'no STATE'};
            window.STATE.gold = 100000;
            window.STATE.equipment = window.STATE.equipment || {};
            // Item uncommon NIV1 sur slot 'shoes' — bonus aligné rollItem (baseBonus 0.02 * mul 2 * lvl 1 = 0.04)
            window.STATE.equipment.shoes = {
                typeId: 'shoes',
                rarityId: 'uncommon',
                level: 1,
                bonus: 0.04
            };
            return {
                gold: window.STATE.gold,
                shoes: JSON.parse(JSON.stringify(window.STATE.equipment.shoes)),
                fnsOk: {
                    upgradeItem: typeof window.upgradeItem === 'function',
                    ascendItem: typeof window.ascendItem === 'function',
                    getItemUpgradeCost: typeof window.getItemUpgradeCost === 'function',
                    canUpgradeItem: typeof window.canUpgradeItem === 'function',
                    canAscendItem: typeof window.canAscendItem === 'function',
                },
                initialCost: window.getItemUpgradeCost(window.STATE.equipment.shoes)
            };
        }""")
        report["T0_initial"] = t0
        report["checks"]["T0_fns_present"] = all((t0.get("fnsOk") or {}).values())
        report["checks"]["T0_initial_cost_500"] = (t0.get("initialCost") == 500)

        # === T1 : 1× upgrade
        t1 = page.evaluate("""() => {
            const ok = window.upgradeItem('shoes');
            return {
                upgrade_returned: ok,
                gold: window.STATE.gold,
                level: window.STATE.equipment.shoes.level,
                rarityId: window.STATE.equipment.shoes.rarityId,
                bonus: window.STATE.equipment.shoes.bonus
            };
        }""")
        report["T1_after_1_upgrade"] = t1
        report["checks"]["T1_returned_true"] = (t1.get("upgrade_returned") is True)
        report["checks"]["T1_level_eq_2"] = (t1.get("level") == 2)
        report["checks"]["T1_gold_eq_99500"] = (t1.get("gold") == 99500)
        # bonus = 0.02 * 2 * 2 = 0.08
        report["checks"]["T1_bonus_recomputed"] = (t1.get("bonus") is not None and abs(t1["bonus"] - 0.08) < 0.0001)

        # === T2 : 4× upgrade pour atteindre cap
        t2 = page.evaluate("""() => {
            const results = [];
            for(let i=0;i<4;i++){
                const ok = window.upgradeItem('shoes');
                results.push({
                    i, ok,
                    level: window.STATE.equipment.shoes.level,
                    gold: window.STATE.gold
                });
            }
            return {
                steps: results,
                finalLevel: window.STATE.equipment.shoes.level,
                finalGold: window.STATE.gold,
                finalBonus: window.STATE.equipment.shoes.bonus
            };
        }""")
        report["T2_after_5_upgrades"] = t2
        # 1+4 = 5 upgrades — cap atteint
        report["checks"]["T2_level_eq_5"] = (t2.get("finalLevel") == 5)
        # Coûts cumulés depuis NIV1 : 500 (1→2) + 1000 (2→3) + 1500 (3→4) + 2000 (4→5) = 5000 ; 5e tentative à NIV5 = 0 (refusée)
        # Gold après T1 : 99500 ; après 3 upgrades 2→5 = -4500 → 95000 ; 5e tentative à NIV5 doit retourner false sans dépense
        # Donc finalGold attendu == 95000
        report["checks"]["T2_gold_eq_95000"] = (t2.get("finalGold") == 95000)
        # bonus at lvl5 uncommon: 0.02 * 2 * 5 = 0.20
        report["checks"]["T2_bonus_recomputed"] = (t2.get("finalBonus") is not None and abs(t2["finalBonus"] - 0.20) < 0.0001)

        # === T3 : canUpgrade au cap doit être false
        t3 = page.evaluate("""() => ({
            canUpgrade: window.canUpgradeItem(window.STATE.equipment.shoes),
            canAscend: window.canAscendItem(window.STATE.equipment.shoes),
            ascendCost: window.getItemAscendCost(window.STATE.equipment.shoes)
        })""")
        report["T3_can_upgrade_at_cap"] = t3
        report["checks"]["T3_canUpgrade_false_at_cap"] = (t3.get("canUpgrade") is False)
        report["checks"]["T3_canAscend_true"] = (t3.get("canAscend") is True)
        # ascendCost = 3 * (500 * 5) = 7500
        report["checks"]["T3_ascendCost_eq_7500"] = (t3.get("ascendCost") == 7500)

        # === T4 : ascend → rare niv1
        t4 = page.evaluate("""() => {
            const ok = window.ascendItem('shoes');
            return {
                ascend_returned: ok,
                gold: window.STATE.gold,
                level: window.STATE.equipment.shoes.level,
                rarityId: window.STATE.equipment.shoes.rarityId,
                bonus: window.STATE.equipment.shoes.bonus
            };
        }""")
        report["T4_after_ascend"] = t4
        report["checks"]["T4_returned_true"] = (t4.get("ascend_returned") is True)
        report["checks"]["T4_rarity_rare"] = (t4.get("rarityId") == "rare")
        report["checks"]["T4_level_eq_1"] = (t4.get("level") == 1)
        # Gold après T2 = 95000, -7500 = 87500
        report["checks"]["T4_gold_eq_87500"] = (t4.get("gold") == 87500)
        # bonus rare niv1 : 0.02 * 4 * 1 = 0.08
        report["checks"]["T4_bonus_recomputed"] = (t4.get("bonus") is not None and abs(t4["bonus"] - 0.08) < 0.0001)

        # === Screenshot modale équipement
        try:
            page.evaluate("""() => {
                if(typeof openEquip === 'function') openEquip();
                else {
                    const m = document.getElementById('equip-modal');
                    if(m){ if(typeof renderEquipment === 'function') renderEquipment(); m.classList.add('show'); }
                }
            }""")
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / "vague14c-upgrade-ui.png"))
        except Exception as e:
            report["screenshot_err"] = str(e)[:200]

        # === Verdict
        report["checks"]["console_clean"] = (len(report["console_errors"]) == 0 and len(report["pageerrors"]) == 0)
        all_passed = all(report["checks"].values())
        report["verdict"] = "PASS" if all_passed else "FAIL"

        browser.close()

    report_path = OUT / "vague14c-upgrade-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
