"""QA late mid-game playthrough km 50-75 — FOULÉE
Force STATE et check biomes/coffres/upgrades/skills/rival/cap vitesse à chaque palier.
"""
from playwright.sync_api import sync_playwright
import json, os, time

URL = "http://localhost:8770/index.html"
OUT = r"D:/alchimia/screenshots/qa-vague10"
os.makedirs(OUT, exist_ok=True)

PALIERS = [49, 50, 51, 55, 60, 65, 70, 74, 75]

def collect(page, km):
    return page.evaluate(f"""() => {{
      try {{
        const s = window.STATE || {{}};
        const stage = (typeof currentStage === 'function') ? currentStage() : null;
        const biome = (typeof currentBiome === 'function' && stage) ? currentBiome(stage.idx) : null;
        const cap = (typeof SPEED_CAP !== 'undefined') ? SPEED_CAP : null;
        const baseSpeed = (typeof runnerBaseSpeed === 'function') ? runnerBaseSpeed() : null;
        const speedMul = (typeof runnerSpeedMultiplier === 'function') ? runnerSpeedMultiplier() : null;
        // Skills unlocked
        const skills = (typeof SKILLS !== 'undefined') ? SKILLS.map(sk => ({{
          id: sk.id, name: sk.name, unlock: sk.unlockLaps,
          unlocked: (s.lapsRun || 0) >= sk.unlockLaps, cd: sk.cooldown, dur: sk.duration
        }})) : [];
        // Upgrades + costs
        const ups = {{}};
        if(typeof UPGRADES_TAP !== 'undefined') {{
          for(const k in UPGRADES_TAP) {{
            const u = UPGRADES_TAP[k];
            const lvl = s[u.state] || 0;
            const cost = (typeof upgradeCost === 'function') ? upgradeCost(k) : null;
            const unlocked = !u.unlockLaps || (s.lapsRun || 0) >= u.unlockLaps;
            ups[k] = {{ lvl, cost, maxLevel: u.maxLevel || null, unlocked, unlockLaps: u.unlockLaps || 0 }};
          }}
        }}
        // Equipement state
        const equipBonus = (typeof window.equipBonus === 'function') ? {{
          speed: window.equipBonus('speed'), tap: window.equipBonus('tap'),
          regen: window.equipBonus('regen'), crit: window.equipBonus('crit')
        }} : null;
        // Achievements unlocked count
        const achCount = s.achievements ? Object.keys(s.achievements).length : 0;
        // Chest count
        const chests = s.chests || {{}};
        const chestTotal = Object.values(chests).reduce((a,b)=>a+(b||0), 0);
        return {{
          km: s.lapsRun, gold: s.gold, totalTaps: s.totalTaps,
          stage: stage ? {{ idx: stage.idx, name: stage.name, km: stage.km, crowd: stage.crowd,
            floors: stage.floors, projectors: stage.projectors, flags: stage.flags,
            extras: Object.keys(stage.extras || {{}}) }} : null,
          biome, cap, baseSpeed, speedMul,
          skills, upgrades: ups, equipBonus, achCount, chests, chestTotal,
          stamina: s.runnerStamina,
          chapter: s.chapter || 1, saison: s.saison || 1,
        }};
      }} catch(e) {{ return {{ err: String(e) }}; }}
    }}""")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 540, "height": 960}, device_scale_factor=2)
    page = ctx.new_page()
    console_errors = []
    page.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))
    page.on("console", lambda m: console_errors.append("console " + m.type + ": " + m.text) if m.type in ("error","warning") else None)

    # localStorage onboarding done
    page.goto(URL, wait_until="domcontentloaded")
    page.evaluate("""() => {
      try {
        localStorage.setItem('foulee_onboarding_done', '1');
        localStorage.setItem('foulee_intro_seen', '1');
        localStorage.setItem('foulee_tuto_done', '1');
      } catch(_){}
    }""")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Try to dismiss intro if visible
    for sel in ['#opening-credits', '#opening-credits-skip', '#tuto-step', '#intro-modal', '#daily-modal-close', '#start-game-btn', '#start-run-btn']:
        try:
            if page.locator(sel).count() > 0 and page.locator(sel).is_visible():
                page.locator(sel).first.click(force=True, timeout=500)
                page.wait_for_timeout(200)
        except Exception:
            pass

    # Force base state
    page.evaluate("""() => {
      try {
        STATE.gold = 5000000;
        STATE.totalTaps = 10000;
        STATE.lapsRun = 50;
        if(typeof checkAchievements === 'function') checkAchievements();
      } catch(e){ console.log('init err', e); }
    }""")
    page.wait_for_timeout(500)

    snapshots = {}
    transitions = {}
    last_biome = None

    for km in PALIERS:
        page.evaluate(f"""() => {{
          try {{
            STATE.lapsRun = {km};
            // clear stage cache
            try {{ _stageCache = {{ km: -1, result: null }}; }} catch(_){{}}
            if(typeof updateRunnerHUD === 'function') updateRunnerHUD();
            if(typeof checkAchievements === 'function') checkAchievements();
            if(typeof renderStats === 'function') renderStats();
          }} catch(e){{ console.log('km err', e); }}
        }}""")
        page.wait_for_timeout(800)
        data = collect(page, km)
        snapshots[km] = data
        biome = data.get("biome")
        if biome != last_biome:
            transitions[km] = {"from": last_biome, "to": biome, "stageName": (data.get("stage") or {}).get("name")}
            last_biome = biome
        # screenshot
        page.screenshot(path=os.path.join(OUT, f"km-{km:03d}.png"))

    # Check : at km 50 exactly, is a legendary chest granted automatically?
    # Simulate calling maybeDropItem() AS IF km had ticked from 49→50.
    chest_test = page.evaluate("""() => {
      try {
        // reset chests
        STATE.chests = { wood:0, iron:0, gold:0, legendary:0 };
        // simulate lap 50 closure
        STATE.lapsRun = 50;
        if(typeof maybeDropItem === 'function') maybeDropItem();
        return JSON.parse(JSON.stringify(STATE.chests));
      } catch(e){ return { err: String(e) }; }
    }""")

    # Simulate ALL the laps from 50 to 75 to count chests we'd get
    chests_50_to_75 = page.evaluate("""() => {
      try {
        STATE.chests = { wood:0, iron:0, gold:0, legendary:0 };
        for(let k = 50; k <= 75; k++){
          STATE.lapsRun = k;
          if(typeof maybeDropItem === 'function') maybeDropItem();
        }
        const out = JSON.parse(JSON.stringify(STATE.chests));
        out._total = Object.values(out).reduce((a,b)=>(typeof b==='number'?a+b:a), 0);
        return out;
      } catch(e){ return { err: String(e) }; }
    }""")

    # Check rival speed scale at km 50 and 75
    rival_test = page.evaluate("""() => {
      try {
        const t50 = 1.0 + Math.min(0.8, 50 * 0.015); // 1.75
        const t75 = 1.0 + Math.min(0.8, 75 * 0.015); // 1.8 (capped)
        const idx50 = Math.min(4, Math.floor(50 / 4));
        const idx75 = Math.min(4, Math.floor(75 / 4));
        const RIVAL = (typeof RIVAL_TYPES !== 'undefined') ? RIVAL_TYPES : null;
        return {
          k50: { scale: t50, idx: idx50 },
          k75: { scale: t75, idx: idx75 },
          // RIVAL_TYPES not in window scope so we just compute
        };
      } catch(e){ return { err: String(e) }; }
    }""")

    # Test cost of cruiseControl at lvl 0..5 + total to max
    cruise_cost = page.evaluate("""() => {
      try {
        const out = [];
        const u = UPGRADES_TAP.cruiseControl;
        const lvls = [0,1,5,10,14,15];
        for(const lvl of lvls){
          STATE.upgradeCruiseControl = lvl;
          out.push({ lvl, cost: upgradeCost('cruiseControl') });
        }
        // total cost from 0 to maxLevel
        let total = 0;
        for(let l = 0; l < u.maxLevel; l++){
          total += Math.floor(u.base * Math.pow(u.factor, l));
        }
        STATE.upgradeCruiseControl = 0;
        return { progression: out, totalToMax: total };
      } catch(e){ return { err: String(e) }; }
    }""")

    report = {
        "paliers": snapshots,
        "transitions": transitions,
        "chest_at_km50_only": chest_test,
        "chests_50_to_75_inclusive": chests_50_to_75,
        "rival_calc": rival_test,
        "cruise_costs": cruise_cost,
        "console_errors": console_errors[-30:],
    }
    with open(os.path.join(OUT, "qa-late-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False)[:8000])
    browser.close()
