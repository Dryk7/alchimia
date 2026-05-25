"""
QA endgame km 75-100 — FOULÉE QA Vague 10
Cible : evaluer le rendu, la difficulte, l'aura champion T6, le moment km 100.
Lecture seule. Aucune modification du jeu.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/"

VIEWPORT = {"width": 540, "height": 960}

# ---------- Patch boot : skip tuto + budget endgame + journal console ----------
INIT_SCRIPT = r"""
(() => {
  // Skip onboarding / cinematics
  try {
    localStorage.setItem('foulee.activeTutoV1', 'done');
    localStorage.setItem('foulee.tutoV3', JSON.stringify({done:true}));
    localStorage.setItem('foulee.gigaTuto', 'done');
    localStorage.setItem('foulee.storySeen', '1');
    localStorage.setItem('foulee.cinematicSeen', '1');
    localStorage.setItem('foulee.openingCinematic', 'done');
    localStorage.setItem('foulee.welcomed', '1');
    localStorage.setItem('foulee.dailyDismissedV1', '1');
  } catch(e){}
  // Bridge logs vers Node
  window.__qaLogs = [];
  ['log','warn','error'].forEach(k => {
    const orig = console[k].bind(console);
    console[k] = (...a) => {
      try { window.__qaLogs.push({lvl:k, msg:a.map(x => {
        try { return typeof x === 'string' ? x : JSON.stringify(x); }
        catch(e){ return String(x); }
      }).join(' ')}); } catch(e){}
      orig(...a);
    };
  });
})();
"""

# Force STATE pour endgame.
def force_state_js(laps_run: int) -> str:
    js = """
    (() => {
      const S = window.STATE;
      if(!S) return 'NO_STATE';
      const km = __KM__;
      S.gold = 50000000;
      S.totalTaps = 50000;
      S.lapsRun = km;
      S.lapProgress = 0;
      S.alchLevel = 50;
      S.totalGoldEarned = Math.max(S.totalGoldEarned||0, 1500000);
      S.hurdlesCleared = Math.max(S.hurdlesCleared||0, 200);
      S.npcOvertakeCount = Math.max(S.npcOvertakeCount||0, 80);
      S.tier6Seen = (km >= 85) ? 1 : (S.tier6Seen||0);
      if(typeof window.renderStats === 'function') try { window.renderStats(); } catch(e){}
      if(typeof window.updateRunnerHUD === 'function') try { window.updateRunnerHUD(); } catch(e){}
      return {
        km: S.lapsRun,
        gold: S.gold,
        taps: S.totalTaps,
        tier6Seen: S.tier6Seen,
        autoCourse: !!S._autoCourseUnlocked,
        epicPlayed: !!S._epicKm100Played
      };
    })()
    """
    return js.replace("__KM__", str(laps_run))

async def dismiss_overlays(page):
    """Ferme modales, cinematics, daily, etc. Tolerant aux echecs."""
    try:
        await page.evaluate("""
        () => {
          // Fermer opening cinematic
          const oc = document.getElementById('opening-cinematic');
          if(oc){ oc.style.display = 'none'; }
          // Fermer toutes les modales actives
          document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
          // Skip giga-tuto si visible
          const gt = document.getElementById('giga-tuto-overlay');
          if(gt){ gt.style.display = 'none'; }
          // Skip active tuto
          if(window.ActiveTuto && typeof window.ActiveTuto.skip === 'function'){
            try { window.ActiveTuto.skip(); } catch(e){}
          }
        }
        """)
    except Exception as e:
        print("dismiss overlay err:", e)

async def start_game(page):
    """Click le bouton 'Prendre le depart' + ferme daily."""
    # 1) Ferme modal daily si visible
    try:
        await page.evaluate("""
        () => {
          document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
          const dm = document.getElementById('daily-modal');
          if(dm){ dm.classList.remove('show'); dm.style.display = 'none'; }
        }
        """)
    except Exception:
        pass
    # 2) Click start-btn
    try:
        btn = await page.query_selector("#start-btn")
        if btn:
            await btn.click(force=True)
            await page.wait_for_timeout(1200)
    except Exception as e:
        print('start_game err:', e)
    # 3) Re-ferme daily si reapparue
    try:
        await page.evaluate("""
        () => {
          document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
          const dm = document.getElementById('daily-modal');
          if(dm){ dm.classList.remove('show'); dm.style.display = 'none'; }
          // Skip giga tuto
          const gt = document.getElementById('giga-tuto-overlay');
          if(gt){ gt.style.display = 'none'; }
        }
        """)
    except Exception:
        pass

async def measure_hud(page) -> dict:
    return await page.evaluate("""
    () => {
      const hud = {};
      const get = (id) => {
        const el = document.getElementById(id);
        if(!el) return null;
        const t = (el.textContent || '').trim();
        const r = el.getBoundingClientRect();
        return { text: t, w: Math.round(r.width), h: Math.round(r.height), visible: r.width>0 && r.height>0 && t.length>0 };
      };
      hud.gold = get('gold-val');
      hud.km = get('runner-km');
      hud.kmh = get('runner-kmh') || get('hud-kmh');
      hud.lvl = get('runner-lvl');
      hud.ascBtn = get('saison-btn');
      // Tier 6 NPCs detectes sur canvas via window.STATE / RUNNER_2D ?
      let npcStats = null;
      try {
        if(window.RUNNER_2D && typeof window.RUNNER_2D._dbgNpcSummary === 'function'){
          npcStats = window.RUNNER_2D._dbgNpcSummary();
        }
      } catch(e){}
      hud.npcSummary = npcStats;
      hud.canAscend = (typeof window.canAscend === 'function') ? !!window.canAscend() : null;
      hud.biome = (typeof window.currentBiome === 'function') ? window.currentBiome() : null;
      return hud;
    }
    """)

async def list_overlapping(page) -> list:
    """Detecte overlap simple entre top HUD elements."""
    return await page.evaluate("""
    () => {
      const ids = ['gold-val','runner-km','runner-kmh','runner-lvl','saison-btn'];
      const rects = ids.map(id => {
        const el = document.getElementById(id);
        if(!el) return null;
        const r = el.getBoundingClientRect();
        return {id, x:r.x, y:r.y, w:r.width, h:r.height};
      }).filter(Boolean);
      const overlaps = [];
      for(let i=0; i<rects.length; i++){
        for(let j=i+1; j<rects.length; j++){
          const a = rects[i], b = rects[j];
          if(a.w === 0 || b.w === 0) continue;
          const ox = !(a.x + a.w <= b.x || b.x + b.w <= a.x);
          const oy = !(a.y + a.h <= b.y || b.y + b.h <= a.y);
          if(ox && oy) overlaps.push(`${a.id} <-> ${b.id}`);
        }
      }
      return overlaps;
    }
    """)

async def main():
    findings = {
        "steps": [],
        "errors": [],
        "warnings": [],
        "observations": {},
        "summary": {}
    }
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (Linux; Android 13; QA) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121 Mobile Safari/537.36"
        )
        page = await ctx.new_context() if False else await ctx.new_page()
        # capture console
        page_errors = []
        def on_console(msg):
            try:
                t = msg.type
                if t in ('error', 'warning'):
                    page_errors.append((t, msg.text))
            except Exception:
                pass
        page.on("console", on_console)
        page.on("pageerror", lambda e: page_errors.append(("pageerror", str(e))))

        await ctx.add_init_script(INIT_SCRIPT)
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(800)
        await dismiss_overlays(page)
        await page.wait_for_timeout(300)
        await start_game(page)
        await page.wait_for_timeout(800)
        await dismiss_overlays(page)
        await page.wait_for_timeout(500)

        # Boucle paliers
        paliers = [75, 85, 95, 99, 100]
        for km in paliers:
            await page.evaluate(force_state_js(km))
            await page.wait_for_timeout(900)
            await dismiss_overlays(page)
            await page.wait_for_timeout(600)
            hud = await measure_hud(page)
            ovl = await list_overlapping(page)
            shot = OUT / f"endgame-km{km:03d}.png"
            await page.screenshot(path=str(shot), full_page=False)
            findings["steps"].append({
                "km": km,
                "hud": hud,
                "overlaps": ovl,
                "screenshot": shot.name
            })

        # KM 100 EPIC : on simule un completeLap au km 100 pour declencher l'event reel
        # (la force directe ne joue pas triggerEpicKm100 — il est appele dans le tick rendering)
        # On regle lapsRun=99 puis lapProgress=0.999 et on tape pour forcer l'event
        await page.evaluate("""
        (() => {
          if(!window.STATE) return;
          window.STATE.lapsRun = 99;
          window.STATE.lapProgress = 0.99;
          window.STATE._epicKm100Played = false;
          if(typeof window.completeLap === 'function'){
            try { window.completeLap(); } catch(e){}
          }
        })()
        """)
        # Le moment epic est appele dans le rendering tick quand lapsRun passe a 100
        # On laisse le tick tourner pour capter le cinematic
        await page.wait_for_timeout(400)
        # screenshot impact frame
        await page.screenshot(path=str(OUT / "endgame-km100-epic-T0.png"))
        await page.wait_for_timeout(900)
        await page.screenshot(path=str(OUT / "endgame-km100-epic-T1.png"))
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT / "endgame-km100-epic-T2.png"))
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT / "endgame-km100-epic-T3.png"))

        # Verifie si triggerEpicKm100 a tourne
        epic_status = await page.evaluate("""
        () => ({
          epicPlayed: !!(window.STATE && window.STATE._epicKm100Played),
          epicNodePresent: !!document.getElementById('epic-km100'),
          ascendBtnVisible: (() => {
            const b = document.getElementById('saison-btn');
            if(!b) return false;
            const r = b.getBoundingClientRect();
            return r.width > 0 && r.height > 0 && b.style.display !== 'none';
          })(),
          canAscend: (typeof window.canAscend === 'function') ? !!window.canAscend() : null,
          ascensionOverlayPresent: !!document.getElementById('ascension-overlay'),
          ascensionOverlayShown: document.getElementById('ascension-overlay')?.classList.contains('show') || false
        })
        """)
        findings["observations"]["epic_status"] = epic_status

        # Capture l'aura T6 directement : on regarde le canvas pour des PNJ Champion
        # Test : on regle km=90 et on spawn quelques NPC T6 si l'API existe
        await page.evaluate("""
        (() => {
          if(!window.STATE) return;
          window.STATE.lapsRun = 90;
          // Try forcer un spawn T6 via API debug
          try {
            if(window.RUNNER_2D && typeof window.RUNNER_2D.spawnNpc === 'function'){
              for(let i=0;i<6;i++) window.RUNNER_2D.spawnNpc({forceTier: 6});
            }
          } catch(e){}
        })()
        """)
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(OUT / "endgame-aura-t6-spawn.png"))
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT / "endgame-aura-t6-followup.png"))

        # Ascension via clic sur bouton
        clicked = await page.evaluate("""
        () => {
          const b = document.getElementById('saison-btn');
          if(!b) return 'no_btn';
          const r = b.getBoundingClientRect();
          if(r.width === 0) return 'btn_hidden';
          b.click();
          return 'clicked';
        }
        """)
        findings["observations"]["ascension_btn"] = clicked
        await page.wait_for_timeout(900)
        await page.screenshot(path=str(OUT / "endgame-ascension-modal.png"))

        # Achievements unlocked check 75-100
        ach = await page.evaluate("""
        () => {
          const S = window.STATE;
          const ACH = window.ACHIEVEMENTS || (typeof ACHIEVEMENTS !== 'undefined' ? ACHIEVEMENTS : null);
          const targetIds = ['lap_75','lap_100','biome_flame','t6_first','speed_25','speed_33'];
          const out = {};
          if(!ACH || !S) return out;
          for(const id of targetIds){
            const def = ACH.find(a => a.id === id);
            if(!def){ out[id] = 'no_def'; continue; }
            try {
              out[id] = !!def.check(S);
            } catch(e){ out[id] = 'err'; }
          }
          // Etat unlocked (le jeu marque-t-il vraiment ?)
          out._unlocked = Object.keys(S.achievements || {});
          return out;
        }
        """)
        findings["observations"]["achievements_check"] = ach

        # Pull all logs
        logs = await page.evaluate("() => window.__qaLogs || []")
        findings["observations"]["console_logs_count"] = len(logs)
        findings["observations"]["console_logs_sample"] = logs[-15:] if logs else []
        findings["observations"]["page_errors"] = [{"type": t, "text": s[:300]} for t, s in page_errors[-25:]]

        await browser.close()

    out = OUT / "endgame-findings.json"
    out.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DONE", out)
    print(json.dumps({k: v for k, v in findings["observations"].items() if k != "console_logs_sample"}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
