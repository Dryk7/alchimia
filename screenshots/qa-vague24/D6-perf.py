"""
D6-perf : Audit READ-ONLY performance mobile Foulée
Mesure FPS, mémoire, DOM, jank aux paliers critiques km 1/30/75/99/100/105/200
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PALIERS = [1, 30, 75, 99, 100, 105, 200]

# Script JS injecté pour mesurer FPS sur 5s
FPS_PROBE = r"""
async (durMs) => {
  return await new Promise(resolve => {
    const frames = [];
    let start = performance.now();
    let last = start;
    let count = 0;
    function tick(now) {
      frames.push(now - last);
      last = now;
      count++;
      if (now - start < durMs) requestAnimationFrame(tick);
      else {
        // stats
        const total = now - start;
        const fpsAvg = (count / (total / 1000));
        const sorted = [...frames].sort((a,b)=>a-b);
        const p50 = sorted[Math.floor(sorted.length*0.5)] || 0;
        const p95 = sorted[Math.floor(sorted.length*0.95)] || 0;
        const p99 = sorted[Math.floor(sorted.length*0.99)] || 0;
        const maxF = sorted[sorted.length-1] || 0;
        const minF = sorted[0] || 0;
        const fpsMin = 1000 / maxF;
        const fpsMax = 1000 / Math.max(minF, 0.01);
        const longFrames = frames.filter(f => f > 33).length; // >33ms = <30fps
        const jankFrames = frames.filter(f => f > 50).length;
        resolve({
          fpsAvg: +fpsAvg.toFixed(1),
          fpsMin: +fpsMin.toFixed(1),
          fpsMax: +fpsMax.toFixed(1),
          frameMs_p50: +p50.toFixed(2),
          frameMs_p95: +p95.toFixed(2),
          frameMs_p99: +p99.toFixed(2),
          frameMs_max: +maxF.toFixed(2),
          longFrames,
          jankFrames,
          totalFrames: count,
          durMs: +total.toFixed(0),
        });
      }
    }
    requestAnimationFrame(tick);
  });
}
"""

SNAPSHOT_PROBE = r"""
() => {
  const out = {};
  out.dom = document.querySelectorAll('*').length;
  out.kmh = (typeof window.STATE !== 'undefined') ? (STATE.displayKmh ?? STATE.kmh ?? null) : null;
  out.lapsRun = (typeof window.STATE !== 'undefined') ? (STATE.lapsRun ?? null) : null;
  out.particles = (window.STATE && Array.isArray(STATE.particles)) ? STATE.particles.length : null;
  try {
    if (performance.memory) {
      out.heapUsedMB = +(performance.memory.usedJSHeapSize / 1048576).toFixed(2);
      out.heapTotalMB = +(performance.memory.totalJSHeapSize / 1048576).toFixed(2);
      out.heapLimitMB = +(performance.memory.jsHeapSizeLimit / 1048576).toFixed(2);
    }
  } catch (e) {}
  const c = document.querySelector('canvas');
  if (c) {
    out.canvasW = c.width;
    out.canvasH = c.height;
    out.canvasCSSW = c.clientWidth;
    out.canvasCSSH = c.clientHeight;
    out.canvasCount = document.querySelectorAll('canvas').length;
  }
  out.dpr = window.devicePixelRatio || 1;
  out.viewportW = window.innerWidth;
  out.viewportH = window.innerHeight;
  out.eventListenersTouches = !!document.documentElement.ontouchstart;
  // Compteur images
  out.images = document.querySelectorAll('img').length;
  out.svgs = document.querySelectorAll('svg').length;
  return out;
}
"""

async def skip_onboarding(page):
    """Force-skip onboarding + tuto + modals via STATE."""
    await page.evaluate(r"""
    () => {
      try {
        if (window.STATE) {
          STATE.onboardingDone = true;
          STATE.tutoStep = 999;
          STATE.hasSeenIntro = true;
          STATE.story = STATE.story || {};
          STATE.story.intro_done = true;
          if (STATE.hints) STATE.hints = {};
        }
        // Close any modal
        document.querySelectorAll('.modal, .modal-overlay, [class*="modal"]').forEach(m => {
          if (m && m.style) m.style.display = 'none';
        });
        // dispatch keydown Escape
        document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));
      } catch (e) { return 'err:' + e.message; }
      return 'ok';
    }
    """)

async def force_lapsRun(page, value):
    """Force STATE.lapsRun à la valeur cible."""
    return await page.evaluate(f"""
    () => {{
      try {{
        if (!window.STATE) return 'no-STATE';
        STATE.lapsRun = {value};
        STATE.lapProgress = 0.5;
        // Si bonus chapitre 2 (>100), assure que lunarUnlocked
        if ({value} >= 100) {{
          STATE.lunarUnlocked = true;
          STATE.chapter2Unlocked = true;
        }}
        return 'ok-' + STATE.lapsRun;
      }} catch (e) {{ return 'err:' + e.message; }}
    }}
    """)

async def tap_burst(page, n=10, delay_ms=30):
    """Simule un burst de N taps rapides."""
    canvas = await page.query_selector('canvas')
    if not canvas:
        return None
    box = await canvas.bounding_box()
    if not box:
        return None
    cx = box['x'] + box['width']/2
    cy = box['y'] + box['height']/2
    # Mesure FPS pendant le burst
    fps_task = asyncio.create_task(page.evaluate(FPS_PROBE, 1500))
    for i in range(n):
        await page.mouse.click(cx, cy, delay=5)
        await asyncio.sleep(delay_ms/1000)
    fps_during = await fps_task
    return fps_during

async def measure_modal_latency(page):
    """Mesure latence ouverture modal (cherche un bouton menu)."""
    selectors = [
        'button[data-modal]',
        '[onclick*="openModal"]',
        '.menu-btn',
        '#menuBtn',
        'button:has-text("MENU")',
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                t0 = await page.evaluate("() => performance.now()")
                await el.click(timeout=500)
                # Wait visible
                await asyncio.sleep(0.05)
                t1 = await page.evaluate("() => performance.now()")
                return {'selector': sel, 'latencyMs': +(t1 - t0)}
        except Exception:
            continue
    return None

async def main():
    results = {
        'url': URL,
        'paliers': {},
        'tap_burst': None,
        'modal_latency': None,
        'baseline': None,
        'after_5min_idle': None,
    }
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--js-flags=--expose-gc'],
        )
        context = await browser.new_context(
            viewport={'width': 540, 'height': 960},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            user_agent='Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
        )
        page = await context.new_page()

        # Capture console errors
        console_errors = []
        page.on('pageerror', lambda e: console_errors.append(str(e)))
        page.on('console', lambda m: console_errors.append(f"[{m.type}] {m.text}") if m.type == 'error' else None)

        await page.goto(URL, wait_until='networkidle', timeout=20000)
        await asyncio.sleep(1.5)
        await skip_onboarding(page)
        await asyncio.sleep(0.5)

        # Baseline snapshot avant jeu
        results['baseline'] = await page.evaluate(SNAPSHOT_PROBE)

        # Mesure pour chaque palier
        for km in PALIERS:
            entry = {'km': km}
            res = await force_lapsRun(page, km)
            entry['forced'] = res
            await asyncio.sleep(0.8)  # stabilise
            entry['snapshot'] = await page.evaluate(SNAPSHOT_PROBE)
            entry['fps'] = await page.evaluate(FPS_PROBE, 5000)
            results['paliers'][str(km)] = entry
            print(f"  km {km}: fps_avg={entry['fps']['fpsAvg']} fps_min={entry['fps']['fpsMin']} "
                  f"long={entry['fps']['longFrames']} dom={entry['snapshot']['dom']} "
                  f"heap={entry['snapshot'].get('heapUsedMB','?')}MB "
                  f"particles={entry['snapshot'].get('particles','?')}")

        # Tap burst au km 30 (mid-game)
        await force_lapsRun(page, 30)
        await asyncio.sleep(0.5)
        results['tap_burst'] = await tap_burst(page, 10, 30)

        # Modal latency
        results['modal_latency'] = await measure_modal_latency(page)

        # Idle 30s pour détecter leaks/accumulation
        await page.evaluate("() => { if(window.STATE) STATE.lapsRun = 50; }")
        snap_before_idle = await page.evaluate(SNAPSHOT_PROBE)
        await asyncio.sleep(30)
        snap_after_idle = await page.evaluate(SNAPSHOT_PROBE)
        results['idle_30s'] = {
            'before': snap_before_idle,
            'after': snap_after_idle,
            'dom_delta': snap_after_idle['dom'] - snap_before_idle['dom'],
            'heap_delta_MB': (snap_after_idle.get('heapUsedMB',0) - snap_before_idle.get('heapUsedMB',0)),
        }

        results['console_errors'] = console_errors[:30]
        await browser.close()

    # Sauvegarde
    out_path = os.path.join(OUT_DIR, 'D6-perf-results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSAVED: {out_path}")
    print(f"Baseline DOM: {results['baseline']['dom']}, DPR: {results['baseline']['dpr']}, "
          f"Canvas: {results['baseline'].get('canvasW','?')}x{results['baseline'].get('canvasH','?')}")
    if results['tap_burst']:
        print(f"Tap burst FPS avg: {results['tap_burst']['fpsAvg']}, min: {results['tap_burst']['fpsMin']}")
    print(f"Modal latency: {results['modal_latency']}")
    print(f"Idle 30s: DOM delta = {results['idle_30s']['dom_delta']}, heap delta = {results['idle_30s']['heap_delta_MB']:.2f}MB")
    if console_errors:
        print(f"Console errors ({len(console_errors)}):", console_errors[:5])

if __name__ == '__main__':
    asyncio.run(main())
