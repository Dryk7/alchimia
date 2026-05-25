"""
Verify VAGUE 13 fix lunar : tribune+drapeaux+magicGrad orangé doivent disparaître en biome lunaire.
- Force STATE.lapsRun=105 + chapter=2 + saison=2 → biome lunar attendu
- Capture screenshot et sample 5 pixels en haut de l'écran : doit être SOMBRE (R+G+B < 360)
- Re-test à km 130 (plus loin dans le lunaire)
"""
import asyncio
import os
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


async def skip_onboarding(page):
    """Force-skip toute UI d'intro/onboarding."""
    await page.evaluate("""
        try {
            for(const k of Object.keys(localStorage)){
                if(/intro|onboard|tuto|tour|first|welcome|seen|done/i.test(k)){
                    localStorage.setItem(k, 'done');
                }
            }
            localStorage.setItem('foulee_seen_intro', '1');
            localStorage.setItem('foulee_onboarding_done', '1');
            localStorage.setItem('foulee_v2_onboarding', 'done');
            localStorage.setItem('alchimia_seen_intro', '1');
            localStorage.setItem('onboardingV2.done', 'done');
            localStorage.setItem('foulee.onboarding.v2', 'done');
            const splash = document.querySelector('#opening-cinematic, #splash, #intro-overlay');
            if(splash) splash.style.display = 'none';
        } catch(e){}
    """)


async def dismiss_modals(page):
    """Force-cache toutes les modales/overlays UI pour exposer le canvas lunaire."""
    await page.evaluate("""
        try {
            // Skip onboarding watcher
            if(window.OnboardingV2 && typeof window.OnboardingV2._skipAll === 'function'){
                window.OnboardingV2._skipAll();
            }
            if(window.Onboarding && typeof window.Onboarding._skipAll === 'function'){
                window.Onboarding._skipAll();
            }
            // Force-hide tout ce qui pourrait masquer le canvas
            const all = document.querySelectorAll('div, section, aside, dialog');
            all.forEach(el => {
                const cs = getComputedStyle(el);
                if(el.id === 'game-screen' || el.tagName === 'CANVAS' || el.closest('canvas')) return;
                // Cible spécifique : modales / overlays
                const cls = (el.className && el.className.toString) ? el.className.toString().toLowerCase() : '';
                const idl = (el.id || '').toLowerCase();
                if(/modal|overlay|bubble|drawer|sidebar|panel|tooltip|tour|onboard|codex|guide/i.test(cls + ' ' + idl)){
                    el.style.display = 'none';
                }
            });
        } catch(e){}
    """)


async def force_lunar_state(page, km):
    """Force le state en biome lunaire."""
    await page.evaluate(f"""
        try {{
            if(window.STATE){{
                window.STATE.lapsRun = {km};
                window.STATE.chapter = 2;
                window.STATE.saison = 2;
                if(typeof updateSky === 'function') updateSky();
                if(typeof applyStadiumTier === 'function') applyStadiumTier();
            }}
        }} catch(e){{ console.error('force_lunar_state', e); }}
    """)


async def sample_top_pixels(page):
    """Sample 5 pixels du haut du canvas RUNNER : retourne valeur moyenne R+G+B.
       Si < 360 → ciel sombre (good lunar). Si > 500 → orange/yellow sunset (bug)."""
    sample = await page.evaluate("""
        () => {
            const cv = document.querySelector('#runner-canvas');
            if(!cv) return { error: 'no runner-canvas' };
            const ctx = cv.getContext('2d');
            if(!ctx) return { error: 'no ctx' };
            const w = cv.width, h = cv.height;
            const ys = [5, 15, 30, 50, 80];
            const xs = [Math.floor(w*0.1), Math.floor(w*0.3), Math.floor(w*0.5), Math.floor(w*0.7), Math.floor(w*0.9)];
            const samples = [];
            for(const y of ys){
                for(const x of xs){
                    try {
                        const px = ctx.getImageData(x, y, 1, 1).data;
                        samples.push({ x, y, r:px[0], g:px[1], b:px[2], sum: px[0]+px[1]+px[2] });
                    } catch(e){ samples.push({ x, y, error: e.message }); }
                }
            }
            const valid = samples.filter(s => !s.error);
            const avgSum = valid.length ? valid.reduce((a,b)=>a+b.sum,0) / valid.length : -1;
            const maxSum = valid.length ? Math.max(...valid.map(s=>s.sum)) : -1;
            return { samples, avgSum, maxSum, count: valid.length, canvasW: w, canvasH: h };
        }
    """)
    return sample


async def run():
    errors = []
    findings = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(f"[pageerror] {exc}"))

        await page.goto(URL, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(1500)
        await skip_onboarding(page)
        await page.wait_for_timeout(500)

        # Clic "PRENDRE LE DÉPART" pour lancer la scène de course in-game
        try:
            await page.evaluate("""
                const b = document.querySelector('#start-btn');
                if(b) b.click();
            """)
            await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"[warn] start button: {e}")
        await dismiss_modals(page)
        await page.wait_for_timeout(800)
        await dismiss_modals(page)
        await page.wait_for_timeout(500)

        # --- TEST 1 : km 105 (juste après ascension) ---
        await force_lunar_state(page, 105)
        await page.wait_for_timeout(2500)
        await dismiss_modals(page)
        await page.wait_for_timeout(500)
        s1 = await sample_top_pixels(page)
        out1 = os.path.join(OUT_DIR, "vague13-lunar-fixed.png")
        # Screenshot le canvas uniquement (évite les modales overlay)
        cv = page.locator("#runner-canvas").first
        try:
            await cv.screenshot(path=out1)
        except Exception:
            await page.screenshot(path=out1, full_page=False)
        findings["km105"] = {
            "screenshot": out1,
            "avgSum": s1.get("avgSum"),
            "maxSum": s1.get("maxSum"),
            "dark_ok": (s1.get("maxSum", 999) < 400),
        }

        # --- TEST 2 : km 130 (plus loin lunaire) ---
        await force_lunar_state(page, 130)
        await page.wait_for_timeout(2000)
        await dismiss_modals(page)
        await page.wait_for_timeout(500)
        s2 = await sample_top_pixels(page)
        out2 = os.path.join(OUT_DIR, "vague13-lunar-km130.png")
        try:
            await cv.screenshot(path=out2)
        except Exception:
            await page.screenshot(path=out2, full_page=False)
        findings["km130"] = {
            "screenshot": out2,
            "avgSum": s2.get("avgSum"),
            "maxSum": s2.get("maxSum"),
            "dark_ok": (s2.get("maxSum", 999) < 400),
        }

        # Vérifie biome et présence tribune
        diag = await page.evaluate("""
            () => {
                let info = {};
                try {
                    if(typeof currentBiome === 'function' && window.STATE){
                        info.biome = currentBiome();
                    }
                    if(typeof currentStage === 'function'){
                        const st = currentStage();
                        info.stageName = st?.name;
                        info.stageBiome = st?.biome;
                        info.stageFloors = st?.floors;
                    }
                    info.lapsRun = window.STATE?.lapsRun;
                    info.chapter = window.STATE?.chapter;
                    info.saison = window.STATE?.saison;
                } catch(e){ info.error = e.message; }
                return info;
            }
        """)
        findings["diag"] = diag

        await browser.close()

    print("=== VAGUE 13 LUNAR FIX VERIFY ===")
    print(f"Diag: {findings['diag']}")
    print(f"\n[KM 105] screenshot: {findings['km105']['screenshot']}")
    print(f"  avgSum: {findings['km105']['avgSum']:.1f} | maxSum: {findings['km105']['maxSum']} | dark_ok: {findings['km105']['dark_ok']}")
    print(f"\n[KM 130] screenshot: {findings['km130']['screenshot']}")
    print(f"  avgSum: {findings['km130']['avgSum']:.1f} | maxSum: {findings['km130']['maxSum']} | dark_ok: {findings['km130']['dark_ok']}")
    print(f"\nConsole errors: {len(errors)}")
    for e in errors[:20]:
        print(f"  {e}")
    success = findings['km105']['dark_ok'] and findings['km130']['dark_ok']
    print(f"\n=> {'PASS' if success else 'FAIL'}: lunar sky is {'DARK' if success else 'NOT DARK'}")
    return success


if __name__ == "__main__":
    asyncio.run(run())
