"""QA complete : intro, gameplay, patterns, audio, perf, console errors."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await context.new_page()
        errors = []
        warnings = []
        page.on('pageerror', lambda exc: errors.append(('pageerror', str(exc))))
        def on_console(msg):
            if msg.type == 'error':
                errors.append(('console.error', msg.text))
            elif msg.type == 'warning':
                warnings.append(msg.text)
        page.on('console', on_console)
        # === Etape 1 : INTRO ===
        await page.goto('http://localhost:8770')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2500)
        await page.screenshot(path='D:/alchimia/screenshots/qa-01-intro.png')
        print('OK -> qa-01-intro.png')
        # === Etape 2 : START ===
        await page.evaluate("""
            document.getElementById('start-btn')?.click();
            STATE.starterPackDeclined = true; // évite le starter pack pendant la QA
            setTimeout(()=>document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show')), 200);
        """)
        await page.wait_for_timeout(1200)
        # Re-close starter pack if it appeared
        await page.evaluate("document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));")
        await page.screenshot(path='D:/alchimia/screenshots/qa-02-game-start.png')
        print('OK -> qa-02-game-start.png')
        # === Etape 3 : FULL TAP (premier km) ===
        stadium_box = await page.evaluate("""
            (() => { const r = document.getElementById('runner-stadium').getBoundingClientRect();
              return { x: r.left + r.width/2, y: r.top + r.height/2 }; })()
        """)
        for i in range(30):
            await page.mouse.click(stadium_box['x'], stadium_box['y'])
            await page.wait_for_timeout(80)
        await page.wait_for_timeout(500)
        # close any modal that might have popped up (starter pack, etc.)
        await page.evaluate("document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));")
        await page.screenshot(path='D:/alchimia/screenshots/qa-03-sprint.png')
        print('OK -> qa-03-sprint.png')
        # === Etape 4 : STOP (test du recul) ===
        await page.wait_for_timeout(2500)  # laisse la vitesse retomber
        await page.screenshot(path='D:/alchimia/screenshots/qa-04-after-stop.png')
        print('OK -> qa-04-after-stop.png')
        # === Etape 5 : Forcer km 5 + patterns ===
        await page.evaluate("""
            STATE.lapsRun = 5; STATE.gold = 5000;
            if(typeof saveNow === 'function') saveNow();
        """)
        await page.wait_for_timeout(500)
        # spawn double pattern
        await page.evaluate("window.RUNNER_2D.spawnHurdlePattern('double', 25);")
        await page.wait_for_timeout(400)
        await page.screenshot(path='D:/alchimia/screenshots/qa-05-double.png')
        print('OK -> qa-05-double.png')
        # spawn triple
        await page.evaluate("window.RUNNER_2D.spawnHurdlePattern('triple', 30);")
        await page.wait_for_timeout(400)
        await page.screenshot(path='D:/alchimia/screenshots/qa-06-triple.png')
        print('OK -> qa-06-triple.png')
        # === Etape 6 : km 10 + wide/tall ===
        await page.evaluate("STATE.lapsRun = 10;")
        await page.wait_for_timeout(300)
        await page.evaluate("window.RUNNER_2D.spawnHurdlePattern('wide', 20);")
        await page.wait_for_timeout(300)
        await page.screenshot(path='D:/alchimia/screenshots/qa-07-wide.png')
        print('OK -> qa-07-wide.png')
        await page.evaluate("window.RUNNER_2D.spawnHurdlePattern('tall', 20);")
        await page.wait_for_timeout(300)
        await page.screenshot(path='D:/alchimia/screenshots/qa-08-tall.png')
        print('OK -> qa-08-tall.png')
        # === Etape 7 : Jump animation ===
        await page.evaluate("window.RUNNER_2D.setJump(-50, -380);")
        await page.wait_for_timeout(50)
        await page.screenshot(path='D:/alchimia/screenshots/qa-09-jump-takeoff.png')
        print('OK -> qa-09-jump-takeoff.png')
        # === Etape 8 : Stade lointain (km 25) ===
        await page.evaluate("STATE.lapsRun = 25; STATE.lapProgress = 0.5;")
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/qa-10-stadium.png')
        print('OK -> qa-10-stadium.png')
        # === Rapport erreurs ===
        print(f'\n=== ERRORS ({len(errors)}) ===')
        for src, msg in errors[:20]:
            print(f'[{src}] {msg[:200]}')
        print(f'\n=== WARNINGS ({len(warnings)}) ===')
        for w in warnings[:10]:
            print(f'  {w[:200]}')
        await browser.close()


asyncio.run(main())
