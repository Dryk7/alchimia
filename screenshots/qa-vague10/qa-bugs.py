"""
QA Vague 10 — Bug hunt visuel + erreurs runtime sur FOULÉE.
Playwright headless 540x960, capture ERROR/WARN/PAGEERROR aux paliers.
Tests :
- paliers km 1, 5, 12, 30, 50, 75, 99, 100, 105 → setLapsRun() + wait 3s
- modales empilées (.modal.show > 1)
- overflow horizontal (scrollWidth > clientWidth)
- éléments "undefined" affichés
- pause/resume (visibilitychange)
- resize 320x480 puis 1024x768 (canvas adapt ?)
- NPC count borné (npcs array size sur 30s d'observation)
"""
import json, time, sys, os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"

PALIERS = [1, 5, 12, 30, 50, 75, 99, 100, 105]

def screenshot(page, name):
    p = OUT / f"{name}.png"
    try:
        page.screenshot(path=str(p))
        return p.name
    except Exception as e:
        return f"err: {e}"

def jump_to_km(page, target_km):
    """Force la progression en setant lapsRun + lapProgress et en mettant à jour la scène."""
    page.evaluate(f"""(km) => {{
        try{{
            window.STATE.lapsRun = km;
            window.STATE.lapProgress = 0;
            // décor : sauter aussi le decorScroll pour cohérence visuelle
            if(typeof decorScroll !== 'undefined' || window.RUNNER_2D){{
                try {{ window.decorScroll = km * 1000; }} catch(_) {{}}
            }}
            // déclencher tier banner si tier change
            if(typeof renderStats === 'function') renderStats();
            if(typeof updateRunnerHUD === 'function') updateRunnerHUD();
            return true;
        }} catch(e){{
            return 'err:'+ e.message;
        }}
    }}""", target_km)

def scan_undefined(page):
    return page.evaluate("""() => {
        const flagged = [];
        const all = document.querySelectorAll('body *');
        for(const el of all){
            if(!el.children.length){
                const t = (el.textContent || '').trim();
                if(t === 'undefined' || t === 'NaN' || t === 'null'){
                    flagged.push({
                        tag: el.tagName,
                        cls: (el.className || '').toString().slice(0, 80),
                        id: el.id || null,
                        text: t,
                    });
                }
            }
        }
        // aussi : input.value === "undefined"
        return flagged.slice(0, 30);
    }""")

def scan_overflow(page):
    return page.evaluate("""() => {
        const out = {
            documentScrollW: document.documentElement.scrollWidth,
            documentClientW: document.documentElement.clientWidth,
            bodyScrollW: document.body.scrollWidth,
            bodyClientW: document.body.clientWidth,
            horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
            offscreenElements: [],
        };
        // éléments visibles partiellement hors écran à droite (très usuels)
        const vw = window.innerWidth;
        document.querySelectorAll('.modal.show, .topbar, .drawer.show, .hud, .panel, .tier-banner, #tuto-hint').forEach(el => {
            const r = el.getBoundingClientRect();
            if(r.width === 0 || r.height === 0) return;
            if(r.right > vw + 4 || r.left < -4){
                out.offscreenElements.push({
                    id: el.id || null,
                    cls: (el.className || '').toString().slice(0, 80),
                    left: Math.round(r.left), right: Math.round(r.right),
                    vw,
                });
            }
        });
        return out;
    }""")

def scan_stacked_modals(page):
    return page.evaluate("""() => {
        const open = Array.from(document.querySelectorAll('.modal.show'));
        return {
            count: open.length,
            ids: open.map(m => m.id || '(no-id)'),
            stacked: open.length > 1,
        };
    }""")

def get_canvas_state(page):
    return page.evaluate("""() => {
        const cv = document.getElementById('runner-canvas');
        if(!cv) return {present: false};
        const r = cv.getBoundingClientRect();
        return {
            present: true,
            cssW: Math.round(r.width), cssH: Math.round(r.height),
            attrW: cv.width, attrH: cv.height,
            dpr: window.devicePixelRatio,
            vw: window.innerWidth, vh: window.innerHeight,
        };
    }""")

def get_npc_count(page):
    return page.evaluate("""() => {
        try {
            if(window.RUNNER_2D && window.RUNNER_2D._debug && window.RUNNER_2D._debug.npcCount){
                return window.RUNNER_2D._debug.npcCount();
            }
            // fallback : compter les éléments .npc-dom ou les sprites
            return null;
        } catch(e){ return 'err:'+e.message; }
    }""")

def get_fps(page):
    """Mesure FPS approx en samplant requestAnimationFrame sur 1.5s."""
    return page.evaluate("""() => new Promise(r => {
        let frames = 0;
        const t0 = performance.now();
        function step(){
            frames++;
            if(performance.now() - t0 < 1500){
                requestAnimationFrame(step);
            } else {
                const elapsed = (performance.now() - t0)/1000;
                r({fps: +(frames/elapsed).toFixed(1), elapsed: +elapsed.toFixed(2), frames});
            }
        }
        requestAnimationFrame(step);
    })""")

def main():
    report = {
        "errors": [],     # pageerror
        "console_errors": [],
        "console_warnings": [],
        "paliers": {},
        "stacked_modals_events": [],
        "offscreen_events": [],
        "undefined_events": [],
        "npc_observation": {},
        "pause_resume": {},
        "resize_tests": {},
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
                loc = ""
                try:
                    loc = f"{msg.location.get('url','')[-80:]}:{msg.location.get('lineNumber','')}"
                except Exception:
                    pass
                rec = {"type": t, "text": txt, "loc": loc}
                if t == "error":
                    report["console_errors"].append(rec)
                elif t in ("warning", "warn"):
                    report["console_warnings"].append(rec)
            except Exception:
                pass

        page.on("console", on_console)
        page.on("pageerror", lambda exc: report["errors"].append(str(exc)[:400]))

        # === init : skip onboarding via localStorage ===
        page.goto(URL, wait_until="domcontentloaded")
        page.evaluate("""() => {
            try {
                localStorage.setItem('foulee.tutoV2', 'done');
                localStorage.setItem('foulee.storySeen', '1');
                localStorage.setItem('foulee.gigaTutoSeen', '1');
                localStorage.setItem('foulee.lastSeenTier', '0');
                localStorage.setItem('foulee.onboardingDone', '1');
            } catch(e){}
        }""")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3500)  # laisser le splash s'effacer

        # close any visible modals up front
        page.evaluate("""() => {
            document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
            const intro = document.getElementById('intro');
            if(intro){ intro.classList.add('gone'); intro.style.display='none'; }
            const story = document.getElementById('story-intro');
            if(story){ story.classList.add('gone'); story.style.display='none'; }
        }""")
        page.wait_for_timeout(800)

        report["initial_canvas"] = get_canvas_state(page)
        screenshot(page, "00-init")

        # === ITER paliers ===
        for km in PALIERS:
            tag = f"km{km:03d}"
            jump_to_km(page, km)
            # laisser le tier banner / decor s'updater
            page.wait_for_timeout(3000)

            stacked = scan_stacked_modals(page)
            overflow = scan_overflow(page)
            undefs = scan_undefined(page)
            screenshot(page, f"palier-{tag}")

            report["paliers"][tag] = {
                "stacked_modals": stacked,
                "overflow": {
                    "horizontal_overflow": overflow["horizontalOverflow"],
                    "doc_scrollW": overflow["documentScrollW"],
                    "doc_clientW": overflow["documentClientW"],
                    "offscreen_count": len(overflow["offscreenElements"]),
                    "offscreen_sample": overflow["offscreenElements"][:5],
                },
                "undefined_count": len(undefs),
                "undefined_sample": undefs[:5],
                "errors_so_far": len(report["errors"]),
                "console_errors_so_far": len(report["console_errors"]),
                "console_warnings_so_far": len(report["console_warnings"]),
            }
            if stacked["stacked"]:
                report["stacked_modals_events"].append({"km": km, "ids": stacked["ids"]})
            if overflow["horizontalOverflow"]:
                report["offscreen_events"].append({"km": km, "diff": overflow["documentScrollW"] - overflow["documentClientW"]})
            if len(undefs) > 0:
                report["undefined_events"].append({"km": km, "sample": undefs[:3]})

        # === NPC count observation (sur 30s) ===
        npc_samples = []
        page.evaluate("""() => { window.STATE.lapsRun = 50; }""")
        page.wait_for_timeout(800)
        for i in range(15):
            c = get_npc_count(page)
            npc_samples.append(c)
            page.wait_for_timeout(2000)
        report["npc_observation"] = {
            "samples": npc_samples,
            "max": max([x for x in npc_samples if isinstance(x, int)], default=None),
            "min": min([x for x in npc_samples if isinstance(x, int)], default=None),
            "first_nonnull": next((x for x in npc_samples if x is not None), None),
        }

        # === PAUSE/RESUME : simuler visibilitychange ===
        page.evaluate("""() => { window.STATE.lapsRun = 25; }""")
        page.wait_for_timeout(500)
        pre_pause = page.evaluate("""() => ({
            lapsRun: window.STATE?.lapsRun || 0,
            lapProgress: window.STATE?.lapProgress || 0,
            t: performance.now()
        })""")
        # simuler tab cachée
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
        fps_after = get_fps(page)
        post_pause = page.evaluate("""() => ({
            lapsRun: window.STATE?.lapsRun || 0,
            lapProgress: window.STATE?.lapProgress || 0,
            t: performance.now()
        })""")
        report["pause_resume"] = {
            "pre_pause": pre_pause,
            "post_pause": post_pause,
            "delta_laps": post_pause["lapsRun"] - pre_pause["lapsRun"],
            "fps_after_resume": fps_after,
        }
        screenshot(page, "pause-resume-after")

        # === RESIZE tests ===
        page.set_viewport_size({"width": 320, "height": 480})
        page.wait_for_timeout(1500)
        screenshot(page, "resize-320x480")
        report["resize_tests"]["320x480"] = {
            "canvas": get_canvas_state(page),
            "overflow": scan_overflow(page),
            "stacked_modals": scan_stacked_modals(page),
        }

        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(1500)
        screenshot(page, "resize-1024x768")
        report["resize_tests"]["1024x768"] = {
            "canvas": get_canvas_state(page),
            "overflow": scan_overflow(page),
            "stacked_modals": scan_stacked_modals(page),
        }

        # retour size mobile
        page.set_viewport_size({"width": 540, "height": 960})
        page.wait_for_timeout(800)

        # === FINAL totals ===
        report["totals"] = {
            "pageerrors": len(report["errors"]),
            "console_errors": len(report["console_errors"]),
            "console_warnings": len(report["console_warnings"]),
            "stacked_modals_events": len(report["stacked_modals_events"]),
            "offscreen_events": len(report["offscreen_events"]),
            "undefined_events": len(report["undefined_events"]),
        }

        # save
        with open(OUT / "qa-bugs-report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        # short summary on stdout
        print(json.dumps({
            "totals": report["totals"],
            "npc_max": report["npc_observation"]["max"],
            "npc_min": report["npc_observation"]["min"],
            "pause_delta_laps": report["pause_resume"]["delta_laps"],
            "fps_after_resume": report["pause_resume"]["fps_after_resume"],
            "resize_320_canvas": report["resize_tests"]["320x480"]["canvas"],
            "resize_1024_canvas": report["resize_tests"]["1024x768"]["canvas"],
            "first_pageerrors": report["errors"][:3],
            "first_console_errors": [e["text"][:120] for e in report["console_errors"][:5]],
            "first_console_warnings": [e["text"][:120] for e in report["console_warnings"][:5]],
            "stacked_events": report["stacked_modals_events"][:5],
            "undefined_events": report["undefined_events"][:5],
        }, indent=2, default=str), flush=True)

        browser.close()

if __name__ == "__main__":
    main()
