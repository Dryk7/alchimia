"""
VAGUE 20 — Verify Season Quests
Tests : init STATE.seasonQuests / updateSeasonQuests / claimSeasonQuest
        marathonien quest end-to-end (force lapsRun=100, claim, check +2 stars)
"""
import asyncio, sys, os, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from playwright.async_api import async_playwright

INDEX_URL = "file://" + str(pathlib.Path(__file__).parent / "index.html").replace("\\", "/")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width":390,"height":844})
        page = await ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(f"PAGEERROR: {e}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE.{msg.type}: {msg.text}") if msg.type == "error" else None)

        await page.goto(INDEX_URL)
        await page.wait_for_load_state("networkidle", timeout=10000)
        # Skip onboarding via localStorage flag
        await page.evaluate("""() => {
            try { localStorage.setItem('foulee.onboardingDone','true'); } catch(e){}
        }""")
        await asyncio.sleep(1.5)

        # === TEST 1 : STATE.seasonQuests initialisé
        has_quests = await page.evaluate("() => !!(window.STATE && window.STATE.seasonQuests && window.STATE.seasonQuests.marathonien)")
        print(f"(1) STATE.seasonQuests init : {'OK' if has_quests else 'FAIL'}")

        # === TEST 2 : Force conditions + updateSeasonQuests
        await page.evaluate("""() => {
            STATE.lapsRun = 100;
            STATE._seasonNoDoping = true;
            STATE.upgradeTapValue = 5;
            STATE.upgradeCritChance = 5;
            STATE.upgradeLapBonus = 5;
            STATE.upgradeAutoTap = 5;
            STATE.upgradeEndurance = 5;
            STATE.upgradeBaseSpeed = 5;
            STATE.upgradeEagleEye = 5;
            STATE.upgradeCruiseControl = 5;
            STATE._seasonHurdleStreak = 50;
            STATE._seasonChestsOpened = 2;
            if(typeof updateSeasonQuests === 'function') updateSeasonQuests();
        }""")
        results = await page.evaluate("""() => ({
            marathonien: STATE.seasonQuests.marathonien.done,
            funambule:   STATE.seasonQuests.funambule.done,
            econome:     STATE.seasonQuests.econome.done,
            collector:   STATE.seasonQuests.collector.done,
            econome_progress: STATE.seasonQuests.econome.progress
        })""")
        print(f"(2) updateSeasonQuests : marathonien={results['marathonien']} funambule={results['funambule']} econome={results['econome']} ({results['econome_progress']}/40) collector={results['collector']}")
        update_ok = results['marathonien'] and results['funambule'] and results['econome'] and results['collector']

        # === TEST 3 : claimSeasonQuest marathonien → +2 stars
        starsBefore = await page.evaluate("() => STATE.stars || 0")
        claimed = await page.evaluate("() => claimSeasonQuest('marathonien')")
        starsAfter = await page.evaluate("() => STATE.stars || 0")
        delta = starsAfter - starsBefore
        print(f"(3) claimSeasonQuest('marathonien') : claimed={claimed} stars {starsBefore}→{starsAfter} (Δ={delta})")
        claim_ok = claimed and (delta == 2)

        # === TEST 4 : openSeasonQuests modal
        modal_exists = await page.evaluate("() => !!document.getElementById('season-quests-modal')")
        await page.evaluate("() => openSeasonQuests && openSeasonQuests()")
        await asyncio.sleep(0.4)
        modal_visible = await page.evaluate("() => document.getElementById('season-quests-modal')?.classList.contains('show')")
        list_html = await page.evaluate("() => document.getElementById('season-quests-list')?.innerHTML?.length || 0")
        print(f"(4) Modale : exists={modal_exists} visible={modal_visible} list_html_len={list_html}")
        modal_ok = modal_exists and modal_visible and list_html > 100

        # === TEST 5 : resetSeasonQuests via doSaisonAscend hook
        await page.evaluate("""() => {
            if(typeof resetSeasonQuests === 'function') resetSeasonQuests();
        }""")
        reset_check = await page.evaluate("""() => ({
            done: STATE.seasonQuests.marathonien.done,
            claimed: STATE.seasonQuests.marathonien.claimed,
            noDoping: STATE._seasonNoDoping,
            chests: STATE._seasonChestsOpened,
            hurdleStreak: STATE._seasonHurdleStreak
        })""")
        reset_ok = (not reset_check['done'] and not reset_check['claimed']
                    and reset_check['noDoping'] is True
                    and reset_check['chests'] == 0
                    and reset_check['hurdleStreak'] == 0)
        print(f"(5) resetSeasonQuests : {reset_check} → {'OK' if reset_ok else 'FAIL'}")

        # Erreurs console
        console_errors = [e for e in errors if 'PAGEERROR' in e or 'CONSOLE.error' in e]
        print(f"\n=== Erreurs console : {len(console_errors)}")
        for e in console_errors[:10]:
            print("  -", e[:200])

        print("\n===== RÉSUMÉ =====")
        print(f"(1) STATE init        : {'OK' if has_quests else 'FAIL'}")
        print(f"(2) updateSeasonQuests: {'OK' if update_ok else 'FAIL'}")
        print(f"(3) claimSeasonQuest  : {'OK' if claim_ok else 'FAIL'}")
        print(f"(4) Modale            : {'OK' if modal_ok else 'FAIL'}")
        print(f"(5) resetSeasonQuests : {'OK' if reset_ok else 'FAIL'}")
        print(f"Erreurs console       : {len(console_errors)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
