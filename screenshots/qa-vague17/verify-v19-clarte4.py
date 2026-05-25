"""
Verify hint pedagogique 1ere fois pour upgrades debloques.
v19 clarte4 - hint contextuel + flag _upgFirstHints.
"""
import asyncio
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("SKIPPED: playwright not installed (no test runner)")
    sys.exit(0)

INDEX = Path(r"D:/alchimia/index.html").resolve()
SCREENSHOT = Path(r"D:/alchimia/screenshots/qa-vague17/audit-v19-clarte4-hint.png")


async def main():
    errors = []
    results = {
        "hint_dom_present": False,
        "flag_set": False,
        "no_second_hint": False,
        "no_console_errors": False,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 412, "height": 915})
        page = await context.new_page()

        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        # Reset localStorage avant chargement
        await page.add_init_script("""
          try { localStorage.clear(); } catch(e) {}
        """)

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
                  STATE._upgFirstHints = {};
                  STATE.lapsRun = 2;
                }
                const intro = document.getElementById('story-intro');
                if (intro) intro.style.display = 'none';
                const splash = document.getElementById('opening-credits');
                if (splash) splash.style.display = 'none';
                window._revealedUnlocks = new Set();
              } catch(e) {}
            """)
        except Exception as e:
            print(f"warn skip onboarding: {e}")

        await page.wait_for_timeout(400)

        # Force lapsRun=3 (au-dessus du seuil unlock lapBonus typiquement km 1+ et tapValue km 0+)
        await page.evaluate("""
          try {
            STATE.lapsRun = 3;
            if (typeof applyProgressiveDisclosure === 'function') {
              applyProgressiveDisclosure();
            }
          } catch(e) { console.error('trigger:', e.message); }
        """)

        # Wait pour le delay 3s du hint + marge
        await page.wait_for_timeout(4000)

        # Check 1 : .upg-first-hint dans le DOM
        hint_count = await page.evaluate("""
          document.querySelectorAll('.upg-first-hint').length
        """)
        results["hint_dom_present"] = hint_count >= 1
        print(f"hint nodes: {hint_count}")

        # Check 2 : STATE._upgFirstHints a au moins une clé true
        flags = await page.evaluate("""
          (() => {
            try {
              if (!STATE._upgFirstHints) return {};
              return STATE._upgFirstHints;
            } catch(e) { return { err: e.message }; }
          })()
        """)
        print(f"_upgFirstHints: {flags}")
        results["flag_set"] = isinstance(flags, dict) and any(v is True for v in flags.values())

        # Snapshot des flags avant re-trigger
        flags_before = dict(flags) if isinstance(flags, dict) else {}

        # Cleanup any visible hint before re-trigger
        await page.evaluate("""
          document.querySelectorAll('.upg-first-hint').forEach(n => n.remove());
        """)

        # Re-trigger : reset lapsRun et re-appel
        await page.evaluate("""
          try {
            STATE.lapsRun = 3;
            window._revealedUnlocks = new Set();
            if (typeof applyProgressiveDisclosure === 'function') {
              applyProgressiveDisclosure();
            }
          } catch(e) { console.error('retrigger:', e.message); }
        """)
        await page.wait_for_timeout(4000)

        hint_count_2 = await page.evaluate("""
          document.querySelectorAll('.upg-first-hint').length
        """)
        print(f"hint nodes after re-trigger: {hint_count_2}")
        # On veut qu'il n'y ait PAS de nouveau hint (deja vu)
        results["no_second_hint"] = hint_count_2 == 0

        SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(SCREENSHOT), full_page=False)

        results["no_console_errors"] = len(errors) == 0

        await browser.close()

    ok = all(results.values())
    print("results:", results)
    print("errors:", len(errors))
    if errors:
        for e in errors[:5]:
            print("  -", e)
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
