"""
VAGUE 15bis - Agent A10 - Vérif enrichissement du panel "Records" :
- Distance totale cumulée
- Ascensions réalisées
- Coffres ouverts
- Boss runners dépassés
- Haies ratées + taux de réussite
- Plus grande rareté item équipée

Étapes :
1. Skip onboarding (storySeen + activeTuto)
2. Force STATE.totalChestsOpened=5, STATE.ascensions=2,
   STATE.totalBossDodged=3, STATE.hurdlesFailed=4, STATE.hurdlesSuccess=16,
   STATE.totalLifetimeKm=250, STATE.equipment={head:{rarity:'epic'}}
3. Appeler renderRecords() puis ouvrir la modale
4. Vérifier que le DOM #records-body contient :
   - "Coffres ouverts" / "Ascensions" / "Distance totale"
   - "Boss dépassés" / "Haies ratées" / "Taux de réussite haies"
   - "Meilleure rareté équipée"
5. Screenshot + 0 erreurs console
"""
import sys
import time
import io
from pathlib import Path

# Force UTF-8 stdout
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[FAIL] playwright introuvable. pip install playwright && playwright install chromium")
    sys.exit(1)

INDEX = Path("D:/alchimia/index.html").resolve()
OUT_DIR = Path("D:/alchimia/screenshots/qa-vague10")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT = OUT_DIR / "v15bis-a10-records-enriched.png"


def main():
    if not INDEX.exists():
        print(f"[FAIL] {INDEX} introuvable")
        return 1

    url = INDEX.as_uri()
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 414, "height": 896})
        page = ctx.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(f"PAGEERROR: {err}"))

        # Skip story/tutos
        page.add_init_script("""
            try{
              localStorage.setItem('storySeen','1');
              localStorage.setItem('foulee.activeTutoV1', JSON.stringify({done:true}));
            }catch(e){}
        """)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"[FAIL] goto: {e}")
            browser.close()
            return 1

        time.sleep(1.5)

        # Étape 1 : injecter stats forcées dans STATE
        injected = page.evaluate("""() => {
            if(!window.STATE) return {error: 'STATE not found'};
            window.STATE.totalChestsOpened = 5;
            window.STATE.ascensions = 2;
            window.STATE.totalBossDodged = 3;
            window.STATE.hurdlesFailed = 4;
            window.STATE.hurdlesSuccess = 16;
            window.STATE.hurdlesCleared = 16;
            window.STATE.totalLifetimeKm = 250;
            window.STATE.lapsRun = 250;
            window.STATE.equipment = {
                head: { rarityId: 'epic', name: 'Bandeau Epique' },
                body: { rarityId: 'rare', name: 'Maillot Rare' },
                feet: { rarityId: 'common', name: 'Baskets' }
            };
            return {
                chests: window.STATE.totalChestsOpened,
                ascensions: window.STATE.ascensions,
                bossDodged: window.STATE.totalBossDodged,
                hurdleFails: window.STATE.hurdlesFailed,
                hurdleSuccess: window.STATE.hurdlesSuccess,
                lifetimeKm: window.STATE.totalLifetimeKm,
                equipKeys: Object.keys(window.STATE.equipment)
            };
        }""")
        print(f"State injected: {injected}")

        time.sleep(0.5)

        # Étape 2 : appeler renderRecords + ouvrir la modale
        rendered = page.evaluate("""() => {
            try {
                if(typeof openRecords === 'function'){
                    openRecords();
                } else if(typeof renderRecords === 'function'){
                    renderRecords();
                }
            } catch(e){ return {error: String(e)}; }
            const body = document.getElementById('records-body');
            const txt = body ? body.textContent : '';
            return {
                hasBody: !!body,
                length: txt.length,
                hasCoffres: txt.includes('Coffres ouverts'),
                hasAscensions: txt.includes('Ascensions'),
                hasDistance: txt.includes('Distance totale'),
                hasBoss: txt.includes('Boss dépassés'),
                hasHurdleFails: txt.includes('Haies ratées'),
                hasHurdleRate: txt.includes('Taux de réussite'),
                hasBestRarity: txt.includes('Meilleure rareté équipée'),
                // Vérif valeurs
                hasChest5: /Coffres ouverts.*?5/s.test(txt),
                hasAsc2: /Ascensions.*?2/s.test(txt),
                hasBoss3: /Boss dépassés.*?3/s.test(txt),
                hasEpic: txt.includes('epic'),
                rate80: txt.includes('80%')
            };
        }""")
        print(f"Render: {rendered}")

        time.sleep(0.8)

        try:
            page.screenshot(path=str(SCREENSHOT), full_page=False)
        except Exception as e:
            print(f"[WARN] screenshot: {e}")

        browser.close()

    # Vérifications
    print("=" * 60)
    print("VAGUE 15bis - A10 - Records panel enriched")
    print("=" * 60)

    if not isinstance(rendered, dict) or rendered.get("error"):
        print(f"[FAIL] Render error: {rendered}")
        return 2

    checks = {
        "Body present":                rendered.get("hasBody", False),
        "Section Coffres":             rendered.get("hasCoffres", False),
        "Section Ascensions":          rendered.get("hasAscensions", False),
        "Section Distance totale":     rendered.get("hasDistance", False),
        "Section Boss":                rendered.get("hasBoss", False),
        "Section Haies ratées":        rendered.get("hasHurdleFails", False),
        "Section Taux de réussite":    rendered.get("hasHurdleRate", False),
        "Section Meilleure rareté":    rendered.get("hasBestRarity", False),
        "Valeur coffres=5":            rendered.get("hasChest5", False),
        "Valeur ascensions=2":         rendered.get("hasAsc2", False),
        "Valeur boss=3":               rendered.get("hasBoss3", False),
        "Rareté epic affichée":        rendered.get("hasEpic", False),
        "Taux haies = 80%":            rendered.get("rate80", False),
        "0 console errors":            len(console_errors) == 0,
    }

    print("-" * 60)
    all_ok = True
    for k, v in checks.items():
        flag = "OK " if v else "FAIL"
        print(f"  [{flag}] {k}")
        if not v:
            all_ok = False

    print("-" * 60)
    print(f"Console errors: {len(console_errors)}")
    for e in console_errors[:5]:
        print(f"  - {e}")
    print(f"Screenshot: {SCREENSHOT}")

    print("=" * 60)
    print("RESULT:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
