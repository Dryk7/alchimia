"""
AUDIT H - Visibilite et decouvrabilite du Star Tree (Prestige) - Vague 17
- Viewport 540x960
- Skip onboarding
- Force STATE.lapsRun=110, chapter=2, saison=2, stars=5, totalStarsEarned=5
- Screenshot HUD (pill etoiles visible ?)
- Ouvrir menu burger : screenshot, verifier PRESTIGE visible
- Cliquer PRESTIGE -> screenshot modale
- Eval : 8 nodes ? Couts ? Boutons actifs ?
- Test : buyStarNode('tapPower') -> bouton update visuellement ?
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(__file__).parent
URL = "http://localhost:8770/index.html"


async def skip_onboarding(page):
    await page.evaluate(
        """
        () => {
          try {
            if (typeof STATE !== 'undefined') {
              STATE.onboardingDone = true;
              STATE.introSeen = true;
              STATE.storySeen = true;
              STATE.hasSeenIntro = true;
              STATE.tutorialDone = true;
              STATE.hasOnboarded = true;
              STATE.skipCinematic = true;
            }
            document.querySelectorAll(
              '.cinematic, .opening-cinematic, .splash, .intro, .story-overlay, [data-onboarding], #epic-km100'
            ).forEach(el => el.remove());
            if (typeof closeAllModals === 'function') closeAllModals();
            if (typeof startGame === 'function') startGame();
          } catch(e){}
        }
        """
    )
    await page.wait_for_timeout(600)
    for sel in [
        "#start-btn", ".start-game-btn", "button:has-text('DEPART')",
        "button:has-text('DEMARRER')", "button:has-text('JOUER')",
        "button:has-text('PRENDRE')"
    ]:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click()
                await page.wait_for_timeout(250)
                break
        except Exception:
            pass


async def force_state(page):
    await page.evaluate(
        """
        () => {
          if (typeof STATE === 'undefined') return;
          STATE.lapsRun = 110;
          STATE.chapter = 2;
          STATE.saison = 2;
          STATE.stars = 5;
          STATE.totalStars = 5;
          STATE.totalStarsEarned = 5;
          STATE.ascensions = 1;
          STATE.gold = 100000;
          // remove any leftover epic overlay
          document.querySelectorAll('#epic-km100, .epic-overlay, .modal.show').forEach(el => {
            if (el.id !== 'menu-modal' && el.id !== 'star-tree-modal') el.remove();
          });
          if (typeof renderStats === 'function') renderStats();
          if (typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
          if (typeof updateHud === 'function') updateHud();
          if (typeof updateTapStrip === 'function') updateTapStrip();
        }
        """
    )
    await page.wait_for_timeout(500)


async def collect_observations(page):
    return await page.evaluate(
        """
        () => {
          const out = {};
          // HUD pill etoiles
          const pill = document.getElementById('hud-stars');
          const pillVal = document.getElementById('hud-stars-val');
          out.hudPill = {
            exists: !!pill,
            displayProp: pill ? pill.style.display : null,
            offsetWidth: pill ? pill.offsetWidth : 0,
            offsetHeight: pill ? pill.offsetHeight : 0,
            visible: pill ? (pill.offsetWidth > 0 && pill.offsetHeight > 0 && pill.style.display !== 'none') : false,
            val: pillVal ? pillVal.textContent : null
          };
          // menu PRESTIGE item
          const prestigeItem = document.querySelector('[data-action="prestige"]');
          out.menuPrestige = {
            exists: !!prestigeItem,
            locked: prestigeItem ? prestigeItem.getAttribute('data-locked') : null,
            text: prestigeItem ? (prestigeItem.textContent || '').trim().replace(/\\s+/g,' ').slice(0,140) : null,
            offsetParent: prestigeItem ? !!prestigeItem.offsetParent : false
          };
          // Star tree modal
          const modal = document.getElementById('star-tree-modal');
          out.modal = {
            exists: !!modal,
            classList: modal ? modal.className : null,
            isShown: modal ? modal.classList.contains('show') : false
          };
          // Modal content (rendered)
          const list = document.getElementById('star-tree-list');
          const avail = document.getElementById('star-tree-avail');
          const cards = list ? Array.from(list.children) : [];
          out.modalContent = {
            availText: avail ? avail.textContent : null,
            nodeCount: cards.length,
            buttons: cards.map(c => {
              const btn = c.querySelector('.star-buy-btn');
              const lbl = c.querySelector('div > div');
              return {
                label: lbl ? lbl.textContent.trim() : null,
                btnText: btn ? btn.textContent.trim() : null,
                disabled: btn ? btn.disabled : null,
                node: btn ? btn.dataset.node : null
              };
            })
          };
          // Tout texte d'intro/explication dans la modale ?
          const modalCard = modal ? modal.querySelector('.modal-card') : null;
          out.modalIntroText = modalCard ? (modalCard.textContent || '').trim().replace(/\\s+/g,' ').slice(0, 400) : null;
          // STAR_TREE_NODES presence
          out.starTreeNodesCount = (typeof STAR_TREE_NODES !== 'undefined') ? STAR_TREE_NODES.length : null;
          // pill display per code path
          out.starsValue = (typeof STATE !== 'undefined') ? STATE.stars : null;
          out.totalStarsEarned = (typeof STATE !== 'undefined') ? STATE.totalStarsEarned : null;
          return out;
        }
        """
    )


async def main():
    findings = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        # Log console errors
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(800)
        await skip_onboarding(page)
        await page.wait_for_timeout(400)
        await force_state(page)
        # ensure HUD updated
        await page.evaluate("() => { if(typeof updateHud === 'function') updateHud(); if(typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure(); }")
        await page.wait_for_timeout(400)

        # Screenshot HUD top zone first
        await page.screenshot(path=str(OUT / "audit-H-hud-pill.png"), clip={"x":0,"y":0,"width":540,"height":160})

        # HUD pill observation pre-menu
        findings["pre_menu"] = await collect_observations(page)

        # Open burger menu
        try:
            await page.click("#menu-toggle", timeout=2000)
            await page.wait_for_timeout(400)
        except Exception as e:
            findings["menu_click_error"] = str(e)

        await page.screenshot(path=str(OUT / "audit-H-menu.png"), full_page=False)

        # Observations menu open
        findings["menu_open"] = await collect_observations(page)

        # Click PRESTIGE
        try:
            clicked = await page.evaluate(
                """
                () => {
                  const el = document.querySelector('[data-action=\"prestige\"]');
                  if(!el) return 'no-element';
                  if(el.getAttribute('data-locked') === '1') return 'locked';
                  el.click();
                  return 'clicked';
                }
                """
            )
            findings["prestige_click_result"] = clicked
            await page.wait_for_timeout(500)
        except Exception as e:
            findings["prestige_click_error"] = str(e)

        await page.screenshot(path=str(OUT / "audit-H-startree.png"), full_page=False)

        # Observations modal open
        findings["modal_open"] = await collect_observations(page)

        # Try buying tapPower
        before_btn = await page.evaluate(
            """
            () => {
              const b = document.querySelector('.star-buy-btn[data-node=\"tapPower\"]');
              if(!b) return null;
              return { text: b.textContent.trim(), disabled: b.disabled, parentHtml: b.parentElement.parentElement.outerHTML.slice(0,200) };
            }
            """
        )
        try:
            buy_result = await page.evaluate(
                """
                () => {
                  if(typeof buyStarNode !== 'function') return 'no-function';
                  const ok = buyStarNode('tapPower');
                  if(typeof renderStarTree === 'function') renderStarTree();
                  return ok;
                }
                """
            )
            findings["buy_result"] = buy_result
            await page.wait_for_timeout(300)
        except Exception as e:
            findings["buy_error"] = str(e)

        after_btn = await page.evaluate(
            """
            () => {
              const b = document.querySelector('.star-buy-btn[data-node=\"tapPower\"]');
              if(!b) return null;
              const lvlNode = b.closest('div').parentElement.querySelector('div[style*="font-weight"]');
              const lvlText = b.closest('div').parentElement.querySelector('div[style*="color:#b08020"]');
              return {
                text: b.textContent.trim(),
                disabled: b.disabled,
                lvlText: lvlText ? lvlText.textContent.trim() : null,
                stateLvl: (STATE.starTree && STATE.starTree.tapPower) || 0,
                stateStars: STATE.stars
              };
            }
            """
        )
        findings["tap_power_before"] = before_btn
        findings["tap_power_after"] = after_btn

        await page.screenshot(path=str(OUT / "audit-H-after-buy.png"), full_page=False)

        # Final summary check : moment narratif au km 100 ?
        # Y a-t-il un onboarding/hint specifique au moment de la 1ere etoile ?
        narrative_hooks = await page.evaluate(
            """
            () => {
              const out = {};
              // Recherche d'un toast/onboarding li a stars
              out.hasUnlockToastInDom = document.querySelectorAll('[id^="unlock-toast"]').length > 0;
              // Recherche d'un cinema d'ascension
              out.hasAscensionCinema = typeof showAscensionCinema === 'function' || typeof triggerEpicKm100 === 'function';
              // Le code recherche t-il une "premiere etoile" ?
              const html = document.documentElement.innerHTML;
              out.codeHasFirstStarHint = /first.?star|premiere.?etoile|première.?étoile/i.test(html);
              out.codeHasStarTreeHint = /openStarTree|star-?tree/i.test(html);
              return out;
            }
            """
        )
        findings["narrative_hooks"] = narrative_hooks
        findings["console_errors"] = errors[:5]

        (OUT / "audit-H-startree.json").write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(findings, indent=2, ensure_ascii=False))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
