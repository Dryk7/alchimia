"""FOULEE Visual Snapshots - 10 scenes cles.

Capture des screenshots de scenarios critiques et compare aux baselines.
Si baseline absent : creation. Si present : diff simplifie (taille fichier +/- 15%).

Usage:
    python visual-snapshots.py            # capture + compare
    python visual-snapshots.py --update   # ecrase les baselines

Exit 0 si tout passe, 1 si diff suspect, 2 si erreur.
"""
import asyncio
import io
import os
import sys
import time

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.stderr.write("Playwright non installe. pip install playwright && playwright install chromium\n")
    sys.exit(2)

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

URL = 'http://localhost:8770/'
HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE_DIR = os.path.join(HERE, 'baselines')
CURRENT_DIR = os.path.join(HERE, 'snapshots-current')
UPDATE = '--update' in sys.argv
TOLERANCE = 0.15  # 15% tolerance sur taille fichier

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
DIM = '\033[2m'
RESET = '\033[0m'

os.makedirs(BASELINE_DIR, exist_ok=True)
os.makedirs(CURRENT_DIR, exist_ok=True)


async def setup_page(p):
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(viewport={'width': 412, 'height': 915}, device_scale_factor=2)
    page = await ctx.new_page()
    return browser, page


async def fresh(page):
    await page.goto(URL, wait_until='domcontentloaded')
    await page.evaluate("() => { try{localStorage.clear(); sessionStorage.clear();}catch(e){} }")
    await page.goto(URL, wait_until='networkidle')
    await page.wait_for_function("() => typeof window.STATE === 'object' && window.STATE !== null", timeout=15000)


async def start_game(page):
    try:
        btn = await page.query_selector('#start-btn')
        if btn and await btn.is_visible():
            await btn.click()
            await page.wait_for_timeout(800)
    except Exception:
        pass


async def force_km(page, km, taps=100):
    await page.evaluate(f"""(km, taps) => {{
        if(!window.STATE) return;
        window.STATE.lapsRun = km;
        window.STATE.totalTaps = Math.max(window.STATE.totalTaps || 0, taps);
        if(typeof updateUI === 'function'){{ try{{updateUI();}}catch(e){{}} }}
    }}""", [km, taps])
    await page.wait_for_timeout(500)


# ---------------- SCENES ----------------

async def scene_splash(page):
    await page.goto(URL, wait_until='domcontentloaded')
    await page.evaluate("() => { try{localStorage.clear();}catch(e){} }")
    await page.goto(URL, wait_until='networkidle')
    await page.wait_for_timeout(1500)


async def scene_km0_fresh(page):
    await fresh(page)
    await start_game(page)
    await page.wait_for_timeout(800)


async def scene_km3_autocourse(page):
    await fresh(page)
    await start_game(page)
    await force_km(page, 3, 200)
    await page.wait_for_timeout(800)


async def scene_km30_urban(page):
    await fresh(page)
    await start_game(page)
    await force_km(page, 30, 500)
    await page.wait_for_timeout(800)


async def scene_km70_stade(page):
    await fresh(page)
    await start_game(page)
    await force_km(page, 70, 1000)
    await page.wait_for_timeout(800)


async def scene_km95_sprint_champion(page):
    await fresh(page)
    await start_game(page)
    await force_km(page, 95, 2000)
    await page.evaluate("() => { if(window.STATE){ window.STATE.gold = 1e9; } }")
    await page.wait_for_timeout(900)


async def scene_km100_ascension(page):
    await fresh(page)
    await start_game(page)
    await force_km(page, 100, 3000)
    await page.wait_for_timeout(900)


async def scene_km105_lunar(page):
    await fresh(page)
    await start_game(page)
    await force_km(page, 105, 3500)
    await page.wait_for_timeout(900)


async def scene_daily_reward_modal(page):
    await fresh(page)
    await start_game(page)
    # Tente d'ouvrir le daily reward
    await page.evaluate("""() => {
        if(typeof showDailyReward === 'function'){ try{ showDailyReward(); }catch(e){} }
        else if(typeof openDailyModal === 'function'){ try{ openDailyModal(); }catch(e){} }
    }""")
    await page.wait_for_timeout(600)


async def scene_daily_challenge_modal(page):
    await fresh(page)
    await start_game(page)
    await page.evaluate("""() => {
        if(typeof showDailyChallenge === 'function'){ try{ showDailyChallenge(); }catch(e){} }
        else if(typeof openDailyChallenge === 'function'){ try{ openDailyChallenge(); }catch(e){} }
        else if(typeof getTodayChallenge === 'function'){ try{ getTodayChallenge(); }catch(e){} }
    }""")
    await page.wait_for_timeout(600)


SCENES = [
    ('01_splash', scene_splash),
    ('02_km0_fresh', scene_km0_fresh),
    ('03_km3_autocourse', scene_km3_autocourse),
    ('04_km30_urban', scene_km30_urban),
    ('05_km70_stade', scene_km70_stade),
    ('06_km95_sprint_champion', scene_km95_sprint_champion),
    ('07_km100_ascension', scene_km100_ascension),
    ('08_km105_lunar', scene_km105_lunar),
    ('09_daily_reward_modal', scene_daily_reward_modal),
    ('10_daily_challenge_modal', scene_daily_challenge_modal),
]


def compare(baseline_path, current_path):
    """Compare simplifie : existence + ratio de taille."""
    if not os.path.exists(baseline_path):
        return {'status': 'created', 'detail': 'baseline cree'}
    bs = os.path.getsize(baseline_path)
    cs = os.path.getsize(current_path)
    if bs == 0:
        return {'status': 'created', 'detail': 'baseline vide remplace'}
    ratio = abs(cs - bs) / bs
    if ratio > TOLERANCE:
        return {'status': 'diff', 'detail': f'taille {bs}->{cs} diff {ratio*100:.1f}%'}
    return {'status': 'match', 'detail': f'{cs}B (diff {ratio*100:.1f}%)'}


async def main():
    print(f'\n{YELLOW}FOULEE Visual Snapshots{RESET}  -  {len(SCENES)} scenes  -  {URL}')
    if UPDATE:
        print(f'  {YELLOW}MODE UPDATE : baselines seront ecrasees{RESET}')
    print()
    t0 = time.time()
    diffs = 0
    created = 0
    matched = 0

    async with async_playwright() as p:
        browser, page = await setup_page(p)
        for name, scene_fn in SCENES:
            try:
                await scene_fn(page)
                current_path = os.path.join(CURRENT_DIR, f'{name}.png')
                baseline_path = os.path.join(BASELINE_DIR, f'{name}.png')
                await page.screenshot(path=current_path, full_page=False)

                if UPDATE or not os.path.exists(baseline_path):
                    # Copie vers baseline
                    with open(current_path, 'rb') as src, open(baseline_path, 'wb') as dst:
                        dst.write(src.read())
                    created += 1
                    print(f'  {GREEN}CREATE{RESET}  {name}  ({os.path.getsize(baseline_path)}B)')
                else:
                    r = compare(baseline_path, current_path)
                    if r['status'] == 'match':
                        matched += 1
                        print(f'  {GREEN}MATCH {RESET}  {name}  {DIM}{r["detail"]}{RESET}')
                    elif r['status'] == 'created':
                        created += 1
                        print(f'  {GREEN}CREATE{RESET}  {name}  {DIM}{r["detail"]}{RESET}')
                    else:
                        diffs += 1
                        print(f'  {RED}DIFF  {RESET}  {name}  {RED}{r["detail"]}{RESET}')
            except Exception as e:
                diffs += 1
                print(f'  {RED}ERROR {RESET}  {name}  {RED}{str(e)[:120]}{RESET}')

        await browser.close()
    dt = time.time() - t0
    print()
    print(f'{YELLOW}---{RESET}')
    print(f'  Total : {len(SCENES)}   {GREEN}match {matched}{RESET}   {YELLOW}create {created}{RESET}   {RED}diff {diffs}{RESET}   ({dt:.1f}s)')
    print()
    return 0 if diffs == 0 else 1


if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(130)
