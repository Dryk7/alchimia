"""QA6 — Star Tree avec spécialisations (vague 20 P5)"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague22")
OUT.mkdir(parents=True, exist_ok=True)

URL = "http://localhost:8770/"

SKIP_ONBOARDING = """
() => {
  try {
    localStorage.setItem('alchimia-onboarded', '1');
    if (typeof STATE !== 'undefined') {
      STATE.onboarded = true;
      STATE.tutorialStep = 999;
    }
  } catch(e) {}
}
"""

RESET_STARS = """
() => {
  STATE.starSpec = null;
  STATE.stars = 10;
  STATE.starTree = { tapPower:0, lapPower:0, dropRate:0, basePower:0, staminaPlus:0, critPower:0, cooldownNeg:0, starsJackpot:0 };
  return { starSpec: STATE.starSpec, stars: STATE.stars };
}
"""

async def main():
    results = {}
    console_errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width":540,"height":960})
        page = await ctx.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(f"PAGEERROR: {err}"))

        await page.goto(URL, wait_until="networkidle")
        await page.evaluate(SKIP_ONBOARDING)
        await page.wait_for_timeout(500)
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(800)

        # Reset starSpec + stars
        reset_state = await page.evaluate(RESET_STARS)
        results["reset_state"] = reset_state

        # === TEST 1 — openStarTree affiche les 3 boutons de spec
        await page.evaluate("openStarTree()")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT/"qa6-01-spec-modal.png"))

        test1 = await page.evaluate("""
        () => {
          const list = document.getElementById('star-tree-list');
          if (!list) return { ok:false, reason:'no-list' };
          const html = list.innerHTML || '';
          const hasSprint = /SPRINTER/i.test(html);
          const hasMara   = /MARATHONIEN/i.test(html);
          const hasHyb    = /HYBRIDE/i.test(html);
          const buttons = list.querySelectorAll('button');
          const onclicks = Array.from(buttons).map(b => (b.getAttribute('onclick')||''));
          const specButtons = onclicks.filter(o => /chooseStarSpec/.test(o));
          return {
            ok: hasSprint && hasMara && hasHyb && specButtons.length === 3,
            hasSprint, hasMara, hasHyb,
            specButtonsCount: specButtons.length,
            buttonsTotal: buttons.length
          };
        }
        """)
        results["test1_choix_obligatoire"] = test1

        # === TEST 2 — chooseStarSpec('sprinter')
        test2 = await page.evaluate("""
        () => {
          const ok = chooseStarSpec('sprinter');
          return { returned: ok, starSpec: STATE.starSpec };
        }
        """)
        await page.wait_for_timeout(400)
        results["test2_choose_sprinter"] = test2

        # === TEST 3 — Re-render affiche 8 nodes
        await page.evaluate("renderStarTree()")
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT/"qa6-02-nodes-sprinter.png"))

        test3 = await page.evaluate("""
        () => {
          const list = document.getElementById('star-tree-list');
          if (!list) return { ok:false };
          const buyBtns = list.querySelectorAll('.star-buy-btn');
          const resetBtn = list.querySelector('button[onclick*="resetStarSpec"]');
          // Compter nodes affichés (data-node)
          const nodes = Array.from(buyBtns).map(b => b.dataset.node);
          // Compter ceux marqués VERROUILLÉ
          const lockedBtns = Array.from(buyBtns).filter(b => (b.textContent||'').includes('VERROUILLÉ'));
          return {
            ok: buyBtns.length === 8,
            nodesCount: buyBtns.length,
            nodes,
            lockedCount: lockedBtns.length,
            hasResetBtn: !!resetBtn
          };
        }
        """)
        results["test3_render_nodes"] = test3

        # === TEST 4 — Lock filter (Sprinter = tapPower OK, lapPower KO)
        test4 = await page.evaluate("""
        () => {
          return {
            tapPower:     isNodeUnlocked('tapPower'),
            critPower:    isNodeUnlocked('critPower'),
            basePower:    isNodeUnlocked('basePower'),
            cooldownNeg:  isNodeUnlocked('cooldownNeg'),
            lapPower:     isNodeUnlocked('lapPower'),
            staminaPlus:  isNodeUnlocked('staminaPlus'),
            dropRate:     isNodeUnlocked('dropRate'),
            starsJackpot: isNodeUnlocked('starsJackpot')
          };
        }
        """)
        results["test4_lock_filter"] = test4

        # === TEST 5 — buyStarNode bloqué sur node hors spec
        test5 = await page.evaluate("""
        () => {
          const before = STATE.stars;
          const lvlBefore = (STATE.starTree && STATE.starTree.lapPower) || 0;
          const ret = buyStarNode('lapPower');
          const after = STATE.stars;
          const lvlAfter = (STATE.starTree && STATE.starTree.lapPower) || 0;
          return {
            returned: ret,
            blocked: ret === false,
            starsUnchanged: before === after,
            lvlUnchanged: lvlBefore === lvlAfter,
            starsBefore: before, starsAfter: after,
            lvlBefore, lvlAfter
          };
        }
        """)
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT/"qa6-03-block-toast.png"))
        results["test5_buy_blocked"] = test5

        # === TEST 6 — resetStarSpec coût 10 + refund + clear spec
        test6 = await page.evaluate("""
        () => {
          STATE.stars = 15;
          // Investir 2 niveaux pour tester refund
          STATE.starTree = { tapPower:1, lapPower:0, dropRate:0, basePower:1, staminaPlus:0, critPower:0, cooldownNeg:0, starsJackpot:0 };
          const before = {
            stars: STATE.stars,
            spec: STATE.starSpec,
            invested: (STATE.starTree.tapPower||0) + (STATE.starTree.basePower||0)
          };
          const ret = resetStarSpec();
          const treeSum = Object.values(STATE.starTree || {}).reduce((a,b)=>a+(b||0), 0);
          return {
            returned: ret,
            before,
            after: {
              stars: STATE.stars,
              spec: STATE.starSpec,
              treeSum
            },
            // 15 - 10 (coût reset) + 2 (refund tapPower+basePower) = 7
            expectedStars: 15 - 10 + 2,
            specCleared: STATE.starSpec === null,
            treeWiped: treeSum === 0
          };
        }
        """)
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT/"qa6-04-after-reset.png"))
        results["test6_reset_spec"] = test6

        # Verif modal reset → re-show choix
        test6b = await page.evaluate("""
        () => {
          renderStarTree();
          const list = document.getElementById('star-tree-list');
          const html = (list && list.innerHTML) || '';
          return {
            backToChoice: /chooseStarSpec/.test(html) && /SPRINTER/i.test(html)
          };
        }
        """)
        results["test6b_back_to_choice"] = test6b

        await browser.close()

    results["console_errors_count"] = len(console_errors)
    results["console_errors"] = console_errors[:10]

    import json
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
