"""
Verify v18-A5 : Fix STATS pane vide dans drawer.

Steps:
1. Skip onboarding
2. Force lapsRun=30, totalChestsOpened=3
3. Cliquer sur tab STATS
4. Wait 500ms
5. Verifier que #stats-quick a >0 children visibles
6. Verifier textContent contient "30 km" et "3"
7. Screenshot audit-v18-A5-stats-pane.png
8. 0 erreurs console
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

        # Force state : lapsRun=30, totalChestsOpened=3 (et reveal tab stats car laps >= 12)
        await page.evaluate("""() => {
          STATE.lapsRun = 30;
          STATE.totalChestsOpened = 3;
          STATE.maxComboReached = 7;
          STATE.totalNpcOvertaken = 12;
          STATE.hurdlesSuccess = 5;
          STATE.totalGoldEarned = 4500;
          if(typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
        }""")
        await page.wait_for_timeout(300)

        # Cliquer sur le tab STATS
        clicked = await page.evaluate("""() => {
          const btn = document.querySelector('.tab-btn[data-tab="stats"]');
          if(!btn) return false;
          btn.click();
          return true;
        }""")
        if not clicked:
            errors.append("Tab STATS button introuvable")
        await page.wait_for_timeout(500)

        # Lire l'etat du pane
        pane_info = await page.evaluate("""() => {
          const pane = document.querySelector('[data-pane="stats"]');
          const quick = document.getElementById('stats-quick');
          return {
            paneVisible: pane ? pane.classList.contains('active') : false,
            quickExists: !!quick,
            quickChildren: quick ? quick.children.length : 0,
            quickHTML: quick ? quick.innerHTML.substring(0, 300) : '',
            text: quick ? (quick.textContent || '').trim() : '',
            stqDist: document.getElementById('stq-dist')?.textContent || '',
            stqChests: document.getElementById('stq-chests')?.textContent || '',
            stqCombo: document.getElementById('stq-combo')?.textContent || '',
            stqNpcs: document.getElementById('stq-npcs')?.textContent || '',
            stqHurdles: document.getElementById('stq-hurdles')?.textContent || '',
            stqTotalg: document.getElementById('stq-totalg')?.textContent || ''
          };
        }""")

        findings.append(f"Pane STATS visible : {pane_info['paneVisible']}")
        findings.append(f"#stats-quick existe : {pane_info['quickExists']}")
        findings.append(f"  children count : {pane_info['quickChildren']}")
        findings.append(f"  stq-dist : '{pane_info['stqDist']}'")
        findings.append(f"  stq-chests : '{pane_info['stqChests']}'")
        findings.append(f"  stq-combo : '{pane_info['stqCombo']}'")
        findings.append(f"  stq-npcs : '{pane_info['stqNpcs']}'")
        findings.append(f"  stq-hurdles : '{pane_info['stqHurdles']}'")
        findings.append(f"  stq-totalg : '{pane_info['stqTotalg']}'")

        # CHECK 1 : >0 children
        if pane_info['quickChildren'] < 1:
            errors.append(f"#stats-quick a 0 children (attendu >0). HTML='{pane_info['quickHTML']}'")

        # CHECK 2 : "30 km" dans le texte
        if "30 km" not in pane_info['text']:
            errors.append(f"Texte ne contient pas '30 km'. text='{pane_info['text'][:200]}'")

        # CHECK 3 : "3" dans coffres
        if pane_info['stqChests'] != "3":
            errors.append(f"stq-chests != '3' (got '{pane_info['stqChests']}')")

        # Screenshot
        try:
            await page.screenshot(path="D:/alchimia/audit-v18-A5-stats-pane.png", full_page=False)
            findings.append("Screenshot OK : audit-v18-A5-stats-pane.png")
        except Exception as e:
            errors.append(f"Screenshot fail : {e}")

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
