"""
AUDIT B - Animation feedback achat upgrade
- Viewport 540x960
- skip onboarding
- Force lapsRun=30, gold=1M
- Drawer upgrades + tab upgrades
- Click programmatique sur .upg-btn[data-upgrade="tapValue"]
- Screenshots: flash immediat, +200ms, +800ms
- Mesure: STATE.upgradeTapValue avant/apres, STATE.gold avant/apres
- CSS animation: getComputedStyle.animation / animationName
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(__file__).parent
URL = "http://localhost:8770/index.html"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[PAGEERROR] {err}"))

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(900)

        # Skip onboarding (cinematic, intro, story, etc.)
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
                // Forcer la fin de tout overlay actif
                document.querySelectorAll('.cinematic, .opening-cinematic, .splash, .intro, .story-overlay, [data-onboarding]').forEach(el => el.remove());
                if (typeof closeAllModals === 'function') closeAllModals();
                if (typeof startGame === 'function') startGame();
              } catch(e){}
            }
            """
        )
        await page.wait_for_timeout(800)

        # Tenter de cliquer "PRENDRE LE DEPART" / start
        try:
            for sel in ["#start-btn", ".start-game-btn", "button:has-text('DÉPART')", "button:has-text('DEMARRER')", "button:has-text('JOUER')"]:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await page.wait_for_timeout(400)
                        break
                except Exception:
                    pass
        except Exception:
            pass

        # Forcer la state: lapsRun=30, gold=1e6
        await page.evaluate(
            """
            () => {
              if (typeof STATE === 'undefined') return;
              STATE.lapsRun = 30;
              STATE.gold = 1000000;
              STATE.totalTaps = 100;
              if (typeof renderStats === 'function') renderStats();
              if (typeof updateTapStrip === 'function') updateTapStrip();
            }
            """
        )
        await page.wait_for_timeout(300)

        # Ouvrir drawer principal + activer tab Upgrades
        opened = await page.evaluate(
            """
            () => {
              const logs = [];
              // 1. Ouvrir le drawer principal (toggle drawer/sheet)
              const drawerTriggers = ['#open-drawer','.drawer-toggle','#hud-menu-toggle','.handle-bar','.sheet-handle','#bottom-sheet-handle'];
              for(const s of drawerTriggers){
                const el = document.querySelector(s);
                if(el){ el.click(); logs.push('drawer-toggle:'+s); break; }
              }
              // 2. Si bottom-sheet a une classe collapsed/closed, l'ouvrir
              const sheet = document.querySelector('.bottom-sheet, #bottom-sheet, .drawer, .sheet-content');
              if(sheet){
                sheet.classList.remove('collapsed','closed','hidden');
                sheet.classList.add('open','expanded','visible');
                if(sheet.style.transform) sheet.style.transform = '';
                if(sheet.style.bottom) sheet.style.bottom = '0';
                logs.push('sheet-forced-open');
              }
              // 3. Activer tab Upgrades
              const tabUp = document.querySelector('.tab-btn[data-tab="upgrades"]');
              if(tabUp){ tabUp.click(); logs.push('tab-upgrades-click'); }
              // 4. Force-active pane upgrades
              document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
              const pane = document.querySelector('.tab-pane[data-pane="upgrades"]');
              if(pane){ pane.classList.add('active'); pane.style.display='block'; logs.push('pane-active'); }
              return logs;
            }
            """
        )
        print("OPEN DRAWER LOGS:", opened)
        await page.wait_for_timeout(600)

        # Si le drawer global a un menu/burger, l'ouvrir
        for sel in ["#menu-btn", ".burger-btn", "[data-menu]"]:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_timeout(250)
            except Exception:
                pass

        # Verifier le bouton tapValue
        btn_info = await page.evaluate(
            """
            () => {
              const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
              if(!btn) return {exists:false};
              const r = btn.getBoundingClientRect();
              return {
                exists:true,
                visible: r.width>0 && r.height>0 && r.top<960,
                rect: {x:r.x, y:r.y, w:r.width, h:r.height},
                classes: btn.className,
                disabled: btn.disabled || btn.classList.contains('locked')
              };
            }
            """
        )
        print("BTN INFO:", json.dumps(btn_info, indent=2))

        # Si le bouton n'est pas visible, scroller ou forcer le drawer ouvert
        if not btn_info.get("visible"):
            await page.evaluate(
                """
                () => {
                  const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
                  if(btn){ btn.scrollIntoView({block:'center'}); }
                }
                """
            )
            await page.wait_for_timeout(300)
            btn_info = await page.evaluate(
                """
                () => {
                  const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
                  if(!btn) return {exists:false};
                  const r = btn.getBoundingClientRect();
                  return {exists:true, visible: r.width>0 && r.height>0, rect:{x:r.x,y:r.y,w:r.width,h:r.height}};
                }
                """
            )
            print("BTN INFO after scroll:", json.dumps(btn_info, indent=2))

        # State AVANT
        before = await page.evaluate(
            """
            () => ({
              gold: STATE.gold,
              tapValue: STATE.upgradeTapValue || 0,
              totalUpgradesBought: STATE.totalUpgradesBought || 0
            })
            """
        )
        print("STATE BEFORE:", before)

        # Hook SFX pour detecter les appels audio (intercept blip via setTimeout proxy)
        await page.evaluate(
            """
            () => {
              window.__SFX_LOG = [];
              // Monkey-patch setTimeout pour tracer les blips programmés dans buyUpgrade
              const _setTimeout = window.setTimeout;
              window.setTimeout = function(fn, ms, ...rest){
                const wrapped = function(){
                  window.__SFX_LOG.push({fn:'setTimeout-fire', ms, t:performance.now()});
                  return fn.apply(this, arguments);
                };
                return _setTimeout.call(this, wrapped, ms, ...rest);
              };
              ['sfxUpgrade','sfxBuyScaled','sfxItemUpgrade','vibrate','particles','punchGoldCounter','spawnTapJuice'].forEach(fn => {
                if(typeof window[fn] === 'function'){
                  const orig = window[fn];
                  window[fn] = function(...a){ window.__SFX_LOG.push({fn, args:a.length, t: performance.now()}); return orig.apply(this, a); };
                }
              });
              // Track AudioContext usage indirectement via createOscillator (blip est local au scope mais utilise A.ctx)
              if(typeof A !== 'undefined' && A.ctx){
                const origOsc = A.ctx.createOscillator.bind(A.ctx);
                A.ctx.createOscillator = function(){
                  const o = origOsc();
                  window.__SFX_LOG.push({fn:'AudioOsc', t:performance.now()});
                  return o;
                };
              }
            }
            """
        )

        # CLICK: trigger l'achat + screenshot IMMEDIAT
        # On declenche le click via JS sync puis on capture sans delay
        await page.evaluate(
            """
            () => {
              const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
              if(btn){ btn.click(); }
            }
            """
        )

        # Screenshot FLASH (immediat, 0ms apres click) — on lit la classe en plein milieu
        css_immediate = await page.evaluate(
            """
            () => {
              const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
              if(!btn) return {};
              const cs = getComputedStyle(btn);
              return {
                classes: btn.className,
                animation: cs.animation,
                animationName: cs.animationName,
                animationDuration: cs.animationDuration,
                transform: cs.transform,
                background: cs.backgroundImage || cs.background
              };
            }
            """
        )
        await page.screenshot(path=str(OUT / "audit-B-flash.png"), full_page=False)

        # +200ms
        await page.wait_for_timeout(200)
        css_mid = await page.evaluate(
            """
            () => {
              const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
              if(!btn) return {};
              const cs = getComputedStyle(btn);
              return { classes: btn.className, transform: cs.transform, animationName: cs.animationName };
            }
            """
        )
        await page.screenshot(path=str(OUT / "audit-B-mid.png"), full_page=False)

        # +800ms (total ~1s apres click)
        await page.wait_for_timeout(800)
        css_end = await page.evaluate(
            """
            () => {
              const btn = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
              if(!btn) return {};
              const cs = getComputedStyle(btn);
              return { classes: btn.className, transform: cs.transform, animationName: cs.animationName };
            }
            """
        )
        await page.screenshot(path=str(OUT / "audit-B-end.png"), full_page=False)

        # State APRES
        after = await page.evaluate(
            """
            () => ({
              gold: STATE.gold,
              tapValue: STATE.upgradeTapValue || 0,
              totalUpgradesBought: STATE.totalUpgradesBought || 0
            })
            """
        )

        sfx_log = await page.evaluate("() => window.__SFX_LOG || []")

        # Compter particles canvas si existe
        particle_info = await page.evaluate(
            """
            () => {
              // Chercher canvas de particules
              const canvases = Array.from(document.querySelectorAll('canvas'));
              return {
                canvasCount: canvases.length,
                ids: canvases.map(c=>c.id || c.className).slice(0,8)
              };
            }
            """
        )

        report = {
            "btn_info": btn_info,
            "state_before": before,
            "state_after": after,
            "gold_delta": before["gold"] - after["gold"],
            "tapValue_delta": after["tapValue"] - before["tapValue"],
            "css_immediate": css_immediate,
            "css_mid": css_mid,
            "css_end": css_end,
            "sfx_log": sfx_log,
            "particle_info": particle_info,
            "console_recent": console_logs[-40:],
        }
        print("\n=== REPORT ===")
        print(json.dumps(report, indent=2, default=str))

        (OUT / "audit-B-report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        await browser.close()


asyncio.run(main())
