"""
QA Vague 22 - Smoke test global (READ-ONLY)
Vérifie démarrage propre + ouverture des modales nouvelles (vagues 16, 20, 21).
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
OUT = Path(r"D:/alchimia/screenshots/qa-vague22")
OUT.mkdir(parents=True, exist_ok=True)

# Collectors globaux
page_errors = []
console_errors = []
console_warnings = []
scenario_errors = {}  # scénario -> liste d'erreurs survenues pendant


def attach_listeners(page, label="global"):
    """Branche les listeners pageerror + console."""
    def on_pageerror(err):
        msg = f"[{label}] pageerror: {err}"
        page_errors.append(msg)
        scenario_errors.setdefault(label, []).append(msg)

    def on_console(msg):
        if msg.type == "error":
            text = f"[{label}] console.error: {msg.text}"
            console_errors.append(text)
            scenario_errors.setdefault(label, []).append(text)
        elif msg.type == "warning":
            t = msg.text or ""
            if "undefined" in t.lower() or "not a function" in t.lower():
                console_warnings.append(f"[{label}] console.warn: {t}")

    page.on("pageerror", on_pageerror)
    page.on("console", on_console)


async def safe_eval(page, expr, label):
    """Eval JS en isolant les erreurs dans le scénario."""
    try:
        return await page.evaluate(expr)
    except Exception as e:
        msg = f"[{label}] eval-fail: {expr[:80]} -> {e}"
        scenario_errors.setdefault(label, []).append(msg)
        return None


async def close_any_modal(page):
    """Tente fermer une modale ouverte via plusieurs heuristiques."""
    try:
        await page.evaluate("""
            () => {
                // 1) bouton close visible
                const sel = ['.modal-close', '[data-close]', '.close', '.btn-close',
                             '.modal .x', '[aria-label="Fermer"]', '[aria-label="close"]'];
                for (const s of sel) {
                    const el = document.querySelector(s);
                    if (el && el.offsetParent !== null) { el.click(); return s; }
                }
                // 2) ESC
                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', keyCode: 27, which: 27}));
                return 'esc';
            }
        """)
        await page.wait_for_timeout(400)
    except Exception:
        pass


async def try_open(page, fn_call, label, screenshot_name):
    """Tente d'invoquer une fonction modal et capture screenshot."""
    scenario_errors.setdefault(label, [])
    # Detect function existence (via window.X pour éviter ReferenceError)
    fn_name = fn_call.split("(")[0].strip()
    exists = await page.evaluate(
        f"() => typeof window['{fn_name}'] === 'function'"
    )
    if not exists:
        scenario_errors[label].append(f"function-undefined: {fn_call}")
        # Screenshot empty state
        try:
            await page.screenshot(path=str(OUT / f"{screenshot_name}-UNDEFINED.png"))
        except Exception:
            pass
        return False

    # Invoque la fonction sur window pour éviter ReferenceError + capte erreur côté JS
    invoke_js = (
        "() => { try { window."
        + fn_call
        + "; return {ok:true}; } catch(e) { return {ok:false, err: String(e)}; } }"
    )
    res = await safe_eval(page, invoke_js, label)
    if isinstance(res, dict) and res.get("ok") is False:
        scenario_errors[label].append(f"invoke-threw: {res.get('err')}")
    await page.wait_for_timeout(800)
    try:
        await page.screenshot(path=str(OUT / f"{screenshot_name}.png"))
    except Exception as e:
        scenario_errors[label].append(f"screenshot-fail: {e}")
    await close_any_modal(page)
    return True


async def try_burger_click(page, action, label, screenshot_name):
    """Ouvre burger + clique data-action."""
    scenario_errors.setdefault(label, [])
    try:
        # Ouvrir burger
        clicked = await page.evaluate("""
            () => {
                const sel = ['#burger', '.burger', '[data-burger]',
                             '[aria-label*="menu" i]', '.menu-toggle', '#menu-btn'];
                for (const s of sel) {
                    const el = document.querySelector(s);
                    if (el) { el.click(); return s; }
                }
                return null;
            }
        """)
        await page.wait_for_timeout(400)

        # Cliquer item
        item_found = await page.evaluate(f"""
            () => {{
                const el = document.querySelector('[data-action="{action}"]');
                if (!el) return false;
                el.click();
                return true;
            }}
        """)
        await page.wait_for_timeout(700)
        try:
            await page.screenshot(path=str(OUT / f"{screenshot_name}.png"))
        except Exception:
            pass
        if not item_found:
            scenario_errors[label].append(f"burger-item-not-found: data-action={action}")
        await close_any_modal(page)
        # Refermer burger si encore ouvert
        await page.evaluate("""
            () => {
                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
            }
        """)
        await page.wait_for_timeout(200)
        return item_found
    except Exception as e:
        scenario_errors[label].append(f"burger-click-fail({action}): {e}")
        return False


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
        )

        # Pre-skip onboarding via init script
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

        # NAVIGATE
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(OUT / "00-init.png"))

        # Détecter fonctions exposées
        exposed = await page.evaluate("""
            () => {
                const names = ['openStarTree','openUpgradeDetail','openSeasonQuests',
                               'openRelics','openProgression','openLore',
                               'applyProgressiveDisclosure'];
                const out = {};
                for (const n of names) out[n] = (typeof window[n]);
                out.STATE = (typeof window.STATE);
                return out;
            }
        """)

        # Force progression state
        attach_listeners(page, "force-state")  # idem listener => duplicates safe
        forced = await page.evaluate("""
            () => {
                try {
                    if (typeof STATE === 'undefined') return {ok:false, reason:'no STATE'};
                    STATE.lapsRun = 120;
                    STATE.gold = 500000;
                    STATE.stars = 10;
                    // Champs alternatifs courants
                    if ('km' in STATE) STATE.km = 120;
                    if ('totalKm' in STATE) STATE.totalKm = 120;
                    if ('soulStars' in STATE) STATE.soulStars = 10;
                    if ('starPoints' in STATE) STATE.starPoints = 10;
                    return {ok:true, lapsRun:STATE.lapsRun, gold:STATE.gold, stars:STATE.stars};
                } catch(e) { return {ok:false, err: String(e)}; }
            }
        """)

        # Apply progressive disclosure
        await safe_eval(
            page,
            "() => { if (typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure(); }",
            "applyProgressiveDisclosure",
        )
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(OUT / "01-after-force-state.png"))

        # ============ MODALES (vagues 16 / 20 / 21) ============
        modals = [
            ("openStarTree()", "openStarTree", "modal-01-starTree"),
            ("openUpgradeDetail('tapValue')", "openUpgradeDetail", "modal-02-upgradeDetail"),
            ("openSeasonQuests()", "openSeasonQuests", "modal-03-seasonQuests"),
            ("openRelics()", "openRelics", "modal-04-relics"),
            ("openProgression()", "openProgression", "modal-05-progression"),
            ("openLore()", "openLore", "modal-06-lore"),
        ]
        modal_results = {}
        for call, label, shot in modals:
            opened = await try_open(page, call, label, shot)
            modal_results[label] = opened

        # ============ BURGER MENU ============
        burger_actions = ["lore", "season-quests", "relics", "progression", "loadouts"]
        burger_results = {}
        for act in burger_actions:
            ok = await try_burger_click(page, act, f"burger:{act}", f"burger-{act}")
            burger_results[act] = ok

        # Burger meta: a-t-on bien trouvé les 5 items ?
        burger_inventory = await page.evaluate("""
            () => {
                const wanted = ['lore','season-quests','relics','progression','loadouts'];
                const out = {};
                for (const a of wanted) {
                    const els = document.querySelectorAll(`[data-action="${a}"]`);
                    out[a] = els.length;
                }
                return out;
            }
        """)

        # ============ REPORT ============
        report = {
            "exposed_functions": exposed,
            "forced_state": forced,
            "modal_results": modal_results,
            "burger_results": burger_results,
            "burger_inventory": burger_inventory,
            "page_errors_total": len(page_errors),
            "console_errors_total": len(console_errors),
            "console_warnings_undef": len(console_warnings),
            "page_errors": page_errors,
            "console_errors": console_errors,
            "console_warnings": console_warnings,
            "scenario_errors": {k: v for k, v in scenario_errors.items() if v},
        }

        (OUT / "qa1-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Pretty print short
        print("=" * 70)
        print("QA VAGUE 22 - SMOKE REPORT")
        print("=" * 70)
        print(f"Exposed funcs: {exposed}")
        print(f"Forced state : {forced}")
        print(f"PageErrors   : {len(page_errors)}")
        print(f"ConsoleErrors: {len(console_errors)}")
        print(f"Warnings undef: {len(console_warnings)}")
        print("--- Modales ---")
        for k, v in modal_results.items():
            print(f"  {k:25s} -> {'OK' if v else 'UNDEFINED'}")
        print("--- Burger inventory ---")
        for k, v in burger_inventory.items():
            print(f"  data-action={k:18s} : {v} match(es)")
        print("--- Burger click results ---")
        for k, v in burger_results.items():
            print(f"  {k:18s} -> {'CLICKED' if v else 'NOT-FOUND'}")
        print("--- Scenario errors ---")
        for label, errs in scenario_errors.items():
            if errs:
                print(f"  [{label}] {len(errs)} error(s)")
                for e in errs[:5]:
                    print(f"     - {e[:180]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
