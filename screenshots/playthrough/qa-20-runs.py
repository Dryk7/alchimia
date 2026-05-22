"""QA : lance 20 sessions distinctes avec différents états + remonte tous les bugs."""
import asyncio, sys, io, json
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REPORT = []
def log(msg):
    print(msg)
    REPORT.append(msg)

SCENARIOS = [
    # (id, label, state_setup, action)
    ('R01', 'Premier launch (fresh)', None, None),
    ('R02', 'km 1 chantier', 'STATE.lapsRun=1; STATE.gold=200', None),
    ('R03', 'km 3 route campagne', 'STATE.lapsRun=3; STATE.gold=500', None),
    ('R04', 'km 10 banlieue', 'STATE.lapsRun=10; STATE.gold=2000', None),
    ('R05', 'km 22 petite ville', 'STATE.lapsRun=22; STATE.gold=10000', None),
    ('R06', 'km 38 urbain', 'STATE.lapsRun=38; STATE.gold=50000; STATE.alchLevel=8', None),
    ('R07', 'km 55 approche stade', 'STATE.lapsRun=55; STATE.gold=200000; STATE.alchLevel=12', None),
    ('R08', 'km 65 banderoles', 'STATE.lapsRun=65; STATE.gold=500000; STATE.alchLevel=15', None),
    ('R09', 'km 70 STADE EN VUE', 'STATE.lapsRun=70; STATE.gold=1000000; STATE.alchLevel=18', None),
    ('R10', 'km 74 tribune remplit', 'STATE.lapsRun=74; STATE.gold=2000000; STATE.alchLevel=20', None),
    ('R11', 'km 80 vasque allumée', 'STATE.lapsRun=80; STATE.gold=5000000; STATE.alchLevel=25; STATE.gems=100', None),
    ('R12', 'km 85 helicoptère', 'STATE.lapsRun=85; STATE.gold=10000000; STATE.alchLevel=28; STATE.gems=150', None),
    ('R13', 'km 90 tribune monumentale', 'STATE.lapsRun=90; STATE.gold=20000000; STATE.alchLevel=32; STATE.gems=200', None),
    ('R14', 'km 94 drone média', 'STATE.lapsRun=94; STATE.gold=40000000; STATE.alchLevel=35; STATE.gems=250', None),
    ('R15', 'km 97 tribune ultime', 'STATE.lapsRun=97; STATE.gold=60000000; STATE.alchLevel=38; STATE.gems=280', None),
    ('R16', 'km 100 ascension', 'STATE.lapsRun=100; STATE.gold=100000000; STATE.alchLevel=40; STATE.gems=300; STATE.stars=10', None),
    ('R17', 'chapitre 2 lunaire', 'STATE.lapsRun=105; STATE.gold=500000000; STATE.alchLevel=50; STATE.gems=500; STATE.stars=25; STATE.chapter=2', None),
    ('R18', 'saison 3 endgame', 'STATE.lapsRun=60; STATE.gold=10000000; STATE.saison=3; STATE.stars=40; STATE.alchLevel=60; STATE.gems=400', None),
    ('R19', 'stamina basse km 20', 'STATE.lapsRun=20; STATE.runnerStamina=0.3; STATE.gold=8000', None),
    ('R20', 'tap interactif rapide', 'STATE.lapsRun=2; STATE.gold=500', 'tap_burst_50'),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)

        errors_global = []
        warnings_global = []
        issues = []  # détails par scénario

        for sid, label, state_setup, action in SCENARIOS:
            page = await ctx.new_page()
            scenario_errors = []
            scenario_warnings = []
            page.on('pageerror', lambda e, sid=sid: (scenario_errors.append(str(e)), errors_global.append(f'[{sid}] {e}')))
            page.on('console', lambda m, sid=sid: (
                scenario_warnings.append(f'{m.type}:{m.text}'),
                warnings_global.append(f'[{sid}] {m.type}: {m.text}')
            ) if m.type in ('warning','error') else None)
            try:
                await page.goto('http://localhost:8770', wait_until='domcontentloaded')
                await page.evaluate('localStorage.setItem("foulee.storySeen","1"); localStorage.setItem("foulee.tutoV3","done"); localStorage.setItem("foulee.activeTutoV1","done");')
                await page.reload()
                await page.wait_for_load_state('networkidle')
                await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
                await page.wait_for_timeout(1500)
                # Apply state setup
                if state_setup:
                    await page.evaluate(f'if(window.STATE){{ {state_setup}; }} _stageCache = {{ km: -1, result: null }};')
                # Action
                if action == 'tap_burst_50':
                    for _ in range(50):
                        await page.evaluate('window.dispatchEvent(new Event("pointerdown")); if(typeof handleTap === "function") handleTap();')
                        await page.wait_for_timeout(30)
                # Close any open modals to focus on game
                await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
                await page.wait_for_timeout(400)
                # Screenshot
                await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/QA20-{sid}.png')

                # DOM checks
                checks = await page.evaluate('''(()=>{
                    const out = {};
                    // 1. Overflow horizontal hors viewport ?
                    const docW = document.documentElement.clientWidth;
                    const overflows = [];
                    document.querySelectorAll('header *, .runner-hud, #runner-stadium > *').forEach(el => {
                        if(!el.offsetParent) return;
                        const r = el.getBoundingClientRect();
                        if(r.right > docW + 4 && r.width > 5){
                            overflows.push({el: el.tagName + (el.id ? '#'+el.id : ''), right: Math.round(r.right)});
                        }
                    });
                    out.overflows = overflows.slice(0, 5);
                    // 2. Texte vide ou "undefined" / "NaN" visible
                    const bad = [];
                    document.querySelectorAll('*').forEach(el => {
                        if(el.children.length === 0 && el.textContent){
                            const t = el.textContent.trim();
                            if(/\\bundefined\\b/.test(t) || /\\bNaN\\b/.test(t) || /\\bnull\\b/.test(t)){
                                bad.push({el: el.tagName + (el.id ? '#'+el.id : ''), text: t.slice(0, 60)});
                            }
                        }
                    });
                    out.bad_text = bad.slice(0, 5);
                    // 3. Position héros / km counter
                    const km = (window.STATE && window.STATE.lapsRun) || 0;
                    const taps = (window.STATE && window.STATE.totalTaps) || 0;
                    const lvl = (window.STATE && window.STATE.alchLevel) || 1;
                    const xp = (window.STATE && window.STATE.alchXp) || 0;
                    out.state = { km, taps, lvl, xp };
                    // 4. Modals ouverts (devrait être 0)
                    out.open_modals = [...document.querySelectorAll('.modal.show')].map(m => m.id);
                    return out;
                })()''')

                # Anomaly detection
                anomalies = []
                if checks['overflows']:
                    anomalies.append(f'overflow: {checks["overflows"]}')
                if checks['bad_text']:
                    anomalies.append(f'bad_text: {checks["bad_text"]}')
                if scenario_errors:
                    anomalies.append(f'errors: {len(scenario_errors)}')
                if checks['open_modals']:
                    anomalies.append(f'still_open: {checks["open_modals"]}')
                if checks['state']['xp'] < 0:
                    anomalies.append(f'xp_negatif: {checks["state"]["xp"]}')
                if anomalies:
                    issues.append((sid, label, anomalies))
                    log(f'[{sid}] {label} -> ANOMALIES: {" | ".join(anomalies)}')
                else:
                    log(f'[{sid}] {label} -> OK')
            except Exception as e:
                log(f'[{sid}] {label} -> CRASH: {str(e)[:200]}')
                issues.append((sid, label, [f'crash: {str(e)[:80]}']))
            finally:
                await page.close()

        log('')
        log(f'===== RÉCAP =====')
        log(f'Total parties : {len(SCENARIOS)}')
        log(f'Avec anomalies : {len(issues)}')
        log(f'Erreurs console globales : {len(errors_global)}')
        log(f'Warnings globaux : {len(warnings_global)}')
        log('')
        log('=== DÉTAIL ANOMALIES ===')
        for sid, label, anos in issues:
            log(f'  [{sid}] {label}')
            for a in anos:
                log(f'    - {a}')
        log('')
        log('=== ERREURS GLOBALES (10 premières) ===')
        for e in errors_global[:10]: log(f'  - {e[:250]}')
        log('=== WARNINGS UNIQUES ===')
        seen = set()
        for w in warnings_global:
            sig = w.split(':',2)[-1][:120]
            if sig in seen: continue
            seen.add(sig)
            log(f'  - {w[:250]}')
            if len(seen) >= 15: break

        with open('D:/alchimia/screenshots/playthrough/qa-20-report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(REPORT))

        await browser.close()

asyncio.run(main())
