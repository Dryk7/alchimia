"""
AUDIT ACCESSIBILITY (VAGUE 17 — Agent J)
Read-only audit a11y des boutons upgrade (.upg-btn) :
  - presence aria-label
  - tabindex
  - contrast ratio texte vs background (WCAG)
  - focus visible au keyboard Tab
  - ordre logique Tab
  - prefers-reduced-motion respecte sur .just-bought / .just-unlocked
"""
import asyncio
import json
import re
from playwright.async_api import async_playwright

URL = "http://localhost:8770/index.html"
OUT_DIR = "D:/alchimia/screenshots/qa-vague10"

# ---- WCAG 2.x relative luminance + contrast ratio --------------------------
def _parse_color(c):
    """Parse 'rgb(r,g,b)' or 'rgba(r,g,b,a)' or '#rrggbb' to (r,g,b,a)."""
    if not c: return None
    c = c.strip()
    m = re.match(r'rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)', c)
    if m:
        r, g, b = int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (r, g, b, a)
    m = re.match(r'#([0-9a-fA-F]{6})', c)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    if c == 'transparent':
        return (0, 0, 0, 0.0)
    return None

def _composite(fg, bg):
    """Composite fg(rgba) over bg(rgba)."""
    if fg is None: return bg
    if bg is None: bg = (255, 255, 255, 1.0)
    fa = fg[3]; ba = bg[3]
    if fa >= 1.0: return (fg[0], fg[1], fg[2], 1.0)
    out_a = fa + ba * (1 - fa)
    if out_a == 0: return (0, 0, 0, 0)
    out_r = (fg[0]*fa + bg[0]*ba*(1-fa)) / out_a
    out_g = (fg[1]*fa + bg[1]*ba*(1-fa)) / out_a
    out_b = (fg[2]*fa + bg[2]*ba*(1-fa)) / out_a
    return (out_r, out_g, out_b, out_a)

def _rel_lum(rgb):
    def chan(v):
        v = v / 255.0
        return v/12.92 if v <= 0.03928 else ((v + 0.055)/1.055) ** 2.4
    return 0.2126*chan(rgb[0]) + 0.7152*chan(rgb[1]) + 0.0722*chan(rgb[2])

def contrast_ratio(fg_str, bg_str, page_bg=(255, 255, 255, 1.0)):
    """WCAG contrast ratio. Composites transparent layers onto page_bg."""
    fg = _parse_color(fg_str)
    bg = _parse_color(bg_str)
    if fg is None: return None
    # Composite bg (might be transparent) over page bg first
    if bg is None or bg[3] < 1.0:
        bg = _composite(bg, page_bg)
    bg_solid = (bg[0], bg[1], bg[2])
    # If fg transparent, composite over bg
    if fg[3] < 1.0:
        fg = _composite(fg, bg + (1.0,) if len(bg) == 3 else bg)
    fg_solid = (fg[0], fg[1], fg[2])
    L1 = _rel_lum(fg_solid)
    L2 = _rel_lum(bg_solid)
    if L1 < L2: L1, L2 = L2, L1
    return round((L1 + 0.05) / (L2 + 0.05), 2)

# ---- helpers ----------------------------------------------------------------
async def skip_overlays(page):
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

async def force_state_and_open_drawer(page):
    await page.evaluate("""
        () => {
            if (window.STATE) {
                STATE.lapsRun = 30;
                STATE.gold = 100000;
                if (typeof updateUpgradeUI === 'function') try { updateUpgradeUI(); } catch(e){}
                if (typeof renderAll === 'function') try { renderAll(); } catch(e){}
                if (typeof refreshUpgrades === 'function') try { refreshUpgrades(); } catch(e){}
            }
            const tabBtn = document.querySelector('.tab-btn[data-tab="upgrades"]');
            if (tabBtn) tabBtn.click();
            const tc = document.querySelector('.tabs-content');
            if (tc) tc.classList.add('open');
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            const pane = document.querySelector('.tab-pane[data-pane="upgrades"]');
            if (pane) pane.classList.add('active');
            const tu = document.querySelector('.tap-upgrades');
            if (tu) tu.scrollTop = 0;
            if (typeof refreshUpgrades === 'function') try { refreshUpgrades(); } catch(e){}
        }
    """)

async def collect_buttons_a11y(page):
    return await page.evaluate("""
        () => {
            const btns = document.querySelectorAll('.tap-upgrades-v2 .upg-btn');
            const result = [];
            btns.forEach((btn, idx) => {
                const cs = getComputedStyle(btn);
                const rect = btn.getBoundingClientRect();
                const isLocked = btn.dataset.locked === '1' || btn.classList.contains('locked');
                const isAfford = btn.classList.contains('affordable');
                const lvlEl = btn.querySelector('.upg-lvl');
                const costEl = btn.querySelector('.upg-cost');
                const nameEl = btn.querySelector('.upg-name');
                const descEl = btn.querySelector('.upg-desc');
                const csLvl = lvlEl ? getComputedStyle(lvlEl) : null;
                const csCost = costEl ? getComputedStyle(costEl) : null;
                const csName = nameEl ? getComputedStyle(nameEl) : null;
                const csDesc = descEl ? getComputedStyle(descEl) : null;
                result.push({
                    index: idx,
                    dataUpgrade: btn.dataset.upgrade,
                    dataUnlockKm: btn.dataset.unlockKm,
                    ariaLabel: btn.getAttribute('aria-label'),
                    ariaDescribedBy: btn.getAttribute('aria-describedby'),
                    ariaDisabled: btn.getAttribute('aria-disabled'),
                    tabindex: btn.getAttribute('tabindex'),
                    role: btn.getAttribute('role'),
                    disabled: btn.disabled,
                    locked: isLocked,
                    affordable: isAfford,
                    visible: rect.width > 0 && rect.height > 0,
                    visualName: nameEl?.textContent?.trim(),
                    visualDesc: descEl?.textContent?.trim(),
                    rect: {w: Math.round(rect.width), h: Math.round(rect.height), x: Math.round(rect.x), y: Math.round(rect.y)},
                    btnBgColor: cs.backgroundColor,
                    btnColor: cs.color,
                    btnFontSize: cs.fontSize,
                    btnFontWeight: cs.fontWeight,
                    nameColor: csName?.color, nameBg: csName?.backgroundColor, nameSize: csName?.fontSize, nameWeight: csName?.fontWeight,
                    descColor: csDesc?.color, descBg: csDesc?.backgroundColor, descSize: csDesc?.fontSize, descWeight: csDesc?.fontWeight,
                    lvlColor: csLvl?.color, lvlBg: csLvl?.backgroundColor, lvlSize: csLvl?.fontSize, lvlWeight: csLvl?.fontWeight,
                    costColor: csCost?.color, costBg: csCost?.backgroundColor, costSize: csCost?.fontSize, costWeight: csCost?.fontWeight,
                });
            });
            return result;
        }
    """)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ===== PASS 1 : audit normal motion =====
        context = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
        )
        await context.add_init_script("""
            localStorage.setItem('foulee.openingSeen', '1');
            localStorage.setItem('foulee.storySeen', '1');
            localStorage.setItem('foulee.tutoV3', 'done');
            localStorage.setItem('foulee.activeTutoV1', 'done');
        """)
        page = await context.new_page()
        page.on("pageerror", lambda e: print(f"[PAGEERR] {e}"))

        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(700)
        await skip_overlays(page)
        await page.wait_for_timeout(250)
        await force_state_and_open_drawer(page)
        await page.wait_for_timeout(500)

        # === A11Y data collect ===
        btns_data = await collect_buttons_a11y(page)

        # === Focus styles (eval default :focus styles on a button) ===
        focus_css = await page.evaluate("""
            () => {
                const out = {};
                const btn = document.querySelector('.tap-upgrades-v2 .upg-btn');
                if (!btn) return out;
                // Apply :focus then read computed style — Playwright will do focus(); here we just read CSS rules
                btn.focus({preventScroll: true});
                const cs = getComputedStyle(btn);
                out.outline = cs.outline;
                out.outlineWidth = cs.outlineWidth;
                out.outlineColor = cs.outlineColor;
                out.outlineStyle = cs.outlineStyle;
                out.outlineOffset = cs.outlineOffset;
                out.boxShadow = cs.boxShadow.substring(0, 200);
                out.activeElement = document.activeElement?.className?.substring(0, 80) || null;
                return out;
            }
        """)

        # === Keyboard navigation : Tab 15 fois et collecte activeElement ===
        await page.evaluate("() => document.body.focus()")
        tab_chain = []
        for i in range(15):
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(50)
            info = await page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el) return null;
                    return {
                        tag: el.tagName,
                        cls: (el.className || '').toString().substring(0, 80),
                        aria: el.getAttribute('aria-label'),
                        dataUpgrade: el.dataset ? el.dataset.upgrade : null,
                        id: el.id || null,
                    };
                }
            """)
            tab_chain.append(info)

        # === Find first upg-btn in tab chain & screenshot focus state ===
        # Reset focus and Tab until reach an upg-btn
        await page.evaluate("() => document.body.focus()")
        upg_focused = False
        tabs_to_upg = 0
        for i in range(40):
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(40)
            tabs_to_upg += 1
            on_upg = await page.evaluate("""
                () => {
                    const el = document.activeElement;
                    return el && el.classList && el.classList.contains('upg-btn');
                }
            """)
            if on_upg:
                upg_focused = True
                break

        # Screenshot focus state
        await page.screenshot(path=f"{OUT_DIR}/audit-J-focus.png", full_page=False)

        # === Reduced-motion check (visual+computed) ===
        # We toggle media via emulateMedia and reload state
        await context.close()
        rm_context = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
            reduced_motion="reduce",
        )
        await rm_context.add_init_script("""
            localStorage.setItem('foulee.openingSeen', '1');
            localStorage.setItem('foulee.storySeen', '1');
            localStorage.setItem('foulee.tutoV3', 'done');
            localStorage.setItem('foulee.activeTutoV1', 'done');
        """)
        rm_page = await rm_context.new_page()
        rm_page.on("pageerror", lambda e: print(f"[PAGEERR-RM] {e}"))
        await rm_page.goto(URL, wait_until="networkidle")
        await rm_page.wait_for_timeout(700)
        await skip_overlays(rm_page)
        await rm_page.wait_for_timeout(250)
        await force_state_and_open_drawer(rm_page)
        await rm_page.wait_for_timeout(500)

        rm_result = await rm_page.evaluate("""
            () => {
                const out = {};
                out.mediaMatches = matchMedia('(prefers-reduced-motion: reduce)').matches;
                const btn = document.querySelector('.tap-upgrades-v2 .upg-btn');
                if (btn) {
                    // Apply just-bought class and read computed animation
                    btn.classList.add('just-bought');
                    const cs = getComputedStyle(btn);
                    out.justBoughtAnimDuration = cs.animationDuration;
                    out.justBoughtAnimName = cs.animationName;
                    out.justBoughtTransitionDuration = cs.transitionDuration;
                    btn.classList.remove('just-bought');
                }
                // Test just-unlocked on a runner-card if exists, else simulate on upg-btn
                let testCard = document.querySelector('.runner-card');
                if (testCard) {
                    testCard.classList.add('just-unlocked');
                    const cs2 = getComputedStyle(testCard);
                    out.justUnlockedAnimDuration = cs2.animationDuration;
                    out.justUnlockedAnimName = cs2.animationName;
                    testCard.classList.remove('just-unlocked');
                }
                return out;
            }
        """)
        await rm_page.screenshot(path=f"{OUT_DIR}/audit-J-reduced-motion.png", full_page=False)
        await rm_context.close()

        # ===== Compute contrast ratios in Python =====
        def cr_summary(rows):
            """Return list of dicts {key, txt, bg, ratio, pass_AA, pass_AA_large}."""
            out = []
            for b in rows:
                if not b['visible']: continue
                btn_bg = b['btnBgColor']
                # Name (large bold => Large Text per WCAG if >= 18.66px bold or 24px)
                name_ratio = contrast_ratio(b['nameColor'], b['nameBg'] if b['nameBg'] and 'rgba(0' not in b['nameBg'] else btn_bg)
                desc_ratio = contrast_ratio(b['descColor'], b['descBg'] if b['descBg'] and 'rgba(0' not in b['descBg'] else btn_bg)
                lvl_ratio = contrast_ratio(b['lvlColor'], b['lvlBg'] if b['lvlBg'] and 'rgba(0' not in b['lvlBg'] else btn_bg)
                cost_ratio = contrast_ratio(b['costColor'], b['costBg'] if b['costBg'] and 'rgba(0' not in b['costBg'] else btn_bg)
                out.append({
                    'upgrade': b['dataUpgrade'],
                    'name': b['visualName'],
                    'locked': b['locked'],
                    'btn_bg': btn_bg,
                    'name_text': b['nameColor'], 'name_size': b['nameSize'], 'name_weight': b['nameWeight'], 'name_ratio': name_ratio,
                    'desc_text': b['descColor'], 'desc_size': b['descSize'], 'desc_ratio': desc_ratio,
                    'lvl_text': b['lvlColor'], 'lvl_bg': b['lvlBg'], 'lvl_size': b['lvlSize'], 'lvl_ratio': lvl_ratio,
                    'cost_text': b['costColor'], 'cost_bg': b['costBg'], 'cost_size': b['costSize'], 'cost_ratio': cost_ratio,
                })
            return out

        contrast = cr_summary(btns_data)

        # === Save full JSON ===
        report = {
            'url': URL,
            'pass1_buttons': btns_data,
            'focus_css': focus_css,
            'tab_chain_15': tab_chain,
            'first_upg_focused_after_n_tabs': tabs_to_upg if upg_focused else None,
            'upg_focused_reached': upg_focused,
            'contrast': contrast,
            'reduced_motion': rm_result,
        }
        with open(f"{OUT_DIR}/audit-J-a11y.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # === Print summary ===
        print("=" * 78)
        print("AUDIT J — ACCESSIBILITE (.upg-btn)")
        print("=" * 78)
        print(f"Boutons trouves: {len(btns_data)} (visibles: {sum(1 for b in btns_data if b['visible'])})")
        print()
        print("--- ARIA & tabindex ---")
        for b in btns_data:
            print(f"  [{b['dataUpgrade']:14s}] aria-label={b['ariaLabel']!r:30s} tabindex={b['tabindex']} role={b['role']} disabled={b['disabled']} locked={b['locked']}")
        print()
        print("--- CONTRAST RATIOS (WCAG, >=4.5 AA normal, >=3 AA large/bold) ---")
        for c in contrast:
            print(f"  [{c['upgrade']:14s}] {c['name']:22s} bg={c['btn_bg']}")
            print(f"      NAME  txt={c['name_text']:18s} size={c['name_size']:6s} weight={c['name_weight']}  ratio={c['name_ratio']}")
            print(f"      DESC  txt={c['desc_text']:18s} size={c['desc_size']:6s} ratio={c['desc_ratio']}")
            print(f"      LVL   txt={c['lvl_text']:18s} bg={c['lvl_bg']:22s} ratio={c['lvl_ratio']}")
            print(f"      COST  txt={c['cost_text']:18s} bg={c['cost_bg']:22s} ratio={c['cost_ratio']}")
        print()
        print("--- FOCUS CSS (default :focus computed) ---")
        for k, v in focus_css.items():
            print(f"  {k}: {v}")
        print()
        print("--- KEYBOARD TAB CHAIN (15 tabs from body) ---")
        for i, t in enumerate(tab_chain, 1):
            if t:
                print(f"  Tab #{i:2d}: <{t['tag']}> .{(t['cls'] or '')[:50]:50s} aria={t['aria']!r} upgrade={t['dataUpgrade']}")
        print()
        print(f"--- Premier .upg-btn focus apres {tabs_to_upg} tabs (reached={upg_focused}) ---")
        print()
        print("--- REDUCED MOTION (context prefers-reduced-motion: reduce) ---")
        for k, v in rm_result.items():
            print(f"  {k}: {v}")
        print()
        print(f"Screenshots: audit-J-focus.png, audit-J-reduced-motion.png")
        print(f"JSON: audit-J-a11y.json")
        print("=" * 78)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
