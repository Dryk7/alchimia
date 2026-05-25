"""
Verify v20-rivals : Rivaux nommés persistants + Boss déterministes T7+.

Steps:
1. Skip onboarding
2. Force lapsRun=50 -> getActiveRival() doit retourner Lucia Vent
3. Force lapsRun=60 -> getActiveBoss() doit retourner Draftbreaker
4. defeatBoss('draftbreaker') -> STATE.stars +=1, STATE.bosses.draftbreaker.defeated === true
5. 0 erreurs console
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

        # === TEST 1 : getActiveRival() à lapsRun=50 doit retourner Lucia Vent
        rival = await page.evaluate("""() => {
          if(typeof STATE !== 'object'){ return { error: 'STATE undefined' }; }
          STATE.lapsRun = 50;
          if(typeof getActiveRival !== 'function'){ return { error: 'getActiveRival missing' }; }
          const r = getActiveRival();
          return r ? { id: r.id, name: r.name, firstKm: r.firstKm, color: r.color } : null;
        }""")

        if not rival or rival.get("error"):
            findings.append(f"FAIL: getActiveRival error: {rival}")
            errors.append("getActiveRival failed")
        else:
            findings.append(f"getActiveRival(km=50) = {rival}")
            if rival.get("name") != "Lucia Vent":
                findings.append(f"FAIL: expected name 'Lucia Vent', got '{rival.get('name')}'")
                errors.append("wrong rival name")
            else:
                findings.append("OK: Rival = Lucia Vent (firstKm=50)")

        # === TEST 2 : getActiveBoss() à lapsRun=60 doit retourner Draftbreaker
        boss = await page.evaluate("""() => {
          STATE.lapsRun = 60;
          if(typeof getActiveBoss !== 'function'){ return { error: 'getActiveBoss missing' }; }
          const b = getActiveBoss();
          return b ? { id: b.id, name: b.name, spawnKm: b.spawnKm, type: b.type, defeated: b.defeated } : null;
        }""")

        if not boss or boss.get("error"):
            findings.append(f"FAIL: getActiveBoss error: {boss}")
            errors.append("getActiveBoss failed")
        else:
            findings.append(f"getActiveBoss(km=60) = {boss}")
            if boss.get("name") != "Draftbreaker":
                findings.append(f"FAIL: expected name 'Draftbreaker', got '{boss.get('name')}'")
                errors.append("wrong boss name")
            else:
                findings.append("OK: Boss = Draftbreaker (spawnKm=60, type=stamina_drain)")

        # === TEST 3 : defeatBoss('draftbreaker') -> stars +=1, defeated=true
        defeat = await page.evaluate("""() => {
          const before = { stars: STATE.stars || 0, defeated: STATE.bosses?.draftbreaker?.defeated };
          if(typeof defeatBoss !== 'function'){ return { error: 'defeatBoss missing' }; }
          defeatBoss('draftbreaker');
          const after = { stars: STATE.stars || 0, defeated: STATE.bosses?.draftbreaker?.defeated, gold: STATE.gold || 0 };
          return { before, after };
        }""")

        if defeat.get("error"):
            findings.append(f"FAIL: defeatBoss error: {defeat}")
            errors.append("defeatBoss failed")
        else:
            findings.append(f"defeatBoss before/after: {defeat}")
            if defeat["after"]["stars"] != defeat["before"]["stars"] + 1:
                findings.append(f"FAIL: stars did not increment (before={defeat['before']['stars']}, after={defeat['after']['stars']})")
                errors.append("stars not incremented")
            else:
                findings.append("OK: stars +=1 (reward boss)")
            if not defeat["after"]["defeated"]:
                findings.append(f"FAIL: bosses.draftbreaker.defeated should be true, got {defeat['after']['defeated']}")
                errors.append("defeated flag not set")
            else:
                findings.append("OK: bosses.draftbreaker.defeated = true")

        # === TEST 4 : getActiveBoss après défaite doit retourner null
        post_defeat = await page.evaluate("""() => {
          const b = getActiveBoss();
          return b ? { id: b.id, name: b.name } : null;
        }""")
        if post_defeat is None:
            findings.append("OK: getActiveBoss() = null après défaite (boss skipped car defeated)")
        else:
            findings.append(f"WARN: getActiveBoss() retourne encore {post_defeat} après défaite")

        # === TEST 5 : Vérification les 7 bosses présents + 5 rivaux
        stats = await page.evaluate("""() => {
          return {
            rivalsCount: Object.keys(STATE.rivals || {}).length,
            bossesCount: Object.keys(STATE.bosses || {}).length,
            rivalNames: Object.values(STATE.rivals || {}).map(r => r.name),
            bossNames: Object.values(STATE.bosses || {}).map(b => b.name)
          };
        }""")
        findings.append(f"Total rivaux: {stats['rivalsCount']}, bosses: {stats['bossesCount']}")
        findings.append(f"Rivaux: {stats['rivalNames']}")
        findings.append(f"Bosses: {stats['bossNames']}")
        if stats["rivalsCount"] != 5:
            errors.append(f"expected 5 rivals, got {stats['rivalsCount']}")
        if stats["bossesCount"] != 7:
            errors.append(f"expected 7 bosses, got {stats['bossesCount']}")

        # Console errors (filter benign)
        relevant_errors = [e for e in console_errors if "favicon" not in e.lower() and "ico" not in e.lower()]
        findings.append(f"Console errors: {len(relevant_errors)}")
        if relevant_errors:
            for e in relevant_errors[:5]:
                findings.append(f"  - {e[:200]}")
        if relevant_errors:
            errors.append("console errors present")

        await browser.close()

    print("=== VERIFY v20-rivals ===")
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
