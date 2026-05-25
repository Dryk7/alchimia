"""
QA Vague 22 - Agent 10 - UX upgrades enrichie (READ-ONLY)
Vérifie : preview effet, modale long-tap, hint pédagogique, codex enrichi,
niveau cap, unaffordable greyed.
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
console_warnings = []
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
        elif msg.type == "warning":
            t = msg.text or ""
            if "undefined" in t.lower() or "not a function" in t.lower():
                console_warnings.append(f"[{label}] console.warn: {t}")

    page.on("pageerror", on_pageerror)
    page.on("console", on_console)


async def safe_eval(page, expr, label):
    try:
        return await page.evaluate(expr)
    except Exception as e:
        msg = f"[{label}] eval-fail: {expr[:80]} -> {e}"
        scenario_errors.setdefault(label, []).append(msg)
        return None


async def close_any_modal(page):
    try:
        await page.evaluate("""
            () => {
                const sel = ['.modal-close', '[data-close]', '[data-close-modal]', '.close', '.btn-close',
                             '.modal .x', '[aria-label="Fermer"]'];
                for (const s of sel) {
                    const el = document.querySelector(s);
                    if (el && el.offsetParent !== null) { el.click(); }
                }
                document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
            }
        """)
        await page.wait_for_timeout(300)
    except Exception:
        pass


async def main():
    results = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
        )
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
        await page.screenshot(path=str(OUT / "qa10-00-init.png"))

        # ============ FORCER STATE (vagues 18-19) ============
        # lapsRun=30 (toutes upgrades early débloquées) ; gold=100k ; upgradeTapValue=5
        attach_listeners(page, "force-state")
        forced = await page.evaluate("""
            () => {
                try {
                    if (typeof STATE === 'undefined') return {ok:false, reason:'no STATE'};
                    STATE.lapsRun = 30;
                    STATE.gold = 100000;
                    STATE.upgradeTapValue = 5;
                    if ('km' in STATE) STATE.km = 30;
                    if ('totalKm' in STATE) STATE.totalKm = 30;
                    return {ok:true, lapsRun:STATE.lapsRun, gold:STATE.gold,
                            upgTV:STATE.upgradeTapValue};
                } catch(e) { return {ok:false, err:String(e)}; }
            }
        """)
        results["forced_state"] = forced

        # Apply progressive disclosure pour révéler les upgrades
        await safe_eval(
            page,
            "() => { if (typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure(); }",
            "applyProgressiveDisclosure",
        )
        await page.wait_for_timeout(500)

        # Bascule vers onglet upgrades si présent
        await safe_eval(
            page,
            """() => {
                const btn = document.querySelector('.tab-btn[data-tab="upgrades"]');
                if (btn) btn.click();
            }""",
            "switch-tab-upgrades",
        )
        await page.wait_for_timeout(400)

        # ============ TEST 1 — Preview effet sur bouton ============
        attach_listeners(page, "test1-preview")
        await safe_eval(
            page,
            "() => { if(typeof updateUpgradesUI === 'function') updateUpgradesUI(); }",
            "test1-preview",
        )
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(OUT / "qa10-01-preview-effet.png"))

        # Inspecter #upg-tap-effect
        preview = await page.evaluate("""
            () => {
                const el = document.getElementById('upg-tap-effect');
                if (!el) return {found:false};
                const txt = el.textContent || '';
                const html = el.innerHTML || '';
                // Vérifie l'effet courant=8.5 (1+5*1.5=8.5) et la flèche
                return {
                    found:true,
                    text:txt,
                    html:html.slice(0, 400),
                    has85: txt.includes('8.5') || html.includes('8.5'),
                    hasArrow: txt.includes('→') || html.includes('→') || html.includes('eff-arrow'),
                    hasCur: html.includes('eff-cur'),
                    hasNext: html.includes('eff-next'),
                    isMax: html.includes('eff-max')
                };
            }
        """)
        results["test1_preview"] = preview

        # ============ TEST 2 — Modale détail long-tap ============
        attach_listeners(page, "test2-modale")
        await safe_eval(
            page,
            "() => { if (typeof showUpgradeDetail === 'function') showUpgradeDetail('tapValue'); }",
            "test2-modale",
        )
        await page.wait_for_timeout(700)
        await page.screenshot(path=str(OUT / "qa10-02-modale-long-tap.png"))

        modale = await page.evaluate("""
            () => {
                const m = document.getElementById('upgrade-detail-modal');
                if (!m) return {found:false};
                const isOpen = m.classList.contains('show');
                const tbl = document.getElementById('upg-detail-table');
                const rows = tbl ? tbl.querySelectorAll('div').length : 0;
                const title = (document.getElementById('upg-detail-title') || {}).textContent || '';
                const buyBtn = document.getElementById('upg-detail-buy');
                const buyTxt = buyBtn ? buyBtn.textContent : '';
                return {
                    found:true,
                    isOpen,
                    rows,
                    title,
                    buyTxt: buyTxt.slice(0, 80),
                    hasTable: !!tbl,
                    tableHtmlSample: tbl ? tbl.innerHTML.slice(0, 200) : ''
                };
            }
        """)
        results["test2_modale"] = modale
        await close_any_modal(page)

        # ============ TEST 3 — Hint pédagogique 1ère unlock ============
        attach_listeners(page, "test3-hint")
        # Reset hints & force lapsRun=2 (avant unlock lapBonus) puis bump à 3
        hint_setup = await page.evaluate("""
            () => {
                try {
                    STATE._upgFirstHints = {};
                    STATE.lapsRun = 2;
                    if (typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
                    return {ok:true, step:1, lapsRun:STATE.lapsRun};
                } catch(e) { return {ok:false, err:String(e)}; }
            }
        """)
        await page.wait_for_timeout(300)

        # Bump à lapsRun=3 et reapply disclosure (déclenche unlock toast + hint)
        await page.evaluate("""
            () => {
                try {
                    STATE.lapsRun = 3;
                    if (typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
                } catch(e) {}
            }
        """)
        await page.wait_for_timeout(3700)  # 3000 délai hint + marge
        await page.screenshot(path=str(OUT / "qa10-03-hint-pedagogique.png"))

        hint = await page.evaluate("""
            () => {
                const h = document.querySelector('.upg-first-hint');
                const toast = document.querySelector('.unlock-toast');
                const pointed = document.querySelector('.hint-pointed');
                const fnHint = (typeof getUpgradeFirstHint === 'function');
                return {
                    hintFound: !!h,
                    hintTxt: h ? (h.textContent || '').slice(0, 200) : null,
                    hintVisible: h ? (h.offsetParent !== null) : false,
                    toastFound: !!toast,
                    pointedFound: !!pointed,
                    getUpgradeFirstHintExists: fnHint,
                    upgFirstHintsState: (STATE && STATE._upgFirstHints) ? Object.keys(STATE._upgFirstHints) : []
                };
            }
        """)
        results["test3_hint"] = {
            "setup": hint_setup,
            "result": hint,
        }

        # ============ TEST 4 — Codex Guide enrichi ============
        attach_listeners(page, "test4-codex")
        # Ouvrir le guide via #help-toggle
        codex_open = await page.evaluate("""
            () => {
                try {
                    const help = document.getElementById('help-toggle');
                    if (help) { help.click(); return 'help-click'; }
                    return 'no-help';
                } catch(e) { return 'err:'+String(e); }
            }
        """)
        await page.wait_for_timeout(700)

        # Cliquer sur l'onglet upgrades du guide
        await page.evaluate("""
            () => {
                const tab = document.querySelector('#guide-tabs .g-tab[data-section="upgrades"]');
                if (tab) tab.click();
            }
        """)
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "qa10-04-codex-guide.png"))

        codex = await page.evaluate("""
            () => {
                const modal = document.getElementById('guide-modal');
                const modalOpen = modal ? modal.classList.contains('show') : false;
                const content = document.querySelector('.guide-content');
                const txt = content ? content.textContent : '';
                const upgSec = document.querySelector('.guide-content .g-sec[data-section="upgrades"]');
                const upgTxt = upgSec ? upgSec.textContent : '';
                return {
                    modalOpen,
                    hasStrategieLeveling: txt.includes('Stratégie de leveling') || upgTxt.includes('Stratégie de leveling'),
                    hasEarly: upgTxt.includes('Early'),
                    hasMid: upgTxt.includes('Mid'),
                    hasLate: upgTxt.includes('Late'),
                    hasSoftCap: upgTxt.includes('Soft cap') || upgTxt.includes('soft cap'),
                    hasFactorLvl: upgTxt.includes('factor^lvl') || upgTxt.includes('factor'),
                    sectionPresent: !!upgSec,
                    sectionTxtLen: upgTxt.length
                };
            }
        """)
        results["test4_codex"] = codex
        await close_any_modal(page)
        await page.wait_for_timeout(300)

        # ============ TEST 5 — Niveau cap "Niv X / Y" affiché ============
        attach_listeners(page, "test5-cap")
        await safe_eval(
            page,
            "() => { if(typeof updateUpgradesUI === 'function') updateUpgradesUI(); }",
            "test5-cap",
        )
        await page.wait_for_timeout(400)
        cap = await page.evaluate("""
            () => {
                const lvls = {};
                ['tap','crit','lap','auto','endurance','speed','eagle','cruise'].forEach(sfx => {
                    const el = document.getElementById('upg-'+sfx+'-lvl');
                    if (el) lvls[sfx] = el.textContent;
                });
                const hasSlash = Object.values(lvls).some(v => v && v.includes('/'));
                return {lvls, hasSlash};
            }
        """)
        results["test5_cap"] = cap

        # ============ TEST 6 — Unaffordable greyed ============
        attach_listeners(page, "test6-unaffordable")
        await page.evaluate("""
            () => { STATE.gold = 0; if(typeof updateUpgradesUI === 'function') updateUpgradesUI(); }
        """)
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT / "qa10-06-unaffordable.png"))
        un = await page.evaluate("""
            () => {
                const all = document.querySelectorAll('.upg-btn');
                const una = document.querySelectorAll('.upg-btn.unaffordable');
                const aff = document.querySelectorAll('.upg-btn.affordable');
                let firstUnaStyle = null;
                if (una.length > 0) {
                    const cs = getComputedStyle(una[0]);
                    firstUnaStyle = {
                        opacity: cs.opacity,
                        filter: cs.filter
                    };
                }
                return {
                    totalUpgBtns: all.length,
                    unaffordableCount: una.length,
                    affordableCount: aff.length,
                    firstUnaStyle
                };
            }
        """)
        results["test6_unaffordable"] = un

        # ============ FINAL REPORT ============
        report = {
            "tests": results,
            "page_errors_total": len(page_errors),
            "console_errors_total": len(console_errors),
            "console_warnings_undef": len(console_warnings),
            "page_errors": page_errors,
            "console_errors": console_errors,
            "console_warnings": console_warnings,
            "scenario_errors": {k: v for k, v in scenario_errors.items() if v},
        }
        (OUT / "qa10-ux-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print("=" * 70)
        print("QA VAGUE 22 - AGENT 10 - UX UPGRADES")
        print("=" * 70)
        print(f"Forced state    : {forced}")
        print(f"PageErrors      : {len(page_errors)}")
        print(f"ConsoleErrors   : {len(console_errors)}")
        print(f"Warnings undef  : {len(console_warnings)}")
        print("--- TESTS ---")
        for k, v in results.items():
            print(f"  [{k}] -> {json.dumps(v, ensure_ascii=False)[:300]}")
        print("--- SCENARIO ERRORS ---")
        for label, errs in scenario_errors.items():
            if errs:
                print(f"  [{label}] {len(errs)} error(s)")
                for e in errs[:3]:
                    print(f"     - {e[:200]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
