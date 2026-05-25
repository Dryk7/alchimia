"""
AUDIT VISUAL DESIGN — Boutons upgrade (.upg-btn)
Read-only audit du design visuel à km 30 avec 100k gouttes.
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
        )
        # Skip onboarding via localStorage before page load
        await context.add_init_script("""
            localStorage.setItem('foulee.openingSeen', '1');
            localStorage.setItem('foulee.storySeen', '1');
            localStorage.setItem('foulee.tutoV3', 'done');
            localStorage.setItem('foulee.activeTutoV1', 'done');
        """)
        page = await context.new_page()
        page.on("pageerror", lambda e: print(f"[PAGEERR] {e}"))
        page.on("console", lambda msg: None)  # silent

        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(800)

        # Dismiss any overlay/modal (daily reward, story, opening, etc.)
        await page.evaluate("""
            () => {
                document.querySelectorAll('.modal, .modal-backdrop, .modal-overlay, .opening-screen, .story-modal, .daily-modal').forEach(m => {
                    m.style.display = 'none';
                    m.classList.remove('open','show','visible','active');
                });
                document.querySelectorAll('[data-close], .modal-close, .close-btn, .btn-close').forEach(b => {
                    try { b.click(); } catch(e){}
                });
                if (window.STATE && STATE.daily) STATE.daily.lastClaim = Date.now();
                localStorage.setItem('foulee.dailySeen', Date.now().toString());
            }
        """)
        await page.wait_for_timeout(300)

        # Click PRENDRE LE DÉPART via JS (avoid 'not stable' animation issues)
        await page.evaluate("""
            () => {
                const b = document.getElementById('start-btn');
                if (b) {
                    b.click();
                    b.dispatchEvent(new MouseEvent('pointerdown', {bubbles:true}));
                    b.dispatchEvent(new MouseEvent('pointerup', {bubbles:true}));
                }
            }
        """)
        await page.wait_for_timeout(3000)

        # Dismiss any post-start modals
        await page.evaluate("""
            () => {
                document.querySelectorAll('.modal-backdrop, .modal-overlay').forEach(m => {
                    m.style.display = 'none';
                });
                document.querySelectorAll('.modal-close, .btn-close, [data-close]').forEach(b => {
                    try { b.click(); } catch(e){}
                });
            }
        """)
        await page.wait_for_timeout(400)

        # Force state km 30 + 100k gold
        await page.evaluate("""
            () => {
                if (window.STATE) {
                    STATE.lapsRun = 30;
                    STATE.gold = 100000;
                    if (typeof updateUpgradeUI === 'function') try { updateUpgradeUI(); } catch(e){}
                    if (typeof renderAll === 'function') try { renderAll(); } catch(e){}
                    if (typeof refreshUpgrades === 'function') try { refreshUpgrades(); } catch(e){}
                }
            }
        """)
        await page.wait_for_timeout(400)

        # Switch to upgrades tab + open drawer
        await page.evaluate("""
            () => {
                const tabBtn = document.querySelector('.tab-btn[data-tab="upgrades"]');
                if (tabBtn) tabBtn.click();
                const tc = document.querySelector('.tabs-content');
                if (tc) tc.classList.add('open');
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                const pane = document.querySelector('.tab-pane[data-pane="upgrades"]');
                if (pane) pane.classList.add('active');
                const tu = document.querySelector('.tap-upgrades-v2');
                if (tu) tu.scrollTop = 0;
            }
        """)
        await page.wait_for_timeout(900)

        # Re-trigger refresh
        await page.evaluate("""
            () => {
                if (typeof refreshUpgrades === 'function') try { refreshUpgrades(); } catch(e){}
                if (typeof updateUpgradeUI === 'function') try { updateUpgradeUI(); } catch(e){}
            }
        """)
        await page.wait_for_timeout(400)

        # Screenshot the whole drawer area
        drawer = await page.query_selector('.tabs-content')
        if drawer:
            await drawer.screenshot(path=f"{OUT_DIR}/audit-A-drawer.png")
        else:
            await page.screenshot(path=f"{OUT_DIR}/audit-A-drawer.png", full_page=False)

        # Full page too for context
        await page.screenshot(path=f"{OUT_DIR}/audit-A-fullpage.png", full_page=False)

        # Eval CSS computed for each .upg-btn
        data = await page.evaluate("""
            () => {
                const btns = document.querySelectorAll('.tap-upgrades-v2 .upg-btn');
                const result = [];
                btns.forEach(btn => {
                    const cs = getComputedStyle(btn);
                    const rect = btn.getBoundingClientRect();
                    const isLocked = btn.dataset.locked === '1' || btn.classList.contains('locked');
                    const isAfford = btn.classList.contains('affordable');
                    const iconWrap = btn.querySelector('.upg-icon-wrap');
                    const iconSvg = btn.querySelector('.upg-icon-wrap svg');
                    const csIcon = iconWrap ? getComputedStyle(iconWrap) : null;
                    const name = btn.querySelector('.upg-name')?.textContent?.trim();
                    const desc = btn.querySelector('.upg-desc')?.textContent?.trim();
                    const lvlEl = btn.querySelector('.upg-lvl');
                    const costEl = btn.querySelector('.upg-cost');
                    const csLvl = lvlEl ? getComputedStyle(lvlEl) : null;
                    const csCost = costEl ? getComputedStyle(costEl) : null;
                    result.push({
                        name,
                        desc,
                        classes: btn.className,
                        dataUpgrade: btn.dataset.upgrade,
                        dataUnlockKm: btn.dataset.unlockKm,
                        locked: isLocked,
                        affordable: isAfford,
                        visible: rect.width > 0 && rect.height > 0,
                        rect: {w: Math.round(rect.width), h: Math.round(rect.height), x: Math.round(rect.x), y: Math.round(rect.y)},
                        btn: {
                            width: cs.width,
                            height: cs.height,
                            padding: cs.padding,
                            fontSize: cs.fontSize,
                            backgroundColor: cs.backgroundColor,
                            background: cs.background.substring(0, 100),
                            color: cs.color,
                            borderRadius: cs.borderRadius,
                            border: cs.border,
                            boxShadow: cs.boxShadow.substring(0, 120),
                        },
                        icon: csIcon ? {
                            w: csIcon.width, h: csIcon.height,
                            bg: csIcon.backgroundColor,
                            border: csIcon.border,
                            borderRadius: csIcon.borderRadius,
                            svgPresent: !!iconSvg,
                            svgColor: iconSvg ? getComputedStyle(iconSvg).color : null,
                        } : null,
                        lvl: csLvl ? {
                            text: lvlEl.textContent,
                            color: csLvl.color,
                            bg: csLvl.backgroundColor,
                            fontSize: csLvl.fontSize,
                            fontWeight: csLvl.fontWeight,
                        } : null,
                        cost: csCost ? {
                            text: costEl.textContent,
                            color: csCost.color,
                            bg: csCost.backgroundColor,
                            fontSize: csCost.fontSize,
                            fontWeight: csCost.fontWeight,
                        } : null,
                    });
                });
                // Count SVGs
                const svgCount = document.querySelectorAll('.tap-upgrades-v2 .upg-icon-wrap svg').length;
                const upgBtnTotal = document.querySelectorAll('.tap-upgrades-v2 .upg-btn').length;
                const upgBtnVisible = Array.from(document.querySelectorAll('.tap-upgrades-v2 .upg-btn'))
                    .filter(b => {
                        const r = b.getBoundingClientRect();
                        return r.width > 0 && r.height > 0 && !(b.dataset.locked === '1');
                    }).length;
                const drawerEl = document.querySelector('.tabs-content');
                const drawerOpen = drawerEl && drawerEl.classList.contains('open');
                const stateInfo = {
                    lapsRun: window.STATE ? STATE.lapsRun : null,
                    gold: window.STATE ? STATE.gold : null,
                };
                // Distinct SVG paths (unique check)
                const svgPaths = Array.from(document.querySelectorAll('.tap-upgrades-v2 .upg-icon-wrap svg')).map(s => {
                    return s.outerHTML.substring(0, 200);
                });
                return {
                    drawerOpen,
                    state: stateInfo,
                    svgCount,
                    upgBtnTotal,
                    upgBtnVisible,
                    distinctSvgPaths: new Set(svgPaths).size,
                    buttons: result,
                };
            }
        """)

        # Persist findings
        with open(f"{OUT_DIR}/audit-A-design.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Print compact summary
        print("=" * 70)
        print(f"STATE: lapsRun={data['state']['lapsRun']}  gold={data['state']['gold']}")
        print(f"Drawer open: {data['drawerOpen']}")
        print(f"Upgrade buttons total/visible: {data['upgBtnTotal']} / {data['upgBtnVisible']}")
        print(f"SVG icons rendered: {data['svgCount']}  | distinct paths: {data['distinctSvgPaths']}")
        print("-" * 70)
        for b in data['buttons']:
            flags = []
            if b['locked']: flags.append('LOCKED')
            if b['affordable']: flags.append('AFFORD')
            if not b['visible']: flags.append('HIDDEN')
            print(f"  [{b['dataUpgrade']:15s}] {b['name']:24s} km>{b['dataUnlockKm']:3s} "
                  f"{b['rect']['w']}x{b['rect']['h']}px  "
                  f"svg={b['icon']['svgPresent'] if b['icon'] else 'N/A'} "
                  f"color={b['icon']['svgColor'] if b['icon'] else 'N/A'} "
                  f"| {' '.join(flags)}")
        print("-" * 70)
        # Sample contrast pairs
        print("CONTRAST SAMPLE (text vs button background):")
        for b in data['buttons'][:3]:
            print(f"  {b['name']}:")
            print(f"    btn bg = {b['btn']['backgroundColor']}")
            print(f"    lvl: text={b['lvl']['color']} bg={b['lvl']['bg']} size={b['lvl']['fontSize']}")
            print(f"    cost: text={b['cost']['color']} bg={b['cost']['bg']} size={b['cost']['fontSize']}")
        print("=" * 70)
        print(f"Screenshot: {OUT_DIR}/audit-A-drawer.png")
        print(f"JSON: {OUT_DIR}/audit-A-design.json")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
