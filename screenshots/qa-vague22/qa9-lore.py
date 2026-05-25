"""
QA Vague 22 — Test READ-ONLY du système Lore Codex (vague 20 P7).

Vérifie :
- LORE_CODEX contient bien 20 entrées
- isLoreUnlocked() retourne true selon paliers (km / boss / ascend / final)
- openLore() ouvre la modale + rendu (unlocked vs locked)
- Compteur "Débloqué X/20" affiché
- Menu burger (data-action=lore) ouvre la modale
- Aucune erreur console
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


async def force_state_and_count(page, mut_js, label):
    """Applique des mutations à STATE puis compte unlocked + retourne ids unlocked."""
    res = await safe_eval(page, f"""
        () => {{
            try {{
                {mut_js}
                if (!window.LORE_CODEX || !window.isLoreUnlocked) return {{err:'no-lore'}};
                const unlocked = [];
                const locked = [];
                for (const e of window.LORE_CODEX) {{
                    if (window.isLoreUnlocked(e)) unlocked.push(e.id);
                    else locked.push(e.id + '(' + e.unlock + ')');
                }}
                return {{
                    total: window.LORE_CODEX.length,
                    count: unlocked.length,
                    unlocked,
                    locked,
                    lapsRun: STATE.lapsRun,
                    ascensions: STATE.ascensions || 0,
                    bosses: STATE.bosses ? Object.keys(STATE.bosses).reduce((a,k)=>{{
                        a[k] = STATE.bosses[k]?.defeated || false; return a;
                    }}, {{}}) : null
                }};
            }} catch(e) {{ return {{err: String(e)}}; }}
        }}
    """, label)
    return res


async def close_modal(page):
    try:
        await page.evaluate("""
            () => {
                const m = document.getElementById('lore-modal');
                if (m) m.classList.remove('show');
                const x = document.querySelector('#lore-modal .modal-close');
                if (x) x.click();
            }
        """)
        await page.wait_for_timeout(300)
    except Exception:
        pass


async def main():
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

        # ============ Q1 : LORE_CODEX contient 20 entrées ============
        codex_meta = await safe_eval(page, """
            () => {
                if (!window.LORE_CODEX) return {ok:false, reason:'undefined'};
                const ids = window.LORE_CODEX.map(e => e.id);
                const conds = window.LORE_CODEX.map(e => e.unlock);
                const dups = ids.filter((id,i)=>ids.indexOf(id)!==i);
                return {
                    ok: true,
                    length: window.LORE_CODEX.length,
                    ids,
                    conds,
                    duplicates: dups,
                    hasTitle: window.LORE_CODEX.every(e=>!!e.title),
                    hasText:  window.LORE_CODEX.every(e=>!!e.text),
                    hasIsLoreUnlocked: typeof window.isLoreUnlocked === 'function',
                    hasOpenLore: typeof window.openLore === 'function',
                    hasRenderLore: typeof window.renderLore === 'function'
                };
            }
        """, "codex-meta")

        # ============ Paliers de progression ============
        # Palier 0 — km=0, aucune entrée
        p0 = await force_state_and_count(page, """
            STATE.lapsRun = 0;
            STATE.ascensions = 0;
            if (STATE.bosses) {
                for (const k in STATE.bosses) STATE.bosses[k].defeated = false;
            }
        """, "palier-km0")

        # Palier km=5 → l01 (km1) + l02 (km5)
        p5 = await force_state_and_count(page, "STATE.lapsRun = 5;", "palier-km5")

        # Palier km=50 → l01..l08 (km1,5,12,20,30,42,50) -> 7 entrées km + 0 boss
        p50 = await force_state_and_count(page, "STATE.lapsRun = 50;", "palier-km50")

        # Palier km=100 → l01..l15 (km1..100)
        p100 = await force_state_and_count(page, "STATE.lapsRun = 100;", "palier-km100")

        # Force boss ironlung defeated → l06
        p_boss = await force_state_and_count(page, """
            STATE.lapsRun = 5;
            STATE.bosses = STATE.bosses || {};
            STATE.bosses.ironlung = STATE.bosses.ironlung || {};
            STATE.bosses.ironlung.defeated = true;
        """, "boss-ironlung")

        # Force ascensions=5 → l18
        p_asc = await force_state_and_count(page, """
            STATE.lapsRun = 0;
            STATE.bosses = STATE.bosses || {};
            for (const k in STATE.bosses) STATE.bosses[k].defeated = false;
            STATE.ascensions = 5;
        """, "ascend5")

        # Force final = moonking defeated + saison >= 10 → l20
        p_final = await force_state_and_count(page, """
            STATE.lapsRun = 200;
            STATE.ascensions = 5;
            STATE.bosses = STATE.bosses || {};
            STATE.bosses.ironlung = {defeated:true};
            STATE.bosses.stormsprint = {defeated:true};
            STATE.bosses.cosmic = {defeated:true};
            STATE.bosses.moonking = {defeated:true};
            STATE.saison = 10;
        """, "all-conditions")

        # ============ Q3 : openLore() rend la modale ============
        # On garde STATE 'all-conditions' pour voir un max d'entrées unlocked dans la modale
        await safe_eval(page, "() => { if (window.openLore) window.openLore(); }", "openLore-call")
        await page.wait_for_timeout(700)
        await page.screenshot(path=str(OUT / "qa9-lore-modal-allUnlocked.png"))

        modal_state_all = await safe_eval(page, """
            () => {
                const m = document.getElementById('lore-modal');
                const visible = m && m.classList.contains('show');
                const list = document.getElementById('lore-list');
                const html = list ? list.innerHTML : '';
                const counterMatch = html.match(/Débloqué\\s*:?\\s*(\\d+)\\s*\\/\\s*(\\d+)/);
                const lockedBlocks = (html.match(/Verrouillé/g) || []).length;
                const goldBlocks = (html.match(/border-left:4px solid #ffd060/g) || []).length;
                const grayBlocks = (html.match(/border-left:4px solid #888/g) || []).length;
                return {
                    visible,
                    counter: counterMatch ? {unlocked:+counterMatch[1], total:+counterMatch[2]} : null,
                    lockedBlocks,
                    goldBlocks,
                    grayBlocks,
                    htmlLen: html.length
                };
            }
        """, "modal-state-all")

        await close_modal(page)

        # ============ Q3 bis : reset STATE puis voir modale avec lockés ============
        await safe_eval(page, """
            () => {
                STATE.lapsRun = 5;
                STATE.ascensions = 0;
                if (STATE.bosses) for (const k in STATE.bosses) STATE.bosses[k].defeated = false;
                STATE.saison = 1;
                if (window.openLore) window.openLore();
            }
        """, "openLore-locked")
        await page.wait_for_timeout(700)
        await page.screenshot(path=str(OUT / "qa9-lore-modal-mostlyLocked.png"))

        modal_state_locked = await safe_eval(page, """
            () => {
                const list = document.getElementById('lore-list');
                const html = list ? list.innerHTML : '';
                const counterMatch = html.match(/Débloqué\\s*:?\\s*(\\d+)\\s*\\/\\s*(\\d+)/);
                const lockedBlocks = (html.match(/Verrouillé/g) || []).length;
                const goldBlocks = (html.match(/border-left:4px solid #ffd060/g) || []).length;
                const grayBlocks = (html.match(/border-left:4px solid #888/g) || []).length;
                return {
                    counter: counterMatch ? {unlocked:+counterMatch[1], total:+counterMatch[2]} : null,
                    lockedBlocks, goldBlocks, grayBlocks
                };
            }
        """, "modal-state-locked")

        await close_modal(page)

        # ============ Q3 ter : burger menu ============
        burger_inv = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[data-action="lore"]');
                return {count: els.length};
            }
        """)
        burger_opened = False
        try:
            await page.evaluate("""
                () => {
                    const sel = ['#burger','.burger','[data-burger]','[aria-label*="menu" i]','.menu-toggle','#menu-btn'];
                    for (const s of sel) {
                        const el = document.querySelector(s);
                        if (el) { el.click(); return; }
                    }
                }
            """)
            await page.wait_for_timeout(400)
            burger_opened = await page.evaluate("""
                () => {
                    const el = document.querySelector('[data-action="lore"]');
                    if (!el) return false;
                    el.click();
                    return true;
                }
            """)
            await page.wait_for_timeout(800)
            await page.screenshot(path=str(OUT / "qa9-lore-burger.png"))
            modal_after_burger = await page.evaluate("""
                () => {
                    const m = document.getElementById('lore-modal');
                    return m && m.classList.contains('show');
                }
            """)
        except Exception as e:
            scenario_errors.setdefault("burger", []).append(str(e))
            modal_after_burger = False

        await close_modal(page)

        # ============ Analyse "entrées silencieuses" ============
        # Une entrée est "silencieuse" si on ne peut pas trouver une combinaison STATE qui la débloque.
        # On force toutes conditions plausibles → si certaines restent locked, c'est suspect.
        silent_check = await safe_eval(page, """
            () => {
                STATE.lapsRun = 9999;
                STATE.ascensions = 99;
                STATE.saison = 99;
                STATE.bosses = STATE.bosses || {};
                ['ironlung','stormsprint','cosmic','moonking','iron_lung','storm_sprint','moon_king'].forEach(k => {
                    STATE.bosses[k] = {defeated:true};
                });
                const stillLocked = [];
                for (const e of window.LORE_CODEX) {
                    if (!window.isLoreUnlocked(e)) stillLocked.push({id:e.id, unlock:e.unlock});
                }
                return {stillLocked, totalBosses: Object.keys(STATE.bosses)};
            }
        """, "silent-check")

        # ============ REPORT ============
        report = {
            "url": URL,
            "codex_meta": codex_meta,
            "paliers": {
                "km0":      p0,
                "km5":      p5,
                "km50":     p50,
                "km100":    p100,
                "boss_ironlung": p_boss,
                "ascend5":  p_asc,
                "final":    p_final,
            },
            "expected": {
                "km0":      0,
                "km5":      2,   # l01(km1) + l02(km5)
                "km50":     7,   # l01,l02,l03(12),l04(20),l05(30),l07(42),l08(50)
                "km100":    14,  # l01..l15 sauf l06(boss),l10(boss) -> 13 km entries + km100 = check
                "boss_ironlung_min": 3,  # km5 (2 km entries) + l06 boss
                "ascend5_min": 1, # juste l18
                "final_min": 19,  # tout sauf rien (selon couverture boss)
            },
            "modal_state_all_unlocked": modal_state_all,
            "modal_state_mostly_locked": modal_state_locked,
            "burger_inventory_lore": burger_inv,
            "burger_opened_modal": modal_after_burger if 'modal_after_burger' in dir() else burger_opened,
            "silent_entries_after_force_everything": silent_check,
            "page_errors_total": len(page_errors),
            "console_errors_total": len(console_errors),
            "console_warnings_undef_total": len(console_warnings),
            "page_errors": page_errors[:20],
            "console_errors": console_errors[:20],
            "console_warnings": console_warnings[:20],
            "scenario_errors": {k:v for k,v in scenario_errors.items() if v},
        }

        (OUT / "qa9-lore-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print("=" * 70)
        print("QA9 LORE CODEX — REPORT")
        print("=" * 70)
        print(f"CODEX defined: {codex_meta}")
        print()
        for k, v in report["paliers"].items():
            if isinstance(v, dict) and "count" in v:
                print(f"[{k:18s}] count={v['count']:2d}/{v.get('total','?')} unlocked={v.get('unlocked')}")
            else:
                print(f"[{k:18s}] {v}")
        print()
        print(f"Modal all-unlocked: {modal_state_all}")
        print(f"Modal mostly-locked: {modal_state_locked}")
        print(f"Burger inventory (data-action=lore): {burger_inv}")
        print(f"Burger opened modal: {report['burger_opened_modal']}")
        print(f"Silent entries (after forcing everything): {silent_check}")
        print()
        print(f"PageErrors:   {len(page_errors)}")
        print(f"ConsoleErrs:  {len(console_errors)}")
        print(f"WarnUndef:    {len(console_warnings)}")
        if page_errors:
            print("--- page errors ---")
            for e in page_errors[:5]: print(f"  {e[:160]}")
        if console_errors:
            print("--- console errors ---")
            for e in console_errors[:5]: print(f"  {e[:160]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
