"""
QA Vague 10 - Test "novice" du joueur, km 0 à 10.
Lance Playwright headless 540x960, charge localhost:8770 SANS skipper storySeen.
Capture console + erreurs + STATE a chaque palier km 1/3/5/10.
"""
import json, time, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"

def dump_state(page):
    """Recup STATE via window."""
    try:
        return page.evaluate("""() => {
            const s = window.STATE || {};
            const visible = Array.from(document.querySelectorAll('.upg-btn'))
                .filter(b => b.offsetParent !== null)
                .map(b => ({
                    id: b.dataset.upgrade,
                    aria: b.getAttribute('aria-label'),
                    disabled: b.disabled,
                    cost: b.querySelector('.upg-cost')?.textContent?.trim() || null
                }));
            return {
                gold: s.gold,
                totalGoldEarned: s.totalGoldEarned,
                tapValue: 1 + (s.upgradeTapValue || 0),
                upgradeTapValue: s.upgradeTapValue || 0,
                lapsRun: s.lapsRun,
                lapProgress: s.lapProgress,
                totalTaps: s.totalTaps || 0,
                runnerStamina: s.runnerStamina,
                cruiseLevel: s.cruiseLevel || s.upgradeCruiseControl || 0,
                cleanAutoKm: s.cleanAutoKm,
                starterPackClaimed: s.starterPackClaimed,
                starterPackDeclined: s.starterPackDeclined,
                visibleUpgrades: visible,
                openModals: Array.from(document.querySelectorAll('.modal.show')).map(m => m.id),
                storyVisible: (document.getElementById('story-intro')?.style.display !== 'none'
                               && !document.getElementById('story-intro')?.classList.contains('gone')),
            };
        }""")
    except Exception as e:
        return {"error": str(e)}

def screenshot(page, name):
    p = OUT / f"{name}.png"
    page.screenshot(path=str(p))
    return p.name

def auto_advance_to_km(page, target_km, max_seconds=120, tag=""):
    """
    Avance via tap automatique sur runner-stadium jusqu'a atteindre target_km.
    Mesure le temps reel.
    """
    start = time.time()
    last_km = page.evaluate("window.STATE.lapsRun || 0")
    iterations = 0
    while True:
        cur = page.evaluate("window.STATE.lapsRun || 0")
        if cur >= target_km:
            return time.time() - start, iterations
        # Tap via evaluate direct (plus rapide et fiable) - simule un pointerdown au centre du stade
        try:
            page.evaluate("""() => {
                const stadium = document.getElementById('runner-stadium');
                if(!stadium) return;
                const rect = stadium.getBoundingClientRect();
                const e = new PointerEvent('pointerdown', {
                    bubbles: true, cancelable: true,
                    clientX: rect.left + rect.width/2,
                    clientY: rect.top + rect.height/2,
                    pointerType: 'touch'
                });
                stadium.dispatchEvent(e);
            }""")
        except Exception as e:
            print(f"[{tag}] tap err: {e}", flush=True)
            break
        iterations += 1
        # tiny pause pour respecter TAP_COOLDOWN_MS (~50ms en pratique)
        page.wait_for_timeout(60)
        if time.time() - start > max_seconds:
            print(f"[{tag}] TIMEOUT at km {cur} after {max_seconds}s ({iterations} taps)", flush=True)
            return time.time() - start, iterations

def main():
    report = {"errors_console": [], "snapshots": {}, "timings": {}, "notes": []}
    with sync_playwright() as p:
        # On efface localStorage en passant en fresh context
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960},
                                  has_touch=True, is_mobile=True)
        page = ctx.new_page()

        # capture console + errors
        page.on("console", lambda m: report["errors_console"].append(
            {"type": m.type, "text": m.text[:300]}) if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda exc: report["errors_console"].append(
            {"type": "pageerror", "text": str(exc)[:300]}))

        page.goto(URL, wait_until="domcontentloaded")
        # purge localStorage pour forcer onboarding FRESH
        page.evaluate("() => { try { localStorage.clear(); } catch(_){} }")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2500)  # laisser le splash/intro charger

        # === T0 : etat tout debut ===
        screenshot(page, "00-initial-load")
        report["snapshots"]["t0_initial"] = dump_state(page)

        # === Examiner story-intro / giga-tuto ===
        story = page.evaluate("""() => {
            const el = document.getElementById('story-intro');
            if(!el) return {present: false};
            const style = window.getComputedStyle(el);
            const steps = Array.from(el.querySelectorAll('.giga-step')).map((s,i) => ({
                step: s.dataset.step, active: s.classList.contains('active'),
                visible: window.getComputedStyle(s).display !== 'none'
            }));
            return {
                present: true,
                display: style.display,
                opacity: style.opacity,
                gone: el.classList.contains('gone'),
                hasNext: !!document.getElementById('giga-next'),
                hasSkip: !!document.getElementById('giga-skip'),
                steps: steps.length,
                stepsState: steps,
            };
        }""")
        report["story_intro"] = story
        screenshot(page, "01-story-intro")

        # naviguer dans le tuto en cliquant SUIVANT
        if story.get("hasNext"):
            for i in range(10):
                try:
                    btn = page.locator("#giga-next")
                    if btn.is_visible():
                        btn.click(force=True)
                        page.wait_for_timeout(350)
                    else:
                        break
                except Exception as e:
                    report["notes"].append(f"giga-next click err iter {i}: {e}")
                    break
        page.wait_for_timeout(1200)
        screenshot(page, "02-after-story")
        report["snapshots"]["t1_after_story"] = dump_state(page)

        # Examine ActiveTuto (les bulles step-by-step)
        active_tuto = page.evaluate("""() => {
            if(typeof ActiveTuto === 'undefined') return {present:false};
            return {
                present: true,
                isActive: ActiveTuto.isActive ? ActiveTuto.isActive() : null,
                isDone: ActiveTuto.isDone ? ActiveTuto.isDone() : null,
                bubbles: Array.from(document.querySelectorAll('.active-tuto-bubble, .active-tuto-arrow'))
                    .map(b => ({
                        cls: b.className,
                        visible: window.getComputedStyle(b).display !== 'none',
                        text: (b.textContent||'').slice(0,80)
                    }))
            };
        }""")
        report["active_tuto"] = active_tuto

        # === Avance jusqu'a km 1 ===
        t1, taps1 = auto_advance_to_km(page, 1, max_seconds=60, tag="km1")
        report["timings"]["km1_seconds"] = round(t1, 2)
        report["timings"]["km1_taps"] = taps1
        screenshot(page, "03-km1")
        report["snapshots"]["km1"] = dump_state(page)

        # === starter pack check ===
        starter = page.evaluate("""() => {
            const m = document.getElementById('starter-modal');
            if(!m) return {present:false};
            return {
                present: true,
                visible: m.classList.contains('show'),
                bodyText: (m.textContent||'').slice(0,400)
            };
        }""")
        report["starter_pack_at_km1"] = starter
        screenshot(page, "04-after-km1-starter")
        # close starter modal si visible pour continuer
        if starter.get("visible"):
            # decline pour ne pas avoir +5000 gold artificiel
            page.evaluate("""() => {
                const m = document.getElementById('starter-modal');
                if(!m) return;
                const btns = m.querySelectorAll('button');
                // cherche un bouton 'Non merci' / 'plus tard' / close
                for(const b of btns){
                    const t = (b.textContent||'').toLowerCase();
                    if(t.includes('merci') || t.includes('tard') || t.includes('plus') || t.includes('fermer') || t.includes('non')){
                        b.click(); return;
                    }
                }
                // sinon ferme par classe
                m.classList.remove('show');
                if(window.STATE) window.STATE.starterPackDeclined = true;
            }""")
            page.wait_for_timeout(400)

        # === Avance jusqu'a km 3 ===
        t3, taps3 = auto_advance_to_km(page, 3, max_seconds=90, tag="km3")
        report["timings"]["km3_seconds_extra"] = round(t3, 2)
        report["timings"]["km3_taps_extra"] = taps3
        screenshot(page, "05-km3")
        report["snapshots"]["km3"] = dump_state(page)

        # === Avance jusqu'a km 5 ===
        t5, taps5 = auto_advance_to_km(page, 5, max_seconds=90, tag="km5")
        report["timings"]["km5_seconds_extra"] = round(t5, 2)
        screenshot(page, "06-km5")
        report["snapshots"]["km5"] = dump_state(page)

        # === Avance jusqu'a km 10 ===
        t10, taps10 = auto_advance_to_km(page, 10, max_seconds=120, tag="km10")
        report["timings"]["km10_seconds_extra"] = round(t10, 2)
        screenshot(page, "07-km10")
        report["snapshots"]["km10"] = dump_state(page)

        # === Test : essayer d'acheter le premier upgrade ===
        first_buy = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('.upg-btn'))
                .filter(b => b.offsetParent !== null);
            const result = [];
            for(const b of btns){
                const id = b.dataset.upgrade;
                if(!id) continue;
                const goldBefore = window.STATE.gold;
                const levelBefore = window.STATE['upgrade' + id.charAt(0).toUpperCase() + id.slice(1)] || 0;
                if(typeof buyUpgrade === 'function'){
                    buyUpgrade(id);
                }
                const goldAfter = window.STATE.gold;
                const levelAfter = window.STATE['upgrade' + id.charAt(0).toUpperCase() + id.slice(1)] || 0;
                result.push({id, goldBefore, goldAfter,
                            cost: goldBefore - goldAfter, levelBefore, levelAfter,
                            bought: levelAfter > levelBefore});
            }
            return result;
        }""")
        report["upgrade_purchases_at_km10"] = first_buy
        screenshot(page, "08-after-upgrades")
        report["snapshots"]["after_upgrades"] = dump_state(page)

        # === Examiner mult/facilites visibles ===
        facilities = page.evaluate("""() => {
            const s = window.STATE;
            const TAP_COMBO_WINDOW = (typeof window.TAP_COMBO_WINDOW !== 'undefined') ? window.TAP_COMBO_WINDOW : null;
            return {
                shopBoostX2Until: s.shopBoostX2Until,
                shopBoostActive: s.shopBoostX2Until && Date.now() < s.shopBoostX2Until,
                shopBoostHoursLeft: s.shopBoostX2Until ? Math.max(0,(s.shopBoostX2Until-Date.now())/3600000) : 0,
                gems: typeof getGems === 'function' ? getGems() : null,
                hasManager: s.team?.sprinter?.mgr,
                eventActive: typeof eventTapMul === 'function' ? eventTapMul() : null,
                ev_eventGoldMul: typeof eventGoldMul === 'function' ? eventGoldMul() : null,
                comboWindow: TAP_COMBO_WINDOW,
                tap_cooldown: typeof TAP_COOLDOWN_MS !== 'undefined' ? TAP_COOLDOWN_MS : null,
            };
        }""")
        report["facilities_audit"] = facilities

        # save report
        with open(OUT / "qa-report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        print(json.dumps({
            "km1_sec": report["timings"].get("km1_seconds"),
            "km1_taps": report["timings"].get("km1_taps"),
            "km3_sec_extra": report["timings"].get("km3_seconds_extra"),
            "km5_sec_extra": report["timings"].get("km5_seconds_extra"),
            "km10_sec_extra": report["timings"].get("km10_seconds_extra"),
            "errors": len(report["errors_console"]),
            "story_present": story.get("present"),
            "starter_appeared": starter.get("visible") or starter.get("present"),
            "gold_km10": report["snapshots"].get("km10",{}).get("gold"),
            "gold_km1": report["snapshots"].get("km1",{}).get("gold"),
            "facilities": facilities,
        }, indent=2, default=str), flush=True)

        browser.close()

if __name__ == "__main__":
    main()
