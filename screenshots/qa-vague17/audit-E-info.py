"""
AUDIT E - Lisibilité des infos critiques sur boutons upgrade.
Mesure font-size, contraste, présence indicateurs affordable/unaffordable.
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


async def open_drawer_upgrades(page):
    await page.evaluate("""() => {
      const tc = document.querySelector('.tabs-content');
      if (tc) tc.classList.add('open');
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === 'upgrades'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.dataset.pane === 'upgrades'));
      try {
        if (typeof renderUpgrades === 'function') renderUpgrades();
        if (typeof updateUI === 'function') updateUI();
      } catch(e){}
    }""")


async def set_state(page, gold, lapsRun=30, tapValue=5, lapBonus=12):
    await page.evaluate(f"""() => {{
      if (typeof STATE !== 'undefined') {{
        STATE.lapsRun = {lapsRun};
        STATE.gold = {gold};
        STATE.upgradeTapValue = {tapValue};
        STATE.upgradeLapBonus = {lapBonus};
      }}
      try {{
        if (typeof renderUpgrades === 'function') renderUpgrades();
        if (typeof updateUI === 'function') updateUI();
      }} catch(e){{}}
    }}""")


async def measure_upgrades(page):
    """Inspecte chaque card upgrade visible et mesure les infos critiques."""
    return await page.evaluate("""() => {
      // Strict: les vrais boutons upgrade
      const containers = Array.from(document.querySelectorAll('button.upg-btn'));

      const getFs = (el, sel) => {
        if (!el) return null;
        const found = el.querySelector(sel);
        if (!found) return null;
        const cs = getComputedStyle(found);
        const rect = found.getBoundingClientRect();
        return {
          fontSize: cs.fontSize,
          color: cs.color,
          fontWeight: cs.fontWeight,
          background: cs.backgroundColor,
          text: (found.innerText || found.textContent || '').trim().slice(0, 80),
          opacity: cs.opacity,
          width: Math.round(rect.width),
          overflow: cs.overflow,
          textOverflow: cs.textOverflow,
          truncated: found.scrollWidth > rect.width + 1
        };
      };

      const out = containers.slice(0, 14).map((c, i) => {
        const cs = getComputedStyle(c);
        const rect = c.getBoundingClientRect();
        const classes = c.className || '';
        const isAffordable = classes.includes('affordable');
        const isLocked = classes.includes('locked');
        const opacity = parseFloat(cs.opacity);
        const visible = rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < 960;
        // Find progress bar
        const barFill = c.querySelector('.upg-bar-fill');
        const bar = c.querySelector('.upg-bar');
        const barW = barFill ? getComputedStyle(barFill).width : null;
        const barParent = bar ? getComputedStyle(bar) : null;
        return {
          idx: i,
          tag: c.tagName.toLowerCase(),
          classes: classes,
          dataUpgrade: c.dataset.upgrade,
          dataUnlockKm: c.dataset.unlockKm,
          opacity: opacity,
          filter: cs.filter,
          affordable: isAffordable,
          locked: isLocked,
          visible: visible,
          background: cs.background.slice(0, 200),
          borderColor: cs.borderColor,
          rect: { w: Math.round(rect.width), h: Math.round(rect.height), x: Math.round(rect.x), y: Math.round(rect.y) },
          name: getFs(c, '.upg-name'),
          cost: getFs(c, '.upg-cost'),
          lvl: getFs(c, '.upg-lvl'),
          desc: getFs(c, '.upg-desc'),
          hasProgressBar: !!bar,
          progressBarWidth: barW,
          progressBarHeight: barParent ? barParent.height : null,
          progressBarBg: barParent ? barParent.backgroundColor : null,
          fullText: (c.innerText || '').trim().slice(0, 200)
        };
      });

      // STATE info
      const stateInfo = (typeof STATE !== 'undefined') ? {
        gold: STATE.gold,
        med: STATE.med,
        lapsRun: STATE.lapsRun,
        upgradeTapValue: STATE.upgradeTapValue,
        upgradeLapBonus: STATE.upgradeLapBonus
      } : null;

      return { state: stateInfo, count: out.length, cards: out };
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

        results = {}

        # === MID LEVELS (gold = 1000) ===
        await set_state(page, gold=1000)
        await open_drawer_upgrades(page)
        await page.wait_for_timeout(500)
        await kill_intro(page)
        await page.screenshot(path=str(OUT / "audit-E-mid-levels.png"), full_page=False)
        results["mid"] = await measure_upgrades(page)

        # === RICH (gold = 999,999,999) ===
        await set_state(page, gold=999999999)
        await open_drawer_upgrades(page)
        await page.wait_for_timeout(400)
        await kill_intro(page)
        await page.screenshot(path=str(OUT / "audit-E-rich.png"), full_page=False)
        results["rich"] = await measure_upgrades(page)

        # === POOR (gold = 0) ===
        await set_state(page, gold=0)
        await open_drawer_upgrades(page)
        await page.wait_for_timeout(400)
        await kill_intro(page)
        await page.screenshot(path=str(OUT / "audit-E-poor.png"), full_page=False)
        results["poor"] = await measure_upgrades(page)

        with open(OUT / "audit-E-info.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Quick textual report
        print("=== AUDIT E SUMMARY ===")
        for key in ["mid", "rich", "poor"]:
            r = results[key]
            print(f"\n--- {key.upper()} (state: gold={r['state']['gold'] if r['state'] else '?'}) ---")
            print(f"cards detected: {r['count']}")
            for c in r["cards"][:14]:
                if not c.get("visible"):
                    continue
                name_txt = c["name"]["text"] if c["name"] else "?"
                name_fs = c["name"]["fontSize"] if c["name"] else "-"
                name_trunc = c["name"]["truncated"] if c["name"] else "?"
                cost_txt = c["cost"]["text"] if c["cost"] else "?"
                cost_fs = c["cost"]["fontSize"] if c["cost"] else "-"
                cost_color = c["cost"]["color"] if c["cost"] else "-"
                lvl_txt = c["lvl"]["text"] if c["lvl"] else "?"
                lvl_fs = c["lvl"]["fontSize"] if c["lvl"] else "-"
                desc_txt = c["desc"]["text"] if c["desc"] else "?"
                desc_fs = c["desc"]["fontSize"] if c["desc"] else "-"
                desc_trunc = c["desc"]["truncated"] if c["desc"] else "?"
                print(f"  [{c['idx']}] name='{name_txt}' fs={name_fs} trunc={name_trunc} | cost='{cost_txt}' fs={cost_fs} color={cost_color} | lvl='{lvl_txt}' fs={lvl_fs} | desc='{desc_txt}' fs={desc_fs} trunc={desc_trunc} | aff={c['affordable']} lock={c['locked']} op={c['opacity']} barW={c['progressBarWidth']}")

        await browser.close()
        print("\n[DONE]")


if __name__ == "__main__":
    asyncio.run(main())
