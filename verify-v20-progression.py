"""
Verify v20-progression : Systeme stats progression (daily + lifetime).

Steps:
1. Skip onboarding
2. Eval trackDailyStat('km', 5); trackDailyStat('gold', 1000)
3. Verifier STATE.lifetimeStats.totalKm === 5
4. Eval openProgression()
5. Verifier #progression-graph et #progression-lifetime ont du contenu
6. 0 erreurs console
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

        # CHECK 1 : trackDailyStat existe
        has_helpers = await page.evaluate("""() => {
          return typeof trackDailyStat === 'function'
              && typeof getRecentDailyStats === 'function'
              && typeof openProgression === 'function'
              && typeof renderProgression === 'function';
        }""")
        findings.append(f"Helpers exposes : {has_helpers}")
        if not has_helpers:
            errors.append("trackDailyStat / openProgression / renderProgression manquants")

        # CHECK 2 : Reset puis trackDailyStat
        result = await page.evaluate("""() => {
          // Reset propre
          STATE.dailyStats = {};
          STATE.lifetimeStats = { totalKm:0, totalGold:0, totalTaps:0, totalHurdles:0, totalNpcs:0, totalChests:0 };
          trackDailyStat('km', 5);
          trackDailyStat('gold', 1000);
          trackDailyStat('taps', 25);
          trackDailyStat('hurdles', 3);
          trackDailyStat('npcs', 7);
          return {
            totalKm: STATE.lifetimeStats.totalKm,
            totalGold: STATE.lifetimeStats.totalGold,
            totalTaps: STATE.lifetimeStats.totalTaps,
            totalHurdles: STATE.lifetimeStats.totalHurdles,
            totalNpcs: STATE.lifetimeStats.totalNpcs,
            dailyKeysCount: Object.keys(STATE.dailyStats).length
          };
        }""")
        findings.append(f"lifetimeStats apres tracks : {result}")
        if result['totalKm'] != 5:
            errors.append(f"totalKm = {result['totalKm']} (attendu 5)")
        if result['totalGold'] != 1000:
            errors.append(f"totalGold = {result['totalGold']} (attendu 1000)")
        if result['totalTaps'] != 25:
            errors.append(f"totalTaps = {result['totalTaps']} (attendu 25)")
        if result['totalHurdles'] != 3:
            errors.append(f"totalHurdles = {result['totalHurdles']} (attendu 3)")
        if result['totalNpcs'] != 7:
            errors.append(f"totalNpcs = {result['totalNpcs']} (attendu 7)")
        if result['dailyKeysCount'] != 1:
            errors.append(f"dailyStats keys count = {result['dailyKeysCount']} (attendu 1)")

        # CHECK 3 : openProgression()
        opened = await page.evaluate("""() => {
          try {
            openProgression();
            return { ok: true };
          } catch(e){
            return { ok: false, err: String(e) };
          }
        }""")
        if not opened.get('ok'):
            errors.append(f"openProgression() throw : {opened.get('err')}")
        await page.wait_for_timeout(400)

        # CHECK 4 : contenu modale
        modal_info = await page.evaluate("""() => {
          const m = document.getElementById('progression-modal');
          const g = document.getElementById('progression-graph');
          const l = document.getElementById('progression-lifetime');
          return {
            modalShown: m ? m.classList.contains('show') : false,
            graphHasContent: g ? (g.innerHTML.length > 50) : false,
            graphLen: g ? g.innerHTML.length : 0,
            lifetimeHasContent: l ? (l.innerHTML.length > 50) : false,
            lifetimeLen: l ? l.innerHTML.length : 0,
            graphSnippet: g ? g.innerHTML.substring(0, 200) : '',
            lifetimeSnippet: l ? l.innerHTML.substring(0, 200) : ''
          };
        }""")
        findings.append(f"Modal shown : {modal_info['modalShown']}")
        findings.append(f"Graph innerHTML len : {modal_info['graphLen']}")
        findings.append(f"Lifetime innerHTML len : {modal_info['lifetimeLen']}")
        findings.append(f"Graph snippet : {modal_info['graphSnippet'][:120]}")
        findings.append(f"Lifetime snippet : {modal_info['lifetimeSnippet'][:120]}")

        if not modal_info['modalShown']:
            errors.append("Modal #progression-modal pas en classe 'show'")
        if not modal_info['graphHasContent']:
            errors.append(f"#progression-graph vide (len={modal_info['graphLen']})")
        if not modal_info['lifetimeHasContent']:
            errors.append(f"#progression-lifetime vide (len={modal_info['lifetimeLen']})")

        # CHECK 5 : getRecentDailyStats retourne 7 jours
        recent_count = await page.evaluate("""() => {
          const arr = getRecentDailyStats(7);
          return arr.length;
        }""")
        findings.append(f"getRecentDailyStats(7) length : {recent_count}")
        if recent_count != 7:
            errors.append(f"getRecentDailyStats(7) len={recent_count} (attendu 7)")

        # Screenshot
        try:
            await page.screenshot(path="D:/alchimia/audit-v20-progression.png")
        except Exception as e:
            findings.append(f"Screenshot failed : {e}")

        await browser.close()

    print("=== FINDINGS ===")
    for f in findings:
        print("  " + f)

    if console_errors:
        print("\n=== CONSOLE ERRORS ===")
        for e in console_errors:
            print("  " + e)
            errors.append("CONSOLE: " + e)

    if errors:
        print("\n=== ERRORS ===")
        for e in errors:
            print("  X " + e)
        sys.exit(1)
    else:
        print("\nOK : tous les checks passent")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
