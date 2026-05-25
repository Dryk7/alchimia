"""
QA Vague 11 - Verification du systeme d'inventaire enrichi.
Verifie:
  - 8 slots d'equipement (au lieu de 5)
  - Items rollItem() avec levels varies selon rarete
  - Set bonus (legendaire 3+, epic+ 5+)
"""
import json, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"


def main():
    console_errors = []
    findings = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()
        page.on("console", lambda msg: (console_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None))
        page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"))

        print("== Chargement page ==")
        page.add_init_script("""
            try {
                localStorage.setItem('foulee.storySeen', '1');
                localStorage.setItem('foulee.onboardingSeen', '1');
                localStorage.setItem('foulee.lastSeenStage', '999');
            } catch(e){}
        """)
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_function("window.STATE && typeof window.rollItem === 'function'", timeout=10000)

        # Force STATE pour ouvrir l'equipement
        page.evaluate("""() => {
            window.STATE.lapsRun = 30;
            window.STATE.totalTaps = 500;
            window.STATE.equipment = {};
        }""")

        # ====================================================================
        # TEST 1 : Compter les slots d'equipement
        # ====================================================================
        print("\n== TEST 1: Nombre de slots ==")
        slot_count = page.evaluate("() => (typeof ITEM_TYPES !== 'undefined' ? ITEM_TYPES.length : -1)")
        slot_ids = page.evaluate("() => (typeof ITEM_TYPES !== 'undefined' ? ITEM_TYPES.map(t => t.id) : [])")
        findings['slot_count'] = slot_count
        findings['slot_ids'] = slot_ids
        print(f"  ITEM_TYPES.length = {slot_count}")
        print(f"  ITEM_TYPES ids = {slot_ids}")
        slots_ok = (slot_count == 8 and 'cap' in slot_ids and 'gloves' in slot_ids and 'medal' in slot_ids)
        print(f"  -> slots=8 + nouveaux slots presents: {slots_ok}")

        # ====================================================================
        # TEST 2 : Drop 50 items, verifier levels varies selon rarete
        # ====================================================================
        print("\n== TEST 2: Levels varies via rollItem() ==")
        items_data = page.evaluate("""() => {
            const items = [];
            for(let i = 0; i < 50; i++){
                items.push(rollItem());
            }
            return items;
        }""")
        levels_per_rarity = {}
        for it in items_data:
            r = it['rarityId']
            levels_per_rarity.setdefault(r, []).append(it['level'])
        print(f"  50 items roll, distribution par rarete:")
        for r, levels in levels_per_rarity.items():
            unique = sorted(set(levels))
            print(f"    {r:12s} -> N={len(levels):2d}, levels uniques={unique}")
        # Verifier qu'on a au moins 2 niveaux differents global
        all_levels = [it['level'] for it in items_data]
        unique_levels_count = len(set(all_levels))
        findings['unique_levels'] = unique_levels_count
        findings['levels_distribution'] = {r: sorted(set(l)) for r, l in levels_per_rarity.items()}
        levels_ok = unique_levels_count >= 2
        print(f"  unique_levels_count = {unique_levels_count} (need >=2)")
        print(f"  -> levels varies: {levels_ok}")

        # ====================================================================
        # TEST 3 : Set bonus avec 3 items legendary
        # ====================================================================
        print("\n== TEST 3: Set bonus 3 legendaires ==")
        set_test = page.evaluate("""() => {
            // Reset
            window.STATE.equipment = {};
            // Equipe 3 items legendaires (jersey, cap = goldMul ; shoes = speed)
            window.STATE.equipment.shoes = { typeId:'shoes', rarityId:'legendary', level:3, bonus:0.1 };
            window.STATE.equipment.jersey = { typeId:'jersey', rarityId:'legendary', level:3, bonus:0.1 };
            window.STATE.equipment.cap = { typeId:'cap', rarityId:'legendary', level:3, bonus:0.1 };
            // Bonus goldMul = somme cap + jersey * 1.15 (set bonus 3+ legendaires)
            const goldBonus = equipBonus('goldMul');
            const speedBonus = equipBonus('speed');
            // Sans set bonus, gold serait 0.2 ; avec set 0.2 * 1.15 = 0.23
            return { goldBonus, speedBonus, expectedGoldWithSet: 0.2 * 1.15 };
        }""")
        print(f"  3 legendaires equipes : goldBonus={set_test['goldBonus']:.4f}, expected ~{set_test['expectedGoldWithSet']:.4f}")
        # Tolerance pour le floating-point
        set_bonus_ok = abs(set_test['goldBonus'] - set_test['expectedGoldWithSet']) < 0.001
        findings['set_bonus_goldMul'] = set_test['goldBonus']
        findings['set_bonus_expected'] = set_test['expectedGoldWithSet']
        print(f"  -> set bonus +15% actif: {set_bonus_ok}")

        # ====================================================================
        # TEST 4 : Set bonus combine 5 epic+legendary
        # ====================================================================
        print("\n== TEST 4: Set bonus 5 epic+ ==")
        set5_test = page.evaluate("""() => {
            window.STATE.equipment = {};
            window.STATE.equipment.shoes = { typeId:'shoes', rarityId:'legendary', level:3, bonus:0.1 };
            window.STATE.equipment.jersey = { typeId:'jersey', rarityId:'legendary', level:3, bonus:0.1 };
            window.STATE.equipment.cap = { typeId:'cap', rarityId:'legendary', level:3, bonus:0.1 };
            window.STATE.equipment.watch = { typeId:'watch', rarityId:'epic', level:2, bonus:0.05 };
            window.STATE.equipment.medal = { typeId:'medal', rarityId:'epic', level:2, bonus:0.05 };
            // goldMul : jersey 0.1 + cap 0.1 = 0.2 ; set 3leg = *1.15 ; set 5+ = *1.10
            // Final = 0.2 * 1.15 * 1.10 = 0.253
            const goldBonus = equipBonus('goldMul');
            const expected = 0.2 * 1.15 * 1.10;
            return { goldBonus, expected };
        }""")
        print(f"  5 epic+legendary equipes : goldBonus={set5_test['goldBonus']:.4f}, expected ~{set5_test['expectedGoldWithSet'] if 'expectedGoldWithSet' in set5_test else set5_test['expected']:.4f}")
        set5_ok = abs(set5_test['goldBonus'] - set5_test['expected']) < 0.001
        findings['set5_bonus_actual'] = set5_test['goldBonus']
        findings['set5_bonus_expected'] = set5_test['expected']
        print(f"  -> set bonus combine actif: {set5_ok}")

        # ====================================================================
        # TEST 5 : Ouvrir l'equipement modal + screenshot
        # ====================================================================
        print("\n== TEST 5: Screenshot equipement modal ==")
        # Reset puis equiper 3 legendaires pour visualiser
        page.evaluate("""() => {
            window.STATE.equipment = {};
            window.STATE.equipment.shoes = { typeId:'shoes', rarityId:'legendary', level:3, bonus:0.1 };
            window.STATE.equipment.jersey = { typeId:'jersey', rarityId:'legendary', level:3, bonus:0.12 };
            window.STATE.equipment.cap = { typeId:'cap', rarityId:'legendary', level:3, bonus:0.08 };
            window.STATE.equipment.gloves = { typeId:'gloves', rarityId:'epic', level:2, bonus:0.04 };
            window.STATE.equipment.medal = { typeId:'medal', rarityId:'epic', level:2, bonus:0.08 };
            window.STATE.equipment.headband = { typeId:'headband', rarityId:'rare', level:2, bonus:0.04 };
            window.STATE.equipment.watch = { typeId:'watch', rarityId:'rare', level:2, bonus:0.06 };
            window.STATE.equipment.wristband = { typeId:'wristband', rarityId:'uncommon', level:1, bonus:0.04 };
            if(typeof openEquip === 'function') openEquip();
        }""")
        time.sleep(0.5)
        screenshot_path = OUT / "VAGUE11-INVENTORY.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
        print(f"  screenshot -> {screenshot_path}")

        # ====================================================================
        # Console errors
        # ====================================================================
        print(f"\n== Erreurs console: {len(console_errors)} ==")
        for e in console_errors[:10]:
            print(f"  {e}")

        # ====================================================================
        # RESUME
        # ====================================================================
        print("\n== RESUME FINDINGS ==")
        print(f"  slot_count = {findings.get('slot_count')} (attendu 8)")
        print(f"  slot_ids = {findings.get('slot_ids')}")
        print(f"  unique_levels = {findings.get('unique_levels')} (attendu >=2)")
        print(f"  set_bonus_goldMul (3leg) = {findings.get('set_bonus_goldMul'):.4f} (attendu ~{findings.get('set_bonus_expected'):.4f})")
        print(f"  set5_bonus (5epic+) = {findings.get('set5_bonus_actual'):.4f} (attendu ~{findings.get('set5_bonus_expected'):.4f})")

        browser.close()

        all_ok = slots_ok and levels_ok and set_bonus_ok and set5_ok and len(console_errors) == 0
        if all_ok:
            print("\n>>> TEST PASSE <<<")
            sys.exit(0)
        else:
            print(f"\n>>> TEST ECHEC (slots={slots_ok}, levels={levels_ok}, set3={set_bonus_ok}, set5={set5_ok}, errors={len(console_errors)}) <<<")
            sys.exit(1)


if __name__ == "__main__":
    main()
