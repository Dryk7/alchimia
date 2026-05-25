"""
QA VAGUE 22 — QA5 : Quetes saisonnieres (vague 20 P2 + branchements vague 21)

Verifie :
- updateSeasonQuests met a jour les 5 quetes
- claimSeasonQuest donne +2 stars + 50k gold
- doSaisonAscend / resetSeasonQuests efface tout
- HUD hint (#hud-quest-hint) apparait quand qch est claimable, disparait apres claim
- 0 erreur console
"""

import asyncio
import sys
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"

async def main():
    errors = []
    findings = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
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
        await page.wait_for_timeout(1500)

        # Sanity : helpers exposes
        sanity = await page.evaluate("""() => ({
          hasUpdate: typeof updateSeasonQuests === 'function',
          hasClaim: typeof claimSeasonQuest === 'function',
          hasReset: typeof resetSeasonQuests === 'function',
          hasOpen: typeof openSeasonQuests === 'function',
          hasState: !!STATE && !!STATE.seasonQuests,
          ids: STATE && STATE.seasonQuests ? Object.keys(STATE.seasonQuests) : []
        })""")
        findings.append(f"Sanity helpers : update={sanity['hasUpdate']} claim={sanity['hasClaim']} reset={sanity['hasReset']} open={sanity['hasOpen']}")
        findings.append(f"  STATE.seasonQuests ids : {sanity['ids']}")
        if not sanity['hasUpdate']: errors.append("updateSeasonQuests absent")
        if not sanity['hasClaim']:  errors.append("claimSeasonQuest absent")
        if not sanity['hasReset']:  errors.append("resetSeasonQuests absent")
        if not sanity['hasState']:  errors.append("STATE.seasonQuests absent")

        # =========================================================
        # Test 1 - MARATHONIEN
        # =========================================================
        t1 = await page.evaluate("""() => {
          STATE._seasonNoDoping = true;
          STATE.lapsRun = 99;
          updateSeasonQuests();
          const at99 = JSON.parse(JSON.stringify(STATE.seasonQuests.marathonien));
          STATE.lapsRun = 100;
          updateSeasonQuests();
          const at100 = JSON.parse(JSON.stringify(STATE.seasonQuests.marathonien));
          // Aussi : avec doping a 100, ne doit PAS done
          STATE._seasonNoDoping = false;
          updateSeasonQuests();
          const at100doping = JSON.parse(JSON.stringify(STATE.seasonQuests.marathonien));
          // Restore pour suite
          STATE._seasonNoDoping = true;
          updateSeasonQuests();
          return { at99, at100, at100doping };
        }""")
        findings.append(f"T1 marathonien @99 : progress={t1['at99']['progress']} done={t1['at99']['done']}")
        findings.append(f"T1 marathonien @100 noDoping : progress={t1['at100']['progress']} done={t1['at100']['done']}")
        findings.append(f"T1 marathonien @100 +doping : done={t1['at100doping']['done']}")
        if t1['at99']['done']:               errors.append("T1: marathonien done=true a 99 km (devrait etre false)")
        if t1['at99']['progress'] != 99:     errors.append(f"T1: marathonien progress @99 != 99 (got {t1['at99']['progress']})")
        if not t1['at100']['done']:          errors.append("T1: marathonien done=false a 100 km sans doping (devrait etre true)")
        if t1['at100doping']['done']:        errors.append("T1: marathonien done=true a 100 km AVEC doping (devrait etre false)")

        # =========================================================
        # Test 2 - FUNAMBULE
        # =========================================================
        t2 = await page.evaluate("""() => {
          STATE._seasonHurdleStreak = 49;
          updateSeasonQuests();
          const at49 = JSON.parse(JSON.stringify(STATE.seasonQuests.funambule));
          STATE._seasonHurdleStreak = 50;
          updateSeasonQuests();
          const at50 = JSON.parse(JSON.stringify(STATE.seasonQuests.funambule));
          return { at49, at50 };
        }""")
        findings.append(f"T2 funambule @49 : progress={t2['at49']['progress']} done={t2['at49']['done']}")
        findings.append(f"T2 funambule @50 : progress={t2['at50']['progress']} done={t2['at50']['done']}")
        if t2['at49']['progress'] != 49: errors.append(f"T2: funambule progress @49 != 49 (got {t2['at49']['progress']})")
        if t2['at49']['done']:           errors.append("T2: funambule done=true @49 (devrait etre false)")
        if not t2['at50']['done']:       errors.append("T2: funambule done=false @50 (devrait etre true)")

        # =========================================================
        # Test 3 - ECONOME (8 upgrades a 5)
        # =========================================================
        t3 = await page.evaluate("""() => {
          ['upgradeTapValue','upgradeCritChance','upgradeLapBonus','upgradeAutoTap','upgradeEndurance','upgradeBaseSpeed','upgradeEagleEye','upgradeCruiseControl']
            .forEach(k => STATE[k] = 5);
          updateSeasonQuests();
          return JSON.parse(JSON.stringify(STATE.seasonQuests.econome));
        }""")
        findings.append(f"T3 econome 8x5 : progress={t3['progress']} done={t3['done']}")
        if t3['progress'] != 40: errors.append(f"T3: econome progress != 40 (got {t3['progress']})")
        if not t3['done']:       errors.append("T3: econome done=false avec 8 upgrades a 5 (devrait etre true)")

        # =========================================================
        # Test 4 - SPRINTER (lit #runner-pace textContent)
        # =========================================================
        t4 = await page.evaluate("""() => {
          // Reset progress sprinter
          STATE.seasonQuests.sprinter.progress = 0;
          // Force le textContent du HUD pace
          let el = document.getElementById('runner-pace');
          const created = !el;
          if(!el){
            el = document.createElement('div');
            el.id = 'runner-pace';
            document.body.appendChild(el);
          }
          const oldText = el.textContent;
          el.textContent = '35';
          updateSeasonQuests();
          const result = JSON.parse(JSON.stringify(STATE.seasonQuests.sprinter));
          // Restore (mais le sprinter cumule le max donc reste a 35 — OK pour la suite)
          if(created){ el.remove(); } else { el.textContent = oldText; }
          return { result, paceElExisted: !created };
        }""")
        findings.append(f"T4 sprinter avec #runner-pace=35 : progress={t4['result']['progress']} done={t4['result']['done']} (HUD #runner-pace existait deja={t4['paceElExisted']})")
        if t4['result']['progress'] < 35: errors.append(f"T4: sprinter progress < 35 (got {t4['result']['progress']})")
        if not t4['result']['done']:      errors.append("T4: sprinter done=false avec pace=35 (devrait etre true)")

        # =========================================================
        # Test 5 - COLLECTOR
        # =========================================================
        t5 = await page.evaluate("""() => {
          STATE._seasonChestsOpened = 2;
          updateSeasonQuests();
          return JSON.parse(JSON.stringify(STATE.seasonQuests.collector));
        }""")
        findings.append(f"T5 collector @2 chests : progress={t5['progress']} done={t5['done']}")
        if t5['progress'] != 2: errors.append(f"T5: collector progress != 2 (got {t5['progress']})")
        if not t5['done']:      errors.append("T5: collector done=false avec 2 chests (devrait etre true)")

        # =========================================================
        # Test CLAIM (marathonien)
        # =========================================================
        claim_check = await page.evaluate("""() => {
          // S'assurer que marathonien.done = true
          STATE._seasonNoDoping = true;
          STATE.lapsRun = 100;
          STATE.seasonQuests.marathonien.claimed = false;
          updateSeasonQuests();
          const before = { gold: STATE.gold || 0, stars: STATE.stars || 0, claimed: STATE.seasonQuests.marathonien.claimed };
          const ok = claimSeasonQuest('marathonien');
          const after = { gold: STATE.gold || 0, stars: STATE.stars || 0, claimed: STATE.seasonQuests.marathonien.claimed };
          // Re-claim doit retourner false
          const okAgain = claimSeasonQuest('marathonien');
          return { ok, okAgain, before, after, dGold: after.gold - before.gold, dStars: after.stars - before.stars };
        }""")
        findings.append(f"Claim marathonien : ok={claim_check['ok']} dGold={claim_check['dGold']} dStars={claim_check['dStars']} claimed={claim_check['after']['claimed']}")
        findings.append(f"  Re-claim ok={claim_check['okAgain']} (doit etre false)")
        if not claim_check['ok']:                errors.append("Claim: claimSeasonQuest('marathonien') retourne false")
        if claim_check['dGold'] != 50000:        errors.append(f"Claim: dGold != 50000 (got {claim_check['dGold']})")
        if claim_check['dStars'] != 2:           errors.append(f"Claim: dStars != 2 (got {claim_check['dStars']})")
        if not claim_check['after']['claimed']:  errors.append("Claim: claimed=false apres claim")
        if claim_check['okAgain']:               errors.append("Claim: re-claim retourne true (devrait etre false)")

        # =========================================================
        # Test HUD HINT (apparait quand qch claimable)
        # =========================================================
        hint_check = await page.evaluate("""async () => {
          // Reset complet pour isolation
          if(typeof resetSeasonQuests === 'function') resetSeasonQuests();
          STATE.lapsRun = 0;
          ['upgradeTapValue','upgradeCritChance','upgradeLapBonus','upgradeAutoTap','upgradeEndurance','upgradeBaseSpeed','upgradeEagleEye','upgradeCruiseControl']
            .forEach(k => STATE[k] = 0);
          const paceEl = document.getElementById('runner-pace');
          if(paceEl) paceEl.textContent = '0';
          // Setup : funambule SEULE done, non claimed -> 1 claimable
          STATE._seasonHurdleStreak = 50;
          STATE.seasonQuests.funambule.claimed = false;
          updateSeasonQuests();
          // Vérif : exactement 1 claimable
          const claimableBefore = Object.values(STATE.seasonQuests).filter(q => q.done && !q.claimed).length;
          // Le hint est cree dans updateRunnerHUD. On l'invoke.
          if(typeof updateRunnerHUD === 'function') updateRunnerHUD();
          await new Promise(r => setTimeout(r, 60));
          const hintBefore = document.getElementById('hud-quest-hint');
          const visibleBefore = !!hintBefore;
          const textBefore = hintBefore ? hintBefore.textContent : null;
          // Claim → hint doit disparaitre apres updateRunnerHUD
          claimSeasonQuest('funambule');
          const claimableAfter = Object.values(STATE.seasonQuests).filter(q => q.done && !q.claimed).length;
          if(typeof updateRunnerHUD === 'function') updateRunnerHUD();
          await new Promise(r => setTimeout(r, 60));
          const hintAfter = document.getElementById('hud-quest-hint');
          const visibleAfter = !!hintAfter;
          return { visibleBefore, textBefore, visibleAfter, claimableBefore, claimableAfter };
        }""")
        findings.append(f"  claimable counts : before={hint_check['claimableBefore']} after_claim={hint_check['claimableAfter']}")
        findings.append(f"HUD hint : claimable=1 -> visible={hint_check['visibleBefore']} text={hint_check['textBefore']!r}")
        findings.append(f"HUD hint : apres claim -> visible={hint_check['visibleAfter']} (doit etre false)")
        if not hint_check['visibleBefore']: errors.append("HUD hint: #hud-quest-hint absent quand qch claimable")
        if hint_check['visibleAfter']:      errors.append("HUD hint: #hud-quest-hint reste visible apres claim (devrait disparaitre)")

        # =========================================================
        # Test RESET ASCENSION (via resetSeasonQuests qui est aussi appele dans doSaisonAscend)
        # =========================================================
        reset_check = await page.evaluate("""() => {
          // Set un etat avec plusieurs quetes done/claimed/progress
          STATE._seasonHurdleStreak = 50;
          STATE._seasonChestsOpened = 2;
          STATE.lapsRun = 100;
          STATE._seasonNoDoping = true;
          updateSeasonQuests();
          STATE.seasonQuests.marathonien.claimed = true;
          STATE.seasonQuests.collector.claimed = false;
          const before = Object.fromEntries(Object.entries(STATE.seasonQuests).map(([k,q]) => [k, {p:q.progress, d:q.done, c:q.claimed}]));
          resetSeasonQuests();
          const after = Object.fromEntries(Object.entries(STATE.seasonQuests).map(([k,q]) => [k, {p:q.progress, d:q.done, c:q.claimed}]));
          return {
            before, after,
            anyDoneAfter: Object.values(STATE.seasonQuests).some(q => q.done),
            anyClaimedAfter: Object.values(STATE.seasonQuests).some(q => q.claimed),
            anyProgressAfter: Object.values(STATE.seasonQuests).some(q => q.progress > 0),
            streak: STATE._seasonHurdleStreak,
            chests: STATE._seasonChestsOpened,
            noDoping: STATE._seasonNoDoping
          };
        }""")
        findings.append(f"Reset : anyDoneAfter={reset_check['anyDoneAfter']} anyClaimedAfter={reset_check['anyClaimedAfter']} anyProgressAfter={reset_check['anyProgressAfter']}")
        findings.append(f"  trackers reset : streak={reset_check['streak']} chests={reset_check['chests']} noDoping={reset_check['noDoping']}")
        if reset_check['anyDoneAfter']:     errors.append("Reset: au moins une quete reste done=true apres reset")
        if reset_check['anyClaimedAfter']:  errors.append("Reset: au moins une quete reste claimed=true apres reset")
        if reset_check['anyProgressAfter']: errors.append("Reset: au moins une quete a progress > 0 apres reset")
        if reset_check['streak'] != 0:      errors.append(f"Reset: _seasonHurdleStreak != 0 (got {reset_check['streak']})")
        if reset_check['chests'] != 0:      errors.append(f"Reset: _seasonChestsOpened != 0 (got {reset_check['chests']})")
        if not reset_check['noDoping']:     errors.append("Reset: _seasonNoDoping != true apres reset")

        # =========================================================
        # Console errors
        # =========================================================
        if console_errors:
            for e in console_errors[:5]:
                errors.append(f"Console: {e[:200]}")

        await browser.close()

    print("=" * 60)
    print("QA5 — QUETES SAISONNIERES")
    print("=" * 60)
    for f in findings:
        print(f"  {f}")
    print()
    if errors:
        print(f"ERRORS ({len(errors)}) :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("OK — Tous les tests passent")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
