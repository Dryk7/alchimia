"""
Verify v20 - Loadouts : 3 presets switchables d'equipement.

Steps:
1. Skip onboarding
2. Eval STATE.equipment = { shoes:{slot:'shoes', rarityId:'rare', level:3, baseBonus:0.01, bonus:0.03} };
3. Eval saveLoadoutToSlot(0) -> verifier STATE.loadouts[0].equipment.shoes existe
4. Eval STATE.equipment = {};
5. Eval loadLoadoutFromSlot(0) -> verifier STATE.equipment.shoes existe
6. 0 erreurs console
"""

import asyncio
import sys
from playwright.async_api import async_playwright

URL = "file:///D:/alchimia/index.html"

async def main():
    errors = []
    findings = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 420, "height": 900})
        page = await ctx.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        await page.goto(URL)
        await page.wait_for_timeout(800)

        # Skip onboarding
        await page.evaluate("""() => {
          try { localStorage.setItem('foulee.onboardingV1', '1'); } catch(e){}
          try { localStorage.setItem('foulee.activeTutoV1', JSON.stringify({done:true})); } catch(e){}
          try { if(typeof STATE === 'object'){ STATE.onboarded = true; } } catch(e){}
        }""")
        await page.reload()
        await page.wait_for_timeout(1200)

        # CHECK 1 : STATE.loadouts existe et a 3 entrees
        init_check = await page.evaluate("""() => {
          return {
            hasLoadouts: Array.isArray(STATE.loadouts),
            count: STATE.loadouts ? STATE.loadouts.length : 0,
            names: STATE.loadouts ? STATE.loadouts.map(l => l.name) : [],
            hasSaveFn: typeof saveLoadoutToSlot === 'function',
            hasLoadFn: typeof loadLoadoutFromSlot === 'function',
            hasRenameFn: typeof renameLoadout === 'function'
          };
        }""")
        findings.append(f"STATE.loadouts existe : {init_check['hasLoadouts']} (count={init_check['count']})")
        findings.append(f"  noms : {init_check['names']}")
        findings.append(f"  saveLoadoutToSlot : {init_check['hasSaveFn']}")
        findings.append(f"  loadLoadoutFromSlot : {init_check['hasLoadFn']}")
        findings.append(f"  renameLoadout : {init_check['hasRenameFn']}")

        if not init_check['hasLoadouts']:
            errors.append("STATE.loadouts n'existe pas ou n'est pas un Array")
        if init_check['count'] != 3:
            errors.append(f"STATE.loadouts.length != 3 (got {init_check['count']})")
        if not init_check['hasSaveFn']:
            errors.append("saveLoadoutToSlot n'est pas une fonction")
        if not init_check['hasLoadFn']:
            errors.append("loadLoadoutFromSlot n'est pas une fonction")
        if not init_check['hasRenameFn']:
            errors.append("renameLoadout n'est pas une fonction")

        # Setup equipment + save in slot 0
        save_check = await page.evaluate("""() => {
          STATE.equipment = { shoes:{slot:'shoes', rarityId:'rare', level:3, baseBonus:0.01, bonus:0.03} };
          const ok = saveLoadoutToSlot(0);
          return {
            ok: ok,
            slot0HasShoes: !!(STATE.loadouts[0] && STATE.loadouts[0].equipment && STATE.loadouts[0].equipment.shoes),
            slot0Active: STATE.loadouts[0] ? STATE.loadouts[0].active : false,
            slot0ShoesLevel: STATE.loadouts[0]?.equipment?.shoes?.level,
            slot0ShoesRarity: STATE.loadouts[0]?.equipment?.shoes?.rarityId
          };
        }""")
        findings.append(f"saveLoadoutToSlot(0) -> ok={save_check['ok']}")
        findings.append(f"  slot[0].equipment.shoes existe : {save_check['slot0HasShoes']}")
        findings.append(f"  slot[0].active : {save_check['slot0Active']}")
        findings.append(f"  slot[0].shoes.level : {save_check['slot0ShoesLevel']}")
        findings.append(f"  slot[0].shoes.rarityId : {save_check['slot0ShoesRarity']}")

        if not save_check['ok']:
            errors.append("saveLoadoutToSlot(0) retourne false")
        if not save_check['slot0HasShoes']:
            errors.append("STATE.loadouts[0].equipment.shoes n'existe pas apres save")
        if save_check['slot0ShoesLevel'] != 3:
            errors.append(f"slot0 shoes.level != 3 (got {save_check['slot0ShoesLevel']})")
        if not save_check['slot0Active']:
            errors.append("slot[0].active != true apres save")

        # Clear + load
        load_check = await page.evaluate("""() => {
          STATE.equipment = {};
          const ok = loadLoadoutFromSlot(0);
          return {
            ok: ok,
            hasShoes: !!(STATE.equipment && STATE.equipment.shoes),
            shoesLevel: STATE.equipment?.shoes?.level,
            shoesRarity: STATE.equipment?.shoes?.rarityId,
            shoesBonus: STATE.equipment?.shoes?.bonus
          };
        }""")
        findings.append(f"loadLoadoutFromSlot(0) -> ok={load_check['ok']}")
        findings.append(f"  STATE.equipment.shoes existe : {load_check['hasShoes']}")
        findings.append(f"  shoes.level : {load_check['shoesLevel']}")
        findings.append(f"  shoes.rarityId : {load_check['shoesRarity']}")
        findings.append(f"  shoes.bonus : {load_check['shoesBonus']}")

        if not load_check['ok']:
            errors.append("loadLoadoutFromSlot(0) retourne false")
        if not load_check['hasShoes']:
            errors.append("STATE.equipment.shoes n'existe pas apres load")
        if load_check['shoesLevel'] != 3:
            errors.append(f"loaded shoes.level != 3 (got {load_check['shoesLevel']})")
        if load_check['shoesRarity'] != 'rare':
            errors.append(f"loaded shoes.rarityId != rare (got {load_check['shoesRarity']})")

        # Rename test
        rename_check = await page.evaluate("""() => {
          const ok = renameLoadout(1, 'Sprint');
          return {
            ok: ok,
            name: STATE.loadouts[1]?.name
          };
        }""")
        findings.append(f"renameLoadout(1, 'Sprint') -> ok={rename_check['ok']}, name='{rename_check['name']}'")
        if rename_check['name'] != 'Sprint':
            errors.append(f"renameLoadout: name != 'Sprint' (got '{rename_check['name']}')")

        # Console errors
        if console_errors:
            for e in console_errors[:5]:
                errors.append(f"Console error : {e}")

        await browser.close()

    print("=== FINDINGS ===")
    for f in findings:
        print(f)
    print()
    print("=== ERRORS ===")
    if errors:
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("  Aucune. OK.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
