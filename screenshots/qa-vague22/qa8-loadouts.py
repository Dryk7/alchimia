"""
QA Vague 22 - qa8 loadouts (READ-ONLY)
Vérifie le système loadouts (vague 20 P6) : save / load / rename / persistence / UI.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
OUT = Path(r"D:/alchimia/screenshots/qa-vague22")
OUT.mkdir(parents=True, exist_ok=True)

page_errors = []
console_errors = []
scenario_errors = {}


def attach_listeners(page, label="global"):
    def on_pageerror(err):
        msg = f"[{label}] pageerror: {err}"
        page_errors.append(msg)
        scenario_errors.setdefault(label, []).append(msg)

    def on_console(msg):
        if msg.type == "error":
            text = f"[{label}] console.error: {msg.text}"
            console_errors.append(text)
            scenario_errors.setdefault(label, []).append(text)

    page.on("pageerror", on_pageerror)
    page.on("console", on_console)


async def safe_eval(page, expr, label):
    try:
        return await page.evaluate(expr)
    except Exception as e:
        msg = f"[{label}] eval-fail: {expr[:120]} -> {e}"
        scenario_errors.setdefault(label, []).append(msg)
        return None


async def main():
    results = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
        )

        # Skip onboarding
        await ctx.add_init_script("""
            try {
                localStorage.setItem('alchimia_onboarding_done', '1');
                localStorage.setItem('alchimia_onboard_done', '1');
                localStorage.setItem('onboarding_done', '1');
                localStorage.setItem('onboardingDone', '1');
                localStorage.setItem('alchimia_tuto_done', '1');
                localStorage.setItem('tuto_done', '1');
                localStorage.setItem('alchimia_intro_seen', '1');
                localStorage.setItem('alchimia_first_run', '0');
            } catch(e) {}
        """)

        page = await ctx.new_page()
        attach_listeners(page, "boot")

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Vérifier fonctions exposées
        exposed = await page.evaluate("""
            () => ({
                saveLoadoutToSlot: typeof window.saveLoadoutToSlot,
                loadLoadoutFromSlot: typeof window.loadLoadoutFromSlot,
                renameLoadout: typeof window.renameLoadout,
                renderLoadouts: typeof window.renderLoadouts,
                openEquip: typeof window.openEquip,
                STATE: typeof window.STATE,
            })
        """)
        results["exposed"] = exposed

        # =====================================================
        # TEST 1 - SAVE preset
        # =====================================================
        attach_listeners(page, "test1-save")
        t1 = await safe_eval(page, """
            () => {
                STATE.equipment = {
                    shoes: { slot:'shoes', rarityId:'rare', level:3, bonus:0.03, baseBonus:0.01 }
                };
                const ret = saveLoadoutToSlot(0);
                return {
                    retval: ret,
                    hasLoadouts: !!STATE.loadouts,
                    slot0_eq: STATE.loadouts && STATE.loadouts[0]
                              ? STATE.loadouts[0].equipment : null,
                    slot0_active: STATE.loadouts && STATE.loadouts[0]
                                  ? STATE.loadouts[0].active : null,
                    slot0_name: STATE.loadouts && STATE.loadouts[0]
                                ? STATE.loadouts[0].name : null,
                };
            }
        """, "test1-save")
        results["test1_save"] = t1

        # =====================================================
        # TEST 2 - LOAD preset
        # =====================================================
        attach_listeners(page, "test2-load")
        t2 = await safe_eval(page, """
            () => {
                STATE.equipment = {};
                const ret = loadLoadoutFromSlot(0);
                return {
                    retval: ret,
                    eq_after: STATE.equipment,
                    shoes_restored: !!(STATE.equipment && STATE.equipment.shoes),
                    shoes_rarity: STATE.equipment && STATE.equipment.shoes
                                  ? STATE.equipment.shoes.rarityId : null,
                    shoes_level: STATE.equipment && STATE.equipment.shoes
                                 ? STATE.equipment.shoes.level : null,
                };
            }
        """, "test2-load")
        results["test2_load"] = t2

        # =====================================================
        # TEST 3 - RENAME
        # =====================================================
        attach_listeners(page, "test3-rename")
        t3 = await safe_eval(page, """
            () => {
                const ret = renameLoadout(0, 'Sprint Build');
                return {
                    retval: ret,
                    slot0_name: STATE.loadouts && STATE.loadouts[0]
                                ? STATE.loadouts[0].name : null,
                };
            }
        """, "test3-rename")
        results["test3_rename"] = t3

        # Force save sur disque pour test persistence
        await safe_eval(page, "() => { if (typeof saveNow === 'function') saveNow(); }", "test3-saveNow")
        await page.wait_for_timeout(400)

        # =====================================================
        # TEST 4 - PERSISTENCE (reload)
        # =====================================================
        attach_listeners(page, "test4-persistence-pre")

        # Capture localStorage avant reload
        ls_dump = await page.evaluate("""
            () => {
                const keys = Object.keys(localStorage);
                const out = {};
                for (const k of keys) {
                    if (k.toLowerCase().includes('loadout') || k.includes('alchimia') || k.includes('save')) {
                        out[k] = (localStorage.getItem(k) || '').slice(0, 200);
                    }
                }
                return { keys_count: keys.length, sample: out };
            }
        """)
        results["ls_keys_before_reload"] = ls_dump

        # Reload
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        attach_listeners(page, "test4-persistence-post")

        t4 = await safe_eval(page, """
            () => {
                const ld = STATE.loadouts && STATE.loadouts[0];
                return {
                    hasLoadouts: !!STATE.loadouts,
                    loadouts_count: STATE.loadouts ? STATE.loadouts.length : 0,
                    slot0_name: ld ? ld.name : null,
                    slot0_eq: ld ? ld.equipment : null,
                    slot0_shoes_rarity: (ld && ld.equipment && ld.equipment.shoes)
                                        ? ld.equipment.shoes.rarityId : null,
                    slot0_active: ld ? ld.active : null,
                };
            }
        """, "test4-persistence-post")
        results["test4_persistence"] = t4

        # =====================================================
        # TEST 5 - UI dans equip-modal
        # =====================================================
        attach_listeners(page, "test5-ui")
        await safe_eval(page, "() => { if (typeof openEquip === 'function') openEquip(); }", "test5-ui")
        await page.wait_for_timeout(800)

        ui_check = await page.evaluate("""
            () => {
                const modal = document.getElementById('equip-modal');
                const isOpen = modal && modal.classList.contains('show');
                const section = document.getElementById('loadouts-section');
                const sectionVisible = section && section.offsetParent !== null;
                const sectionText = section ? (section.textContent || '').slice(0, 200) : '';
                const inputs = section ? section.querySelectorAll('input[type="text"]').length : 0;
                const saveBtns = section ? section.querySelectorAll('button').length : 0;
                // Check si autres parties d'equip-modal pas cassées
                const body = document.getElementById('equip-body');
                const bodyHasContent = body && body.children.length > 0;
                return {
                    modal_open: isOpen,
                    section_exists: !!section,
                    section_visible: !!sectionVisible,
                    section_text_snippet: sectionText,
                    inputs_count: inputs,
                    buttons_count: saveBtns,
                    equip_body_present: bodyHasContent,
                    equip_body_children: body ? body.children.length : 0,
                };
            }
        """)
        results["test5_ui"] = ui_check
        await page.screenshot(path=str(OUT / "qa8-loadouts-equip-modal.png"))

        # Fermer la modale
        await page.evaluate("""
            () => {
                document.getElementById('equip-modal')?.classList.remove('show');
            }
        """)
        await page.wait_for_timeout(200)

        # =====================================================
        # TEST 6 - SAVE EMPTY (allowed ou refused ?)
        # =====================================================
        attach_listeners(page, "test6-save-empty")
        t6 = await safe_eval(page, """
            () => {
                STATE.equipment = {};
                const ret = saveLoadoutToSlot(1);
                return {
                    retval: ret,
                    slot1_eq: STATE.loadouts && STATE.loadouts[1]
                              ? STATE.loadouts[1].equipment : null,
                    slot1_eq_keys: STATE.loadouts && STATE.loadouts[1] && STATE.loadouts[1].equipment
                                   ? Object.keys(STATE.loadouts[1].equipment) : null,
                    slot1_active: STATE.loadouts && STATE.loadouts[1]
                                  ? STATE.loadouts[1].active : null,
                    slot0_active_after: STATE.loadouts && STATE.loadouts[0]
                                        ? STATE.loadouts[0].active : null,
                };
            }
        """, "test6-save-empty")
        results["test6_save_empty"] = t6

        # =====================================================
        # TEST BONUS - Load slot empty
        # =====================================================
        attach_listeners(page, "test6b-load-empty")
        t6b = await safe_eval(page, """
            () => {
                const ret = loadLoadoutFromSlot(2);
                return { retval: ret };
            }
        """, "test6b-load-empty")
        results["test6b_load_empty"] = t6b

        # =====================================================
        # TEST BONUS - rename invalid (out of range)
        # =====================================================
        attach_listeners(page, "test7-invalid")
        t7 = await safe_eval(page, """
            () => ({
                rename_neg: renameLoadout(-1, 'X'),
                rename_3: renameLoadout(3, 'X'),
                save_neg: saveLoadoutToSlot(-1),
                save_3: saveLoadoutToSlot(3),
                load_neg: loadLoadoutFromSlot(-1),
                load_3: loadLoadoutFromSlot(3),
            })
        """, "test7-invalid")
        results["test7_invalid"] = t7

        # =====================================================
        # CONSOLE ERRORS
        # =====================================================
        results["page_errors"] = page_errors
        results["console_errors"] = console_errors
        results["scenario_errors"] = scenario_errors

        # Save report
        report_path = OUT / "qa8-loadouts-report.json"
        report_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print(json.dumps(results, indent=2, default=str))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
