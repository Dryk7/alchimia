"""
AUDIT F — Descriptions évocatrices upgrades + Tooltips tap-and-hold
Read-only audit : capture .upg-desc texts + check long-press tooltip system
on each upgrade button. Compare to i18n dict (lines 8898-8905).
"""
import asyncio
import json
from playwright.async_api import async_playwright

URL = "http://localhost:8770/index.html"
OUT_DIR = "D:/alchimia/screenshots/qa-vague10"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
            has_touch=True,
            is_mobile=True,
        )
        await context.add_init_script("""
            localStorage.setItem('foulee.openingSeen', '1');
            localStorage.setItem('foulee.storySeen', '1');
            localStorage.setItem('foulee.tutoV3', 'done');
            localStorage.setItem('foulee.activeTutoV1', 'done');
            localStorage.setItem('foulee.dailySeen', Date.now().toString());
        """)
        page = await context.new_page()
        page.on("pageerror", lambda e: print(f"[PAGEERR] {e}"))

        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(800)

        # Dismiss modals
        await page.evaluate("""
            () => {
                document.querySelectorAll('.modal, .modal-backdrop, .opening-screen, .story-modal, .daily-modal, #opening-cinematic, #intro, #story-modal').forEach(m => {
                    m.style.display = 'none';
                    m.classList.remove('open','show','visible','active');
                });
                document.querySelectorAll('[data-close], .modal-close, .close-btn').forEach(b => { try { b.click(); } catch(e){} });
                if (window.STATE && STATE.daily) STATE.daily.lastClaim = Date.now();
            }
        """)
        await page.wait_for_timeout(300)

        # Force state km 30 + 100k gold so every upgrade is unlocked & affordable
        await page.evaluate("""
            () => {
                if (window.STATE) {
                    STATE.lapsRun = 30;
                    STATE.gold = 100000;
                    if (typeof renderAll === 'function') try { renderAll(); } catch(e){}
                    if (typeof refreshUpgrades === 'function') try { refreshUpgrades(); } catch(e){}
                    if (typeof updateUpgradesUI === 'function') try { updateUpgradesUI(); } catch(e){}
                }
            }
        """)
        await page.wait_for_timeout(400)

        # Open the upgrades drawer
        await page.evaluate("""
            () => {
                const tabBtn = document.querySelector('.tab-btn[data-tab="upgrades"]');
                if (tabBtn) tabBtn.click();
                const tc = document.querySelector('.tabs-content');
                if (tc) tc.classList.add('open');
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                const pane = document.querySelector('.tab-pane[data-pane="upgrades"]');
                if (pane) pane.classList.add('active');
                const tu = document.querySelector('.tap-upgrades, .tap-upgrades-v2');
                if (tu) tu.scrollTop = 0;
            }
        """)
        await page.wait_for_timeout(600)
        await page.evaluate("if(typeof updateUpgradesUI==='function') try{updateUpgradesUI()}catch(e){}")
        await page.wait_for_timeout(300)

        # === 1. Collect every upgrade meta ===
        upgrades = await page.evaluate("""
            () => {
                const out = [];
                document.querySelectorAll('.upg-btn').forEach(btn => {
                    const id = btn.getAttribute('data-upgrade');
                    const name = btn.querySelector('.upg-name')?.textContent?.trim() || '';
                    const desc = btn.querySelector('.upg-desc')?.textContent?.trim() || '';
                    const lvl = btn.querySelector('.upg-lvl')?.textContent?.trim() || '';
                    const cost = btn.querySelector('.upg-cost')?.textContent?.trim() || '';
                    const dataTooltip = btn.getAttribute('data-tooltip') || '';
                    const dataTooltipTitle = btn.getAttribute('data-tooltip-title') || '';
                    const dataBonus = btn.getAttribute('data-bonus') || '';
                    const ariaLabel = btn.getAttribute('aria-label') || '';
                    const ariaDescribedBy = btn.getAttribute('aria-describedby') || '';
                    // Style colors
                    const nameEl = btn.querySelector('.upg-name');
                    const descEl = btn.querySelector('.upg-desc');
                    const nameColor = nameEl ? getComputedStyle(nameEl).color : '';
                    const descColor = descEl ? getComputedStyle(descEl).color : '';
                    const nameSize  = nameEl ? getComputedStyle(nameEl).fontSize : '';
                    const descSize  = descEl ? getComputedStyle(descEl).fontSize : '';
                    const descWeight = descEl ? getComputedStyle(descEl).fontWeight : '';
                    const descRect = descEl ? descEl.getBoundingClientRect() : null;
                    const descLineHeight = descEl ? parseFloat(getComputedStyle(descEl).lineHeight) : 0;
                    const lineCount = (descEl && descLineHeight > 0) ? Math.round(descRect.height / descLineHeight) : 0;
                    out.push({ id, name, desc, lvl, cost, dataTooltip, dataTooltipTitle,
                        dataBonus, ariaLabel, ariaDescribedBy,
                        nameColor, descColor, nameSize, descSize, descWeight,
                        descLineCount: lineCount,
                        descHeightPx: descRect ? Math.round(descRect.height) : 0 });
                });
                return out;
            }
        """)

        # === 2. Get i18n dict for the upg_desc_* keys ===
        i18n_descs = await page.evaluate("""
            () => {
                const out = { fr: {}, en: {} };
                if (typeof I18N_STRINGS === 'undefined') return out;
                for (const lang of ['fr','en']) {
                    const d = I18N_STRINGS[lang] || {};
                    for (const k of Object.keys(d)) {
                        if (k.startsWith('upg_desc_')) out[lang][k] = d[k];
                    }
                }
                return out;
            }
        """)

        # === 3. Long-press test on each upgrade — see if a tooltip appears ===
        # First check if Tooltips system exists
        tooltips_info = await page.evaluate("""
            () => {
                return {
                    hasTooltips: typeof window.Tooltips !== 'undefined',
                    hasTooltipCss: !!document.querySelector('style, link') && document.documentElement.outerHTML.includes('foulee-tooltip'),
                    countDataTooltipGlobal: document.querySelectorAll('[data-tooltip]').length,
                    countUpgWithDataTooltip: document.querySelectorAll('.upg-btn[data-tooltip]').length,
                    countUpgWithDataBonus: document.querySelectorAll('.upg-btn[data-bonus]').length
                };
            }
        """)

        # Attempt long-press on the PUISSANCE upgrade
        longpress_results = []
        for upg in upgrades[:3]:  # test first 3 to save time
            uid = upg["id"]
            try:
                btn = await page.query_selector(f'.upg-btn[data-upgrade="{uid}"]')
                if not btn:
                    longpress_results.append({"id": uid, "tooltipShown": False, "reason": "button not found"})
                    continue
                box = await btn.bounding_box()
                if not box:
                    longpress_results.append({"id": uid, "tooltipShown": False, "reason": "no bbox"})
                    continue
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2

                # Simulate pointerdown (long-press)
                await page.mouse.move(cx, cy)
                await page.mouse.down()
                await page.wait_for_timeout(900)  # hold 900ms (> HOLD_MS=500)

                # Capture tooltip state
                tt_state = await page.evaluate("""
                    () => {
                        const t = document.querySelector('.foulee-tooltip');
                        if (!t) return { exists: false };
                        return {
                            exists: true,
                            hasShow: t.classList.contains('show'),
                            opacity: getComputedStyle(t).opacity,
                            text: (t.querySelector('.foulee-tooltip-body')?.textContent || '').trim(),
                            title: (t.querySelector('.foulee-tooltip-title')?.textContent || '').trim()
                        };
                    }
                """)
                # Screenshot the visible viewport with tooltip
                await page.screenshot(path=f"{OUT_DIR}/audit-F-tooltip-{uid}.png", full_page=False)
                await page.mouse.up()
                await page.wait_for_timeout(700)  # wait for fade-out
                longpress_results.append({"id": uid, "tooltipShown": tt_state.get("hasShow", False) and float(tt_state.get("opacity", 0) or 0) > 0.5, "state": tt_state})
            except Exception as e:
                try:
                    await page.mouse.up()
                except Exception:
                    pass
                longpress_results.append({"id": uid, "tooltipShown": False, "reason": str(e)})

        # === 4. Drawer screenshot for visual reference ===
        try:
            drawer = await page.query_selector('.tabs-content')
            if drawer:
                await drawer.screenshot(path=f"{OUT_DIR}/audit-F-drawer.png")
            else:
                await page.screenshot(path=f"{OUT_DIR}/audit-F-drawer.png")
        except Exception:
            pass

        report = {
            "upgrades": upgrades,
            "i18n_descs": i18n_descs,
            "tooltips_system": tooltips_info,
            "longpress_tests": longpress_results,
        }
        with open(f"{OUT_DIR}/audit-F-tooltips.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(json.dumps(report, ensure_ascii=False, indent=2))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
