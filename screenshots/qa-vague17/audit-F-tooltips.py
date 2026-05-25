"""
Audit F — VAGUE 17 — Descriptions detaillees / Tooltips
Verifie disponibilite de tooltips, hold-tap, descriptions niveau suivant
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague17")
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = {
    "tooltip_system_global": None,
    "buttons": [],
    "next_level_preview_fn": None,
    "codex_presence": None,
    "errors": [],
}

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960}, device_scale_factor=1)
        page = ctx.new_page()

        # Capture console errors
        page.on("console", lambda msg: RESULTS["errors"].append(msg.text) if msg.type == "error" else None)

        page.goto("http://localhost:8770/", wait_until="domcontentloaded", timeout=15000)

        # Skip onboarding + force state
        page.evaluate(
            """() => {
                try { localStorage.setItem('foulee.onboardingDone','1'); } catch(e){}
                try { localStorage.setItem('alchimia.tuto.done','1'); } catch(e){}
                try { localStorage.setItem('foulee.tutoStep','done'); } catch(e){}
            }"""
        )
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # Force lapsRun=30 + gold=100000 (post unlock all upgrades)
        page.evaluate(
            """() => {
                try {
                    if(window.STATE){
                        STATE.lapsRun = 30;
                        STATE.gold = 100000;
                        STATE.upgradeTapValue = 5;
                        STATE.upgradeCritChance = 2;
                        STATE.upgradeLapBonus = 3;
                        STATE.upgradeAutoTap = 1;
                        STATE.upgradeEndurance = 1;
                        STATE.upgradeBaseSpeed = 1;
                        STATE.upgradeEagleEye = 1;
                        if(typeof updateUpgradesUI === 'function') updateUpgradesUI();
                        if(typeof renderHUD === 'function') renderHUD();
                    }
                } catch(e){ return 'err:'+e.message; }
                return 'ok';
            }"""
        )
        page.wait_for_timeout(500)

        # Open upgrades drawer (try common selectors)
        opened = page.evaluate(
            """() => {
                // Try clicking the upgrade tab in HUD bottom drawer
                const tab = document.querySelector('[data-tab="upgrades"], .tab-upgrades, #tab-upgrades, .drawer-tab-upgrades');
                if(tab){ tab.click(); return 'tab-click'; }
                // Try the side button
                const btn = document.querySelector('.hud-upgrades, #btn-upgrades, .btn-upgrades');
                if(btn){ btn.click(); return 'btn-click'; }
                // Try generic drawer open
                const drawer = document.querySelector('.tap-upgrades-v2, #upgrades-grid, .upgrades-grid');
                if(drawer){ drawer.scrollIntoView(); return 'scroll'; }
                return 'no-trigger';
            }"""
        )
        page.wait_for_timeout(800)

        # Try a broader strategy: explicitly open via the bottom drawer
        page.evaluate(
            """() => {
                const all = document.querySelectorAll('button, .tab, [role=tab]');
                for(const el of all){
                    const t = (el.textContent||'').trim().toUpperCase();
                    if(t === 'UPGRADES' || t === 'AMELIORATIONS' || t.includes('UPGRADE')){
                        try { el.click(); return; } catch(e){}
                    }
                }
            }"""
        )
        page.wait_for_timeout(800)

        # Probe global tooltip system
        RESULTS["tooltip_system_global"] = page.evaluate(
            """() => ({
                tooltipsObj: typeof window.Tooltips,
                hasDataTooltipElements: document.querySelectorAll('[data-tooltip]').length,
                hasFouleeBubble: !!document.querySelector('.foulee-tooltip'),
            })"""
        )

        # Inspect each upg-btn
        btn_info = page.evaluate(
            """() => {
                const out = [];
                const btns = document.querySelectorAll('.upg-btn');
                btns.forEach(b => {
                    const rect = b.getBoundingClientRect();
                    out.push({
                        upgradeId: b.getAttribute('data-upgrade'),
                        ariaLabel: b.getAttribute('aria-label'),
                        title: b.getAttribute('title'),
                        dataTooltip: b.getAttribute('data-tooltip'),
                        dataTooltipTitle: b.getAttribute('data-tooltip-title'),
                        dataBonus: b.getAttribute('data-bonus'),
                        dataUnlockKm: b.getAttribute('data-unlock-km'),
                        dataLocked: b.getAttribute('data-locked'),
                        visible: rect.width > 0 && rect.height > 0,
                        rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
                        name: (b.querySelector('.upg-name')||{}).textContent || '',
                        desc: (b.querySelector('.upg-desc')||{}).textContent || '',
                        lvl: (b.querySelector('.upg-lvl')||{}).textContent || '',
                        cost: (b.querySelector('.upg-cost')||{}).textContent || '',
                    });
                });
                return out;
            }"""
        )
        RESULTS["buttons"] = btn_info

        # Check presence of preview function (_previewUpgradeBonus)
        RESULTS["next_level_preview_fn"] = page.evaluate(
            """() => ({
                hasPreviewFn: typeof window._previewUpgradeBonus,
                samples: (typeof _previewUpgradeBonus === 'function') ? {
                    tapValue: _previewUpgradeBonus('tapValue'),
                    critChance: _previewUpgradeBonus('critChance'),
                    lapBonus: _previewUpgradeBonus('lapBonus'),
                } : null
            })"""
        )

        # Find first visible upg-btn and simulate hold
        target = None
        for b in btn_info:
            if b["visible"] and b["upgradeId"] == "tapValue":
                target = b
                break
        if not target:
            for b in btn_info:
                if b["visible"]:
                    target = b
                    break

        tooltip_appears = None
        if target:
            cx = target["rect"]["x"] + target["rect"]["w"] / 2
            cy = target["rect"]["y"] + target["rect"]["h"] / 2
            try:
                page.mouse.move(cx, cy)
                page.mouse.down()
                page.wait_for_timeout(1500)
                tooltip_appears = page.evaluate(
                    """() => {
                        const tt = document.querySelector('.foulee-tooltip.show');
                        if(!tt) return { visible: false, text: null };
                        return {
                            visible: true,
                            text: tt.textContent,
                            title: (tt.querySelector('.foulee-tooltip-title')||{}).textContent || '',
                            body:  (tt.querySelector('.foulee-tooltip-body')||{}).textContent || '',
                        };
                    }"""
                )
                page.screenshot(path=str(OUT / "audit-F-tooltip-tap.png"))
                page.mouse.up()
            except Exception as e:
                RESULTS["errors"].append("hold-error: " + str(e))
        RESULTS["hold_tap_result"] = tooltip_appears
        RESULTS["hold_target"] = target

        # Codex / Guide presence
        RESULTS["codex_presence"] = page.evaluate(
            """() => {
                const codex = document.querySelector('#codex, .codex, [data-modal=codex], #guide-modal, .guide-modal');
                const guideBtn = Array.from(document.querySelectorAll('button, a')).find(el =>
                    /guide|codex/i.test((el.textContent||'') + ' ' + (el.getAttribute('aria-label')||''))
                );
                return {
                    codexElement: !!codex,
                    guideButtonFound: !!guideBtn,
                    guideButtonText: guideBtn ? (guideBtn.textContent||'').trim().slice(0,40) : null,
                };
            }"""
        )

        browser.close()

    (OUT / "audit-F-tooltips.json").write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2))
    print(json.dumps(RESULTS, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
