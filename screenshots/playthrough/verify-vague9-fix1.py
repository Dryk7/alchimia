"""
VAGUE 9 - FIX 1 : Vérification refonte design héros.
- Héros agrandi (~15%)
- Maillot bleu électrique
- Aura bleu clair pulsante + outline doré subtil

Capture screenshot et erreurs console.
"""
import asyncio
from playwright.async_api import async_playwright

URL = "http://localhost:8770"
OUT = r"D:/alchimia/screenshots/playthrough/VAGUE9-FIX1-hero-bigger.png"

async def main():
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        # Capture des erreurs console
        page.on("pageerror", lambda exc: errors.append(f"PAGEERROR: {exc}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE.{msg.type}: {msg.text}") if msg.type == "error" else None)

        # Set localStorage flags AVANT le chargement complet
        await page.goto(URL, wait_until="domcontentloaded")
        await page.evaluate("""
            localStorage.setItem('foulee.openingSeen', '1');
            localStorage.setItem('foulee.storySeen', '1');
            localStorage.setItem('foulee.tutoV3', 'done');
            localStorage.setItem('foulee.activeTutoV1', 'done');
        """)

        # Pré-set flags pour skip daily reward modal
        await page.evaluate("""
            const today = new Date().toISOString().slice(0,10);
            localStorage.setItem('foulee.dailyLastClaim', today);
            localStorage.setItem('foulee.dailyShown', today);
        """)

        # Reload pour appliquer les flags localStorage
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(2500)

        # Force STATE pour skip starter pack et avoir héros en run
        try:
            await page.evaluate("""
                if (typeof STATE !== 'undefined') {
                    STATE.starterPackDeclined = true;
                    STATE.starterPackClaimed = true;
                    STATE.lapsRun = 10;
                    STATE.totalTaps = 100;
                }
            """)
        except Exception as e:
            errors.append(f"STATE_EVAL: {e}")

        # Ferme toute modal visible : clique sur tout bouton .close, .modal-close, ou la touche Escape
        try:
            await page.evaluate("""
                // Ferme tous les modals/overlays
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

        # Tap quelques fois pour activer le run et voir le héros courir
        try:
            for _ in range(8):
                await page.mouse.click(270, 700)
                await page.wait_for_timeout(120)
        except Exception as e:
            errors.append(f"TAP: {e}")

        await page.wait_for_timeout(1500)

        # Screenshot
        await page.screenshot(path=OUT, full_page=False)

        await browser.close()

    # Filtrer doublons et déduire les vraies erreurs
    real_errors = [e for e in errors if "favicon" not in e.lower()]
    print(f"Erreurs : {len(real_errors)}")
    for e in real_errors[:5]:
        print(f"  - {e}")
    print(f"Screenshot : {OUT}")

if __name__ == "__main__":
    asyncio.run(main())
