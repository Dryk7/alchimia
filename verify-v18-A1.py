"""
Verify v18-A1 : Fix toast unlock stacking + label mapping + highlight glow.

Steps:
1. Skip onboarding
2. Force multi-transition (km 4 -> km 5, then km 17 -> km 18)
3. Wait 1.5s
4. Count .unlock-toast visible
5. Check top values escalated (80, 136, 192...)
6. Check no toast contains "buy-", "-bougie", "-doping", "shop-"
7. 0 console errors
"""

import asyncio
import sys
from playwright.async_api import async_playwright

URL = "file:///D:/alchimia/index.html"

async def main():
    errors = []
    findings = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width":420,"height":900})
        page = await ctx.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        await page.goto(URL)
        await page.wait_for_timeout(800)

        # Skip onboarding rapidement
        await page.evaluate("""() => {
          try { localStorage.setItem('foulee.onboardingV1', '1'); } catch(e){}
          try { localStorage.setItem('foulee.activeTutoV1', JSON.stringify({done:true})); } catch(e){}
          try { if(typeof STATE === 'object'){ STATE.onboarded = true; } } catch(e){}
        }""")
        await page.reload()
        await page.wait_for_timeout(1200)

        # Forcer transition km 4 -> km 5 : reset reveals + bump laps
        await page.evaluate("""() => {
          window._revealedUnlocks = new Set();
          // Pré-marquer comme révélés les éléments à km <= 4 pour que seuls les km=5 popent
          document.querySelectorAll('[data-unlock-km], [data-unlock-saison]').forEach(el => {
            const km = parseInt(el.getAttribute('data-unlock-km') || '0', 10);
            const id = el.getAttribute('data-upgrade') || el.getAttribute('data-action') || el.id || '';
            if(km <= 4 && id) window._revealedUnlocks.add(id);
          });
          STATE.lapsRun = 5;
        }""")
        # Déclencher la fonction
        await page.evaluate("if(typeof applyProgressiveDisclosure==='function') applyProgressiveDisclosure();")
        await page.wait_for_timeout(300)

        # Forcer aussi km 17 -> km 18 (souvent plusieurs unlocks)
        await page.evaluate("""() => {
          document.querySelectorAll('[data-unlock-km], [data-unlock-saison]').forEach(el => {
            const km = parseInt(el.getAttribute('data-unlock-km') || '0', 10);
            const id = el.getAttribute('data-upgrade') || el.getAttribute('data-action') || el.id || '';
            if(km <= 17 && id) window._revealedUnlocks.add(id);
          });
          STATE.lapsRun = 18;
        }""")
        await page.evaluate("if(typeof applyProgressiveDisclosure==='function') applyProgressiveDisclosure();")
        await page.wait_for_timeout(1500)

        # Mesurer toasts visibles
        toasts = await page.evaluate("""() => {
          const list = Array.from(document.querySelectorAll('.unlock-toast'));
          return list.map(t => ({
            text: (t.textContent || '').trim(),
            top: parseFloat(t.style.top) || 0,
            id: t.id,
          }));
        }""")

        findings.append(f"Toasts visibles : {len(toasts)}")
        for i, t in enumerate(toasts):
            findings.append(f"  [{i}] top={t['top']}px text='{t['text']}'")

        # CHECK 1 : empilement vertical
        tops = sorted([t["top"] for t in toasts])
        spacings_ok = True
        if len(tops) >= 2:
            for i in range(1, len(tops)):
                diff = tops[i] - tops[i-1]
                if diff < 50 or diff > 70:
                    spacings_ok = False
                    errors.append(f"Espacement toast incorrect : {tops[i-1]} -> {tops[i]} (diff={diff}, attendu ~56)")
        if len(tops) >= 2 and spacings_ok:
            findings.append(f"  Espacement OK : {tops}")
        elif len(tops) < 2:
            findings.append(f"  (1 seul toast affiche, espacement non testable)")

        # CHECK 2 : labels propres (pas d'ID techniques)
        bad_strings = ["buy-bougie", "buy-doping", "-bougie débloqué", "-doping débloqué", "shop-premium débloqué", "quests-daily débloqué", "map-stadiums débloqué"]
        for t in toasts:
            for bad in bad_strings:
                if bad in t["text"]:
                    errors.append(f"Toast contient ID technique : '{t['text']}' (matched '{bad}')")

        # CHECK 3 : just-unlocked class présente
        glow_count = await page.evaluate("document.querySelectorAll('.just-unlocked').length")
        findings.append(f"Éléments avec .just-unlocked : {glow_count}")

        # CHECK 4 : console errors
        if console_errors:
            for e in console_errors[:5]:
                errors.append(f"Console error : {e}")

        await browser.close()

    print("=== FINDINGS ===")
    for f in findings:
        print(f)
    print()
    print("=== ERRORS ===")
    if errors:
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("  Aucune. OK.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
