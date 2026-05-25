"""
AUDIT A — Design visuel des boutons upgrade
QA Vague 17 — Read-only

Evalue palette, contraste, icones SVG, hierarchie des .upg-btn
"""
import asyncio
import json
from playwright.async_api import async_playwright

URL = "http://localhost:8770/index.html"
OUT_DIR = r"D:/alchimia/screenshots/qa-vague17"

def luminance(s):
    if s is None:
        return None
    s = str(s).strip()
    r = g = b = 0
    try:
        if s.startswith("#"):
            h = s.lstrip("#")
            if len(h) == 3:
                h = "".join(c*2 for c in h)
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        elif s.startswith("rgb"):
            nums = s[s.find("(")+1:s.find(")")].split(",")
            r = float(nums[0]); g = float(nums[1]); b = float(nums[2])
        else:
            return None
    except Exception:
        return None
    def chan(c):
        c = c / 255.0
        return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055) ** 2.4
    return 0.2126*chan(r) + 0.7152*chan(g) + 0.0722*chan(b)

def contrast_ratio(fg, bg):
    Lf = luminance(fg); Lb = luminance(bg)
    if Lf is None or Lb is None:
        return None
    hi, lo = max(Lf, Lb), min(Lf, Lb)
    return round((hi + 0.05) / (lo + 0.05), 2)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width":540,"height":960})
        page = await ctx.new_page()
        console_msgs = []
        page.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text}"))

        await page.goto(URL, wait_until="networkidle")

        await page.evaluate("""
          () => {
            try {
              localStorage.setItem('foulee_onboarding_done','1');
              localStorage.setItem('foulee_tuto_done','1');
              localStorage.setItem('foulee_intro_seen','1');
              localStorage.setItem('foulee_story_seen','1');
              localStorage.setItem('foulee_daily_seen','1');
            } catch(e){}
          }
        """)
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(800)

        await page.evaluate("""
          () => {
            document.querySelectorAll('.modal, .overlay, [role=dialog]').forEach(el => {
              const closeBtn = el.querySelector('[data-close],.close,.modal-close,.btn-close');
              if (closeBtn) closeBtn.click();
              else el.style.display='none';
            });
          }
        """)

        await page.evaluate("""
          () => {
            if (window.STATE){
              window.STATE.lapsRun = 30;
              window.STATE.gold = 50000;
              if (window.STATE.kmCovered !== undefined) window.STATE.kmCovered = 30;
              if (window.STATE.totalKm !== undefined) window.STATE.totalKm = 30;
            }
          }
        """)

        clicked_start = False
        try:
            btn = await page.query_selector('button:has-text("PRENDRE LE DEPART"), button:has-text("DEPART"), #btn-start, .btn-start')
            if btn:
                await btn.click()
                clicked_start = True
        except Exception as e:
            print("[start click err]", e)
        if not clicked_start:
            try:
                await page.evaluate("""
                  () => {
                    const btns = [...document.querySelectorAll('button')];
                    const cta = btns.find(b => /PRENDRE|DEPART|DEPART|START|GO/i.test(b.textContent||''));
                    if (cta) cta.click();
                  }
                """)
                clicked_start = True
            except Exception:
                pass

        await page.wait_for_timeout(2000)

        await page.evaluate("""
          () => {
            if (window.STATE){
              window.STATE.lapsRun = 30;
              window.STATE.gold = 50000;
              if (window.STATE.kmCovered !== undefined) window.STATE.kmCovered = 30;
              if (window.STATE.totalKm !== undefined) window.STATE.totalKm = 30;
              if (typeof window.renderUpgrades === 'function') window.renderUpgrades();
              if (typeof window.updateUpgradeButtons === 'function') window.updateUpgradeButtons();
              if (typeof window.refreshUpgradeUI === 'function') window.refreshUpgradeUI();
            }
          }
        """)

        opened = await page.evaluate("""
          () => {
            const results = [];
            const triggers = [
              '#drawer-toggle','#btn-drawer','.drawer-toggle','.btn-drawer',
              'button[aria-label*="menu" i]','button[aria-label*="upgrade" i]',
              '#upgrades-tab','.tab-upgrades','#tab-upgrades'
            ];
            for (const sel of triggers){
              const el = document.querySelector(sel);
              if (el){ el.click(); results.push('clicked:'+sel); break; }
            }
            const drawer = document.querySelector('#drawer, .drawer, .upgrades-drawer, .tap-upgrades-v2');
            if (drawer){
              drawer.classList.add('open','active','visible');
              drawer.style.display='';
              results.push('drawer-open');
            }
            const upgTab = document.querySelector('[data-tab="upgrades"], #tab-upgrades, .tab-upgrades');
            if (upgTab) { upgTab.click(); results.push('tab-upgrades'); }
            return results;
          }
        """)
        print("[opened]", opened)

        await page.wait_for_timeout(500)

        await page.evaluate("""
          () => {
            if (typeof window.renderUpgrades === 'function') window.renderUpgrades();
            if (typeof window.updateUpgradeButtons === 'function') window.updateUpgradeButtons();
            if (typeof window.refreshUpgradeUI === 'function') window.refreshUpgradeUI();
            document.querySelectorAll('.upg-btn').forEach(b => {
              b.removeAttribute('data-locked');
              b.classList.remove('locked');
              b.classList.add('affordable');
            });
          }
        """)
        await page.wait_for_timeout(300)

        # Scroll the upgrades container into view + screenshot via element handle
        await page.evaluate("""
          () => {
            const c = document.querySelector('.tap-upgrades-v2, #upgrades-grid, .upgrades-grid');
            if (c) c.scrollIntoView({block:'center', inline:'center'});
          }
        """)
        await page.wait_for_timeout(400)

        box_info = await page.evaluate("""
          () => {
            const c = document.querySelector('.tap-upgrades-v2, #upgrades-grid, .upgrades-grid');
            if (!c) return null;
            const r = c.getBoundingClientRect();
            return { x:r.x, y:r.y, w:r.width, h:r.height, scrollY: window.scrollY };
          }
        """)
        print("[upgrades container box after scroll]", box_info)

        await page.screenshot(path=f"{OUT_DIR}/audit-A-fullpage.png", full_page=True)

        # Element-handle screenshot (independent of viewport position)
        try:
            handle = await page.query_selector('.tap-upgrades-v2, #upgrades-grid, .upgrades-grid')
            if handle:
                await handle.screenshot(path=f"{OUT_DIR}/audit-A-buttons.png")
            else:
                await page.screenshot(path=f"{OUT_DIR}/audit-A-buttons.png", full_page=False)
        except Exception as e:
            print("[element shot err]", e)
            await page.screenshot(path=f"{OUT_DIR}/audit-A-buttons.png", full_page=False)

        btn_data = await page.evaluate("""
          () => {
            const out = [];
            document.querySelectorAll('.upg-btn').forEach(b => {
              const cs = getComputedStyle(b);
              const nameEl = b.querySelector('.upg-name');
              const costEl = b.querySelector('.upg-cost');
              const lvlEl  = b.querySelector('.upg-lvl');
              const barEl  = b.querySelector('.upg-bar-fill');
              const svg    = b.querySelector('svg');
              const wrap   = b.querySelector('.upg-icon-wrap');
              const wrapCs = wrap ? getComputedStyle(wrap) : null;
              const svgCs  = svg ? getComputedStyle(svg) : null;
              out.push({
                upgrade: b.dataset.upgrade,
                cls: b.className,
                visible: cs.display !== 'none' && cs.visibility !== 'hidden',
                bg: cs.backgroundColor,
                bgImage: cs.backgroundImage,
                border: cs.border,
                borderColor: cs.borderColor,
                padding: cs.padding,
                radius: cs.borderRadius,
                width: b.getBoundingClientRect().width,
                height: b.getBoundingClientRect().height,
                name: nameEl ? {
                  text: nameEl.textContent,
                  fontSize: getComputedStyle(nameEl).fontSize,
                  color: getComputedStyle(nameEl).color,
                  weight: getComputedStyle(nameEl).fontWeight
                } : null,
                cost: costEl ? {
                  text: costEl.textContent,
                  fontSize: getComputedStyle(costEl).fontSize,
                  color: getComputedStyle(costEl).color,
                  bg: getComputedStyle(costEl).backgroundColor
                } : null,
                lvl: lvlEl ? {
                  text: lvlEl.textContent,
                  fontSize: getComputedStyle(lvlEl).fontSize,
                  color: getComputedStyle(lvlEl).color,
                  bg: getComputedStyle(lvlEl).backgroundColor
                } : null,
                bar: barEl ? {
                  bg: getComputedStyle(barEl).backgroundColor,
                  bgImage: getComputedStyle(barEl).backgroundImage,
                  widthCss: getComputedStyle(barEl).width,
                  height: getComputedStyle(barEl).height,
                  rect: { w: barEl.getBoundingClientRect().width, h: barEl.getBoundingClientRect().height }
                } : null,
                svg: svg ? {
                  viewBox: svg.getAttribute('viewBox'),
                  pathCount: svg.querySelectorAll('path').length,
                  circleCount: svg.querySelectorAll('circle').length,
                  polyCount: svg.querySelectorAll('polygon,polyline').length,
                  totalShapes: svg.querySelectorAll('*').length,
                  color: svgCs ? svgCs.color : null,
                  fill: svgCs ? svgCs.fill : null,
                  width: svgCs ? svgCs.width : null,
                  outerHTML: svg.outerHTML
                } : null,
                wrap: wrapCs ? {
                  bg: wrapCs.backgroundColor,
                  color: wrapCs.color,
                  width: wrapCs.width,
                  height: wrapCs.height
                } : null
              });
            });
            return out;
          }
        """)

        for d in btn_data:
            try:
                if d.get("name") and d.get("bg"):
                    bg = d["bg"] if d["bg"] != "rgba(0, 0, 0, 0)" else "#fffaee"
                    d["contrast_name_vs_bg"] = contrast_ratio(d["name"]["color"], bg)
                if d.get("cost"):
                    d["contrast_cost_vs_costbg"] = contrast_ratio(d["cost"]["color"], d["cost"]["bg"])
                if d.get("lvl"):
                    d["contrast_lvl_vs_lvlbg"] = contrast_ratio(d["lvl"]["color"], d["lvl"]["bg"])
            except Exception as e:
                d["contrast_err"] = str(e)

        signatures = []
        for d in btn_data:
            if d.get("svg"):
                svg_html = d["svg"]["outerHTML"]
                signatures.append((svg_html[:200], d["svg"]["pathCount"], d["svg"]["circleCount"], d["svg"]["polyCount"]))
            else:
                signatures.append(None)
        distinct = len(set(s for s in signatures if s is not None))

        report = {
            "url": URL,
            "viewport": "540x960",
            "start_clicked": clicked_start,
            "upgrade_count": len(btn_data),
            "distinct_svg_signatures": distinct,
            "buttons": btn_data,
            "console_first_50": console_msgs[:50]
        }

        with open(f"{OUT_DIR}/audit-A-design.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"[done] {len(btn_data)} upgrade buttons analyzed, {distinct} distinct SVG signatures")

        await browser.close()

asyncio.run(main())
