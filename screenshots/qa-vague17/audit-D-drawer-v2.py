"""
AUDIT D v2 - Drawer + Onglets - retire l'opening cinematic pour voir vraiment
"""
import asyncio
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
    """Force la fin de l'opening cinematic et de tout overlay."""
    await page.evaluate("""() => {
      // Vire intro & opening cinematic
      ['intro', 'opening-cinematic', 'splash', 'story-overlay'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
      });
      document.querySelectorAll('.intro, .opening-cinematic, .splash, .story-overlay, #intro-canvas').forEach(el => {
        el.style.display = 'none';
        el.style.opacity = '0';
        el.style.pointerEvents = 'none';
      });
      // Vire popup notifs en bas
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
        await page.wait_for_timeout(500)

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
        await page.wait_for_timeout(600)
        await kill_intro(page)  # rekill in case re-shown

        await page.screenshot(path=str(OUT / "audit-D-v2-upgrades-open.png"), full_page=False)

        # Tabs-content fermé pour comparaison
        await page.evaluate("""() => {
          const tc = document.querySelector('.tabs-content');
          if (tc) tc.classList.remove('open');
        }""")
        await page.wait_for_timeout(400)
        await kill_intro(page)
        await page.screenshot(path=str(OUT / "audit-D-v2-closed.png"), full_page=False)

        # Team tab
        await page.evaluate("""() => {
          const tc = document.querySelector('.tabs-content');
          if (tc) tc.classList.add('open');
          document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === 'team'));
          document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.dataset.pane === 'team'));
        }""")
        await page.wait_for_timeout(400)
        await kill_intro(page)
        await page.screenshot(path=str(OUT / "audit-D-v2-team-open.png"), full_page=False)

        # Stats tab
        await page.evaluate("""() => {
          const tc = document.querySelector('.tabs-content');
          if (tc) tc.classList.add('open');
          document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === 'stats'));
          document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.dataset.pane === 'stats'));
          try { if (typeof renderStats === 'function') renderStats(); if (typeof updateUI === 'function') updateUI(); } catch(e){}
        }""")
        await page.wait_for_timeout(400)
        await kill_intro(page)
        await page.screenshot(path=str(OUT / "audit-D-v2-stats-open.png"), full_page=False)

        await browser.close()
        print("[DONE v2]")


if __name__ == "__main__":
    asyncio.run(main())
