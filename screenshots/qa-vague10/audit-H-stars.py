"""
AUDIT READ-ONLY — Star Tree Prestige modal (vague 16bis D — openStarTree)
Évalue : visibilité bouton PRESTIGE, ouverture modale, design mobile,
         affichage 8 nodes, compteur étoiles, buttons buy refresh après achat,
         visuel "tree" vs liste.
"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

# Force UTF-8 stdout on Windows so we can print ⭐ etc.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

URL = "http://localhost:8770/index.html"
OUT_DIR = "D:/alchimia/screenshots/qa-vague10"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
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
        page.on("console", lambda msg: msg.type == "error" and print(f"[CONSOLE-ERR] {msg.text}"))

        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(800)

        # Force state : km 100+, 20 étoiles, 1 ascension (pour debloquer PRESTIGE)
        await page.evaluate("""
            () => {
                if (window.STATE) {
                    STATE.lapsRun = 100;
                    STATE.stars = 20;
                    STATE.ascensions = 1;
                    if (!STATE.starTree) STATE.starTree = {};
                    // Re-evaluate menu unlocks (data-unlock-km)
                    if (typeof refreshMenuUnlocks === 'function') try { refreshMenuUnlocks(); } catch(e){}
                    if (typeof updateMenuUnlocks === 'function') try { updateMenuUnlocks(); } catch(e){}
                    if (typeof refreshUnlocks === 'function') try { refreshUnlocks(); } catch(e){}
                    if (typeof refreshHUD === 'function') try { refreshHUD(); } catch(e){}
                    // Force unlock via direct DOM scan (fallback)
                    document.querySelectorAll('[data-unlock-km]').forEach(el => {
                        const needKm = parseInt(el.getAttribute('data-unlock-km') || '0', 10);
                        if (STATE.lapsRun >= needKm) {
                            el.classList.remove('locked', 'menu-locked');
                            el.removeAttribute('data-locked');
                            el.style.display = '';
                            el.style.opacity = '';
                            el.style.pointerEvents = '';
                        }
                    });
                }
            }
        """)
        await page.wait_for_timeout(300)

        # 1) Open burger menu
        await page.evaluate("""
            () => {
                const t = document.getElementById('menu-toggle');
                if (t) t.click();
            }
        """)
        await page.wait_for_timeout(500)

        # Screenshot menu (avec bouton PRESTIGE visible)
        await page.screenshot(path=f"{OUT_DIR}/audit-H-menu-prestige.png")

        # Inspect PRESTIGE button visibility
        prestige_info = await page.evaluate("""
            () => {
                const btn = document.querySelector('.menu-item[data-action="prestige"]');
                if (!btn) return { found: false };
                const rect = btn.getBoundingClientRect();
                const cs = getComputedStyle(btn);
                return {
                    found: true,
                    rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
                    visible: rect.width > 0 && rect.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0.1,
                    display: cs.display,
                    visibility: cs.visibility,
                    opacity: cs.opacity,
                    pointerEvents: cs.pointerEvents,
                    classes: btn.className,
                    locked: btn.classList.contains('locked') || btn.classList.contains('menu-locked') || btn.dataset.locked === '1',
                    unlockKm: btn.getAttribute('data-unlock-km'),
                    title: btn.querySelector('.mi-title')?.textContent?.trim(),
                    sub: btn.querySelector('.mi-sub')?.textContent?.trim(),
                };
            }
        """)
        print("=" * 72)
        print(f"PRESTIGE BUTTON: {json.dumps(prestige_info, indent=2, ensure_ascii=False)}")

        # 2) Click PRESTIGE via the menu (open star tree)
        opened = await page.evaluate("""
            () => {
                const btn = document.querySelector('.menu-item[data-action="prestige"]');
                if (!btn) return { ok: false, reason: 'btn not found' };
                btn.click();
                return { ok: true };
            }
        """)
        print(f"Click PRESTIGE result: {opened}")
        await page.wait_for_timeout(500)

        # Force open if click didn't propagate
        await page.evaluate("""
            () => { if (typeof openStarTree === 'function') openStarTree(); }
        """)
        await page.wait_for_timeout(400)

        # Screenshot modale ouverte
        await page.screenshot(path=f"{OUT_DIR}/audit-H-star-tree.png")

        # Inspect modal + nodes
        modal_info = await page.evaluate("""
            () => {
                const m = document.getElementById('star-tree-modal');
                if (!m) return { found: false };
                const rect = m.getBoundingClientRect();
                const cs = getComputedStyle(m);
                const card = m.querySelector('.modal-card');
                const cardRect = card ? card.getBoundingClientRect() : null;
                const cardCs = card ? getComputedStyle(card) : null;
                const isOpen = m.classList.contains('show') || cs.display !== 'none';
                const avail = document.getElementById('star-tree-avail');
                const availCs = avail ? getComputedStyle(avail) : null;
                const list = document.getElementById('star-tree-list');
                const nodes = list ? Array.from(list.children).map(node => {
                    const btn = node.querySelector('.star-buy-btn');
                    const nameDiv = node.querySelector('div > div:nth-child(1) > div:nth-child(1)');
                    const descDiv = node.querySelector('div > div:nth-child(1) > div:nth-child(2)');
                    const lvlDiv = node.querySelector('div > div:nth-child(1) > div:nth-child(3)');
                    const r = node.getBoundingClientRect();
                    return {
                        label: nameDiv?.textContent?.trim(),
                        desc: descDiv?.textContent?.trim(),
                        levelLine: lvlDiv?.textContent?.trim(),
                        btnText: btn?.textContent?.trim(),
                        btnDisabled: btn?.disabled === true,
                        btnDataNode: btn?.dataset?.node,
                        visible: r.width > 0 && r.height > 0,
                        h: Math.round(r.height),
                    };
                }) : [];
                return {
                    found: true,
                    isOpen,
                    modalDisplay: cs.display,
                    modalOpacity: cs.opacity,
                    modalClasses: m.className,
                    card: cardRect ? {
                        x: Math.round(cardRect.x), y: Math.round(cardRect.y),
                        w: Math.round(cardRect.width), h: Math.round(cardRect.height),
                        maxWidth: cardCs?.maxWidth, maxHeight: cardCs?.maxHeight,
                        overflowY: cardCs?.overflowY,
                    } : null,
                    avail: {
                        text: avail?.textContent?.trim(),
                        fontSize: availCs?.fontSize,
                        fontWeight: availCs?.fontWeight,
                        color: availCs?.color,
                    },
                    nodeCount: nodes.length,
                    nodes,
                    viewport: { w: window.innerWidth, h: window.innerHeight },
                };
            }
        """)
        print("-" * 72)
        print(f"MODAL: open={modal_info.get('isOpen')} display={modal_info.get('modalDisplay')}")
        print(f"  card: {modal_info.get('card')}")
        print(f"  avail: {modal_info.get('avail')}")
        print(f"  nodeCount: {modal_info.get('nodeCount')}")
        for i, n in enumerate(modal_info.get('nodes', [])):
            print(f"    [{i+1}] {n.get('label'):20s} | {n.get('levelLine'):12s} | {n.get('btnText'):8s} | disabled={n.get('btnDisabled')} | h={n.get('h')}")

        # 3) Snapshot state BEFORE buy
        before = await page.evaluate("""
            () => ({
                stars: window.STATE?.stars,
                starTree: JSON.parse(JSON.stringify(window.STATE?.starTree || {})),
            })
        """)
        print("-" * 72)
        print(f"BEFORE BUY: stars={before.get('stars')} starTree={before.get('starTree')}")

        # 4) Click first available buy btn
        click_res = await page.evaluate("""
            () => {
                const btn = document.querySelector('.star-buy-btn:not([disabled])');
                if (!btn) return { ok: false, reason: 'no enabled buy btn' };
                const node = btn.dataset.node;
                const txt = btn.textContent.trim();
                btn.click();
                return { ok: true, node, txt };
            }
        """)
        print(f"BUY click: {click_res}")
        await page.wait_for_timeout(400)

        # Screenshot après achat
        await page.screenshot(path=f"{OUT_DIR}/audit-H-after-buy.png")

        # 5) Snapshot state AFTER buy + new btn text
        after = await page.evaluate("""
            (data) => {
                const node = data.node;
                let newBtnTxt = null;
                let newBtnDisabled = null;
                if (node) {
                    const btn = document.querySelector(`.star-buy-btn[data-node="${node}"]`);
                    if (btn) {
                        newBtnTxt = btn.textContent.trim();
                        newBtnDisabled = btn.disabled === true;
                    }
                }
                return {
                    stars: window.STATE?.stars,
                    starTree: JSON.parse(JSON.stringify(window.STATE?.starTree || {})),
                    newBtnTxt,
                    newBtnDisabled,
                };
            }
        """, click_res)
        print(f"AFTER BUY: stars={after.get('stars')} starTree={after.get('starTree')}")
        print(f"  Refresh btn '{click_res.get('node')}': '{click_res.get('txt')}' -> '{after.get('newBtnTxt')}' (disabled={after.get('newBtnDisabled')})")

        # Sanity: state changed?
        stars_dropped = (before.get('stars') or 0) > (after.get('stars') or 0)
        node_incremented = False
        if click_res.get('ok'):
            n = click_res.get('node')
            before_lvl = (before.get('starTree') or {}).get(n, 0)
            after_lvl = (after.get('starTree') or {}).get(n, 0)
            node_incremented = after_lvl > before_lvl
        print(f"VALID: stars_dropped={stars_dropped} node_incremented={node_incremented}")

        # 6) Look for tree-style visuals (branches, lines, svg connectors)
        visual_check = await page.evaluate("""
            () => {
                const m = document.getElementById('star-tree-modal');
                if (!m) return null;
                const svgs = m.querySelectorAll('svg');
                const lines = m.querySelectorAll('line, path');
                const cards = m.querySelectorAll('#star-tree-list > *');
                // sample backgrounds
                const cardBgs = Array.from(cards).slice(0, 3).map(c => getComputedStyle(c).background.substring(0, 100));
                return {
                    nbSvgs: svgs.length,
                    nbLines: lines.length,
                    nbCards: cards.length,
                    cardSampleBgs: cardBgs,
                    listLayout: m.querySelector('#star-tree-list')?.style?.cssText || '',
                };
            }
        """)
        print(f"VISUAL: {json.dumps(visual_check, indent=2, ensure_ascii=False)}")

        # Save full findings
        full = {
            "prestige_button": prestige_info,
            "modal": modal_info,
            "before": before,
            "click": click_res,
            "after": after,
            "valid": {"stars_dropped": stars_dropped, "node_incremented": node_incremented},
            "visual": visual_check,
        }
        with open(f"{OUT_DIR}/audit-H-stars.json", "w", encoding="utf-8") as f:
            json.dump(full, f, indent=2, ensure_ascii=False)

        print("=" * 72)
        print(f"Screenshots: {OUT_DIR}/audit-H-*.png")
        print(f"JSON: {OUT_DIR}/audit-H-stars.json")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
