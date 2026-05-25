"""
QA Vague 10 — Deep bug hunt (suite à qa-bugs.py qui sort 0/0/0 trop clean).
Réutilise la même grille mais :
- Ne short-circuite PAS le splash (laisse-le faire son taf)
- Tape RÉELLEMENT sur le stadium pour exercer le pipeline complet
- Sonde window.RUNNER_2D.npcs (le vrai tableau exposé)
- Check fps live pendant le jeu réel
- Probe les modals via openX() function calls (force pop-up tests)
- Compare le rendu canvas pixel-checksum entre paliers (catch frozen render)
"""
import json, time, hashlib, base64
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"

PALIERS = [1, 5, 12, 30, 50, 75, 99, 100, 105]

def screenshot(page, name):
    p = OUT / f"{name}.png"
    try:
        page.screenshot(path=str(p), full_page=False)
        return p.name
    except Exception as e:
        return f"err: {e}"

def hash_canvas(page):
    """Récupère un hash du contenu canvas (catch frozen / black screen)."""
    return page.evaluate("""() => {
        const cv = document.getElementById('runner-canvas');
        if(!cv) return null;
        try {
            const data = cv.toDataURL('image/png');
            // hash léger (length + 64 derniers chars suffisent à détecter frozen)
            return {
                len: data.length,
                tail: data.slice(-64),
                size: cv.width + 'x' + cv.height,
            };
        } catch(e){ return 'err:'+e.message; }
    }""")

def force_taps(page, count=30, interval_ms=70):
    """Tape vraiment sur le stadium pour exercer le pipeline."""
    page.evaluate(f"""async () => {{
        const stadium = document.getElementById('runner-stadium');
        if(!stadium) return;
        const rect = stadium.getBoundingClientRect();
        const cx = rect.left + rect.width/2;
        const cy = rect.top + rect.height/2;
        for(let i=0; i<{count}; i++){{
            const ev = new PointerEvent('pointerdown', {{bubbles:true, cancelable:true, clientX:cx, clientY:cy, pointerType:'touch'}});
            stadium.dispatchEvent(ev);
            await new Promise(r => setTimeout(r, {interval_ms}));
        }}
    }}""")

def get_npc_count(page):
    return page.evaluate("""() => {
        try {
            if(window.RUNNER_2D && Array.isArray(window.RUNNER_2D.npcs)){
                return window.RUNNER_2D.npcs.length;
            }
            return null;
        } catch(e){ return 'err:'+e.message; }
    }""")

def get_npc_detail(page):
    return page.evaluate("""() => {
        try {
            if(!window.RUNNER_2D || !Array.isArray(window.RUNNER_2D.npcs)) return null;
            const ns = window.RUNNER_2D.npcs;
            return {
                count: ns.length,
                lanes: ns.map(n => n.laneIdx),
                meters: ns.map(n => Math.round(n.metersAhead*10)/10),
                tiers: ns.map(n => n.tier),
            };
        } catch(e){ return 'err:'+e.message; }
    }""")

def fps_sample(page, duration_ms=2000):
    return page.evaluate(f"""() => new Promise(r => {{
        let frames = 0;
        const t0 = performance.now();
        function step(){{
            frames++;
            if(performance.now() - t0 < {duration_ms}){{
                requestAnimationFrame(step);
            }} else {{
                const e = (performance.now() - t0)/1000;
                r({{fps: +(frames/e).toFixed(1), frames, elapsed: +e.toFixed(2)}});
            }}
        }}
        requestAnimationFrame(step);
    }})""")

def scan_undefined(page):
    return page.evaluate("""() => {
        const flagged = [];
        for(const el of document.querySelectorAll('body *')){
            if(!el.children.length){
                const t = (el.textContent || '').trim();
                if(t === 'undefined' || t === 'NaN' || /^undefined$/.test(t) || t.includes('undefined')){
                    flagged.push({
                        tag: el.tagName,
                        cls: (el.className||'').toString().slice(0,80),
                        id: el.id || null,
                        text: t.slice(0, 100),
                    });
                }
            }
        }
        return flagged.slice(0, 30);
    }""")

def scan_offscreen(page):
    """Plus large scan : visible elements with right<0 or left>vw."""
    return page.evaluate("""() => {
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const flagged = [];
        const tracked = ['button', 'a', '.btn', '.modal', '.topbar', '.drawer', '.hud',
                         '.tier-banner', '.popup', '#tuto-hint', '#tier-banner', '.modal-card'];
        for(const sel of tracked){
            document.querySelectorAll(sel).forEach(el => {
                const r = el.getBoundingClientRect();
                if(r.width === 0 || r.height === 0) return;
                const style = getComputedStyle(el);
                if(style.display === 'none' || style.visibility === 'hidden') return;
                const opacity = parseFloat(style.opacity || '1');
                if(opacity < 0.05) return;
                if(r.right < 1 || r.left > vw - 1){
                    flagged.push({
                        sel,
                        id: el.id || null,
                        cls: (el.className||'').toString().slice(0, 60),
                        left: Math.round(r.left), right: Math.round(r.right),
                        opacity: opacity.toFixed(2),
                    });
                }
            });
        }
        return {vw, vh, count: flagged.length, sample: flagged.slice(0, 8)};
    }""")

def main():
    report = {
        "pageerrors": [],
        "console_errors": [],
        "console_warnings": [],
        "console_logs": [],   # garder un comptage info
        "paliers": {},
        "npc_observation": [],
        "canvas_hashes": [],
        "pause_resume": {},
        "resize_tests": {},
        "modal_probes": {},
        "notes": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960},
                                  has_touch=True, is_mobile=True)
        page = ctx.new_page()

        def on_console(msg):
            try:
                t = msg.type
                txt = msg.text[:400]
                loc = msg.location.get('url','')[-60:] + ':' + str(msg.location.get('lineNumber',''))
                rec = {"type": t, "text": txt, "loc": loc}
                if t == "error":
                    report["console_errors"].append(rec)
                elif t in ("warning", "warn"):
                    report["console_warnings"].append(rec)
                elif t == "log":
                    if len(report["console_logs"]) < 50:
                        report["console_logs"].append(rec)
            except Exception:
                pass

        page.on("console", on_console)
        page.on("pageerror", lambda exc: report["pageerrors"].append(str(exc)[:400]))

        page.goto(URL, wait_until="domcontentloaded")
        # skip onboarding via localStorage avant reload
        page.evaluate("""() => {
            try {
                localStorage.setItem('foulee.tutoV2', 'done');
                localStorage.setItem('foulee.storySeen', '1');
                localStorage.setItem('foulee.gigaTutoSeen', '1');
                localStorage.setItem('foulee.lastSeenTier', '0');
                localStorage.setItem('foulee.onboardingDone', '1');
                localStorage.setItem('foulee.openingSeen', '1');
                localStorage.setItem('foulee.cinematicSeen', '1');
            } catch(e){}
        }""")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(5000)  # laisser le splash/cinématique finir

        # force-close intro/story overlays s'ils restent visibles
        page.evaluate("""() => {
            const ids = ['intro', 'story-intro', 'opening-credits', 'opening-overlay'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if(el){
                    el.classList.add('gone');
                    el.style.display = 'none';
                    el.style.pointerEvents = 'none';
                }
            });
            document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
        }""")
        page.wait_for_timeout(1500)

        screenshot(page, "deep-00-init")

        # === ITER paliers, avec vraie progression visuelle ===
        for km in PALIERS:
            tag = f"km{km:03d}"
            page.evaluate(f"""(km) => {{
                window.STATE.lapsRun = km;
                window.STATE.lapProgress = 0;
                if(typeof renderStats === 'function') renderStats();
                if(typeof updateRunnerHUD === 'function') updateRunnerHUD();
            }}""", km)
            # tap pour exercer le pipeline render + NPC spawn
            force_taps(page, count=15, interval_ms=70)
            page.wait_for_timeout(3000)

            stacked = page.evaluate("""() => {
                const open = Array.from(document.querySelectorAll('.modal.show'));
                return {count: open.length, ids: open.map(m => m.id || '?')};
            }""")
            overflow = page.evaluate("""() => {
                return {
                    horizontal: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
                    scrollW: document.documentElement.scrollWidth,
                    clientW: document.documentElement.clientWidth,
                };
            }""")
            undefs = scan_undefined(page)
            offscreen = scan_offscreen(page)
            canvas = hash_canvas(page)
            npc = get_npc_detail(page)
            fps = fps_sample(page, 1500)
            screenshot(page, f"deep-{tag}")

            report["paliers"][tag] = {
                "stacked_modals": stacked,
                "overflow_horizontal": overflow["horizontal"],
                "overflow_scrollW": overflow["scrollW"],
                "overflow_clientW": overflow["clientW"],
                "undefined_count": len(undefs),
                "undefined_sample": undefs[:3],
                "offscreen_count": offscreen["count"],
                "offscreen_sample": offscreen["sample"],
                "canvas_hash": canvas,
                "npc_count": npc["count"] if isinstance(npc, dict) else None,
                "npc_tiers": npc.get("tiers") if isinstance(npc, dict) else None,
                "fps": fps,
                "errors_total_so_far": len(report["pageerrors"]),
                "console_err_so_far": len(report["console_errors"]),
                "console_warn_so_far": len(report["console_warnings"]),
            }
            report["canvas_hashes"].append({"km": km, "hash": canvas})

        # === NPC observation soutenue (40s @ km 50) ===
        page.evaluate("""() => { window.STATE.lapsRun = 50; }""")
        force_taps(page, count=20, interval_ms=60)
        for i in range(20):
            c = get_npc_count(page)
            report["npc_observation"].append({"t_iter": i, "count": c})
            page.wait_for_timeout(2000)

        # === PAUSE/RESUME ===
        force_taps(page, count=8, interval_ms=60)
        pre = page.evaluate("""() => ({laps: window.STATE.lapsRun, prog: window.STATE.lapProgress, perf: performance.now()})""")
        canvas_before_pause = hash_canvas(page)
        page.evaluate("""() => {
            Object.defineProperty(document, 'hidden', {value: true, configurable: true});
            Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true});
            document.dispatchEvent(new Event('visibilitychange'));
        }""")
        page.wait_for_timeout(5000)
        page.evaluate("""() => {
            Object.defineProperty(document, 'hidden', {value: false, configurable: true});
            Object.defineProperty(document, 'visibilityState', {value: 'visible', configurable: true});
            document.dispatchEvent(new Event('visibilitychange'));
        }""")
        page.wait_for_timeout(1500)
        post = page.evaluate("""() => ({laps: window.STATE.lapsRun, prog: window.STATE.lapProgress, perf: performance.now()})""")
        canvas_after_pause = hash_canvas(page)
        fps_after = fps_sample(page, 1500)
        report["pause_resume"] = {
            "pre": pre, "post": post,
            "delta_laps": post["laps"] - pre["laps"],
            "delta_prog": round((post["prog"] or 0) - (pre["prog"] or 0), 4),
            "canvas_changed": (canvas_before_pause != canvas_after_pause) if (canvas_before_pause and canvas_after_pause) else None,
            "fps_after_resume": fps_after,
        }
        screenshot(page, "deep-pause-resume")

        # === RESIZE ===
        for (w, h, name) in [(320, 480, "320x480"), (1024, 768, "1024x768")]:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(1500)
            force_taps(page, count=5, interval_ms=80)
            page.wait_for_timeout(1500)
            screenshot(page, f"deep-resize-{name}")
            cv = page.evaluate("""() => {
                const c = document.getElementById('runner-canvas');
                if(!c) return null;
                const r = c.getBoundingClientRect();
                return {
                    cssW: Math.round(r.width), cssH: Math.round(r.height),
                    attrW: c.width, attrH: c.height,
                    vw: window.innerWidth, vh: window.innerHeight,
                };
            }""")
            of = page.evaluate("""() => ({
                horizontal: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
                scrollW: document.documentElement.scrollWidth,
                clientW: document.documentElement.clientWidth,
            })""")
            stacked_resize = page.evaluate("""() => Array.from(document.querySelectorAll('.modal.show')).map(m => m.id||'?')""")
            offscreen_resize = scan_offscreen(page)
            report["resize_tests"][name] = {
                "canvas": cv,
                "overflow": of,
                "stacked_modals": stacked_resize,
                "offscreen_count": offscreen_resize["count"],
                "offscreen_sample": offscreen_resize["sample"],
            }

        # back to 540
        page.set_viewport_size({"width": 540, "height": 960})
        page.wait_for_timeout(1000)

        # === MODAL PROBES : ouvrir tous les modals via functions exposées ===
        modal_open_fns = [
            ("guide", "openGuide()"),
            ("shop", "openShopModal && openShopModal()"),
            ("daily", "openDailyModal && openDailyModal()"),
            ("equip", "openEquip && openEquip()"),
            ("saison", "openSaisonModal && openSaisonModal()"),
            ("runnerProfile", "openRunnerProfile && openRunnerProfile()"),
            ("cardCollection", "openCardCollection && openCardCollection()"),
            ("chests", "openChestsModal && openChestsModal()"),
            ("mapStadiums", "openMapStadiums && openMapStadiums()"),
            ("wardrobe", "openWardrobe && openWardrobe()"),
            ("records", "openRecordsModal && openRecordsModal()"),
            ("settings", "openSettings && openSettings()"),
            ("credits", "openCredits && openCredits()"),
            ("skillTree", "openSkillTree && openSkillTree()"),
        ]
        for (name, code) in modal_open_fns:
            try:
                # close everything first
                page.evaluate("""() => {
                    document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
                }""")
                page.wait_for_timeout(200)
                opened = page.evaluate(f"""() => {{
                    try {{
                        {code};
                        return true;
                    }} catch(e) {{
                        return 'err: ' + e.message;
                    }}
                }}""")
                page.wait_for_timeout(700)
                undefs = scan_undefined(page)
                stacked = page.evaluate("""() => {
                    const open = Array.from(document.querySelectorAll('.modal.show'));
                    return {count: open.length, ids: open.map(m => m.id || '?')};
                }""")
                offscreen = scan_offscreen(page)
                report["modal_probes"][name] = {
                    "opened": opened,
                    "undefined_count": len(undefs),
                    "undefined_sample": undefs[:5],
                    "stacked": stacked,
                    "offscreen_count": offscreen["count"],
                    "offscreen_sample": offscreen["sample"],
                }
                screenshot(page, f"deep-modal-{name}")
            except Exception as e:
                report["modal_probes"][name] = {"error": str(e)[:200]}

        report["totals"] = {
            "pageerrors": len(report["pageerrors"]),
            "console_errors": len(report["console_errors"]),
            "console_warnings": len(report["console_warnings"]),
            "console_logs_sampled": len(report["console_logs"]),
        }

        with open(OUT / "qa-bugs-deep-report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        # === SUMMARY out ===
        npc_counts = [s["count"] for s in report["npc_observation"] if isinstance(s["count"], int)]
        # canvas frozen ? compare hashes
        tails = [c["hash"]["tail"] if isinstance(c["hash"], dict) else None for c in report["canvas_hashes"]]
        unique_tails = len(set([t for t in tails if t]))

        # paliers : look for any palier with overflow / undefined / offscreen
        problem_paliers = []
        for tag, info in report["paliers"].items():
            issues = []
            if info["overflow_horizontal"]: issues.append("overflow")
            if info["undefined_count"] > 0: issues.append(f"undef({info['undefined_count']})")
            if info["offscreen_count"] > 0: issues.append(f"offscreen({info['offscreen_count']})")
            if info["stacked_modals"]["count"] > 1: issues.append("stacked-modals")
            if isinstance(info["fps"], dict) and info["fps"]["fps"] < 25: issues.append(f"low-fps({info['fps']['fps']})")
            if issues: problem_paliers.append({tag: issues})

        problem_modals = []
        for name, info in report["modal_probes"].items():
            if isinstance(info, dict):
                issues = []
                if info.get("opened") != True: issues.append(f"open-fail: {str(info.get('opened'))[:60]}")
                if info.get("undefined_count", 0) > 0: issues.append(f"undef({info['undefined_count']})")
                if info.get("offscreen_count", 0) > 0: issues.append(f"offscreen({info['offscreen_count']})")
                if issues: problem_modals.append({name: issues})

        print(json.dumps({
            "totals": report["totals"],
            "npc_counts_during_obs": npc_counts,
            "npc_max": max(npc_counts) if npc_counts else None,
            "npc_min": min(npc_counts) if npc_counts else None,
            "canvas_unique_frames_across_paliers": unique_tails,
            "pause_delta_laps": report["pause_resume"]["delta_laps"],
            "pause_delta_prog": report["pause_resume"]["delta_prog"],
            "pause_canvas_changed_during_pause": report["pause_resume"].get("canvas_changed"),
            "fps_after_resume": report["pause_resume"]["fps_after_resume"],
            "resize_320_canvas": report["resize_tests"]["320x480"]["canvas"],
            "resize_1024_canvas": report["resize_tests"]["1024x768"]["canvas"],
            "first_pageerrors": report["pageerrors"][:3],
            "first_console_errors": [e["text"][:120] for e in report["console_errors"][:5]],
            "first_console_warnings": [e["text"][:120] for e in report["console_warnings"][:5]],
            "problem_paliers": problem_paliers,
            "problem_modals": problem_modals,
            "fps_per_palier": {tag: info["fps"]["fps"] if isinstance(info["fps"], dict) else None for tag, info in report["paliers"].items()},
            "npc_per_palier": {tag: info["npc_count"] for tag, info in report["paliers"].items()},
        }, indent=2, default=str), flush=True)

        browser.close()

if __name__ == "__main__":
    main()
