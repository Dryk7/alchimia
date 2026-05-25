"""
VAGUE 13 — Verify pause: lapProgress ne doit pas avancer pendant document.hidden.
"""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        await page.goto("http://localhost:8770/", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        # Skip onboarding via localStorage flags + reload pour appliquer
        await page.evaluate(
            """() => {
                try { localStorage.setItem('foulee.onboardingDone', '1'); } catch(e){}
                try { localStorage.setItem('foulee.tutoV2', JSON.stringify({step:-1,seen:true})); } catch(e){}
                try { localStorage.setItem('foulee.storyIntroSeen', '1'); } catch(e){}
            }"""
        )
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        # Si modal d'intro encore présent, on tente de skip
        try:
            await page.evaluate(
                """() => {
                    document.querySelectorAll('.opening-credits, .story-intro, .modal.show, .onboarding-overlay').forEach(el => el.remove());
                    if(window.STATE){ window.STATE.lapsRun = 10; }
                }"""
            )
        except Exception:
            pass

        # Force lapsRun
        await page.evaluate("() => { if(window.STATE){ window.STATE.lapsRun = 10; } }")

        # Stabilisation
        await page.wait_for_timeout(1000)

        # Note lapProgress avant pause
        lap_progress_0 = await page.evaluate(
            "() => (window.STATE && window.STATE.lapProgress) || 0"
        )
        print(f"lapProgress0 (avant pause) = {lap_progress_0}")

        # Cache le tab via Object.defineProperty + dispatch event
        await page.evaluate(
            """() => {
                Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
                Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
                document.dispatchEvent(new Event('visibilitychange'));
            }"""
        )

        # Attend 5s avec tab "caché"
        await page.wait_for_timeout(5000)

        # Note lapProgress pendant pause
        lap_progress_1 = await page.evaluate(
            "() => (window.STATE && window.STATE.lapProgress) || 0"
        )
        delta_pause = lap_progress_1 - lap_progress_0
        print(f"lapProgress1 (apres 5s pause) = {lap_progress_1}")
        print(f"DELTA pendant pause = {delta_pause:.6f}")

        # Test : delta doit etre < 0.001
        if abs(delta_pause) < 0.001:
            print("PASS: lapProgress n'a pas avance pendant pause (< 0.001)")
        else:
            print(f"FAIL: lapProgress a avance de {delta_pause:.6f} pendant pause (>= 0.001)")

        # Restore visibility
        await page.evaluate(
            """() => {
                Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
                Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
                document.dispatchEvent(new Event('visibilitychange'));
            }"""
        )

        # Attend 2s pour resume
        await page.wait_for_timeout(2000)

        lap_progress_2 = await page.evaluate(
            "() => (window.STATE && window.STATE.lapProgress) || 0"
        )
        delta_resume = lap_progress_2 - lap_progress_1
        print(f"lapProgress2 (apres 2s resume) = {lap_progress_2}")
        print(f"DELTA pendant resume = {delta_resume:.6f}")

        if delta_resume > 0:
            print("PASS: le jeu reprend apres restore visibility")
        else:
            print("WARN: le jeu ne semble pas reprendre (delta_resume <= 0)")

        print(f"\nErreurs console: {len(console_errors)}")
        for e in console_errors[:5]:
            print(f"  - {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
