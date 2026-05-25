"""
QA Vague 24 - D1 First 5 min (READ-ONLY).
Simule un VRAI nouveau joueur : localStorage CLEAR, aucun guide.
Capture toutes les 30s pendant 5 min, simule un tap toutes les 2s.
Snapshot STATE + comptage modales + detection moments "vides".
"""
import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
OUT = Path(r"D:/alchimia/screenshots/qa-vague24")
OUT.mkdir(parents=True, exist_ok=True)

TOTAL_DURATION_S = 300   # 5 minutes
TAP_INTERVAL_S   = 2.0   # 1 tap toutes les 2s = "joueur calme"
SNAPSHOT_EVERY_S = 30    # screenshot + STATE snapshot

page_errors = []
console_errors = []
modal_open_events = []   # liste {t_s, kind, id, classes}
empty_moments    = []    # liste {t_s, reason}


async def safe_eval(page, expr):
    try:
        return await page.evaluate(expr)
    except Exception as e:
        return {"_evalError": str(e)}


async def click_xy(page, x, y):
    """Synthetic tap au centre de la zone de jeu (canvas)."""
    try:
        await page.mouse.click(x, y)
    except Exception:
        pass


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=1,
        )

        # VRAI fresh : on EFFACE tout localStorage avant et apres goto
        await ctx.add_init_script("""
            try {
                localStorage.clear();
                sessionStorage.clear();
                if (window.indexedDB && indexedDB.databases) {
                    indexedDB.databases().then(dbs => {
                        for (const d of dbs) {
                            try { indexedDB.deleteDatabase(d.name); } catch(e){}
                        }
                    });
                }
            } catch(e) {}
        """)

        page = await ctx.new_page()

        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)
        # double-clear apres lecture eventuelle d'un save serveur
        await page.evaluate("try{localStorage.clear();sessionStorage.clear();}catch(e){}")
        await page.wait_for_timeout(200)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        # Snapshot AVANT toute interaction = "0s splash"
        await page.screenshot(path=str(OUT / "t000-splash.png"))

        splash_state = await safe_eval(page, """
            () => ({
                hasStartBtn: !!document.querySelector('#start-btn'),
                startBtnVisible: !!(document.querySelector('#start-btn') && document.querySelector('#start-btn').offsetParent !== null),
                bodyClass: document.body.className,
                visibleModals: Array.from(document.querySelectorAll('.modal.show, .modal-show, .overlay.show'))
                    .map(m => ({id: m.id, cls: m.className})),
                introVisible: !!(document.querySelector('#intro, #splash, .splash') &&
                                 document.querySelector('#intro, #splash, .splash').offsetParent !== null),
                STATE_present: typeof window.STATE !== 'undefined',
                gold: window.STATE && window.STATE.gold,
                taps: window.STATE && window.STATE.totalTaps,
                lapsRun: window.STATE && window.STATE.lapsRun,
            })
        """)

        # === Hook MutationObserver : compte les modal.show / popups ===
        await page.evaluate("""
            window.__modalLog = [];
            const startT = performance.now();
            const obs = new MutationObserver(muts => {
                for (const m of muts) {
                    if (m.type !== 'attributes') continue;
                    const el = m.target;
                    if (!(el instanceof HTMLElement)) continue;
                    const wasShow = (m.oldValue || '').includes('show');
                    const isShow  = el.classList.contains('show');
                    if (!wasShow && isShow) {
                        window.__modalLog.push({
                            t: (performance.now() - startT)/1000,
                            id: el.id || '',
                            cls: el.className || '',
                            tag: el.tagName,
                        });
                    }
                }
            });
            obs.observe(document.body, {
                subtree: true,
                attributes: true,
                attributeOldValue: true,
                attributeFilter: ['class'],
            });
            // log popup-queue items aussi (popups en bas)
            window.__popupCount = 0;
            const obs2 = new MutationObserver(muts => {
                for (const m of muts) {
                    for (const n of m.addedNodes) {
                        if (n.nodeType === 1) {
                            const c = (n.className || '');
                            if (typeof c === 'string' && (c.includes('popup') || c.includes('toast') || c.includes('notif'))) {
                                window.__popupCount++;
                            }
                        }
                    }
                }
            });
            obs2.observe(document.body, { childList: true, subtree: true });
        """)

        # === Cliquer PRENDRE LE DEPART si visible ===
        clicked_start = await page.evaluate("""
            () => {
                const btn = document.querySelector('#start-btn');
                if (btn && btn.offsetParent !== null) { btn.click(); return true; }
                return false;
            }
        """)
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUT / "t001-after-start.png"))

        # === Detecter le centre de la zone de tap ===
        tap_target = await page.evaluate("""
            () => {
                // Priorite : #tap-area > canvas plein ecran > body center
                const el = document.querySelector('#tap-area') ||
                           document.querySelector('canvas') ||
                           document.body;
                const r = el.getBoundingClientRect();
                return {
                    x: r.left + r.width/2,
                    y: r.top  + r.height/2,
                    found: el.id || el.tagName,
                };
            }
        """)

        snapshots = []
        t_start = time.time()
        last_snap = -1
        last_state_for_idle = None
        last_state_change_t = 0

        # Pour log "moment vide" : on regarde si gold/taps/laps bougent
        async def take_snapshot(t_s):
            await page.screenshot(path=str(OUT / f"t{int(t_s):03d}-tick.png"))
            st = await safe_eval(page, """
                () => {
                    const ST = window.STATE || {};
                    const visibleModals = Array.from(document.querySelectorAll('.modal.show, .modal-show'))
                        .filter(m => m.offsetParent !== null)
                        .map(m => ({id: m.id, cls: (m.className||'').slice(0,80)}));
                    // Tutorial / hint visible ?
                    const tutoHint = document.querySelector('#tuto-hint');
                    const tutoVisible = !!(tutoHint && tutoHint.offsetParent !== null && (tutoHint.textContent||'').trim());
                    // Skill ready ?
                    const skillBtns = Array.from(document.querySelectorAll('#skills-bar button, .skill-btn'))
                        .filter(b => b.offsetParent !== null);
                    const skillsReady = skillBtns.filter(b => !b.disabled && !b.classList.contains('cooldown') && !b.classList.contains('locked')).length;
                    // Coffre ?
                    const chestBtn = document.querySelector('[data-action="chests"], .chest-btn, #chest-btn');
                    const chestVisible = !!(chestBtn && chestBtn.offsetParent !== null);
                    // Upgrade tab badge "affordable"
                    const upgBadge = document.querySelector('#tab-upg-affordable');
                    const upgAffordable = upgBadge ? (upgBadge.textContent||'').trim() : '';
                    // Gold visible HUD ?
                    const goldEl = document.querySelector('#gold-val, #hud-gold-val, .gold-val');
                    const goldText = goldEl ? (goldEl.textContent||'').trim() : '';
                    // KM visible HUD ?
                    const kmEl = document.querySelector('#hud-km-val, #km-val, .km-val');
                    const kmText = kmEl ? (kmEl.textContent||'').trim() : '';
                    return {
                        gold: ST.gold || 0,
                        totalTaps: ST.totalTaps || 0,
                        lapsRun: ST.lapsRun || 0,
                        lapProgress: ST.lapProgress || 0,
                        stamina: ST.stamina,
                        upgrades: ST.upgrades ? Object.keys(ST.upgrades).length : 0,
                        upgradeAffordable: upgAffordable,
                        skillsReady: skillsReady,
                        skillsTotal: skillBtns.length,
                        chestVisible: chestVisible,
                        tutoVisible: tutoVisible,
                        tutoMsg: tutoVisible ? (document.querySelector('#tuto-msg')||{}).textContent : '',
                        visibleModals: visibleModals,
                        goldHudText: goldText,
                        kmHudText: kmText,
                        modalLogLen: (window.__modalLog||[]).length,
                        popupCount: window.__popupCount || 0,
                    };
                }
            """)
            st["_t"] = t_s
            snapshots.append(st)
            return st

        # initial snapshot a t=2s post-start
        s0 = await take_snapshot(0)

        # Boucle 5 minutes
        next_snap_at = SNAPSHOT_EVERY_S
        next_tap_at  = TAP_INTERVAL_S
        last_taps = s0.get("totalTaps", 0)
        last_gold = s0.get("gold", 0)
        last_laps = s0.get("lapsRun", 0)
        idle_start = None

        while True:
            elapsed = time.time() - t_start
            if elapsed >= TOTAL_DURATION_S:
                break

            # TAP simule
            if elapsed >= next_tap_at:
                await click_xy(page, tap_target["x"], tap_target["y"])
                next_tap_at += TAP_INTERVAL_S

            # SNAPSHOT
            if elapsed >= next_snap_at:
                st = await take_snapshot(int(next_snap_at))
                # Detecter idle : si gold n'a pas bouge depuis >10s (et taps non plus)
                if (st["gold"] == last_gold and st["totalTaps"] == last_taps and st["lapsRun"] == last_laps):
                    empty_moments.append({
                        "t_s": int(next_snap_at),
                        "gold": st["gold"],
                        "taps": st["totalTaps"],
                        "laps": st["lapsRun"],
                        "reason": "state-unchanged-30s",
                    })
                last_gold = st["gold"]
                last_taps = st["totalTaps"]
                last_laps = st["lapsRun"]
                next_snap_at += SNAPSHOT_EVERY_S

            await asyncio.sleep(0.25)

        # Final dump
        modal_log = await page.evaluate("() => window.__modalLog || []")
        popup_count = await page.evaluate("() => window.__popupCount || 0")
        final_state = await safe_eval(page, """
            () => {
                const ST = window.STATE || {};
                return {
                    gold: ST.gold,
                    totalTaps: ST.totalTaps,
                    lapsRun: ST.lapsRun,
                    totalPlayMs: ST.totalPlayMs,
                    upgrades: ST.upgrades ? Object.entries(ST.upgrades).map(([k,v]) => `${k}:${v}`) : [],
                    achievements: ST.achievements ? Object.keys(ST.achievements).length : 0,
                };
            }
        """)
        await page.screenshot(path=str(OUT / "t300-final.png"))

        # === Analyse moments cle ===
        # 1er tap : trouve dans snapshots quand totalTaps passe de 0 a >0
        first_tap_t = None
        first_gold_t = None
        first_upgrade_t = None
        first_km_t = None
        first_modal_unprompted_t = None
        for s in snapshots:
            if first_tap_t is None and s.get("totalTaps", 0) > 0:
                first_tap_t = s["_t"]
            if first_gold_t is None and s.get("gold", 0) > 0:
                first_gold_t = s["_t"]
            if first_upgrade_t is None and s.get("upgrades", 0) > 0:
                first_upgrade_t = s["_t"]
            if first_km_t is None and s.get("lapsRun", 0) >= 1:
                first_km_t = s["_t"]

        # Modales spontanees (ouvertes sans clic explicite joueur) : on regarde les classes inhabituelles
        spontaneous_modals = [m for m in modal_log if m["t"] > 5 and not m["cls"].startswith("tab-")]

        report = {
            "url": URL,
            "viewport": "540x960",
            "duration_s": TOTAL_DURATION_S,
            "tap_interval_s": TAP_INTERVAL_S,
            "splash_state": splash_state,
            "clicked_start_btn": clicked_start,
            "tap_target": tap_target,
            "page_errors": page_errors,
            "console_errors_total": len(console_errors),
            "snapshots": snapshots,
            "empty_moments": empty_moments,
            "modal_open_events_total": len(modal_log),
            "modal_open_events_sample": modal_log[:30],
            "spontaneous_modals_after_5s": spontaneous_modals[:20],
            "popup_count": popup_count,
            "final_state": final_state,
            "key_moments": {
                "first_tap_t": first_tap_t,
                "first_gold_t": first_gold_t,
                "first_upgrade_t": first_upgrade_t,
                "first_km_t": first_km_t,
            },
        }
        (OUT / "D1-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        # === Pretty print resume ===
        print("=" * 70)
        print("QA VAGUE 24 - D1 FIRST 5 MIN")
        print("=" * 70)
        print(f"Splash visible:    {splash_state.get('introVisible')}")
        print(f"start-btn clicked: {clicked_start}")
        print(f"Tap target:        {tap_target.get('found')} @ ({tap_target['x']:.0f},{tap_target['y']:.0f})")
        print(f"Page errors:       {len(page_errors)}")
        print(f"Console errors:    {len(console_errors)}")
        print(f"Total modal.show:  {len(modal_log)}")
        print(f"Spontaneous modals (after 5s, non-tab): {len(spontaneous_modals)}")
        print(f"Popup events:      {popup_count}")
        print("--- Key moments ---")
        print(f"  first_tap_t     : {first_tap_t}s")
        print(f"  first_gold_t    : {first_gold_t}s")
        print(f"  first_upgrade_t : {first_upgrade_t}s")
        print(f"  first_km_t      : {first_km_t}s")
        print(f"Empty moments:     {len(empty_moments)}")
        for em in empty_moments:
            print(f"  t={em['t_s']}s : taps={em['taps']} gold={em['gold']} laps={em['laps']}")
        print("--- Snapshot timeline ---")
        for s in snapshots:
            print(f"  t={s['_t']:3d}s | gold={s['gold']:>6} taps={s['totalTaps']:>4} km={s['lapsRun']:>3} "
                  f"upg={s['upgrades']} skillsRdy={s['skillsReady']}/{s['skillsTotal']} "
                  f"chest={'Y' if s['chestVisible'] else '.'} tuto={'Y' if s['tutoVisible'] else '.'} "
                  f"goldHUD='{(s.get('goldHudText') or '')[:8]}' kmHUD='{(s.get('kmHudText') or '')[:6]}'")
        print(f"--- Final ---")
        print(f"  gold={final_state.get('gold')} taps={final_state.get('totalTaps')} laps={final_state.get('lapsRun')}")
        print(f"  upgrades: {final_state.get('upgrades')}")
        print(f"  achievements: {final_state.get('achievements')}")
        print("--- Spontaneous modal samples ---")
        for m in spontaneous_modals[:10]:
            print(f"  t={m['t']:.1f}s id={m['id']} cls={m['cls'][:70]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
