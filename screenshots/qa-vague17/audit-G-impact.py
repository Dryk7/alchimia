"""
AUDIT G - Impact ressenti des achats (Vague 17)
- Viewport 540x960
- skip onboarding
- Force lapsRun=30, gold=100000
- Mesure AVANT achat : vitesse (#runner-pace), STATE.upgradeTapValue,
  tapValue calcule, displayKmh, perTap (#tap-per-tap), perLap (#tap-per-lap)
- Achete tapValue lvl 0 -> 1 via click
- Wait 500ms, mesure APRES (memes metriques)
- Verifie si toast/floating "+X" change visiblement
- Verifie preview "+X" sur le bouton (data-bonus)
- Verifie particles/flash bouton (classe just-bought)
- Repete test pour baseSpeed (impact displayKmh)
- Repete test pour autoTap (impact passive gain via tickAutoTap)
- Screenshot HUD avant/apres
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(__file__).parent
URL = "http://localhost:8770/index.html"


async def skip_onboarding(page):
    """Skip cinematic / story / tutorial overlays."""
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
              '.cinematic, .opening-cinematic, .splash, .intro, .story-overlay, [data-onboarding]'
            ).forEach(el => el.remove());
            if (typeof closeAllModals === 'function') closeAllModals();
            if (typeof startGame === 'function') startGame();
          } catch(e){}
        }
        """
    )
    await page.wait_for_timeout(700)
    # Click any visible start button
    for sel in [
        "#start-btn", ".start-game-btn", "button:has-text('DEPART')",
        "button:has-text('DEMARRER')", "button:has-text('JOUER')",
        "button:has-text('PRENDRE')"
    ]:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click()
                await page.wait_for_timeout(300)
                break
        except Exception:
            pass


async def force_state(page, gold=100000, laps=30):
    await page.evaluate(
        f"""
        () => {{
          if (typeof STATE === 'undefined') return;
          STATE.lapsRun = {laps};
          STATE.gold = {gold};
          STATE.totalTaps = 100;
          if (typeof renderStats === 'function') renderStats();
          if (typeof updateTapStrip === 'function') updateTapStrip();
        }}
        """
    )
    await page.wait_for_timeout(250)


async def open_upgrades(page):
    """Open upgrades drawer / make .upg-btn visible."""
    await page.evaluate(
        """
        () => {
          if (typeof openUpgradesDrawer === 'function') { openUpgradesDrawer(); return; }
          if (typeof openDrawer === 'function') { openDrawer('upgrades'); return; }
          const candidates = [
            '[data-drawer="upgrades"]', '[data-tab="upgrades"]',
            '#open-upgrades', '.btn-upgrades'
          ];
          for (const s of candidates) {
            const el = document.querySelector(s);
            if (el) { el.click(); return; }
          }
          const drawer = document.querySelector('.tap-upgrades-v2, #upgrades-drawer, .upgrades-panel');
          if (drawer) { drawer.style.display='block'; drawer.classList.add('open','visible'); }
        }
        """
    )
    await page.wait_for_timeout(400)


async def measure(page, label):
    """Mesure les metriques HUD + STATE."""
    return await page.evaluate(
        f"""
        () => {{
          const paceEl = document.getElementById('runner-pace');
          const perTapEl = document.getElementById('tap-per-tap');
          const perLapEl = document.getElementById('tap-per-lap');
          const boostPerTapEl = document.getElementById('boost-per-tap');
          const goldEl = document.getElementById('gold-val');
          const tapValue = 1 + (STATE.upgradeTapValue||0) * 1.5;
          // Try read displayKmh from any global (RUNNER_2D)
          let displayKmh = null;
          try {{ displayKmh = (typeof window.displayKmh !== 'undefined') ? window.displayKmh : null; }} catch(_){{}}
          // Detect particles function existence + just-bought class state on btn
          const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
          const baseBtn = document.querySelector('.upg-btn[data-upgrade="baseSpeed"]');
          const autoBtn = document.querySelector('.upg-btn[data-upgrade="autoTap"]');
          return {{
            label: '{label}',
            gold: STATE.gold,
            upgradeTapValue: STATE.upgradeTapValue || 0,
            upgradeBaseSpeed: STATE.upgradeBaseSpeed || 0,
            upgradeAutoTap: STATE.upgradeAutoTap || 0,
            tapValueCalc: tapValue,
            displayKmh: displayKmh,
            paceText: paceEl ? paceEl.textContent : null,
            perTapText: perTapEl ? perTapEl.textContent : null,
            perLapText: perLapEl ? perLapEl.textContent : null,
            boostPerTapText: boostPerTapEl ? boostPerTapEl.textContent : null,
            goldText: goldEl ? goldEl.textContent : null,
            btnTapBonus: btn ? btn.getAttribute('data-bonus') : null,
            btnTapClasses: btn ? btn.className : null,
            btnBaseBonus: baseBtn ? baseBtn.getAttribute('data-bonus') : null,
            btnAutoBonus: autoBtn ? autoBtn.getAttribute('data-bonus') : null
          }};
        }}
        """
    )


async def buy_and_observe(page, upgrade_id):
    """Click upgrade button, capture immediate classes + post 500ms."""
    # Hook particles + showToast/floating
    await page.evaluate(
        """
        () => {
          window.__FX_LOG = [];
          ['particles','vibrate','showToast','floating','flashStat','punchGoldCounter','_flashStatChange'].forEach(fn => {
            if (typeof window[fn] === 'function') {
              const orig = window[fn];
              window[fn] = function(...a){
                try { window.__FX_LOG.push({fn, args: a.slice(0,3), t: performance.now()}); } catch(_){}
                return orig.apply(this, a);
              };
            }
          });
        }
        """
    )
    # Click
    await page.evaluate(
        f"""
        () => {{
          const btn = document.querySelector('.upg-btn[data-upgrade="{upgrade_id}"]');
          if (btn) {{ btn.scrollIntoView({{block:'center'}}); btn.click(); }}
        }}
        """
    )
    # Immediate snapshot (animation in progress)
    immediate = await page.evaluate(
        f"""
        () => {{
          const btn = document.querySelector('.upg-btn[data-upgrade="{upgrade_id}"]');
          if (!btn) return {{exists:false}};
          const cs = getComputedStyle(btn);
          return {{
            exists: true,
            classes: btn.className,
            animationName: cs.animationName,
            animationDuration: cs.animationDuration,
            justBought: btn.classList.contains('just-bought')
          }};
        }}
        """
    )
    await page.wait_for_timeout(500)
    fx_log = await page.evaluate("() => window.__FX_LOG || []")
    return {"immediate": immediate, "fx_log": fx_log}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text[:200]}"))
        page.on("pageerror", lambda err: console_logs.append(f"[PAGEERROR] {str(err)[:200]}"))

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(900)

        await skip_onboarding(page)
        await force_state(page, gold=100000, laps=30)
        await open_upgrades(page)

        # ============ TEST 1 : tapValue lvl 0 -> 1 ============
        before_tap = await measure(page, "BEFORE tapValue buy")
        print("=== BEFORE tapValue ===")
        print(json.dumps(before_tap, indent=2, ensure_ascii=False))

        # Screenshot HUD avant
        await page.screenshot(path=str(OUT / "audit-G-before-hud.png"))

        # Achat tapValue
        tap_result = await buy_and_observe(page, "tapValue")
        print("\n=== TAP BUY IMMEDIATE ===")
        print(json.dumps(tap_result["immediate"], indent=2, ensure_ascii=False))
        print(f"FX events triggered: {len(tap_result['fx_log'])}")
        for fx in tap_result["fx_log"][:10]:
            print(f"  - {fx['fn']}")

        after_tap = await measure(page, "AFTER tapValue buy")
        print("\n=== AFTER tapValue ===")
        print(json.dumps(after_tap, indent=2, ensure_ascii=False))

        await page.screenshot(path=str(OUT / "audit-G-after.png"))

        # Delta TAP
        delta_tap = {
            "tapValue_delta": after_tap["upgradeTapValue"] - before_tap["upgradeTapValue"],
            "tapValueCalc_delta": after_tap["tapValueCalc"] - before_tap["tapValueCalc"],
            "perTapText_change": (before_tap["perTapText"], after_tap["perTapText"]),
            "boostPerTapText_change": (before_tap["boostPerTapText"], after_tap["boostPerTapText"]),
            "goldText_change": (before_tap["goldText"], after_tap["goldText"]),
            "pace_change": (before_tap["paceText"], after_tap["paceText"]),
            "btn_bonus_preview": after_tap["btnTapBonus"],
        }
        print("\n=== DELTA tapValue ===")
        print(json.dumps(delta_tap, indent=2, ensure_ascii=False))

        # ============ TEST 2 : baseSpeed lvl 0 -> 1 ============
        await force_state(page, gold=100000, laps=30)
        before_bs = await measure(page, "BEFORE baseSpeed buy")
        bs_result = await buy_and_observe(page, "baseSpeed")
        after_bs = await measure(page, "AFTER baseSpeed buy")

        delta_bs = {
            "baseSpeed_delta": after_bs["upgradeBaseSpeed"] - before_bs["upgradeBaseSpeed"],
            "displayKmh_change": (before_bs["displayKmh"], after_bs["displayKmh"]),
            "pace_change": (before_bs["paceText"], after_bs["paceText"]),
            "btn_bonus_preview": after_bs["btnBaseBonus"],
            "fx_count": len(bs_result["fx_log"]),
        }
        print("\n=== DELTA baseSpeed ===")
        print(json.dumps(delta_bs, indent=2, ensure_ascii=False))

        # Wait & measure speed evolution
        await page.wait_for_timeout(2000)
        after_bs_2s = await measure(page, "BS +2s")
        print(f"\nbaseSpeed pace +2s: {after_bs_2s['paceText']}  displayKmh: {after_bs_2s['displayKmh']}")

        # ============ TEST 3 : autoTap lvl 0 -> 1 ============
        await force_state(page, gold=100000, laps=30)
        before_at = await measure(page, "BEFORE autoTap buy")
        at_result = await buy_and_observe(page, "autoTap")
        after_at = await measure(page, "AFTER autoTap buy")
        # Wait 3s for autoTap to passively earn gold (rate = 1.5/s)
        await page.wait_for_timeout(3000)
        after_at_3s = await measure(page, "AT +3s")

        delta_at = {
            "autoTap_delta": after_at["upgradeAutoTap"] - before_at["upgradeAutoTap"],
            "gold_change_after_3s": (after_at["gold"], after_at_3s["gold"]),
            "gold_passive_gain_3s": after_at_3s["gold"] - after_at["gold"],
            "btn_bonus_preview": after_at["btnAutoBonus"],
            "fx_count": len(at_result["fx_log"]),
        }
        print("\n=== DELTA autoTap ===")
        print(json.dumps(delta_at, indent=2, ensure_ascii=False))

        # ============ QUESTION 3 : preview affichee AVANT achat ? ============
        # Verifier que data-bonus est sur le bouton AVANT click
        await force_state(page, gold=100000, laps=30)
        preview_check = await page.evaluate(
            """
            () => {
              const r = {};
              ['tapValue','baseSpeed','autoTap','lapBonus','critChance'].forEach(id => {
                const btn = document.querySelector(`.upg-btn[data-upgrade="${id}"]`);
                if (btn) {
                  r[id] = {
                    data_bonus: btn.getAttribute('data-bonus'),
                    has_preview_visible_in_dom: !!btn.querySelector('.upg-preview, .upg-next, [data-preview]'),
                    desc_text: (btn.querySelector('.upg-desc')||{}).textContent || null,
                    lvl_text: (btn.querySelector('.upg-lvl')||{}).textContent || null,
                    cost_text: (btn.querySelector('.upg-cost')||{}).textContent || null
                  };
                }
              });
              return r;
            }
            """
        )
        print("\n=== PREVIEW CHECK (data-bonus + visible) ===")
        print(json.dumps(preview_check, indent=2, ensure_ascii=False))

        # ============ QUESTION 4 : HUD flash visible ? ============
        # Acheter encore et capter flash gold-val
        await force_state(page, gold=100000, laps=30)
        await page.evaluate(
            """
            () => {
              window.__GOLD_FLASH = [];
              const goldEl = document.getElementById('gold-val');
              if (goldEl) {
                const mo = new MutationObserver(muts => {
                  muts.forEach(m => {
                    window.__GOLD_FLASH.push({
                      type: m.type,
                      attr: m.attributeName,
                      classes: goldEl.className,
                      text: goldEl.textContent,
                      t: performance.now()
                    });
                  });
                });
                mo.observe(goldEl, {attributes:true, childList:true, subtree:true, characterData:true});
                window.__GOLD_MO = mo;
              }
            }
            """
        )
        await buy_and_observe(page, "tapValue")
        gold_flash = await page.evaluate("() => window.__GOLD_FLASH || []")
        print(f"\n=== GOLD MUTATIONS during buy: {len(gold_flash)} ===")
        for g in gold_flash[:8]:
            print(f"  - {g.get('type')} {g.get('attr','')} classes='{g.get('classes','')}' text='{g.get('text','')[:40]}'")

        # ============ SUMMARY JSON ============
        summary = {
            "tapValue": {
                "before": before_tap, "after": after_tap, "delta": delta_tap,
                "fx_events": len(tap_result["fx_log"]),
                "fx_names": [f["fn"] for f in tap_result["fx_log"]],
                "btn_animation": tap_result["immediate"]
            },
            "baseSpeed": {
                "before": before_bs, "after": after_bs,
                "after_2s": after_bs_2s, "delta": delta_bs
            },
            "autoTap": {
                "before": before_at, "after": after_at,
                "after_3s": after_at_3s, "delta": delta_at
            },
            "preview_check": preview_check,
            "gold_mutations_count": len(gold_flash),
            "console_errors": [l for l in console_logs if "ERROR" in l.upper() or "PAGEERROR" in l][:5]
        }
        (OUT / "audit-G-impact.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("\n=== SAVED: audit-G-impact.json ===")
        print(f"Console errors: {len(summary['console_errors'])}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
