"""
VAGUE 13 — Vérification FPS km 100 (cinematic épique).
Test : mesurer FPS aux km 5 (baseline), 99, 100 (cinematic), 101 (post).
Cap particles : 150 confetti, 20 ambient.
Frame-skip défensif si dt > 50ms.
"""
import json, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"


def skip_onboarding(page):
    """Skip tuto/intro/story → directement dans le jeu."""
    page.evaluate("""() => {
        try {
            // Skip onboarding flags
            if(window.STATE){
                window.STATE.tutorialDone = true;
                window.STATE.tutorialStep = 999;
                window.STATE.storyShown = true;
                window.STATE.introSeen = true;
                window.STATE._autoCourseUnlocked = true;
                window.STATE._epicKm100Played = false;
            }
            // Fermer modales et splash
            document.querySelectorAll('.modal.show, .modal.is-open').forEach(m=>m.classList.remove('show','is-open'));
            const splash = document.getElementById('splash') || document.getElementById('opening-cinematic');
            if(splash) splash.style.display = 'none';
            // Click "PRENDRE LE DÉPART" si présent
            const startBtn = document.querySelector('#btn-start, [data-action="start"], .btn-start');
            if(startBtn) startBtn.click();
            return true;
        } catch(e) { return 'err:' + e.message; }
    }""")
    page.wait_for_timeout(500)


def force_km(page, km):
    page.evaluate(f"""(km) => {{
        try {{
            window.STATE.lapsRun = km;
            window.STATE.lapProgress = 0;
            if(km === 99) window.STATE._epicKm100Played = false;
            // Reset perf counters
            window._lastFrameMs = null;
            window._frameSkipCounter = 0;
            return true;
        }} catch(e) {{ return 'err:' + e.message; }}
    }}""", km)


def measure_fps(page, duration_ms, label):
    """Mesure FPS sur duration_ms via requestAnimationFrame counter."""
    result = page.evaluate(f"""async () => {{
        return await new Promise(resolve => {{
            let frames = 0;
            const t0 = performance.now();
            const target = t0 + {duration_ms};
            function _count(){{
                frames++;
                if(performance.now() < target){{
                    requestAnimationFrame(_count);
                }} else {{
                    const dt = (performance.now() - t0) / 1000;
                    resolve({{ frames, dt, fps: frames / dt }});
                }}
            }}
            requestAnimationFrame(_count);
        }});
    }}""")
    print(f"[{label}] frames={result['frames']} dt={result['dt']:.2f}s FPS={result['fps']:.1f}")
    return result['fps']


def main():
    errors = []
    fps_results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 540, 'height': 960})
        page = ctx.new_page()
        page.on('console', lambda msg: (
            errors.append(f"{msg.type}: {msg.text}")
            if msg.type in ('error', 'warning') else None
        ))
        page.on('pageerror', lambda exc: errors.append(f"PAGEERROR: {exc}"))

        print("[1] Loading page...")
        page.goto(URL, wait_until='load', timeout=15000)
        page.wait_for_timeout(2000)
        skip_onboarding(page)
        page.wait_for_timeout(1500)

        # km 5 baseline
        print("\n=== BASELINE km 5 ===")
        force_km(page, 5)
        page.wait_for_timeout(2500)
        fps_results['km5'] = measure_fps(page, 2000, 'km5')

        # km 99
        print("\n=== km 99 ===")
        force_km(page, 99)
        page.wait_for_timeout(2500)
        fps_results['km99'] = measure_fps(page, 2000, 'km99')

        # km 100 — déclenche cinematic épique
        print("\n=== km 100 (cinematic épique) ===")
        force_km(page, 100)
        # Déclenche la cinematic manuellement après force
        page.evaluate("""() => {
            try {
                if(typeof triggerEpicKm100 === 'function' && !window.STATE._epicKm100Played){
                    window.STATE._epicKm100Played = true;
                    triggerEpicKm100();
                }
            } catch(e){}
        }""")
        page.wait_for_timeout(2000)  # laisse cinematic démarrer
        fps_results['km100_cinematic'] = measure_fps(page, 3000, 'km100')

        # km 101 — post cinematic
        print("\n=== km 101 (post épique) ===")
        page.wait_for_timeout(4500)  # attendre fin cinematic
        force_km(page, 101)
        page.wait_for_timeout(2000)
        fps_results['km101'] = measure_fps(page, 2000, 'km101')

        # Vérifier les caps de particles
        particle_state = page.evaluate("""() => {
            try {
                return {
                    confetti: (typeof confetti !== 'undefined' && confetti) ? confetti.length : 'undefined',
                    ambientParticles: (typeof ambientParticles !== 'undefined' && ambientParticles) ? ambientParticles.length : 'undefined',
                    _epicActive: window._epicActive,
                };
            } catch(e){ return 'err:' + e.message; }
        }""")
        print("\n=== Particle state ===")
        print(json.dumps(particle_state, indent=2))

        browser.close()

    print("\n========================================")
    print("RÉSULTATS FPS")
    print("========================================")
    for k, v in fps_results.items():
        print(f"  {k:25s} : {v:.1f} fps")
    print(f"\nErreurs console : {len(errors)}")
    for e in errors[:10]:
        print(f"  - {e}")

    # Verdict
    print("\n========================================")
    print("VERDICT")
    print("========================================")
    baseline = fps_results.get('km5', 0)
    km100 = fps_results.get('km100_cinematic', 0)
    if km100 >= 30:
        print(f"OK : FPS km 100 = {km100:.1f} >= 30 (avant fix : 18.6)")
    elif km100 >= 25:
        print(f"AMELIORE : FPS km 100 = {km100:.1f} (avant fix : 18.6, but pas 30+)")
    else:
        print(f"INSUFFISANT : FPS km 100 = {km100:.1f} (encore < 25)")
    print(f"baseline km 5 = {baseline:.1f} fps")


if __name__ == '__main__':
    main()
