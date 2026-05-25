"""
AUDIT C - Notification "NOUVEAU : X débloqué !" sur paliers km (Vague 17)
- Viewport 540x960
- Skip onboarding
- Force STATE.lapsRun aux 8 paliers (1, 3, 5, 8, 12, 18, 25, 30)
- Pour vraiment déclencher la transition: force N-1 puis attend tick puis N
- Pour chaque palier : screenshot + observe toast (texte, couleur, durée, animation)
- Vérifie que le bouton perd data-locked="1"
- Vérifie si un SFX est déclenché (hook AudioContext + audio elements)
"""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Force UTF-8 stdout on Windows for emoji safety
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = Path(__file__).parent
URL = "http://localhost:8770/index.html"

# Paliers et upgrade attendu (cf data-unlock-km dans index.html lignes 8180-8288)
PALIERS = [
    (1,  "tapValue",      "Puissance"),
    (3,  "lapBonus",      "Trophée"),
    (5,  "critChance",    "Chance critique"),
    (8,  "eagleEye",      "Vision d'Aigle"),
    (12, "endurance",     "Souffle"),
    (18, "autoTap",       "Auto-pilote"),
    (25, "baseSpeed",     "Vitesse"),
    (30, "cruiseControl", "Pilote automatique"),
]


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


async def install_hooks(page):
    """Install audio + DOM hooks BEFORE running any test."""
    await page.evaluate(
        """
        () => {
          // SFX hook : intercept all AudioContext.createOscillator + Audio()
          window.__SFX_LOG = [];
          try {
            const AC = window.AudioContext || window.webkitAudioContext;
            if (AC) {
              const origOsc = AC.prototype.createOscillator;
              AC.prototype.createOscillator = function(...args){
                const t = performance.now();
                const o = origOsc.apply(this, args);
                try {
                  window.__SFX_LOG.push({
                    type:'oscillator', t,
                    freq: o.frequency ? o.frequency.value : null
                  });
                } catch(_){}
                return o;
              };
            }
            const origPlay = HTMLAudioElement.prototype.play;
            HTMLAudioElement.prototype.play = function(){
              try { window.__SFX_LOG.push({ type:'audio.play', t: performance.now(), src: this.src }); } catch(_){}
              return origPlay.apply(this, arguments);
            };
          } catch(e){}
          // Toast observer : track all new fixed-positioned divs that contain "NOUVEAU"
          window.__TOAST_LOG = [];
          const mo = new MutationObserver(muts => {
            muts.forEach(m => {
              m.addedNodes.forEach(n => {
                if (n.nodeType !== 1) return;
                const id = n.id || '';
                const txt = (n.textContent||'').trim();
                if (id.startsWith('unlock-toast-') || txt.includes('NOUVEAU')) {
                  const cs = getComputedStyle(n);
                  window.__TOAST_LOG.push({
                    t: performance.now(),
                    id: id,
                    text: txt,
                    animation: cs.animationName + ' ' + cs.animationDuration,
                    background: cs.background.slice(0,120),
                    color: cs.color,
                    position: cs.position,
                    top: cs.top,
                    zIndex: cs.zIndex
                  });
                }
              });
            });
          });
          mo.observe(document.body, {childList:true, subtree:true});
          window.__TOAST_MO = mo;
        }
        """
    )


async def reset_unlocks(page):
    """Reset _revealedUnlocks set so we can re-trigger each palier."""
    await page.evaluate(
        """
        () => {
          window._revealedUnlocks = new Set();
        }
        """
    )


async def force_palier(page, target_km):
    """Force lapsRun = N-1 (locked) then to N (unlocked) and trigger disclosure."""
    # Step 1 : N-1 to ensure the upgrade is locked + cleared from revealed
    await page.evaluate(
        f"""
        () => {{
          STATE.lapsRun = {max(0, target_km-1)};
          if (typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
        }}
        """
    )
    await page.wait_for_timeout(200)
    # Clear SFX + TOAST log JUST before crossing the threshold
    await page.evaluate(
        """
        () => {
          window.__SFX_LOG = [];
          window.__TOAST_LOG_BASELINE = (window.__TOAST_LOG || []).length;
        }
        """
    )
    # Step 2 : cross to N
    await page.evaluate(
        f"""
        () => {{
          STATE.lapsRun = {target_km};
          if (typeof applyProgressiveDisclosure === 'function') applyProgressiveDisclosure();
        }}
        """
    )


async def observe_palier(page, target_km, upgrade_id):
    """After threshold crossed, wait 2s and capture state."""
    await page.wait_for_timeout(2000)
    return await page.evaluate(
        f"""
        () => {{
          const baseline = window.__TOAST_LOG_BASELINE || 0;
          const newToasts = (window.__TOAST_LOG||[]).slice(baseline);
          const sfx = (window.__SFX_LOG||[]).slice();
          const btn = document.querySelector('.upg-btn[data-upgrade="{upgrade_id}"]');
          const btnInfo = btn ? {{
            exists: true,
            locked: btn.getAttribute('data-locked'),
            display: getComputedStyle(btn).display,
            visibility: getComputedStyle(btn).visibility,
            classes: btn.className,
            ariaLabel: btn.getAttribute('aria-label')
          }} : {{exists:false}};
          // Toast currently in DOM ?
          const stillThere = Array.from(document.querySelectorAll('[id^="unlock-toast-"]')).map(n => ({{
            id:n.id,
            text:(n.textContent||'').trim(),
            ageMs: performance.now() - parseInt(n.id.replace('unlock-toast-',''),10)
          }}));
          return {{
            km: {target_km},
            upgrade: '{upgrade_id}',
            newToasts: newToasts,
            sfxCount: sfx.length,
            sfx: sfx.slice(0,5),
            btn: btnInfo,
            toastsStillInDOM: stillThere
          }};
        }}
        """
    )


async def wait_for_toast_gone(page):
    """Wait until all unlock-toast nodes are removed (or 5s timeout)."""
    for _ in range(50):
        n = await page.evaluate("() => document.querySelectorAll('[id^=\"unlock-toast-\"]').length")
        if n == 0:
            return
        await page.wait_for_timeout(100)


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
        await install_hooks(page)

        # Open upgrades drawer so we can SEE the buttons revealing
        await page.evaluate(
            """
            () => {
              if (typeof openUpgradesDrawer === 'function') { openUpgradesDrawer(); return; }
              if (typeof openDrawer === 'function') { openDrawer('upgrades'); return; }
              const cands = ['[data-drawer="upgrades"]', '[data-tab="upgrades"]', '#open-upgrades'];
              for (const s of cands) {
                const el = document.querySelector(s);
                if (el) { el.click(); return; }
              }
              const dr = document.querySelector('.tap-upgrades-v2, #upgrades-drawer, .upgrades-panel');
              if (dr) { dr.style.display='block'; dr.classList.add('open','visible'); }
            }
            """
        )
        await page.wait_for_timeout(400)

        # Disable the setInterval to control timing manually (otherwise auto-tick can trigger toast at unwanted moment)
        # On le LAISSE actif au contraire : c'est le comportement réel à mesurer.

        results = []
        for (km, upg_id, label_expected) in PALIERS:
            # Wait any previous toast gone
            await wait_for_toast_gone(page)
            # Reset reveals so the palier toast can fire (sinon, croissant lapsRun ne retriggera pas si déjà vu)
            # NOTE: en conditions réelles, _revealedUnlocks persiste entre paliers (chaque palier différent),
            # donc on NE reset PAS le set. On reset juste les uplocks de paliers >= km.
            await page.evaluate(
                f"""
                () => {{
                  if (window._revealedUnlocks) {{
                    window._revealedUnlocks.delete('{upg_id}');
                  }}
                }}
                """
            )
            await force_palier(page, km)
            obs = await observe_palier(page, km, upg_id)
            obs["label_expected"] = label_expected
            results.append(obs)
            # Screenshot
            shot_path = OUT / f"audit-C-km{km}.png"
            await page.screenshot(path=str(shot_path))
            print(f"\n=== KM {km} -> {upg_id} ({label_expected}) ===")
            print(f"  toasts triggered: {len(obs['newToasts'])}")
            for t in obs["newToasts"]:
                print(f"    text: '{t['text']}'")
                print(f"    animation: {t['animation']}")
                print(f"    bg: {t['background'][:80]}")
                print(f"    pos: {t['position']} top={t['top']} z={t['zIndex']}")
            print(f"  SFX events: {obs['sfxCount']}")
            print(f"  btn: exists={obs['btn'].get('exists')} locked={obs['btn'].get('locked')} display={obs['btn'].get('display')}")
            print(f"  toasts still in DOM: {len(obs['toastsStillInDOM'])}")

        # Visual highlight check : est-ce que le bouton est highlight (animation/glow) après reveal ?
        # On regarde le dernier palier (km30) -> classes du btn et animations CSS
        last_btn_state = await page.evaluate(
            """
            () => {
              const btns = Array.from(document.querySelectorAll('.upg-btn'));
              return btns.map(b => ({
                upg: b.getAttribute('data-upgrade'),
                locked: b.getAttribute('data-locked'),
                classes: b.className,
                animationName: getComputedStyle(b).animationName,
                boxShadow: getComputedStyle(b).boxShadow.slice(0,80)
              }));
            }
            """
        )

        summary = {
            "paliers": results,
            "total_paliers": len(PALIERS),
            "paliers_with_toast": sum(1 for r in results if len(r["newToasts"]) > 0),
            "paliers_with_sfx": sum(1 for r in results if r["sfxCount"] > 0),
            "paliers_btn_unlocked": sum(1 for r in results if r["btn"].get("locked") == "0"),
            "last_btn_states": last_btn_state,
            "console_errors": [l for l in console_logs if "ERROR" in l.upper() or "PAGEERROR" in l][:5]
        }
        (OUT / "audit-C-unlock.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("\n=== SUMMARY ===")
        print(f"  Paliers testés          : {summary['total_paliers']}")
        print(f"  Paliers avec toast      : {summary['paliers_with_toast']}")
        print(f"  Paliers avec SFX        : {summary['paliers_with_sfx']}")
        print(f"  Boutons effectivement débloqués : {summary['paliers_btn_unlocked']}")
        print(f"  Console errors          : {len(summary['console_errors'])}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
