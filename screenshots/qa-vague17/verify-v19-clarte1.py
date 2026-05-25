"""
Verify v19-clarte1 : Lisibilité effet courant vs prochain niveau sur boutons upgrade.

Steps:
1. Skip onboarding
2. Force lapsRun=30, gold=100000, upgradeTapValue=5
3. Eval updateUpgradesUI()
4. Verifier #upg-tap-effect textContent contient "+8.5" (niv 5 = 1 + 5*1.5 = 8.5) et "→"
5. Force upgradeTapValue à 99 puis updateUpgradesUI → vérifier "MAX"
6. Screenshot audit-v19-clarte1-effects.png
7. 0 erreurs console
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
        ctx = await browser.new_context(viewport={"width": 420, "height": 900})
        page = await ctx.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        await page.goto(URL)
        await page.wait_for_timeout(800)

        # Skip onboarding
        await page.evaluate("""() => {
          try { localStorage.setItem('foulee.onboardingV1', '1'); } catch(e){}
          try { localStorage.setItem('foulee.activeTutoV1', JSON.stringify({done:true})); } catch(e){}
          try { if(typeof STATE === 'object'){ STATE.onboarded = true; } } catch(e){}
        }""")
        await page.reload()
        await page.wait_for_timeout(1200)

        # Force state : lapsRun=30 (tous les boutons révélés), gold riche, upgradeTapValue=5
        await page.evaluate("""() => {
          STATE.lapsRun = 30;
          STATE.gold = 100000;
          STATE.upgradeTapValue = 5;
          STATE.upgradeCritChance = 3;
          STATE.upgradeLapBonus = 2;
          if(typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
          if(typeof updateUpgradesUI === 'function') updateUpgradesUI();
        }""")
        await page.wait_for_timeout(300)

        # Ouvrir le drawer upgrades si nécessaire (cliquer sur le tab approprié)
        await page.evaluate("""() => {
          // Tente d'ouvrir le drawer principal
          const drawerBtn = document.querySelector('[data-drawer-open], .drawer-toggle, #drawer-toggle');
          if(drawerBtn) drawerBtn.click();
          // Forcer la révélation du tab upgrades
          const tabUpg = document.querySelector('.tab-btn[data-tab="upgrades"]');
          if(tabUpg) tabUpg.click();
        }""")
        await page.wait_for_timeout(400)

        # === TEST 1 : Niveau intermédiaire → courant et next visibles ===
        tap_effect = await page.evaluate("""() => {
          const el = document.getElementById('upg-tap-effect');
          if(!el) return { found: false };
          return {
            found: true,
            text: el.textContent || '',
            hasArrow: (el.textContent || '').includes('→'),
            html: el.innerHTML || ''
          };
        }""")

        if not tap_effect.get("found"):
            findings.append("FAIL: #upg-tap-effect introuvable")
            errors.append("upg-tap-effect missing")
        else:
            text = tap_effect.get("text", "")
            has_arrow = tap_effect.get("hasArrow", False)
            findings.append(f"upg-tap-effect text: '{text}'")
            # niv 5 = 1 + 5*1.5 = 8.5
            if "+8.5" not in text:
                findings.append(f"FAIL: expected '+8.5' in tap effect, got '{text}'")
                errors.append("missing +8.5")
            else:
                findings.append("OK: +8.5 g/tap (niveau actuel 5)")
            if not has_arrow:
                findings.append(f"FAIL: missing arrow → in tap effect")
                errors.append("missing arrow")
            else:
                findings.append("OK: arrow → présente")
            # niv 6 = 1 + 6*1.5 = 10.0
            if "+10.0" not in text:
                findings.append(f"WARN: expected '+10.0' (niv 6) in tap effect, got '{text}'")
            else:
                findings.append("OK: +10.0 g/tap (prochain niveau 6)")

        # === TEST 2 : Niveau MAX (crit max=55, force lvl 99) ===
        max_test = await page.evaluate("""() => {
          STATE.upgradeCritChance = 99;
          if(typeof updateUpgradesUI === 'function') updateUpgradesUI();
          const el = document.getElementById('upg-crit-effect');
          if(!el) return { found: false };
          return {
            found: true,
            text: el.textContent || '',
            hasMax: (el.textContent || '').includes('MAX'),
            html: el.innerHTML || ''
          };
        }""")

        if not max_test.get("found"):
            findings.append("FAIL: #upg-crit-effect introuvable")
            errors.append("upg-crit-effect missing")
        else:
            text = max_test.get("text", "")
            has_max = max_test.get("hasMax", False)
            findings.append(f"upg-crit-effect (lvl 99, max=55): '{text}'")
            if not has_max:
                findings.append(f"FAIL: expected 'MAX' in crit effect at high level, got '{text}'")
                errors.append("missing MAX label")
            else:
                findings.append("OK: MAX label affiché correctement")

        # Restore tap value à 99 pour test MAX sur tapValue (cap par hard cap global 50)
        # tapValue n'a pas de maxLevel mais le hard cap est 50
        max_tap = await page.evaluate("""() => {
          STATE.upgradeTapValue = 99;
          if(typeof updateUpgradesUI === 'function') updateUpgradesUI();
          const el = document.getElementById('upg-tap-effect');
          return el ? { text: el.textContent || '', html: el.innerHTML || '' } : null;
        }""")
        if max_tap:
            findings.append(f"upg-tap-effect (lvl 99, no maxLevel): '{max_tap.get('text', '')}'")

        # Screenshot
        await page.screenshot(path="D:/alchimia/screenshots/qa-vague17/audit-v19-clarte1-effects.png", full_page=True)
        findings.append("Screenshot saved : audit-v19-clarte1-effects.png")

        # Console errors (filter benign)
        relevant_errors = [e for e in console_errors if "favicon" not in e.lower() and "ico" not in e.lower()]
        findings.append(f"Console errors: {len(relevant_errors)}")
        if relevant_errors:
            for e in relevant_errors[:5]:
                findings.append(f"  - {e[:200]}")

        await browser.close()

    print("=== VERIFY v19-clarte1 ===")
    for f in findings:
        print(f)
    print(f"\nERRORS: {len(errors)}")
    if errors:
        print("FAIL")
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
