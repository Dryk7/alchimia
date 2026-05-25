#!/usr/bin/env python3
"""
verify-v20-starspec.py
======================
Vérifie l'implémentation Vague 20 — Star Spec (3 spécialisations Star Tree).

Tests :
1. STATE.starSpec init (null par défaut)
2. STAR_SPEC_DEFS expose les 3 spécialisations
3. chooseStarSpec('sprinter') verrouille sur sprinter
4. isNodeUnlocked respecte la spec (tapPower=true pour sprinter, lapPower=false)
5. resetStarSpec refund + reset
6. Modal renderStarTree affiche les 3 specs si pas de spec
7. buyStarNode bloque les nodes verrouillés
8. Save/load roundtrip starSpec

Usage:
    python verify-v20-starspec.py
"""

import asyncio
import json
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: pip install playwright && playwright install chromium")
    sys.exit(1)

GAME_HTML = Path(__file__).parent / "index.html"
if not GAME_HTML.exists():
    print(f"ERROR: {GAME_HTML} introuvable")
    sys.exit(1)

URL = f"file:///{GAME_HTML.as_posix()}"


async def run():
    results = []
    errors = []

    def add(name, ok, msg=""):
        sym = "OK" if ok else "FAIL"
        results.append((name, ok, msg))
        print(f"[{sym}] {name}{(' — ' + msg) if msg else ''}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        await page.goto(URL)
        await page.wait_for_function("typeof STATE !== 'undefined'", timeout=15000)

        # Skip onboarding / intro
        await page.evaluate("""() => {
            try { localStorage.setItem('foulee_intro_seen', '1'); } catch(e){}
            // Force some stars to test
            STATE.stars = 50;
        }""")

        # === Test 1 : starSpec init null
        spec0 = await page.evaluate("STATE.starSpec")
        add("1. STATE.starSpec init null", spec0 is None, f"got={spec0!r}")

        # === Test 2 : STAR_SPEC_DEFS expose les 3 specs
        defs = await page.evaluate("Object.keys(STAR_SPEC_DEFS || {})")
        ok2 = set(defs or []) == {'sprinter', 'marathonien', 'hybride'}
        add("2. STAR_SPEC_DEFS expose 3 specs", ok2, f"keys={defs!r}")

        # === Test 3 : openStarTree + renderStarTree avec spec=null montre les 3 choix
        await page.evaluate("STATE.starSpec = null; if(typeof openStarTree==='function') openStarTree();")
        await page.wait_for_timeout(200)
        html_choice = await page.evaluate("(document.getElementById('star-tree-list') || {}).innerHTML || ''")
        ok3 = ('SPRINTER' in html_choice) and ('MARATHONIEN' in html_choice) and ('HYBRIDE' in html_choice)
        add("3. Modal montre les 3 spécialisations", ok3, f"len={len(html_choice)}")

        # === Test 4 : chooseStarSpec('sprinter') verrouille
        await page.evaluate("chooseStarSpec('sprinter')")
        spec1 = await page.evaluate("STATE.starSpec")
        add("4. chooseStarSpec('sprinter')", spec1 == 'sprinter', f"got={spec1!r}")

        # === Test 5 : isNodeUnlocked respecte la spec
        tap_ok = await page.evaluate("isNodeUnlocked('tapPower')")
        lap_ok = await page.evaluate("isNodeUnlocked('lapPower')")
        ok5 = (tap_ok is True) and (lap_ok is False)
        add("5. isNodeUnlocked sprinter (tap=true, lap=false)", ok5, f"tap={tap_ok}, lap={lap_ok}")

        # === Test 6 : buyStarNode bloque les nodes verrouillés
        await page.evaluate("STATE.stars = 100")
        buy_locked = await page.evaluate("buyStarNode('lapPower')")
        buy_unlocked = await page.evaluate("buyStarNode('tapPower')")
        ok6 = (buy_locked is False) and (buy_unlocked is True)
        add("6. buyStarNode bloque verrouillé / autorise unlocked", ok6, f"locked={buy_locked}, unl={buy_unlocked}")

        # === Test 7 : resetStarSpec refund + reset
        await page.evaluate("STATE.stars = 50; STATE.starTree.tapPower = 3;")
        before_stars = await page.evaluate("STATE.stars")
        reset_ok = await page.evaluate("resetStarSpec()")
        after_stars = await page.evaluate("STATE.stars")
        after_spec = await page.evaluate("STATE.starSpec")
        after_tap = await page.evaluate("STATE.starTree.tapPower")
        # 50 - 10 (cost) + 3 (refund) = 43
        ok7 = reset_ok and (after_spec is None) and (after_tap == 0) and (after_stars == 43)
        add("7. resetStarSpec refund + clear", ok7, f"stars {before_stars}->{after_stars}, spec={after_spec}, tap={after_tap}")

        # === Test 8 : Save/load roundtrip
        await page.evaluate("chooseStarSpec('marathonien')")
        if await page.evaluate("typeof saveNow === 'function'"):
            await page.evaluate("saveNow()")
        # simuler reload via loadSave
        await page.evaluate("""() => {
            STATE.starSpec = null;
            if(typeof loadSave === 'function') loadSave();
            else if(typeof load === 'function') load();
        }""")
        after_load = await page.evaluate("STATE.starSpec")
        add("8. Save/load roundtrip", after_load == 'marathonien', f"got={after_load!r}")

        # === Console errors
        ok_console = (len(errors) == 0)
        add("9. 0 erreurs console", ok_console, f"{len(errors)} errors")
        for e in errors[:5]:
            print(f"      | {e}")

        await browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*50}\nRESULT: {passed}/{total} tests passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
