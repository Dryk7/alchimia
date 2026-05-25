"""
VAGUE 9 - FIX 2 : Vérification anatomie + vêtements + accessoires héros.
- A1: Taille marquée (waist tapering)
- A2: Cou visible
- A3: Col rond
- B1: Dossard #1 signature gold
- B2: Bandes latérales short
- B3: Semelles chaussures
- C1: Bandeau cyan/blanc héros

Capture screenshot et erreurs console.
"""
import asyncio
from playwright.async_api import async_playwright

URL = "http://localhost:8770"
OUT = r"D:/alchimia/screenshots/playthrough/VAGUE9-FIX2-anatomy-clothes.png"

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
                    STATE.lapsRun = 10;
                    STATE.totalTaps = 100;
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

        try:
            for _ in range(8):
                await page.mouse.click(270, 700)
                await page.wait_for_timeout(120)
        except Exception as e:
            errors.append(f"TAP: {e}")

        await page.wait_for_timeout(1500)
        await page.screenshot(path=OUT, full_page=False)
        await browser.close()

    real_errors = [e for e in errors if "favicon" not in e.lower()]
    print(f"Erreurs : {len(real_errors)}")
    for e in real_errors[:10]:
        print(f"  - {e}")
    print(f"Screenshot : {OUT}")

if __name__ == "__main__":
    asyncio.run(main())
