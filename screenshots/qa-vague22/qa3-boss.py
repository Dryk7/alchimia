"""
QA Vague 22 - Boss system (READ-ONLY)
Vérifie que les 7 bosses spawn aux km déterministes (60/80/110/140/170/200/250)
et que defeatBoss() accorde les rewards (+1 star, +10000 gold).
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
OUT = Path(r"D:/alchimia/screenshots/qa-vague22")
OUT.mkdir(parents=True, exist_ok=True)

# Boss config attendu — vagues 20/21
EXPECTED_BOSSES = [
    (60,  'draftbreaker'),
    (80,  'shadowpace'),
    (110, 'stormsprint'),
    (140, 'ironlung'),
    (170, 'mirror'),
    (200, 'cosmic'),
    (250, 'moonking'),
]

page_errors = []
console_errors = []
scenario_errors = {}


def attach_listeners(page, label="global"):
    def on_pageerror(err):
        msg = f"[{label}] pageerror: {err}"
        page_errors.append(msg)
        scenario_errors.setdefault(label, []).append(msg)

    def on_console(msg):
        if msg.type == "error":
            text = f"[{label}] console.error: {msg.text}"
            console_errors.append(text)
            scenario_errors.setdefault(label, []).append(text)

    page.on("pageerror", on_pageerror)
    page.on("console", on_console)


async def safe_eval(page, expr, label):
    try:
        return await page.evaluate(expr)
    except Exception as e:
        msg = f"[{label}] eval-fail: {expr[:90]} -> {e}"
        scenario_errors.setdefault(label, []).append(msg)
        return None


async def test_boss_spawn(page, km, expected_id):
    """Force lapsRun=km, spawn un npc, vérifie qu'il a bossId."""
    label = f"spawn_km{km}"
    scenario_errors.setdefault(label, [])

    # 1) Reset bosses defeated flags pour s'assurer qu'il peut re-spawn
    await safe_eval(page, """
        () => {
            if (window.STATE && STATE.bosses) {
                for (const id in STATE.bosses) STATE.bosses[id].defeated = false;
            }
        }
    """, label)

    # 2) Force lapsRun
    await safe_eval(page, f"() => {{ STATE.lapsRun = {km}; }}", label)

    # 3) Vide les npcs existants (pour test propre)
    await safe_eval(page, """
        () => {
            // npcs vit dans closure — on essaie via dump fonction si exposée
            // Sinon on n'a pas accès direct, on spawn plusieurs et on cherche le boss
        }
    """, label)

    # 4) Vérifier getBossIdForKm
    expected_via_helper = await safe_eval(
        page,
        f"() => (typeof getBossIdForKm === 'function') ? getBossIdForKm({km}) : null",
        label,
    )

    # 5) Vérifier getActiveBoss
    active_boss = await safe_eval(
        page,
        "() => (typeof getActiveBoss === 'function') ? getActiveBoss() : null",
        label,
    )

    # 6) Forcer spawnNpc plusieurs fois (les lanes peuvent rejeter le spawn)
    spawn_attempts = 0
    spawned_boss_npc = None
    for attempt in range(20):
        spawn_attempts += 1
        result = await safe_eval(page, """
            () => {
                if (typeof spawnNpc !== 'function') return {ok:false, reason:'no spawnNpc'};
                try {
                    spawnNpc();
                    // Cherche dans window.npcs si exposé, sinon on tente via STATE/global
                    return {ok:true};
                } catch(e) { return {ok:false, err:String(e)}; }
            }
        """, label)
        if not result or not result.get("ok"):
            scenario_errors[label].append(f"spawnNpc-fail attempt {attempt}: {result}")
            break

    # 7) Le tableau npcs vit dans une closure. Tente plusieurs accès.
    npcs_dump = await safe_eval(page, """
        () => {
            // Tentative 1: window.npcs
            if (Array.isArray(window.npcs)) return {src:'window.npcs', list: window.npcs.map(n => ({
                tier: n.tier, isBoss: n.isBoss, bossId: n.bossId, laneIdx: n.laneIdx, metersAhead: n.metersAhead
            }))};
            // Tentative 2: STATE.npcs
            if (window.STATE && Array.isArray(STATE.npcs)) return {src:'STATE.npcs', list: STATE.npcs.map(n => ({
                tier: n.tier, isBoss: n.isBoss, bossId: n.bossId
            }))};
            return {src:'none', list: []};
        }
    """, label)

    # 8) Si npcs invisibles depuis l'extérieur, on s'appuie sur les helpers : getBossIdForKm + getActiveBoss
    boss_found = None
    if npcs_dump and npcs_dump.get("list"):
        for n in npcs_dump["list"]:
            if n.get("isBoss") or n.get("bossId"):
                boss_found = n
                break

    result = {
        "km": km,
        "expected_id": expected_id,
        "getBossIdForKm": expected_via_helper,
        "getActiveBoss": active_boss,
        "spawn_attempts": spawn_attempts,
        "npcs_src": npcs_dump.get("src") if npcs_dump else None,
        "npcs_total": len(npcs_dump.get("list", [])) if npcs_dump else 0,
        "boss_npc": boss_found,
        "helper_match": expected_via_helper == expected_id,
        "active_match": (active_boss and active_boss.get("id") == expected_id) if active_boss else False,
        "npc_bossId_match": (boss_found and boss_found.get("bossId") == expected_id) if boss_found else False,
        "npc_isBoss_true": bool(boss_found and boss_found.get("isBoss") is True) if boss_found else False,
        "npc_tier_ge6": bool(boss_found and (boss_found.get("tier") or 0) >= 6) if boss_found else False,
    }

    # Screenshot
    try:
        await page.screenshot(path=str(OUT / f"boss-{km:03d}-{expected_id}.png"))
    except Exception:
        pass

    return result


async def test_defeat_boss(page):
    """Test defeatBoss('draftbreaker') — vérifie rewards."""
    label = "defeatBoss"
    scenario_errors.setdefault(label, [])

    # Snapshot avant
    before = await safe_eval(page, """
        () => ({
            stars: STATE.stars || 0,
            gold: STATE.gold || 0,
            totalStarsEarned: STATE.totalStarsEarned || 0,
            defeated: STATE.bosses?.draftbreaker?.defeated,
        })
    """, label)

    # Reset si déjà défait pour bien tester l'incrément
    await safe_eval(page, """
        () => { if (STATE.bosses?.draftbreaker) STATE.bosses.draftbreaker.defeated = false; }
    """, label)

    before2 = await safe_eval(page, """
        () => ({
            stars: STATE.stars || 0,
            gold: STATE.gold || 0,
            totalStarsEarned: STATE.totalStarsEarned || 0,
            defeated: STATE.bosses?.draftbreaker?.defeated,
        })
    """, label)

    # Appel defeatBoss
    call_result = await safe_eval(page, """
        () => {
            if (typeof defeatBoss !== 'function') return {ok:false, reason:'no defeatBoss'};
            try { defeatBoss('draftbreaker'); return {ok:true}; }
            catch(e) { return {ok:false, err:String(e)}; }
        }
    """, label)

    # Snapshot après
    after = await safe_eval(page, """
        () => ({
            stars: STATE.stars || 0,
            gold: STATE.gold || 0,
            totalStarsEarned: STATE.totalStarsEarned || 0,
            defeated: STATE.bosses?.draftbreaker?.defeated,
        })
    """, label)

    delta_stars = (after["stars"] - before2["stars"]) if (after and before2) else None
    delta_gold = (after["gold"] - before2["gold"]) if (after and before2) else None
    delta_total_stars = (after["totalStarsEarned"] - before2["totalStarsEarned"]) if (after and before2) else None

    try:
        await page.screenshot(path=str(OUT / "boss-defeat-draftbreaker.png"))
    except Exception:
        pass

    return {
        "call": call_result,
        "before": before2,
        "after": after,
        "delta_stars": delta_stars,
        "delta_gold": delta_gold,
        "delta_totalStars": delta_total_stars,
        "stars_plus_1": delta_stars == 1,
        "gold_plus_10000": delta_gold == 10000,
        "defeated_true": after.get("defeated") is True if after else False,
    }


async def test_defeated_no_respawn(page):
    """Vérifie qu'un boss déjà défait ne respawn pas."""
    label = "no_respawn"
    scenario_errors.setdefault(label, [])

    # 'draftbreaker' a été défait au test précédent
    await safe_eval(page, "() => { STATE.lapsRun = 60; }", label)

    helper_id = await safe_eval(
        page,
        "() => (typeof getBossIdForKm === 'function') ? getBossIdForKm(60) : null",
        label,
    )
    active = await safe_eval(
        page,
        "() => (typeof getActiveBoss === 'function') ? getActiveBoss() : null",
        label,
    )

    return {
        "km": 60,
        "expected_id_when_defeated": None,  # car déjà défait
        "getBossIdForKm_returned": helper_id,
        "getActiveBoss_returned": active,
        "skip_defeated_ok": helper_id is None,
    }


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
        )

        # Pre-skip onboarding
        await ctx.add_init_script("""
            try {
                localStorage.setItem('foulee.tutoV2', 'done');
                localStorage.setItem('alchimia_onboarding_done', '1');
                localStorage.setItem('onboarding_done', '1');
                localStorage.setItem('onboardingDone', '1');
                localStorage.setItem('alchimia_tuto_done', '1');
                localStorage.setItem('tuto_done', '1');
                localStorage.setItem('alchimia_intro_seen', '1');
                localStorage.setItem('alchimia_first_run', '0');
            } catch(e) {}
        """)

        page = await ctx.new_page()
        attach_listeners(page, "boot")

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(OUT / "boss-00-init.png"))

        # Vérifie expositions
        exposed = await page.evaluate("""
            () => ({
                getBossIdForKm: typeof window.getBossIdForKm,
                getActiveBoss: typeof window.getActiveBoss,
                defeatBoss: typeof window.defeatBoss,
                spawnNpc: typeof window.spawnNpc,
                BOSS_KM_MAP: typeof window.BOSS_KM_MAP,
                STATE_bosses: typeof window.STATE?.bosses,
                STATE_bosses_keys: window.STATE?.bosses ? Object.keys(window.STATE.bosses) : [],
            })
        """)

        # Dump du BOSS_KM_MAP réel
        boss_km_map = await page.evaluate("() => window.BOSS_KM_MAP || null")

        # Dump initial STATE.bosses
        initial_bosses = await page.evaluate("""
            () => {
                if (!window.STATE?.bosses) return null;
                const out = {};
                for (const id in STATE.bosses) {
                    const b = STATE.bosses[id];
                    out[id] = { name: b.name, spawnKm: b.spawnKm, type: b.type, defeated: b.defeated };
                }
                return out;
            }
        """)

        # Force gold/state pour habiliter le jeu
        await page.evaluate("""
            () => {
                STATE.gold = 100000;
                STATE.stars = 0;
                STATE.totalStarsEarned = 0;
            }
        """)

        # ============ Test spawn à chaque km boss ============
        spawn_results = []
        for km, expected_id in EXPECTED_BOSSES:
            attach_listeners(page, f"spawn_km{km}")
            res = await test_boss_spawn(page, km, expected_id)
            spawn_results.append(res)

        # ============ Test defeatBoss + reward ============
        defeat_result = await test_defeat_boss(page)

        # ============ Test pas de respawn après défaite ============
        no_respawn = await test_defeated_no_respawn(page)

        # ============ Test boundaries (km ±1 et ±2) ============
        boundaries = {}
        for km, expected_id in [(59, 'draftbreaker'), (61, 'draftbreaker'),
                                 (62, None), (58, None)]:  # ±1 OK, ±2 KO pour getBossIdForKm
            # Reset defeated flags
            await page.evaluate("""
                () => {
                    if (STATE.bosses) {
                        for (const id in STATE.bosses) STATE.bosses[id].defeated = false;
                    }
                }
            """)
            r = await page.evaluate(
                f"() => (typeof getBossIdForKm === 'function') ? getBossIdForKm({km}) : null"
            )
            boundaries[f"km_{km}"] = {"expected": expected_id, "got": r, "match": r == expected_id}

        # ============ REPORT ============
        report = {
            "exposed": exposed,
            "boss_km_map": boss_km_map,
            "initial_bosses": initial_bosses,
            "spawn_results": spawn_results,
            "defeat_result": defeat_result,
            "no_respawn_after_defeat": no_respawn,
            "boundaries": boundaries,
            "page_errors_total": len(page_errors),
            "console_errors_total": len(console_errors),
            "page_errors": page_errors,
            "console_errors": console_errors,
            "scenario_errors": {k: v for k, v in scenario_errors.items() if v},
        }

        (OUT / "qa3-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Print synthèse
        print("=" * 70)
        print("QA VAGUE 22 - QA3 BOSS REPORT")
        print("=" * 70)
        print(f"Exposed: {exposed}")
        print(f"BOSS_KM_MAP: {boss_km_map}")
        print(f"Initial bosses keys: {list((initial_bosses or {}).keys())}")
        print(f"Errors  pageerror={len(page_errors)}  console.error={len(console_errors)}")
        print("-" * 70)
        print("--- Spawn par km ---")
        for r in spawn_results:
            checks = [
                "helper" if r["helper_match"] else "X-helper",
                "active" if r["active_match"] else "X-active",
                "npc.bossId" if r["npc_bossId_match"] else "X-npc.bossId",
                "npc.isBoss" if r["npc_isBoss_true"] else "X-npc.isBoss",
                "tier>=6" if r["npc_tier_ge6"] else "X-tier>=6",
            ]
            print(f"  km={r['km']:3d} expected={r['expected_id']:14s} | "
                  f"helper={r['getBossIdForKm']!s:14s} active={r['active_match']!s:5s} "
                  f"npcs={r['npcs_total']} src={r['npcs_src']} | {' '.join(checks)}")
        print("-" * 70)
        print("--- defeatBoss('draftbreaker') ---")
        d = defeat_result
        print(f"  call: {d['call']}")
        print(f"  before: {d['before']}")
        print(f"  after : {d['after']}")
        print(f"  +stars=1 ? {d['stars_plus_1']}")
        print(f"  +gold=10000 ? {d['gold_plus_10000']}")
        print(f"  defeated=true ? {d['defeated_true']}")
        print("-" * 70)
        print("--- Pas de respawn après défaite ---")
        print(f"  km60 après défaite: getBossIdForKm={no_respawn['getBossIdForKm_returned']}  active={no_respawn['getActiveBoss_returned']}")
        print(f"  skip OK: {no_respawn['skip_defeated_ok']}")
        print("-" * 70)
        print("--- Boundaries ---")
        for k, v in boundaries.items():
            print(f"  {k}: expected={v['expected']} got={v['got']} match={v['match']}")
        print("-" * 70)
        if scenario_errors:
            print("--- Scenario errors (truncated) ---")
            for label, errs in scenario_errors.items():
                if errs:
                    print(f"  [{label}] {len(errs)} err(s):")
                    for e in errs[:3]:
                        print(f"     - {e[:180]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
