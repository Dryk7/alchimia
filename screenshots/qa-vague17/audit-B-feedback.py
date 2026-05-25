"""
AUDIT B - Feedback satisfaisant lors d'un achat upgrade (Vague 17)
- Viewport 540x960
- skip onboarding
- Force lapsRun=30, gold=1000000
- Screenshot AVANT click
- Click [data-upgrade="tapValue"]
- Screenshot pendant l'animation (200ms)
- Screenshot 1s apres
- Eval classes ajoutees, .just-bought presence + duree
- Verifier SFX, particules DOM, animation gold counter
- Pas de modification du jeu - lecture pure
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
              '.cinematic, .opening-cinematic, .splash, .intro, .story-overlay, [data-onboarding]'
            ).forEach(el => el.remove());
            if (typeof closeAllModals === 'function') closeAllModals();
            if (typeof startGame === 'function') startGame();
          } catch(e){}
        }
        """
    )
    await page.wait_for_timeout(700)
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


async def force_state(page, gold=1000000, laps=30):
    await page.evaluate(
        f"""
        () => {{
          if (typeof STATE === 'undefined') return;
          STATE.lapsRun = {laps};
          STATE.gold = {gold};
          STATE.totalTaps = 200;
          if (typeof renderStats === 'function') renderStats();
          if (typeof updateTapStrip === 'function') updateTapStrip();
        }}
        """
    )
    await page.wait_for_timeout(250)


async def open_upgrades(page):
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
    await page.wait_for_timeout(500)


async def snapshot(page, label):
    return await page.evaluate(
        f"""
        () => {{
          const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
          const goldEl = document.getElementById('gold-val');
          // Count DOM-based FX elements
          const fxSelectors = ['.particle', '.gold-fly', '.reward-pop', '.sparkle',
            '.float-text', '.toast', '.float-pop', '.flash', '.shake', '.epic-sparkle'];
          const fxCounts = {{}};
          let totalFx = 0;
          fxSelectors.forEach(s => {{
            const n = document.querySelectorAll(s).length;
            fxCounts[s] = n;
            totalFx += n;
          }});
          // Canvas FX_PARTS array (game uses canvas particles, not DOM)
          let canvasParts = null;
          try {{ canvasParts = (typeof FX_PARTS !== 'undefined') ? FX_PARTS.length : null; }} catch(_){{}}
          let canvasShocks = null;
          try {{ canvasShocks = (typeof SHOCKS !== 'undefined') ? SHOCKS.length : null; }} catch(_){{}}
          return {{
            label: '{label}',
            t: performance.now(),
            btnExists: !!btn,
            btnClasses: btn ? btn.className : null,
            btnJustBought: btn ? btn.classList.contains('just-bought') : false,
            btnTransform: btn ? getComputedStyle(btn).transform : null,
            btnAnimName: btn ? getComputedStyle(btn).animationName : null,
            btnAnimDuration: btn ? getComputedStyle(btn).animationDuration : null,
            btnBackground: btn ? getComputedStyle(btn).background.slice(0,80) : null,
            goldText: goldEl ? goldEl.textContent : null,
            goldClasses: goldEl ? goldEl.className : null,
            goldCounting: goldEl ? goldEl.classList.contains('counting') : false,
            stateGold: (typeof STATE !== 'undefined') ? STATE.gold : null,
            stateTapValue: (typeof STATE !== 'undefined') ? (STATE.upgradeTapValue||0) : null,
            domFxCounts: fxCounts,
            domFxTotal: totalFx,
            canvasParticles: canvasParts,
            canvasShocks: canvasShocks,
          }};
        }}
        """
    )


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
        await force_state(page, gold=1000000, laps=30)
        await open_upgrades(page)
        await page.wait_for_timeout(400)

        # ============ EXISTENCE CHECK ============
        existence = await page.evaluate(
            """
            () => {
              return {
                hasSfxUpgrade: typeof sfxUpgrade === 'function',
                hasSfxBuyScaled: typeof sfxBuyScaled === 'function',
                hasSfxItemUpgrade: typeof sfxItemUpgrade === 'function',
                hasPunchGoldCounter: typeof punchGoldCounter === 'function',
                hasVibrate: typeof vibrate === 'function',
                hasParticles: typeof particles === 'function',
                hasFlashStat: typeof flashStat === 'function',
                hasShowToast: typeof showToast === 'function',
                hasBuyUpgrade: typeof buyUpgrade === 'function',
                hasFloating: typeof floating === 'function',
                hasShockwave: typeof shockwave === 'function',
                btnVisible: !!document.querySelector('.upg-btn[data-upgrade="tapValue"]'),
              };
            }
            """
        )
        print("=== EXISTENCE CHECKS ===")
        print(json.dumps(existence, indent=2, ensure_ascii=False))

        # Hook FX call log
        await page.evaluate(
            """
            () => {
              window.__FX_LOG = [];
              const hooks = ['particles','vibrate','showToast','floating','flashStat',
                'punchGoldCounter','_flashStatChange','sfxBuyScaled','sfxItemUpgrade',
                'shockwave','blip'];
              hooks.forEach(fn => {
                if (typeof window[fn] === 'function') {
                  const orig = window[fn];
                  window[fn] = function(...a){
                    try { window.__FX_LOG.push({fn, args: a.slice(0,3).map(x => {
                      if (typeof x === 'object') return '[obj]';
                      return String(x).slice(0,40);
                    }), t: performance.now()}); } catch(_){}
                    return orig.apply(this, a);
                  };
                }
              });
              // MutationObserver on the button to detect class changes
              window.__BTN_MUT = [];
              const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
              if (btn) {
                const mo = new MutationObserver(muts => {
                  muts.forEach(m => {
                    window.__BTN_MUT.push({
                      t: performance.now(),
                      attr: m.attributeName,
                      classes: btn.className.slice(0,200)
                    });
                  });
                });
                mo.observe(btn, {attributes:true});
              }
              // MutationObserver on gold-val
              window.__GOLD_MUT = [];
              const goldEl = document.getElementById('gold-val');
              if (goldEl) {
                const mog = new MutationObserver(muts => {
                  muts.forEach(m => {
                    window.__GOLD_MUT.push({
                      t: performance.now(),
                      type: m.type,
                      attr: m.attributeName,
                      classes: goldEl.className,
                      text: (goldEl.textContent||'').slice(0,40)
                    });
                  });
                });
                mog.observe(goldEl, {attributes:true, childList:true, subtree:true, characterData:true});
              }
            }
            """
        )

        # ============ BEFORE SCREENSHOT ============
        before = await snapshot(page, "BEFORE")
        await page.screenshot(path=str(OUT / "audit-B-before.png"))
        print("\n=== BEFORE click ===")
        print(json.dumps(before, indent=2, ensure_ascii=False))

        # ============ CLICK ============
        t_click_eval = await page.evaluate(
            """
            () => {
              const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
              if (!btn) return {clicked:false};
              btn.scrollIntoView({block:'center'});
              const t0 = performance.now();
              btn.click();
              return {clicked:true, t0};
            }
            """
        )
        print(f"\n=== CLICK FIRED @ t={t_click_eval.get('t0')} ===")

        # ============ ~200ms DURING ============
        await page.wait_for_timeout(200)
        during = await snapshot(page, "DURING (+200ms)")
        await page.screenshot(path=str(OUT / "audit-B-during.png"))
        print("\n=== DURING (+200ms) ===")
        print(json.dumps(during, indent=2, ensure_ascii=False))

        # ============ +1s AFTER ============
        await page.wait_for_timeout(800)  # total ~1s
        after = await snapshot(page, "AFTER (+1s)")
        await page.screenshot(path=str(OUT / "audit-B-after.png"))
        print("\n=== AFTER (+1s) ===")
        print(json.dumps(after, indent=2, ensure_ascii=False))

        # ============ FX LOG ============
        fx_log = await page.evaluate("() => window.__FX_LOG || []")
        btn_mut = await page.evaluate("() => window.__BTN_MUT || []")
        gold_mut = await page.evaluate("() => window.__GOLD_MUT || []")

        print(f"\n=== FX FUNCTION CALLS during buy ({len(fx_log)}) ===")
        # Group/dedupe by fn name
        fn_counts = {}
        for fx in fx_log:
            fn_counts[fx['fn']] = fn_counts.get(fx['fn'], 0) + 1
        for fn, count in sorted(fn_counts.items(), key=lambda x: -x[1]):
            print(f"  - {fn}: x{count}")
        print(f"\nFirst 10 FX events:")
        for fx in fx_log[:10]:
            print(f"  t={fx['t']:.0f} {fx['fn']}({fx['args']})")

        # Compute .just-bought duration
        jb_added_t = None
        jb_removed_t = None
        for m in btn_mut:
            cl = m.get('classes', '')
            if 'just-bought' in cl and jb_added_t is None:
                jb_added_t = m['t']
            elif 'just-bought' not in cl and jb_added_t is not None and jb_removed_t is None:
                jb_removed_t = m['t']
        jb_duration = (jb_removed_t - jb_added_t) if (jb_added_t and jb_removed_t) else None

        print(f"\n=== BUTTON MUTATIONS ({len(btn_mut)}) ===")
        print(f"  just-bought added at t={jb_added_t}, removed at t={jb_removed_t}, duration={jb_duration}ms")
        for m in btn_mut[:8]:
            print(f"  t={m['t']:.0f} attr={m.get('attr')} classes='{(m.get('classes') or '')[:80]}'")

        print(f"\n=== GOLD MUTATIONS ({len(gold_mut)}) ===")
        for m in gold_mut[:8]:
            print(f"  t={m['t']:.0f} {m.get('type')} attr={m.get('attr','')} text='{m.get('text','')}' classes='{m.get('classes','')[:40]}'")
        gold_animations = [m for m in gold_mut if 'counting' in (m.get('classes') or '') or m.get('attr') == 'class']
        print(f"  -> gold counter class mutations: {len(gold_animations)}")
        print(f"  -> gold text changes: {len([m for m in gold_mut if m.get('type') == 'characterData' or m.get('type') == 'childList'])}")

        # ============ DELTAS ============
        delta = {
            "gold_text_before": before.get('goldText'),
            "gold_text_during": during.get('goldText'),
            "gold_text_after": after.get('goldText'),
            "state_gold_before": before.get('stateGold'),
            "state_gold_after": after.get('stateGold'),
            "gold_spent": (before.get('stateGold') or 0) - (after.get('stateGold') or 0),
            "tapValue_before": before.get('stateTapValue'),
            "tapValue_after": after.get('stateTapValue'),
            "just_bought_during": during.get('btnJustBought'),
            "just_bought_after": after.get('btnJustBought'),
            "btn_anim_during": during.get('btnAnimName'),
            "btn_anim_duration": during.get('btnAnimDuration'),
            "btn_transform_during": during.get('btnTransform'),
            "btn_transform_after": after.get('btnTransform'),
            "domFx_before": before.get('domFxTotal'),
            "domFx_during": during.get('domFxTotal'),
            "domFx_after": after.get('domFxTotal'),
            "canvasParticles_before": before.get('canvasParticles'),
            "canvasParticles_during": during.get('canvasParticles'),
            "canvasParticles_after": after.get('canvasParticles'),
            "canvasShocks_during": during.get('canvasShocks'),
        }
        print("\n=== DELTAS ===")
        print(json.dumps(delta, indent=2, ensure_ascii=False))

        # ============ SUMMARY JSON ============
        summary = {
            "existence": existence,
            "before": before,
            "during": during,
            "after": after,
            "delta": delta,
            "fx_call_counts": fn_counts,
            "fx_total_calls": len(fx_log),
            "fx_first10": fx_log[:10],
            "button_mutations_count": len(btn_mut),
            "just_bought_duration_ms": jb_duration,
            "gold_mutations_count": len(gold_mut),
            "console_errors": [l for l in console_logs if "ERROR" in l.upper() or "PAGEERROR" in l][:5]
        }
        (OUT / "audit-B-feedback.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("\n=== SAVED: audit-B-feedback.json + 3 screenshots ===")
        print(f"Console errors: {len(summary['console_errors'])}")
        for e in summary['console_errors']:
            print(f"  {e}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
