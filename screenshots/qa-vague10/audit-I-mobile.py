"""
AUDIT I — Mobile responsive des upgrades.
READ-ONLY. Sert la page depuis http://localhost:8770/, manipule uniquement
en mémoire (localStorage + DOM in-page) et produit des screenshots.

Tests :
  - 320x568 (iPhone SE)
  - 412x915 (Pixel 7)

Pour chaque taille :
  - Skip onboarding
  - Force lapsRun=30, gold=100000 (via UPGRADES.gold / UPGRADES.lapsRun)
  - Ouvre l'onglet UPGRADES (tab-upgrades)
  - Screenshot HUD + drawer
  - Mesure scrollWidth, overflow vertical du drawer, hauteur boutons
"""

from playwright.sync_api import sync_playwright
import json
import pathlib

OUT_DIR = pathlib.Path(r"D:/alchimia/screenshots/qa-vague10")
OUT_DIR.mkdir(parents=True, exist_ok=True)

URL = "http://localhost:8770/"

SIZES = [
    ("320x568", 320, 568),
    ("412x915", 412, 915),
]

# Script JS pour skip onboarding + forcer état
SETUP_JS = r"""
() => {
  // Skip toutes les portes d'onboarding/intro
  try {
    localStorage.setItem('foulee.openingSeen', '1');
    localStorage.setItem('foulee.storySeen', '1');
    localStorage.setItem('foulee.onboardingDone', 'done');
    localStorage.setItem('foulee.onboardingV2', 'done');
  } catch(e){}

  // Forcer save minimum pour que le jeu charge
  try {
    const existing = localStorage.getItem('alchimia.save');
    if (!existing) {
      localStorage.setItem('alchimia.save', JSON.stringify({
        gold: 100000,
        lapsRun: 30,
      }));
    }
  } catch(e){}
}
"""

# Une fois la page chargée, on tente de pousser les valeurs sur l'objet runtime
FORCE_STATE_JS = r"""
() => {
  let touched = {};
  try {
    if (window.STATE) {
      window.STATE.gold = 100000;
      window.STATE.lapsRun = 30;
      window.STATE.saison = window.STATE.saison || 1;
      touched.STATE = { gold: window.STATE.gold, lapsRun: window.STATE.lapsRun };
    }
  } catch(e){ touched.errSTATE = String(e); }
  // Déverrouille tous les boutons upgrades via le système de progressive disclosure
  try {
    if (typeof applyProgressiveDisclosure === 'function') {
      applyProgressiveDisclosure();
      touched.applyProgressiveDisclosure = true;
    }
  } catch(e){ touched.errAPD = String(e); }
  // Fallback : force data-locked=0 sur tous les upg-btn
  try {
    document.querySelectorAll('.upg-btn[data-locked="1"]').forEach(b => {
      b.setAttribute('data-locked','0');
    });
    touched.forcedUnlock = document.querySelectorAll('.upg-btn').length;
  } catch(e){}
  // Refresh HUD si dispo
  try { if (typeof renderUpgrades === 'function') renderUpgrades(); } catch(e){}
  try { if (typeof updateHUD === 'function') updateHUD(); } catch(e){}
  return touched;
}
"""

MEASURE_JS = r"""
() => {
  const docEl = document.documentElement;
  const scrollWidth = docEl.scrollWidth;
  const clientWidth = docEl.clientWidth;
  const horizontalOverflow = scrollWidth > clientWidth;

  // Drawer / panneau upgrade : on cible le pane upgrades et sa container
  const pane = document.querySelector('[data-pane="upgrades"]');
  const grid = document.querySelector('.tap-upgrades-v2');

  let drawerInfo = null;
  if (pane) {
    const r = pane.getBoundingClientRect();
    drawerInfo = {
      scrollHeight: pane.scrollHeight,
      clientHeight: pane.clientHeight,
      offsetHeight: pane.offsetHeight,
      verticalOverflow: pane.scrollHeight > pane.clientHeight,
      width: r.width, height: r.height
    };
  }

  // Boutons upgrade : mesurer hauteur, largeur, position
  const btns = Array.from(document.querySelectorAll('.tap-upgrades-v2 .upg-btn'));
  const btnMetrics = btns.map(b => {
    const r = b.getBoundingClientRect();
    const cs = getComputedStyle(b);
    return {
      label: (b.querySelector('.upg-name')||{}).textContent || b.getAttribute('aria-label') || '',
      visible: r.width > 0 && r.height > 0,
      width: Math.round(r.width),
      height: Math.round(r.height),
      top: Math.round(r.top),
      bottom: Math.round(r.bottom),
      locked: b.classList.contains('locked') || b.dataset.locked === '1',
      display: cs.display,
    };
  });

  // Grid : nb colonnes effectives ?
  let gridCols = null;
  if (grid) {
    const cs = getComputedStyle(grid);
    gridCols = cs.gridTemplateColumns;
  }

  // Espace mal utilisé : surface drawer vs surface boutons visibles
  let utilization = null;
  if (drawerInfo && btnMetrics.length) {
    const totalBtnArea = btnMetrics
      .filter(b => b.visible)
      .reduce((s,b)=> s + (b.width * b.height), 0);
    const drawerArea = drawerInfo.width * Math.max(drawerInfo.height, drawerInfo.scrollHeight);
    utilization = drawerArea > 0 ? +(totalBtnArea / drawerArea).toFixed(3) : null;
  }

  return {
    viewport: { w: window.innerWidth, h: window.innerHeight },
    scrollWidth, clientWidth, horizontalOverflow,
    drawer: drawerInfo,
    gridCols,
    buttons: btnMetrics,
    btnCount: btnMetrics.length,
    btnVisible: btnMetrics.filter(b => b.visible).length,
    btnUnder48: btnMetrics.filter(b => b.visible && b.height < 48).length,
    btnUnder44: btnMetrics.filter(b => b.visible && b.height < 44).length,
    utilization,
  };
}
"""

OPEN_UPGRADES_JS = r"""
() => {
  // Tente plusieurs façons d'ouvrir l'onglet upgrades
  // 1. Click sur bouton avec data-tab="upgrades"
  let opened = false;
  const candidates = [
    '[data-tab="upgrades"]',
    'button[aria-controls="upgrades"]',
    '.tab-btn[data-pane="upgrades"]',
    '[data-tab-target="upgrades"]',
  ];
  for (const sel of candidates) {
    const el = document.querySelector(sel);
    if (el) { el.click(); opened = sel; break; }
  }
  // 2. Force show du pane et de son parent drawer si on a un id
  const pane = document.querySelector('[data-pane="upgrades"]');
  if (pane) {
    pane.classList.add('active','show','open');
    pane.style.display = 'block';
    // remonte le parent drawer/tab-container
    let p = pane.parentElement;
    while (p) {
      if (p.classList && (p.classList.contains('drawer') || p.classList.contains('tab-drawer'))) {
        p.classList.add('open','show');
        p.style.transform = 'translateY(0)';
        p.style.display = 'block';
        document.body.classList.add('tab-drawer-open');
        opened = (opened||'') + '|forced-parent';
        break;
      }
      p = p.parentElement;
    }
  }
  return opened;
}
"""

def run():
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for label, w, h in SIZES:
                ctx = browser.new_context(
                    viewport={"width": w, "height": h},
                    device_scale_factor=2,
                    is_mobile=True,
                    has_touch=True,
                    user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36",
                )
                page = ctx.new_page()
                # 1) charger une 1re fois pour pouvoir set localStorage sur le bon origin
                page.goto(URL, wait_until="domcontentloaded", timeout=20000)
                page.evaluate(SETUP_JS)
                # 2) recharger pour que le code de boot voie le localStorage
                page.goto(URL, wait_until="load", timeout=20000)
                page.wait_for_timeout(1500)

                touched = page.evaluate(FORCE_STATE_JS)
                page.wait_for_timeout(200)

                opened = page.evaluate(OPEN_UPGRADES_JS)
                page.wait_for_timeout(400)
                # refresh UI à nouveau au cas où certains renders soient lazy
                page.evaluate(FORCE_STATE_JS)
                page.wait_for_timeout(300)

                # Scroll au pane upgrades pour qu'il soit dans le viewport
                page.evaluate("""() => {
                  const pane = document.querySelector('[data-pane="upgrades"]');
                  if (pane) pane.scrollIntoView({block:'start', inline:'nearest'});
                }""")
                page.wait_for_timeout(300)

                # Screenshot viewport (HUD splash + drawer scrollé) + full-page de référence
                shot = OUT_DIR / f"audit-I-{label}-upgrades.png"
                page.screenshot(path=str(shot), full_page=False)
                shot_full = OUT_DIR / f"audit-I-{label}-upgrades-full.png"
                page.screenshot(path=str(shot_full), full_page=True)

                metrics = page.evaluate(MEASURE_JS)
                metrics["_setup"] = {"touched": touched, "openedSelector": opened}
                results[label] = metrics

                ctx.close()
        finally:
            browser.close()

    # Sauvegarder JSON + résumé console
    out_json = OUT_DIR / "audit-I-mobile.json"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=== AUDIT I — MOBILE RESPONSIVE ===")
    for label, m in results.items():
        print(f"\n--- {label} ---")
        print(f"viewport={m['viewport']}  scrollWidth={m['scrollWidth']}  clientWidth={m['clientWidth']}  H-overflow={m['horizontalOverflow']}")
        d = m["drawer"]
        if d:
            print(f"drawer pane: w={int(d['width'])} h={int(d['height'])} scrollH={d['scrollHeight']} V-overflow={d['verticalOverflow']}")
        print(f"gridCols={m['gridCols']}")
        print(f"buttons total={m['btnCount']} visible={m['btnVisible']}  under48={m['btnUnder48']} under44={m['btnUnder44']}")
        print(f"utilization (btns area / drawer area)={m['utilization']}")
        for b in m["buttons"]:
            print(f"  - {b['label']!r:25s} h={b['height']} w={b['width']} top={b['top']} locked={b['locked']} disp={b['display']}")
        print(f"setup: {m['_setup']}")
    print(f"\nScreenshots dans: {OUT_DIR}")
    print(f"JSON: {out_json}")

if __name__ == "__main__":
    run()
