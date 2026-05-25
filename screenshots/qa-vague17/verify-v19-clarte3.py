"""
Verify enriched Upgrades section in Guide (Codex).
v19 clarte3 - tableau detaille des effets par niveau.
"""
import asyncio
import json
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("SKIPPED: playwright not installed (no test runner)")
    sys.exit(0)

INDEX = Path(r"D:/alchimia/index.html").resolve()
SCREENSHOT = Path(r"D:/alchimia/screenshots/qa-vague17/audit-v19-clarte3-codex.png")

async def main():
    errors = []
    found = {"PUISSANCE": False, "TROPHEE": False, "Strategie": False}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 412, "height": 915})
        page = await context.new_page()

        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        await page.goto(f"file:///{INDEX.as_posix()}")
        await page.wait_for_load_state("networkidle")

        # Skip onboarding
        try:
            await page.evaluate("""
              try {
                if (typeof STATE !== 'undefined') {
                  STATE.gigaStep = 99;
                  STATE.tutoStep = 99;
                  STATE.onboardingDone = true;
                }
                const intro = document.getElementById('story-intro');
                if (intro) intro.style.display = 'none';
                const splash = document.getElementById('opening-credits');
                if (splash) splash.style.display = 'none';
              } catch(e) {}
            """)
        except Exception as e:
            print(f"warn skip onboarding: {e}")

        await page.wait_for_timeout(400)

        # Try open guide modal
        opened = await page.evaluate("""
          (() => {
            try {
              if (typeof openModal === 'function') {
                openModal('guide-modal');
                return 'openModal';
              }
              const m = document.getElementById('guide-modal');
              if (m) {
                m.classList.add('show');
                m.style.display = 'flex';
                return 'manual';
              }
              return null;
            } catch(e) { return 'err:' + e.message; }
          })()
        """)
        print(f"guide opened via: {opened}")

        await page.wait_for_timeout(300)

        # Click upgrades tab
        try:
            await page.evaluate("""
              const tab = document.querySelector('#guide-tabs .g-tab[data-section=\"upgrades\"]');
              if (tab) tab.click();
            """)
        except Exception as e:
            print(f"warn click upgrades tab: {e}")

        await page.wait_for_timeout(300)

        # Check DOM content
        content = await page.evaluate("""
          (() => {
            const sec = document.querySelector('.g-sec[data-section=\"upgrades\"]');
            return sec ? sec.innerText : '';
          })()
        """)

        if "PUISSANCE" in content: found["PUISSANCE"] = True
        if "TROPH" in content: found["TROPHEE"] = True  # TROPHEE/TROPHÉE
        if "Strat" in content: found["Strategie"] = True

        SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(SCREENSHOT), full_page=False)

        await browser.close()

    ok = all(found.values()) and len(errors) == 0
    print("found:", found)
    print("errors:", len(errors))
    if errors:
        for e in errors[:5]:
            print("  -", e)
    print("OK" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
