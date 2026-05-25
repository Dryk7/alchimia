"""
QA Mid-Early Playthrough — FOULÉE km 10/20/25/30
Spot-check des paliers via STATE.lapsRun forcé.
Lecture seule. Pas de modif du jeu.
"""
import os, json, time
from playwright.sync_api import sync_playwright

OUT = r"D:/alchimia/screenshots/qa-vague10"
URL = "http://localhost:8770/"
MILESTONES = [10, 20, 25, 30]

DUMP_JS = r"""
() => {
  const S = window.STATE || {};
  // Skill cooldowns
  const skillsInfo = (typeof SKILLS !== 'undefined' && Array.isArray(SKILLS)) ? SKILLS.map(s => ({
    id: s.id, name: s.name, unlockLaps: s.unlockLaps, cooldown: s.cooldown,
    unlocked: (S.lapsRun || 0) >= s.unlockLaps,
    lastUsed: (S.skillsLastUsed && S.skillsLastUsed[s.id]) || 0,
  })) : null;
  // Upgrades available + level + cost
  let upgradesInfo = null;
  if (typeof UPGRADES_TAP !== 'undefined' && typeof upgradeCost === 'function') {
    upgradesInfo = {};
    for (const k of Object.keys(UPGRADES_TAP)) {
      const u = UPGRADES_TAP[k];
      const lvl = S[u.state] || 0;
      const visible = !u.unlockLaps || (S.lapsRun || 0) >= u.unlockLaps;
      upgradesInfo[k] = {
        lvl, cost: upgradeCost(k), visible,
        maxLevel: u.maxLevel || null, unlockLaps: u.unlockLaps || 0,
        affordable: (S.gold || 0) >= upgradeCost(k),
      };
    }
  }
  // Achievements unlocked
  const achievementsUnlocked = S.achievements ? Object.keys(S.achievements).length : 0;
  const achievementsList = S.achievements ? Object.keys(S.achievements) : [];
  // Chests
  const chests = S.chests || {};
  const totalChests = Object.values(chests).reduce((a,b)=>a+(b||0),0);
  // Equipement
  const equip = S.equipment || S.equippedItems || null;
  const inv = S.inventory || null;
  // Rival
  const rivalsWon = S.rivalsWon || 0;
  const rivalsLost = S.rivalsLost || 0;
  return {
    lapsRun: S.lapsRun || 0,
    gold: S.gold || 0,
    upgradeBaseSpeed: S.upgradeBaseSpeed || 0,
    upgradeTapValue: S.upgradeTapValue || 0,
    upgradeCritChance: S.upgradeCritChance || 0,
    upgradeLapBonus: S.upgradeLapBonus || 0,
    upgradeAutoTap: S.upgradeAutoTap || 0,
    upgradeEndurance: S.upgradeEndurance || 0,
    upgradeEagleEye: S.upgradeEagleEye || 0,
    upgradeCruiseControl: S.upgradeCruiseControl || 0,
    stars: S.stars || 0,
    chests, totalChests,
    rivalsWon, rivalsLost,
    achievementsUnlocked, achievementsList,
    skillsInfo, upgradesInfo,
    equip_keys: equip ? Object.keys(equip) : null,
    inv_count: inv ? (Array.isArray(inv) ? inv.length : Object.keys(inv).length) : null,
  };
}
"""

def dismiss_modals(page):
    # Ferme tout overlay/modal éventuel
    selectors = [
        '.modal.show .modal-close', '.modal.open .close', '.modal-close',
        '.overlay .close', '.opening-skip', '#opening-cinema button',
        '.story-skip', '.intro-skip', '.btn-close',
        'button:has-text("Skip")', 'button:has-text("Passer")',
        'button:has-text("OK")', 'button:has-text("Continuer")',
        'button:has-text("Fermer")', 'button:has-text("Non merci")',
    ]
    for sel in selectors:
        try:
            els = page.query_selector_all(sel)
            for el in els:
                if el.is_visible():
                    el.click(timeout=500)
                    page.wait_for_timeout(120)
        except Exception:
            pass

def main():
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width':540,'height':960}, device_scale_factor=2)
        page = ctx.new_page()
        console_errors = []
        page.on('console', lambda m: console_errors.append((m.type, m.text)) if m.type in ('error','warning') else None)

        # Skip onboarding via localStorage AVANT chargement
        page.add_init_script("""
          try {
            localStorage.setItem('foulee.openingSeen','1');
            localStorage.setItem('foulee.storySeen','1');
            localStorage.setItem('foulee.tutoV3','done');
            localStorage.setItem('foulee.activeTutoV1','done');
          } catch(e){}
        """)
        page.goto(URL, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(800)
        dismiss_modals(page)
        page.wait_for_timeout(300)

        # Click sur "Prendre le départ" / start
        try:
            for sel in ['button:has-text("PRENDRE LE DÉPART")','button:has-text("PRENDRE")','button:has-text("DÉPART")','button:has-text("START")','#btn-start']:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click(timeout=2000); break
        except Exception:
            pass
        page.wait_for_timeout(800)
        dismiss_modals(page)

        # Bloque starter pack
        page.evaluate("""
          () => {
            try {
              if(window.STATE){
                window.STATE.starterPackDeclined = true;
                window.STATE.starterPackClaimed  = true;
              }
            } catch(e){}
          }
        """)
        page.wait_for_timeout(200)
        dismiss_modals(page)

        page.screenshot(path=os.path.join(OUT, 'qa-00-game-start.png'))

        # Tester chaque palier — simulation organique : pour chaque km incrémentiel, on appelle maybeDropItem + checkAchievements
        prev_km = 0
        for km in MILESTONES:
            page.evaluate(f"""
              () => {{
                try {{
                  const start = window.STATE.lapsRun || 0;
                  for(let k = start + 1; k <= {km}; k++){{
                    window.STATE.lapsRun = k;
                    if(typeof maybeDropItem === 'function') maybeDropItem();
                    if(typeof checkAchievements === 'function') checkAchievements();
                  }}
                  if(typeof refreshQuests === 'function') refreshQuests();
                  if(typeof updateChestBadge === 'function') updateChestBadge();
                }} catch(e){{ console.log('set lapsRun err', e); }}
              }}
            """)
            page.wait_for_timeout(700)
            dismiss_modals(page)
            dump = page.evaluate(DUMP_JS)
            results[f'km_{km}'] = dump
            page.screenshot(path=os.path.join(OUT, f'qa-km{km:02d}-hud.png'))

            # Tente d'ouvrir le shop upgrades pour screenshot
            try:
                for sel in ['button:has-text("UPGRADES")','button:has-text("Améliorations")','button:has-text("Shop")','#btn-shop','[data-action="openShopModal"]','[data-modal="shop"]']:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click(timeout=1500)
                        page.wait_for_timeout(400)
                        page.screenshot(path=os.path.join(OUT, f'qa-km{km:02d}-shop.png'))
                        dismiss_modals(page)
                        break
            except Exception:
                pass

            # Tente d'ouvrir le chests modal
            try:
                page.evaluate("() => { if(typeof openChestsModal==='function') openChestsModal(); }")
                page.wait_for_timeout(350)
                page.screenshot(path=os.path.join(OUT, f'qa-km{km:02d}-chests.png'))
                dismiss_modals(page)
            except Exception:
                pass

        # Dump global équipement + inv + console
        glob = page.evaluate(r"""
          () => {
            const S = window.STATE || {};
            return {
              keys: Object.keys(S).sort(),
              hasEquipFn: typeof openEquip === 'function',
              hasWardrobeFn: typeof openWardrobe === 'function',
              hasSkillTreeFn: typeof openSkillTree === 'function',
              chestsState: S.chests || null,
              equipment: S.equipment || S.equippedItems || null,
              inventory: S.inventory || null,
              skills: S.skills || null,
              skillsLastUsed: S.skillsLastUsed || null,
              rivalsWon: S.rivalsWon || 0,
              rivalsLost: S.rivalsLost || 0,
              activeRival: S.activeRival || null,
            };
          }
        """)
        results['_global'] = glob
        results['_console'] = console_errors[:60]

        with open(os.path.join(OUT, 'qa-midearly-dump.json'), 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        browser.close()
    print(json.dumps({'paliers': MILESTONES, 'console_msgs': len(results['_console'])}, indent=2))

if __name__ == '__main__':
    main()
