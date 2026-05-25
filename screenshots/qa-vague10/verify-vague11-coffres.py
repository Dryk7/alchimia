"""
QA Vague 11 - Verification du systeme de coffres refondu.
Le but : prouver que seuls les km 50 et 100 donnent un coffre (gold + legendary).
Methode : on appelle directement maybeDropItem() apres avoir force STATE.lapsRun.
"""
import json, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"


def get_chests(page):
    return page.evaluate("""() => {
        const c = (window.STATE && window.STATE.chests) || {};
        return {
            wood: c.wood || 0,
            iron: c.iron || 0,
            gold: c.gold || 0,
            legendary: c.legendary || 0,
            total: (c.wood||0) + (c.iron||0) + (c.gold||0) + (c.legendary||0)
        };
    }""")


def test_km(page, km, label, results):
    """Force STATE.lapsRun = km, appelle maybeDropItem(), retourne le diff de coffres."""
    before = get_chests(page)
    page.evaluate(f"() => {{ window.STATE.lapsRun = {km}; window.STATE.totalTaps = 200; if(typeof maybeDropItem === 'function') maybeDropItem(); }}")
    after = get_chests(page)
    diff = {k: after[k] - before[k] for k in ['wood', 'iron', 'gold', 'legendary']}
    gained = [k for k, v in diff.items() if v > 0]
    chest_given = gained[0] if gained else None
    print(f"  km={km:3d} ({label:20s}) before total={before['total']} -> after total={after['total']} | coffre donne: {chest_given or 'AUCUN'}")
    results.append({"km": km, "label": label, "chest": chest_given, "diff": diff})
    return diff


def main():
    console_errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()
        page.on("console", lambda msg: (console_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None))
        page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"))

        print("== Chargement page ==")
        # Skip onboarding via localStorage avant load
        page.add_init_script("""
            try {
                localStorage.setItem('foulee.storySeen', '1');
                localStorage.setItem('foulee.onboardingSeen', '1');
                localStorage.setItem('foulee.lastSeenStage', '999');
            } catch(e){}
        """)
        page.goto(URL, wait_until="domcontentloaded")
        # Attendre que STATE soit pret
        page.wait_for_function("window.STATE && typeof window.maybeDropItem === 'function'", timeout=10000)

        # Init STATE.chests proprement
        page.evaluate("""() => {
            if(typeof _ensureChestState === 'function') _ensureChestState();
            window.STATE.chests = { wood:0, iron:0, gold:0, legendary:0 };
        }""")

        baseline = get_chests(page)
        print(f"Baseline chests: {baseline}")

        print("\n== Test chaque km cle ==")
        results = []
        # Tests de tous les km demandes
        for km, label in [
            (49, "avant mi-parcours"),
            (50, "MI-PARCOURS (gold attendu)"),
            (51, "apres mi-parcours"),
            (75, "ancien jalon 75"),
            (99, "avant ascension"),
            (100, "ASCENSION (legendary attendu)"),
            (101, "apres ascension"),
        ]:
            test_km(page, km, label, results)

        final = get_chests(page)
        print(f"\nFinal chests: {final}")

        # Assertions
        print("\n== Verification ==")
        ok = True
        # km 49 ne doit avoir donne aucun coffre
        r49 = next(r for r in results if r['km'] == 49)
        if r49['chest'] is not None:
            print(f"  FAIL km 49 a donne un coffre: {r49['chest']}")
            ok = False
        else:
            print(f"  OK km 49 -> aucun coffre")
        # km 50 doit avoir donne gold
        r50 = next(r for r in results if r['km'] == 50)
        if r50['chest'] != 'gold':
            print(f"  FAIL km 50 -> attendu gold, recu {r50['chest']}")
            ok = False
        else:
            print(f"  OK km 50 -> gold")
        # km 51 aucun
        r51 = next(r for r in results if r['km'] == 51)
        if r51['chest'] is not None:
            print(f"  FAIL km 51 a donne un coffre: {r51['chest']}")
            ok = False
        else:
            print(f"  OK km 51 -> aucun coffre")
        # km 75 ne doit plus donner de coffre (ancien jalon)
        r75 = next(r for r in results if r['km'] == 75)
        if r75['chest'] is not None:
            print(f"  FAIL km 75 a donne un coffre: {r75['chest']}")
            ok = False
        else:
            print(f"  OK km 75 -> aucun coffre")
        # km 99 aucun
        r99 = next(r for r in results if r['km'] == 99)
        if r99['chest'] is not None:
            print(f"  FAIL km 99 a donne un coffre: {r99['chest']}")
            ok = False
        else:
            print(f"  OK km 99 -> aucun coffre")
        # km 100 doit avoir donne legendary
        r100 = next(r for r in results if r['km'] == 100)
        if r100['chest'] != 'legendary':
            print(f"  FAIL km 100 -> attendu legendary, recu {r100['chest']}")
            ok = False
        else:
            print(f"  OK km 100 -> legendary")
        # km 101 aucun
        r101 = next(r for r in results if r['km'] == 101)
        if r101['chest'] is not None:
            print(f"  FAIL km 101 a donne un coffre: {r101['chest']}")
            ok = False
        else:
            print(f"  OK km 101 -> aucun coffre")

        # Erreurs console
        print(f"\n== Erreurs console: {len(console_errors)} ==")
        for e in console_errors[:10]:
            print(f"  {e}")

        # Resume tableau
        print("\n== Tableau recapitulatif ==")
        print(f"{'km':>4} | {'coffre':<12} | resultat")
        print("-" * 40)
        for r in results:
            chest = r['chest'] if r['chest'] else 'aucun'
            print(f"{r['km']:>4} | {chest:<12} | {r['label']}")

        browser.close()

        if ok and len(console_errors) == 0:
            print("\n>>> TEST PASSE <<<")
            sys.exit(0)
        else:
            print(f"\n>>> TEST ECHEC (ok={ok}, errors={len(console_errors)}) <<<")
            sys.exit(1)


if __name__ == "__main__":
    main()
