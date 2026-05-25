"""
AUDIT READ-ONLY — Lisibilité boutons upgrade
Évalue : cost, level, progress bar, nom, desc, état affordable
"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

URL = "http://localhost:8770/index.html"
OUT_DIR = "D:/alchimia/screenshots/qa-vague10"

UPGRADES = [
    "tapValue", "critChance", "lapBonus", "autoTap",
    "endurance", "baseSpeed", "eagleEye", "cruiseControl",
]


def log(*a):
    print(*a, flush=True)


async def main():
    async with async_playwright() as p:
        log("[1] launching chromium")
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
        page.on("pageerror", lambda e: log(f"[PAGEERR] {e}"))

        log("[2] goto")
        await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1200)

        log("[3] force state + close blocking modals + give some levels")
        await page.evaluate("""
            () => {
                if (window.STATE) {
                    STATE.lapsRun = 30;
                    STATE.gold = 100000;
                    STATE.dailyLast = Date.now(); // marque comme déjà claim
                    // Donne quelques niveaux pour voir la barre de progression
                    STATE.upgradeTapValue   = 8;   // bar = 8/30 = 27%
                    STATE.upgradeCritChance = 12;  // bar = 12/55 = 22%
                    STATE.upgradeLapBonus   = 5;   // bar = 5/30 = 17%
                    STATE.upgradeAutoTap    = 3;   // bar = 3/30 = 10%
                    STATE.upgradeEndurance  = 10;  // bar = 10/20 = 50%
                    STATE.upgradeBaseSpeed  = 6;   // bar = 6/15 = 40%
                    STATE.upgradeEagleEye   = 9;   // bar = 9/15 = 60%
                    STATE.upgradeCruiseControl = 2; // bar = 2/15 = 13%
                }
                // Ferme TOUS les modals (.show)
                document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
                document.querySelectorAll('.modal').forEach(m => { m.style.display = 'none'; });
            }
        """)
        await page.wait_for_timeout(200)

        log("[4a] click PRENDRE LE DÉPART pour bypass intro")
        try:
            await page.evaluate("""
                () => {
                    // Hide intro overlay (élément block)
                    const intro = document.getElementById('intro');
                    if (intro) intro.style.display = 'none';
                    // Hide other splash-like overlays
                    document.querySelectorAll('#story, .story-overlay, .opening-overlay, #opening').forEach(el => { el.style.display = 'none'; });
                    // Click le bouton pour bind les states
                    const startBtn = document.getElementById('start-btn');
                    if (startBtn) startBtn.click();
                }
            """)
        except Exception as e:
            log(f"  [WARN] start click: {e}")
        await page.wait_for_timeout(800)

        log("[4b] open drawer + upgrades pane")
        await page.evaluate("""
            () => {
                // Re-ferme tout modal qui aurait pu repop
                document.querySelectorAll('.modal').forEach(m => { m.style.display = 'none'; m.classList.remove('show'); });
                document.querySelectorAll('#intro, #story, .opening-overlay').forEach(el => { el.style.display = 'none'; });
                const tc = document.querySelector('.tabs-content');
                if (tc) tc.classList.add('open');
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                const pane = document.querySelector('.tab-pane[data-pane="upgrades"]');
                if (pane) pane.classList.add('active');
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                const tabBtn = document.querySelector('.tab-btn[data-tab="upgrades"]');
                if (tabBtn) tabBtn.classList.add('active');
            }
        """)
        await page.wait_for_timeout(500)

        log("[5] refresh upgrades UI")
        await page.evaluate("""
            () => {
                if (typeof updateUpgradesUI === 'function') try { updateUpgradesUI(); } catch(e){}
                if (typeof refreshUpgrades === 'function') try { refreshUpgrades(); } catch(e){}
            }
        """)
        await page.wait_for_timeout(300)

        log("[6] full-page screenshot (drawer area)")
        await page.screenshot(path=f"{OUT_DIR}/audit-E-drawer-full.png", full_page=False)

        log("[7] eval per-upgrade data (one shot)")
        results = await page.evaluate("""
            (ids) => {
                const out = [];
                for (const uid of ids) {
                    const btn = document.querySelector(`.upg-btn[data-upgrade="${uid}"]`);
                    if (!btn) { out.push({id: uid, found: false}); continue; }
                    const rect = btn.getBoundingClientRect();
                    const cs = getComputedStyle(btn);
                    const nameEl = btn.querySelector('.upg-name');
                    const descEl = btn.querySelector('.upg-desc');
                    const lvlEl = btn.querySelector('.upg-lvl');
                    const costEl = btn.querySelector('.upg-cost');
                    const barFill = btn.querySelector('.upg-bar-fill');
                    const barCont = btn.querySelector('.upg-bar');
                    const csName = nameEl ? getComputedStyle(nameEl) : null;
                    const csDesc = descEl ? getComputedStyle(descEl) : null;
                    const csLvl  = lvlEl  ? getComputedStyle(lvlEl)  : null;
                    const csCost = costEl ? getComputedStyle(costEl) : null;
                    const csBarF = barFill ? getComputedStyle(barFill) : null;
                    const csBarC = barCont ? getComputedStyle(barCont) : null;
                    const barRectF = barFill ? barFill.getBoundingClientRect() : null;
                    const barRectC = barCont ? barCont.getBoundingClientRect() : null;
                    let pctFill = null;
                    if (barRectF && barRectC && barRectC.width > 0) {
                        pctFill = Math.round((barRectF.width / barRectC.width) * 1000) / 10;
                    }
                    out.push({
                        id: uid,
                        found: true,
                        rect: {w: Math.round(rect.width), h: Math.round(rect.height), x: Math.round(rect.x), y: Math.round(rect.y)},
                        visible: rect.width > 0 && rect.height > 0,
                        locked: btn.classList.contains('locked'),
                        affordable: btn.classList.contains('affordable'),
                        opacity: cs.opacity,
                        cursor: cs.cursor,
                        filter: cs.filter,
                        name: {
                            text: nameEl ? nameEl.textContent.trim() : null,
                            fontSize: csName ? csName.fontSize : null,
                            fontWeight: csName ? csName.fontWeight : null,
                            color: csName ? csName.color : null,
                            textTransform: csName ? csName.textTransform : null,
                        },
                        desc: {
                            text: descEl ? descEl.textContent.trim() : null,
                            fontSize: csDesc ? csDesc.fontSize : null,
                            color: csDesc ? csDesc.color : null,
                        },
                        lvl: {
                            text: lvlEl ? lvlEl.textContent.trim() : null,
                            fontSize: csLvl ? csLvl.fontSize : null,
                            fontWeight: csLvl ? csLvl.fontWeight : null,
                            color: csLvl ? csLvl.color : null,
                            bg: csLvl ? csLvl.backgroundColor : null,
                        },
                        cost: {
                            text: costEl ? costEl.textContent.trim() : null,
                            fontSize: csCost ? csCost.fontSize : null,
                            fontWeight: csCost ? csCost.fontWeight : null,
                            color: csCost ? csCost.color : null,
                            bg: csCost ? csCost.backgroundColor : null,
                        },
                        bar: {
                            barContainerW: barRectC ? Math.round(barRectC.width) : null,
                            barContainerH: barRectC ? Math.round(barRectC.height) : null,
                            barFillW: barRectF ? Math.round(barRectF.width) : null,
                            pctFill,
                            fillBg: csBarF ? (csBarF.background || '').substring(0, 80) : null,
                            contBg: csBarC ? csBarC.backgroundColor : null,
                        },
                    });
                }
                return out;
            }
        """, UPGRADES)
        log(f"[7] got {len(results)} entries")

        # State dump
        log("[8] dump state")
        state_dump = await page.evaluate("""
            () => {
                const out = {
                    gold: window.STATE ? STATE.gold : null,
                    lapsRun: window.STATE ? STATE.lapsRun : null,
                };
                try {
                    if (window.UPGRADES_TAP) {
                        out.upgradesDef = {};
                        for (const k of Object.keys(window.UPGRADES_TAP)) {
                            const u = window.UPGRADES_TAP[k];
                            const stateKey = u.state;
                            out.upgradesDef[k] = {
                                level: STATE[stateKey] || 0,
                                maxLevel: u.maxLevel || null,
                                base: u.base, factor: u.factor,
                                cost: (typeof upgradeCost === 'function') ? upgradeCost(k) : null,
                            };
                        }
                    }
                } catch (e) { out.error = String(e); }
                return out;
            }
        """)

        # Per-upgrade clip screenshots using rect data
        log("[9] take clip screenshots per upgrade")
        for r in results:
            if not r.get("found") or not r.get("visible"):
                continue
            rect = r["rect"]
            # clamp to viewport
            x = max(0, rect["x"])
            y = max(0, rect["y"])
            w = max(10, min(540 - x, rect["w"]))
            h = max(10, min(960 - y, rect["h"]))
            try:
                await page.screenshot(
                    path=f"{OUT_DIR}/audit-E-{r['id']}.png",
                    clip={"x": x, "y": y, "width": w, "height": h},
                )
            except Exception as e:
                log(f"  [WARN] clip {r['id']}: {e}")

        log("[10] write JSON")
        full_data = {"state": state_dump, "results": results}
        with open(f"{OUT_DIR}/audit-E-readability.json", "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=2, ensure_ascii=False)

        log("=" * 72)
        log(f"STATE: gold={state_dump.get('gold')} lapsRun={state_dump.get('lapsRun')}")
        log("-" * 72)
        for r in results:
            if not r.get("found"):
                log(f"  {r.get('id')}: NOT FOUND")
                continue
            flags = []
            if r["locked"]: flags.append("LOCK")
            if r["affordable"]: flags.append("AFFORD")
            try:
                if float(r["opacity"]) < 1.0: flags.append(f"op={r['opacity']}")
            except Exception:
                pass
            cost = r["cost"]; lvl = r["lvl"]; bar = r["bar"]
            log(
                f"  [{r['id']:14s}] {r['name']['text']:24s} "
                f"name={r['name']['fontSize']}/{r['name']['fontWeight']} "
                f"lvl='{lvl['text']}' ({lvl['fontSize']}) "
                f"cost='{cost['text']}' ({cost['fontSize']}) "
                f"bar={bar['pctFill']}% "
                f"[{' '.join(flags)}]"
            )
        log("=" * 72)
        log(f"Files: {OUT_DIR}/audit-E-*.png + audit-E-readability.json")
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log(f"FATAL: {e}")
        sys.exit(1)
