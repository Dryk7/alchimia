"""
VAGUE 15 - Agent A8 - Verification BIOME PARTICLES
Force km=5 (rural), attendre 3s, screenshot.
Force km=80 (stadium), attendre 3s, screenshot.
0 erreurs console attendues.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"


def force_km(page, km):
    """Force le STATE pour avoir km comme distance courue (lapsRun=km, lapProgress=0.5)."""
    return page.evaluate(f"""() => {{
        if(!window.STATE) return {{error: 'STATE not found'}};
        window.STATE.lapsRun = {km};
        window.STATE.lapProgress = 0.5;
        // Reset les particules pour repartir de zéro
        window._biomeParticles = [];
        // Sanity check : biome attendu
        const stage = (typeof currentStage === 'function') ? currentStage() : null;
        return {{
            lapsRun: window.STATE.lapsRun,
            biome: stage ? stage.biome : null,
        }};
    }}""")


def snapshot_particles(page):
    return page.evaluate("""() => {
        const arr = window._biomeParticles || [];
        return {
            count: arr.length,
            sample: arr.slice(0, 3).map(p => ({
                x: Math.round(p.x), y: Math.round(p.y),
                vx: +p.vx.toFixed(2), vy: +p.vy.toFixed(2),
                size: p.size,
                color: typeof p.color === 'string' ? p.color : String(p.color),
                life: +p.life.toFixed(2),
            })),
        };
    }""")


def run():
    console_msgs = []
    page_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()

        page.on("console", lambda msg: console_msgs.append({"type": msg.type, "text": msg.text}))
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        page.add_init_script("try{localStorage.setItem('storySeen','1')}catch(e){}")

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Démarrer la course si bouton présent
        try:
            page.evaluate("""() => {
                const btn = document.getElementById('start-run-btn') || document.querySelector('[data-action=\\"start-run\\"]');
                if(btn) btn.click();
            }""")
        except Exception:
            pass
        page.wait_for_timeout(1500)

        errors = 0

        # ---- TEST 1 : km=5 (rural) ----
        forced = force_km(page, 5)
        print(f"[km=5] forced -> {forced}")
        if forced.get("biome") != "rural":
            print(f"WARN: biome attendu 'rural', got {forced.get('biome')!r}")

        page.wait_for_timeout(3000)
        snap = snapshot_particles(page)
        print(f"[km=5] particles after 3s -> count={snap['count']}")
        for s in snap["sample"]:
            print(f"   sample: {s}")

        if snap["count"] == 0:
            print("FAIL: aucune particule rurale spawned après 3s")
            errors += 1
        else:
            # Vérifie qu'au moins une particule a la couleur rurale verte
            rural_color = "rgba(120,180,80,0.7)"
            green_found = any(rural_color in s.get("color", "") for s in snap["sample"])
            if green_found:
                print("OK: au moins une particule rurale verte trouvée")
            else:
                print(f"INFO: pas de couleur rurale exacte dans l'échantillon (count={snap['count']}, sample peut être petit)")

        try:
            page.screenshot(path=str(OUT / "v15-a8-particles-rural-km5.png"), full_page=False)
            print(f"OK: screenshot rural sauvegardé")
        except Exception as e:
            print(f"WARN: screenshot rural failed: {e}")

        # ---- TEST 2 : km=80 (stadium) ----
        forced = force_km(page, 80)
        print(f"\n[km=80] forced -> {forced}")
        if forced.get("biome") != "stadium":
            print(f"WARN: biome attendu 'stadium', got {forced.get('biome')!r}")

        page.wait_for_timeout(3000)
        snap = snapshot_particles(page)
        print(f"[km=80] particles after 3s -> count={snap['count']}")
        for s in snap["sample"]:
            print(f"   sample: {s}")

        if snap["count"] == 0:
            print("FAIL: aucune particule stadium spawned après 3s")
            errors += 1
        else:
            stadium_colors = ["#e84030", "#ffd060", "#4080ff", "#7ec46a"]
            stadium_found = any(s.get("color", "") in stadium_colors for s in snap["sample"])
            if stadium_found:
                print("OK: au moins une particule stadium confetti trouvée")
            else:
                print(f"INFO: pas de couleur stadium dans le petit échantillon (count={snap['count']})")

        try:
            page.screenshot(path=str(OUT / "v15-a8-particles-stadium-km80.png"), full_page=False)
            print(f"OK: screenshot stadium sauvegardé")
        except Exception as e:
            print(f"WARN: screenshot stadium failed: {e}")

        # ---- Console errors ----
        console_errs = [m for m in console_msgs if m["type"] == "error"]
        if console_errs:
            print(f"\nFAIL: {len(console_errs)} erreurs console:")
            for m in console_errs[:10]:
                print(f"  - {m['text']}")
            errors += len(console_errs)
        else:
            print("\nOK: 0 erreurs console")

        if page_errors:
            print(f"FAIL: {len(page_errors)} page errors:")
            for e in page_errors[:10]:
                print(f"  - {e}")
            errors += len(page_errors)
        else:
            print("OK: 0 page errors")

        browser.close()
        return errors


if __name__ == "__main__":
    err = run()
    print()
    print("=== RÉSUMÉ ===")
    print(f"errors = {err}")
    if err == 0:
        print("STATUS = OK")
        sys.exit(0)
    else:
        print("STATUS = FAIL")
        sys.exit(1)
