"""
D3-VISUAL : Audit polish visuel global Foulée vs jeux mobile premium.

Capture 8 scènes (splash + 7 biomes/moments) en 540x960 DPR=2,
puis mesure:
  - nombre de couleurs uniques (palette)
  - nombre de fonts CSS
  - nombre de tailles de texte
  - count emoji vs SVG
  - sample homogénéité palette (variance hue)
"""
import asyncio
import os
from collections import Counter
from playwright.async_api import async_playwright

OUT_DIR = "D:/alchimia/screenshots/qa-vague24"
os.makedirs(OUT_DIR, exist_ok=True)

# === 8 scènes à capturer ===
SCENES = [
    {
        'name': 'D3-01-splash',
        'setup': "/* attendre le splash, ne rien faire */",
        'wait': 1500,
        'pre_click_start': False,
    },
    {
        'name': 'D3-02-km1',
        'setup': """
            STATE.lapsRun = 1; STATE.lapProgress = 0.30;
            STATE.gold = 15;
            if(typeof saveNow === 'function') saveNow();
            if(typeof render === 'function') render();
        """,
        'wait': 800,
        'pre_click_start': True,
    },
    {
        'name': 'D3-03-km10',
        'setup': """
            STATE.lapsRun = 10; STATE.lapProgress = 0.50;
            STATE.gold = 500;
            if(typeof saveNow === 'function') saveNow();
            if(typeof render === 'function') render();
        """,
        'wait': 800,
        'pre_click_start': True,
    },
    {
        'name': 'D3-04-km30',
        'setup': """
            STATE.lapsRun = 30; STATE.lapProgress = 0.55;
            STATE.gold = 5000;
            if(typeof saveNow === 'function') saveNow();
            if(typeof render === 'function') render();
        """,
        'wait': 800,
        'pre_click_start': True,
    },
    {
        'name': 'D3-05-km50-stadium',
        'setup': """
            STATE.lapsRun = 50; STATE.lapProgress = 0.55;
            STATE.gold = 15000;
            if(typeof saveNow === 'function') saveNow();
            if(typeof render === 'function') render();
        """,
        'wait': 800,
        'pre_click_start': True,
    },
    {
        'name': 'D3-06-km75',
        'setup': """
            STATE.lapsRun = 75; STATE.lapProgress = 0.50;
            STATE.gold = 40000;
            if(typeof saveNow === 'function') saveNow();
            if(typeof render === 'function') render();
        """,
        'wait': 800,
        'pre_click_start': True,
    },
    {
        'name': 'D3-07-km100-ascension',
        'setup': """
            STATE.lapsRun = 100; STATE.lapProgress = 0.50;
            STATE.gold = 80000;
            if(typeof saveNow === 'function') saveNow();
            if(typeof render === 'function') render();
        """,
        'wait': 1000,
        'pre_click_start': True,
    },
    {
        'name': 'D3-08-km110-lunar',
        'setup': """
            STATE.lapsRun = 110; STATE.lapProgress = 0.40;
            STATE.gold = 120000;
            if(typeof saveNow === 'function') saveNow();
            if(typeof render === 'function') render();
        """,
        'wait': 1000,
        'pre_click_start': True,
    },
]


PALETTE_SAMPLER_JS = r"""
() => {
  // Mesure les couleurs uniques utilisées et tailles texte / fonts présents.
  const out = {
    colors: new Set(),
    bgColors: new Set(),
    borderColors: new Set(),
    fonts: new Set(),
    fontSizes: new Set(),
    emojiCount: 0,
    svgCount: 0,
    imgCount: 0,
    canvasCount: 0,
    visibleTextNodes: 0,
    domNodes: 0,
  };
  const emojiRe = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F000}-\u{1F2FF}]/u;
  const all = document.querySelectorAll('*');
  out.domNodes = all.length;
  all.forEach(el => {
    if(el.offsetParent === null && el.tagName !== 'BODY' && el.tagName !== 'HTML') return; // skip hidden
    const cs = getComputedStyle(el);
    if(cs.color) out.colors.add(cs.color);
    if(cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') out.bgColors.add(cs.backgroundColor);
    if(cs.borderTopColor && cs.borderTopWidth !== '0px') out.borderColors.add(cs.borderTopColor);
    if(cs.fontFamily) out.fonts.add(cs.fontFamily.split(',')[0].replace(/['"]/g,'').trim());
    if(cs.fontSize) out.fontSizes.add(cs.fontSize);
    if(el.tagName === 'SVG' || el.tagName === 'svg') out.svgCount++;
    if(el.tagName === 'IMG') out.imgCount++;
    if(el.tagName === 'CANVAS') out.canvasCount++;
    const txt = el.childNodes;
    for(const n of txt){
      if(n.nodeType === 3 && n.textContent.trim().length){
        out.visibleTextNodes++;
        if(emojiRe.test(n.textContent)) out.emojiCount++;
      }
    }
  });
  return {
    uniqueColors: out.colors.size,
    uniqueBgColors: out.bgColors.size,
    uniqueBorderColors: out.borderColors.size,
    fonts: Array.from(out.fonts),
    fontCount: out.fonts.size,
    fontSizes: Array.from(out.fontSizes).sort(),
    fontSizeCount: out.fontSizes.size,
    emojiNodes: out.emojiCount,
    svgCount: out.svgCount,
    imgCount: out.imgCount,
    canvasCount: out.canvasCount,
    domNodes: out.domNodes,
    sampleColors: Array.from(out.colors).slice(0, 20),
    sampleBgColors: Array.from(out.bgColors).slice(0, 20),
  };
}
"""


PIXEL_SAMPLER_JS = r"""
() => {
  // Sample 200 pixels du canvas principal (si présent) pour mesurer
  // l'homogénéité de la palette (variance HSL).
  const canvases = Array.from(document.querySelectorAll('canvas'));
  if(canvases.length === 0) return { noCanvas: true };
  // prendre le plus grand
  let c = canvases[0]; let area = c.width * c.height;
  for(const k of canvases){
    if(k.width * k.height > area){ c = k; area = k.width * k.height; }
  }
  try {
    const ctx = c.getContext('2d');
    const w = c.width, h = c.height;
    if(w < 4 || h < 4) return { tooSmall: true };
    const N = 400;
    const samples = [];
    for(let i = 0; i < N; i++){
      const x = Math.floor(Math.random() * w);
      const y = Math.floor(Math.random() * h);
      const d = ctx.getImageData(x, y, 1, 1).data;
      // skip pure transparent
      if(d[3] < 32) continue;
      samples.push([d[0], d[1], d[2]]);
    }
    // bucket couleurs (réduit en grille 6 par canal = 216 buckets)
    const buckets = new Map();
    samples.forEach(([r,g,b]) => {
      const key = `${Math.floor(r/43)}-${Math.floor(g/43)}-${Math.floor(b/43)}`;
      buckets.set(key, (buckets.get(key)||0) + 1);
    });
    // top 8
    const top = Array.from(buckets.entries()).sort((a,b)=>b[1]-a[1]).slice(0,8);
    return {
      canvasW: w,
      canvasH: h,
      sampled: samples.length,
      uniqueBuckets: buckets.size,
      dominantBuckets: top.map(([k,v]) => ({ bucket: k, count: v })),
    };
  } catch(e){
    return { error: String(e) };
  }
}
"""


async def main():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={'width': 540, 'height': 960},
            device_scale_factor=2,
        )
        page = await context.new_page()
        await page.goto('http://localhost:8770/')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(1200)

        for scene in SCENES:
            # mark visited tutorial / story so the UI is "clean"
            await page.evaluate("""
                localStorage.setItem('foulee.activeTutoV1','done');
                localStorage.setItem('foulee.storyIntroV1','done');
                localStorage.setItem('foulee.openingShown','1');
            """)

            if scene['pre_click_start']:
                # click PRENDRE LE DEPART if still on intro
                try:
                    has_start = await page.evaluate("!!document.getElementById('start-btn')")
                    if has_start:
                        visible = await page.evaluate("""
                            (() => {
                              const el = document.getElementById('start-btn');
                              if(!el) return false;
                              const r = el.getBoundingClientRect();
                              return r.width > 0 && r.height > 0 && el.offsetParent !== null;
                            })()
                        """)
                        if visible:
                            await page.click('#start-btn', timeout=2000)
                            await page.wait_for_timeout(900)
                except Exception as e:
                    print(f"  warn start-btn: {e}")

                # close any opening cinematic / modals
                try:
                    await page.evaluate("""
                        document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
                        const oc = document.getElementById('opening-cinematic');
                        if(oc) oc.style.display = 'none';
                    """)
                except Exception:
                    pass

            # apply scene setup
            try:
                await page.evaluate(scene['setup'])
            except Exception as e:
                print(f"  warn setup {scene['name']}: {e}")

            # close any modals that re-opened
            try:
                await page.evaluate("""
                    document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
                    document.querySelectorAll('.active-tuto-overlay,.active-tuto-bubble,.active-tuto-arrow').forEach(e=>e.remove());
                """)
            except Exception:
                pass

            await page.wait_for_timeout(scene['wait'])

            # measurements
            metrics = {}
            try:
                metrics = await page.evaluate(PALETTE_SAMPLER_JS)
            except Exception as e:
                metrics = {'error': str(e)}
            pixel_sample = {}
            try:
                pixel_sample = await page.evaluate(PIXEL_SAMPLER_JS)
            except Exception as e:
                pixel_sample = {'error': str(e)}

            shot_path = f"{OUT_DIR}/{scene['name']}.png"
            await page.screenshot(path=shot_path, full_page=False)
            print(f"OK -> {shot_path}")
            print(f"   colors={metrics.get('uniqueColors')} fonts={metrics.get('fonts')} sizes={metrics.get('fontSizeCount')} emoji={metrics.get('emojiNodes')} svg={metrics.get('svgCount')} canvas={metrics.get('canvasCount')}")
            results.append({
                'scene': scene['name'],
                'metrics': metrics,
                'pixel_sample': pixel_sample,
            })

        await browser.close()

    # write a small JSON summary alongside
    import json
    with open(f"{OUT_DIR}/D3-visual-metrics.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nMetrics JSON -> {OUT_DIR}/D3-visual-metrics.json")


asyncio.run(main())
