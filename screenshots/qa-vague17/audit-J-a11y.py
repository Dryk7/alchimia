"""
AUDIT J - Accessibilite a11y des upgrades
- aria-label
- focus / tabIndex
- contrast ratio WCAG AA
- outline :focus
- <html lang>
"""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

OUT = Path(r"D:/alchimia/screenshots/qa-vague17")
URL = "http://localhost:8770/index.html"


async def kill_intro(page):
    await page.evaluate("""() => {
      ['intro', 'opening-cinematic', 'splash', 'story-overlay'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
      });
      document.querySelectorAll('.intro, .opening-cinematic, .splash, .story-overlay, #intro-canvas').forEach(el => {
        el.style.display = 'none';
        el.style.opacity = '0';
        el.style.pointerEvents = 'none';
      });
      document.querySelectorAll('.popup-bus, .runner-bubble, .notification, .new-feature-toast').forEach(el => {
        el.style.display = 'none';
      });
      try {
        localStorage.setItem('alchimia_onboarded', '1');
        localStorage.setItem('alchimia_story_seen', '1');
        localStorage.setItem('alchimia_tuto_done', '1');
      } catch(e){}
    }""")


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)

        try:
            await page.click("button:has-text('PRENDRE LE DÉPART')", timeout=2500)
        except Exception:
            pass
        await page.wait_for_timeout(800)
        await kill_intro(page)
        await page.wait_for_timeout(400)

        # Force STATE + drawer + upgrades active
        await page.evaluate("""() => {
          if (typeof STATE !== 'undefined') {
            STATE.lapsRun = 30;
            STATE.gold = 100000;
            STATE.med = 100000;
          }
          const tc = document.querySelector('.tabs-content');
          if (tc) tc.classList.add('open');
          document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === 'upgrades'));
          document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.dataset.pane === 'upgrades'));
          try { if (typeof renderUpgrades === 'function') renderUpgrades(); if (typeof updateUI === 'function') updateUI(); } catch(e){}
        }""")
        await page.wait_for_timeout(700)
        await kill_intro(page)

        # ============================================================
        # Collecte des donnees a11y
        # ============================================================
        results = await page.evaluate("""() => {
          // Helper: WCAG luminance + contrast ratio
          function parseColor(str) {
            if (!str) return null;
            const m = str.match(/rgba?\\(([^)]+)\\)/);
            if (!m) return null;
            const parts = m[1].split(',').map(s => parseFloat(s.trim()));
            return { r: parts[0], g: parts[1], b: parts[2], a: parts[3] !== undefined ? parts[3] : 1 };
          }
          function relLum(c) {
            const conv = v => {
              v = v / 255;
              return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
            };
            return 0.2126 * conv(c.r) + 0.7152 * conv(c.g) + 0.0722 * conv(c.b);
          }
          function contrastRatio(c1, c2) {
            if (!c1 || !c2) return null;
            const L1 = relLum(c1);
            const L2 = relLum(c2);
            const hi = Math.max(L1, L2);
            const lo = Math.min(L1, L2);
            return (hi + 0.05) / (lo + 0.05);
          }

          // Trouve la vraie couleur de fond (remonte parents si transparent)
          function effectiveBg(el) {
            let node = el;
            while (node && node !== document.body) {
              const cs = getComputedStyle(node);
              const c = parseColor(cs.backgroundColor);
              if (c && c.a > 0) return c;
              node = node.parentElement;
            }
            const cs = getComputedStyle(document.body);
            return parseColor(cs.backgroundColor) || { r: 255, g: 255, b: 255, a: 1 };
          }

          const out = {
            htmlLang: document.documentElement.getAttribute('lang') || null,
            htmlLangPresent: !!document.documentElement.getAttribute('lang'),
            buttons: [],
            summary: {}
          };

          const btns = Array.from(document.querySelectorAll('.upg-btn'));
          out.summary.totalButtons = btns.length;

          let withAria = 0, focusable = 0, contrastPass = 0, contrastFail = 0, contrastSamples = [];

          btns.forEach((b, i) => {
            const aria = b.getAttribute('aria-label');
            const ariaLabelledBy = b.getAttribute('aria-labelledby');
            const ariaDescribedBy = b.getAttribute('aria-describedby');
            const role = b.getAttribute('role');
            const txt = (b.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 80);
            const ti = b.tabIndex;
            const cs = getComputedStyle(b);
            const fg = parseColor(cs.color);
            const bg = effectiveBg(b);
            const ratio = contrastRatio(fg, bg);
            const focusOutlineWidth = cs.outlineWidth;
            const focusOutlineStyle = cs.outlineStyle;
            const focusOutlineColor = cs.outlineColor;

            const info = {
              idx: i,
              text: txt,
              tag: b.tagName,
              ariaLabel: aria,
              ariaLabelledBy: ariaLabelledBy,
              ariaDescribedBy: ariaDescribedBy,
              role: role,
              tabIndex: ti,
              focusable: ti >= 0 || b.tagName === 'BUTTON' || b.tagName === 'A',
              color: cs.color,
              backgroundColor: cs.backgroundColor,
              effectiveBg: bg ? `rgb(${Math.round(bg.r)},${Math.round(bg.g)},${Math.round(bg.b)})` : null,
              contrastRatio: ratio ? +ratio.toFixed(2) : null,
              wcagAA: ratio ? ratio >= 4.5 : null,
              wcagAALarge: ratio ? ratio >= 3 : null,
              outlineWidth: focusOutlineWidth,
              outlineStyle: focusOutlineStyle,
              outlineColor: focusOutlineColor,
              disabled: b.disabled || b.classList.contains('locked') || b.classList.contains('disabled'),
              classList: b.className
            };

            if (aria || ariaLabelledBy) withAria++;
            if (info.focusable && !info.disabled) focusable++;
            if (ratio != null) {
              if (ratio >= 4.5) contrastPass++; else contrastFail++;
              contrastSamples.push(ratio);
            }
            out.buttons.push(info);
          });

          out.summary.withAriaLabel = withAria;
          out.summary.focusable = focusable;
          out.summary.contrastPass = contrastPass;
          out.summary.contrastFail = contrastFail;
          out.summary.avgContrast = contrastSamples.length
            ? +(contrastSamples.reduce((a, b) => a + b, 0) / contrastSamples.length).toFixed(2)
            : null;
          out.summary.minContrast = contrastSamples.length ? +Math.min(...contrastSamples).toFixed(2) : null;
          out.summary.maxContrast = contrastSamples.length ? +Math.max(...contrastSamples).toFixed(2) : null;

          // CSS rules for :focus
          let focusRules = [];
          try {
            for (const sheet of document.styleSheets) {
              try {
                const rules = sheet.cssRules || sheet.rules || [];
                for (const r of rules) {
                  if (r.selectorText && /:focus/.test(r.selectorText)) {
                    focusRules.push({
                      sel: r.selectorText,
                      style: r.style ? r.style.cssText.slice(0, 200) : ''
                    });
                  }
                }
              } catch(e) { /* CORS */ }
            }
          } catch(e) {}
          out.focusRules = focusRules.slice(0, 30);
          out.summary.focusRuleCount = focusRules.length;

          return out;
        }""")

        # ============================================================
        # Test Tab navigation - quels elements recoivent focus ?
        # ============================================================
        tab_focus = []
        # Reset focus to body first
        await page.evaluate("() => document.body.focus()")
        for i in range(10):
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(60)
            info = await page.evaluate("""() => {
              const a = document.activeElement;
              if (!a) return null;
              const cs = getComputedStyle(a);
              return {
                tag: a.tagName,
                cls: (a.className || '').toString().slice(0, 80),
                id: a.id || null,
                text: (a.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 60),
                ariaLabel: a.getAttribute('aria-label'),
                outline: cs.outline,
                outlineWidth: cs.outlineWidth,
                outlineColor: cs.outlineColor,
                boxShadow: cs.boxShadow.slice(0, 80)
              };
            }""")
            tab_focus.append({"step": i + 1, "el": info})

        results["tabNavigation"] = tab_focus

        # ============================================================
        # Screenshot avec un upgrade focused
        # ============================================================
        await page.evaluate("""() => {
          const btn = document.querySelector('.upg-btn:not(.locked):not([disabled])') || document.querySelector('.upg-btn');
          if (btn) {
            btn.focus();
            btn.scrollIntoView({block: 'center'});
          }
        }""")
        await page.wait_for_timeout(400)
        await kill_intro(page)
        await page.screenshot(path=str(OUT / "audit-J-focus.png"), full_page=False)

        # Aussi screenshot complet de la zone upgrades pour contexte
        await page.screenshot(path=str(OUT / "audit-J-context.png"), full_page=False)

        # ============================================================
        # Dump JSON
        # ============================================================
        out_path = OUT / "audit-J-a11y.json"
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        # ============================================================
        # Console summary
        # ============================================================
        s = results["summary"]
        print("=" * 60)
        print("AUDIT J - A11Y UPGRADES")
        print("=" * 60)
        print(f"html lang: {results['htmlLang']!r}  (present={results['htmlLangPresent']})")
        print(f"Total .upg-btn: {s['totalButtons']}")
        print(f"  avec aria-label: {s['withAriaLabel']}/{s['totalButtons']}")
        print(f"  focusables (tabIndex>=0 ou button/a, non disabled): {s['focusable']}/{s['totalButtons']}")
        print(f"  contrast >=4.5:1 (AA): {s['contrastPass']}/{s['contrastPass']+s['contrastFail']}")
        print(f"  contrast avg/min/max: {s['avgContrast']} / {s['minContrast']} / {s['maxContrast']}")
        print(f"  CSS :focus rules: {s['focusRuleCount']}")
        print()
        print("--- Sample buttons (5 premiers) ---")
        for b in results["buttons"][:5]:
            print(f"[{b['idx']}] {b['tag']} text={b['text'][:40]!r}")
            print(f"     aria-label={b['ariaLabel']!r}  tabIdx={b['tabIndex']}  focusable={b['focusable']}")
            print(f"     fg={b['color']}  bg={b['effectiveBg']}  ratio={b['contrastRatio']} AA={b['wcagAA']}")
            print(f"     outline: {b['outlineStyle']} {b['outlineWidth']} {b['outlineColor']}")
        print()
        print("--- Tab navigation (10 Tab) ---")
        for t in tab_focus:
            el = t['el']
            if el:
                print(f"Tab #{t['step']:2}: {el['tag']:8} cls={el['cls'][:35]!r} aria={el['ariaLabel']!r} outline={el['outline'][:40]!r}")
            else:
                print(f"Tab #{t['step']:2}: <none>")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
