"""
VAGUE 9 - FIX 3 : Vérification animations + expressions faciales + effets sprint héros.
- A1: Yeux 33% plus grands (rayon 1.5→2, highlights 0.6→0.8)
- A2: Sourcils EFFORT (convergents agressifs)
- A3: Joues rouges seuil 0.5→0.4
- B1: Hop amplitude 5→8 (rebond plus visible)
- B2: kneeUp 1.0→1.3 (foulée plus haute)
- C1: Étincelles sous chaussures (chaussures rares au sprint)
- C2: Onde de choc sol (sprint max >0.75)

Force lapsRun=30, totalTaps=200, simule 5 secondes pour voir animations.
Capture screenshot + erreurs console.
"""
import asyncio
from playwright.async_api import async_playwright

URL = "http://localhost:8770"
OUT = r"D:/alchimia/screenshots/playthrough/VAGUE9-FIX3-final.png"

async def main():
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        page.on("pageerror", lambda exc: errors.append(f"PAGEERROR: {exc}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE.{msg.type}: {msg.text}") if msg.type == "error" else None)

        await page.goto(URL, wait_until="domcontentloaded")
        await page.evaluate("""
            localStorage.setItem('foulee.openingSeen', '1');
            localStorage.setItem('foulee.storySeen', '1');
            localStorage.setItem('foulee.tutoV3', 'done');
            localStorage.setItem('foulee.activeTutoV1', 'done');
        """)

        await page.evaluate("""
            const today = new Date().toISOString().slice(0,10);
            localStorage.setItem('foulee.dailyLastClaim', today);
            localStorage.setItem('foulee.dailyShown', today);
        """)

        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(2500)

        try:
            await page.evaluate("""
                if (typeof STATE !== 'undefined') {
                    STATE.starterPackDeclined = true;
                    STATE.starterPackClaimed = true;
                    STATE.lapsRun = 30;
                    STATE.totalTaps = 200;
                }
            """)
        except Exception as e:
            errors.append(f"STATE_EVAL: {e}")

        try:
            await page.evaluate("""
                document.querySelectorAll('.modal, .overlay, .drawer, [class*="modal"], [class*="overlay"]').forEach(el => {
                    if (el.style) el.style.display = 'none';
                    el.remove();
                });
                document.querySelectorAll('.modal-close, .close-btn, .btn-close, [class*="close"]').forEach(b => {
                    try { b.click(); } catch(e) {}
                });
            """)
        except Exception as e:
            errors.append(f"CLOSE_MODAL: {e}")

        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)

        # Spam-tap pour maintenir effort élevé (sprint max -> faceExpr='effort', shockwave, sparks)
        try:
            for _ in range(30):
                await page.mouse.click(270, 700)
                await page.wait_for_timeout(100)
        except Exception as e:
            errors.append(f"TAP: {e}")

        # Laisse tourner 5s pour observer animations + hop + foulée
        await page.wait_for_timeout(5000)

        # Petit burst final pour locker l'effort au sprint au moment du screenshot
        try:
            for _ in range(10):
                await page.mouse.click(270, 700)
                await page.wait_for_timeout(80)
        except Exception as e:
            errors.append(f"TAP2: {e}")
        await page.wait_for_timeout(500)

        await page.screenshot(path=OUT, full_page=False)
        await browser.close()

    real_errors = [e for e in errors if "favicon" not in e.lower()]
    print(f"Erreurs : {len(real_errors)}")
    for e in real_errors[:10]:
        print(f"  - {e}")
    print(f"Screenshot : {OUT}")

if __name__ == "__main__":
    asyncio.run(main())
