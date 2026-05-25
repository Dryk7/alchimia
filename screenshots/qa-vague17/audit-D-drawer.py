"""
AUDIT D - Drawer + Onglets pour upgrades
Vague 17 - UX read-only audit
"""
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Force UTF-8 stdout sur Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

OUT = Path(r"D:/alchimia/screenshots/qa-vague17")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"

async def skip_onboarding(page):
    """Skip story intro et tuto."""
    await page.evaluate("""() => {
        try { localStorage.setItem('alchimia_onboarded', '1'); } catch(e) {}
        try { localStorage.setItem('alchimia_story_seen', '1'); } catch(e) {}
        try { localStorage.setItem('alchimia_tuto_done', '1'); } catch(e) {}
        try { localStorage.setItem('alchimia_first_run', '0'); } catch(e) {}
        // Bypass tout overlay intro/daily
        document.querySelectorAll('.modal.show, .story-overlay, .intro-overlay, .opening-cinematic, #daily-modal').forEach(el => {
          el.classList.remove('show', 'active');
          el.style.display = 'none';
        });
    }""")
    # Click PRENDRE LE DÉPART si présent
    try:
        await page.click("button:has-text('PRENDRE LE DÉPART')", timeout=2500)
    except Exception:
        pass
    await page.wait_for_timeout(800)
    # Re-clean modals after game start
    await page.evaluate("""() => {
        document.querySelectorAll('.modal.show, .story-overlay, .intro-overlay, .opening-cinematic').forEach(el => {
          el.classList.remove('show','active');
          el.style.display='none';
        });
    }""")
    await page.wait_for_timeout(400)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960}, device_scale_factor=2)
        page = await ctx.new_page()
        # Capture errors console
        console_errors = []
        page.on("pageerror", lambda e: console_errors.append(f"PAGEERR: {e}"))
        page.on("console", lambda m: console_errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)

        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await skip_onboarding(page)
        await page.wait_for_timeout(1000)

        # =========== 1) ÉTAT INIT du drawer ===========
        await page.screenshot(path=str(OUT / "audit-D-init.png"), full_page=False)

        init_state = await page.evaluate("""() => {
          const tabsContent = document.querySelector('.tabs-content');
          const tabsStrip = document.querySelector('.tabs-strip');
          const tabBtns = Array.from(document.querySelectorAll('.tab-btn'));
          const panes = Array.from(document.querySelectorAll('.tab-pane'));
          const activeTab = tabBtns.find(b => b.classList.contains('active'));
          const activePane = panes.find(p => p.classList.contains('active'));
          const tabsRect = tabsContent ? tabsContent.getBoundingClientRect() : null;
          const stripRect = tabsStrip ? tabsStrip.getBoundingClientRect() : null;
          return {
            tabsContent_exists: !!tabsContent,
            tabsContent_open: tabsContent ? tabsContent.classList.contains('open') : null,
            tabsContent_classes: tabsContent ? tabsContent.className : null,
            tabsContent_maxHeight: tabsContent ? getComputedStyle(tabsContent).maxHeight : null,
            tabsContent_height: tabsRect ? Math.round(tabsRect.height) : null,
            tabsContent_top: tabsRect ? Math.round(tabsRect.top) : null,
            tabsContent_bottom: tabsRect ? Math.round(tabsRect.bottom) : null,
            tab_btn_count: tabBtns.length,
            tab_btn_labels: tabBtns.map(b => (b.querySelector('.tab-label')?.textContent || '').trim()),
            tab_btn_data: tabBtns.map(b => b.dataset.tab),
            tab_btn_visible: tabBtns.map(b => {
              const r = b.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            }),
            active_tab: activeTab ? activeTab.dataset.tab : null,
            active_pane: activePane ? activePane.dataset.pane : null,
            pane_data_list: panes.map(p => p.dataset.pane),
            strip_position: stripRect ? {
              top: Math.round(stripRect.top),
              bottom: Math.round(stripRect.bottom),
              height: Math.round(stripRect.height),
            } : null,
            viewport_height: window.innerHeight,
          };
        }""")

        print("[INIT STATE]")
        for k, v in init_state.items():
            print(f"  {k}: {v}")

        # =========== 2) FORCE STATE + drawer open ===========
        await page.evaluate("""() => {
          if (typeof STATE !== 'undefined') {
            STATE.lapsRun = 30;
            STATE.gold = 100000;
            STATE.med = 100000;
          }
          // Force ouvrir le drawer sur upgrades
          const tabsContent = document.querySelector('.tabs-content');
          if (tabsContent) tabsContent.classList.add('open');
          // Active le tab upgrades
          document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === 'upgrades'));
          document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.dataset.pane === 'upgrades'));
          // Force render upgrades si une fonction existe
          try {
            if (typeof renderUpgrades === 'function') renderUpgrades();
            if (typeof updateUI === 'function') updateUI();
          } catch(e) {}
        }""")
        await page.wait_for_timeout(800)

        await page.screenshot(path=str(OUT / "audit-D-full.png"), full_page=False)

        # =========== 3) Mesurer scroll content upgrades ===========
        upg_pane = await page.evaluate("""() => {
          const pane = document.querySelector('.tab-pane[data-pane="upgrades"]');
          const tabsContent = document.querySelector('.tabs-content');
          const upgrades = Array.from(document.querySelectorAll('.upg-btn'));
          const visibleUpgs = upgrades.filter(u => {
            const r = u.getBoundingClientRect();
            return r.top < window.innerHeight && r.bottom > 0 && r.width > 0 && r.height > 0;
          });
          const tcRect = tabsContent ? tabsContent.getBoundingClientRect() : null;
          return {
            pane_exists: !!pane,
            pane_scrollHeight: pane ? pane.scrollHeight : null,
            pane_clientHeight: pane ? pane.clientHeight : null,
            tabsContent_scrollHeight: tabsContent ? tabsContent.scrollHeight : null,
            tabsContent_clientHeight: tabsContent ? tabsContent.clientHeight : null,
            tabsContent_offsetHeight: tabsContent ? tabsContent.offsetHeight : null,
            tabsContent_overflowY: tabsContent ? getComputedStyle(tabsContent).overflowY : null,
            tabsContent_rect: tcRect ? {
              top: Math.round(tcRect.top), bottom: Math.round(tcRect.bottom),
              height: Math.round(tcRect.height)
            } : null,
            need_scroll: tabsContent ? (tabsContent.scrollHeight > tabsContent.clientHeight + 5) : null,
            upgrade_total: upgrades.length,
            upgrade_visible_in_viewport: visibleUpgs.length,
            upgrade_names: upgrades.map(u => (u.querySelector('.upg-name')?.textContent || '').trim()),
            upgrade_unlock_km: upgrades.map(u => u.dataset.unlockKm),
            upgrade_locked_count: upgrades.filter(u => u.classList.contains('locked')).length,
            upgrade_disabled_count: upgrades.filter(u => u.disabled).length,
            upgrade_display: upgrades.map(u => {
              const r = u.getBoundingClientRect();
              return {
                name: (u.querySelector('.upg-name')?.textContent || '').trim(),
                visible: r.width > 0 && r.height > 0,
                top: Math.round(r.top), bottom: Math.round(r.bottom),
                in_viewport: r.top < window.innerHeight && r.bottom > 0,
              };
            }),
          };
        }""")

        print("\n[UPGRADES PANE]")
        for k, v in upg_pane.items():
            if k == "upgrade_display":
                print(f"  {k}:")
                for d in v:
                    print(f"    - {d}")
            else:
                print(f"  {k}: {v}")

        # Check grid vs list ?
        layout_info = await page.evaluate("""() => {
          const ups = document.querySelector('.tap-upgrades, .tap-upgrades-v2');
          if (!ups) return null;
          const st = getComputedStyle(ups);
          return {
            display: st.display,
            gridTemplateColumns: st.gridTemplateColumns,
            flexDirection: st.flexDirection,
            gap: st.gap,
            class: ups.className,
          };
        }""")
        print("\n[LAYOUT UPGRADES CONTAINER]")
        print(f"  {layout_info}")

        # =========== 4) Test click sur autres tabs (via JS, intro-canvas intercepts pointer) ===========
        tab_tests = {}
        for tab in ["team", "stats", "upgrades"]:
            try:
                await page.evaluate(f"""(t) => {{
                  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === t));
                  document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.dataset.pane === t));
                  const tc = document.querySelector('.tabs-content');
                  if (tc) tc.classList.add('open');
                }}""", tab)
                await page.wait_for_timeout(300)
                snap = await page.evaluate(f"""() => {{
                  const pane = document.querySelector('.tab-pane[data-pane="{tab}"]');
                  return {{
                    is_active: pane ? pane.classList.contains('active') : null,
                    rect: pane ? (() => {{ const r=pane.getBoundingClientRect(); return {{top:Math.round(r.top), height:Math.round(r.height)}}; }})() : null,
                    item_count: pane ? pane.querySelectorAll('button, .stat-card, .team-card, .upg-btn').length : 0,
                    html_short: pane ? pane.innerHTML.slice(0,160) : null,
                  }};
                }}""")
                tab_tests[tab] = snap
                await page.screenshot(path=str(OUT / f"audit-D-tab-{tab}.png"), full_page=False)
            except Exception as e:
                tab_tests[tab] = f"ERR: {e}"

        print("\n[TABS TESTS]")
        for k, v in tab_tests.items():
            print(f"  {k}: {v}")

        # =========== 5) Close button / overlay ===========
        close_info = await page.evaluate("""() => {
          const closeBtns = document.querySelectorAll('.tabs-content .close, .tabs-content .drawer-close, .tabs-content button[aria-label*="ermer"], #tabs-close, .tabs-close');
          const overlay = document.getElementById('drawer-overlay');
          return {
            close_btn_count: closeBtns.length,
            close_btn_labels: Array.from(closeBtns).map(b => b.textContent.trim().slice(0,30) + ' / aria=' + (b.getAttribute('aria-label')||'')),
            drawer_overlay_exists: !!overlay,
            drawer_overlay_show: overlay ? overlay.classList.contains('show') : null,
          };
        }""")
        print("\n[CLOSE / OVERLAY]")
        for k, v in close_info.items():
            print(f"  {k}: {v}")

        # =========== 6) Screenshot HUD bas complet ===========
        # Replier sur upgrades pour shoot final
        await page.evaluate("""() => {
          document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === 'upgrades'));
          document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.dataset.pane === 'upgrades'));
        }""")
        await page.wait_for_timeout(300)
        # Crop bas écran (drawer + HUD)
        await page.screenshot(path=str(OUT / "audit-D-hud-bottom.png"),
                              clip={"x": 0, "y": 480, "width": 540, "height": 480})

        # =========== Console errors ===========
        if console_errors:
            print("\n[CONSOLE ERRORS]")
            for e in console_errors[:10]:
                print(f"  {e}")

        await browser.close()
        print("\n[DONE] Screenshots in", OUT)


if __name__ == "__main__":
    asyncio.run(main())
