"""
QA VAGUE 17 — Audit C : Notification "NOUVEAU : X débloqué !"
Read-only : observe la mécanique applyProgressiveDisclosure() + toast unlock.
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright

OUT = r"D:/alchimia/screenshots/qa-vague10"
URL = "http://localhost:8770/index.html"

PALIERS = [
    {"km": 1, "name": "tapValue"},
    {"km": 3, "name": "lapBonus"},
    {"km": 5, "name": "critChance"},
    {"km": 8, "name": "eagleEye"},
    {"km": 12, "name": "endurance"},
    {"km": 18, "name": "autoTap"},
    {"km": 25, "name": "baseSpeed"},
    {"km": 30, "name": "cruiseControl"},
]

async def skip_onboarding(page):
    """Saute le splash + tuto actif si présents."""
    await page.evaluate("""
        () => {
            // Bypass tuto actif
            try { localStorage.setItem('foulee.activeTutoV1', JSON.stringify({done:true, step:99})); } catch(e){}
            try { localStorage.setItem('alchimia.tutoSeen', '1'); } catch(e){}
            // Bypass splash si présent
            const splash = document.getElementById('splash');
            if (splash) splash.style.display = 'none';
            const opening = document.getElementById('opening-cinematic');
            if (opening) opening.style.display = 'none';
        }
    """)

async def get_toast_info(page):
    """Capture l'état des toasts unlock."""
    return await page.evaluate("""
        () => {
            const toasts = Array.from(document.querySelectorAll('[id^="unlock-toast"]'));
            return {
                count: toasts.length,
                texts: toasts.map(t => t.textContent),
                positions: toasts.map(t => {
                    const r = t.getBoundingClientRect();
                    return { top: r.top, left: r.left, width: r.width, height: r.height };
                }),
                styles: toasts.map(t => {
                    const cs = window.getComputedStyle(t);
                    return {
                        position: cs.position,
                        zIndex: cs.zIndex,
                        background: cs.background.slice(0, 100),
                        color: cs.color,
                        fontSize: cs.fontSize,
                        fontWeight: cs.fontWeight,
                        animation: cs.animation,
                        opacity: cs.opacity,
                        transform: cs.transform
                    };
                }),
                viewport: { w: window.innerWidth, h: window.innerHeight },
                revealed: window._revealedUnlocks ? Array.from(window._revealedUnlocks) : []
            };
        }
    """)

async def get_btn_flash(page, upgrade_id):
    """Vérifie si le bouton drawer a la classe .just-unlocked."""
    return await page.evaluate("""
        (id) => {
            const btn = document.querySelector(`.upg-btn[data-upgrade="${id}"]`);
            if (!btn) return { found: false };
            return {
                found: true,
                classes: btn.className,
                hasJustUnlocked: btn.classList.contains('just-unlocked'),
                locked: btn.getAttribute('data-locked'),
                visible: btn.offsetParent !== null
            };
        }
    """, upgrade_id)

async def force_palier(page, km):
    """Force lapsRun à la valeur km, puis appelle applyProgressiveDisclosure."""
    await page.evaluate(f"""
        () => {{
            if (typeof STATE !== 'undefined') {{
                STATE.lapsRun = {km};
            }}
            if (typeof applyProgressiveDisclosure === 'function') {{
                applyProgressiveDisclosure();
            }}
        }}
    """)

async def reset_unlocks(page):
    """Reset le set _revealedUnlocks et lapsRun=0."""
    await page.evaluate("""
        () => {
            window._revealedUnlocks = new Set();
            if (typeof STATE !== 'undefined') STATE.lapsRun = 0;
            // Cleanup toasts existants
            document.querySelectorAll('[id^="unlock-toast"]').forEach(t => t.remove());
        }
    """)

async def main():
    os.makedirs(OUT, exist_ok=True)
    results = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 540, "height": 960}, device_scale_factor=2)
        page = await ctx.new_page()

        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text[:200]}"))

        await page.goto(URL, wait_until="networkidle", timeout=20000)
        await asyncio.sleep(1.5)
        await skip_onboarding(page)
        await asyncio.sleep(0.5)

        # Pré-check : applyProgressiveDisclosure existe ?
        has_func = await page.evaluate("typeof applyProgressiveDisclosure === 'function'")
        has_state = await page.evaluate("typeof STATE !== 'undefined' && typeof STATE.lapsRun !== 'undefined'")
        results["preflight"] = {
            "applyProgressiveDisclosure_exists": has_func,
            "STATE_lapsRun_exists": has_state,
            "viewport": "540x960",
        }

        # Pour chaque palier : reset, set km, capture, attend fade
        for palier in PALIERS:
            km = palier["km"]
            name = palier["name"]
            label = f"km{km}_{name}"

            # Reset
            await reset_unlocks(page)
            await asyncio.sleep(0.5)

            # Force km
            await force_palier(page, km)
            await asyncio.sleep(0.8)  # laisse l'animation entrer

            # Screenshot apparition
            shot_in = os.path.join(OUT, f"audit-C-unlock-{label}.png")
            await page.screenshot(path=shot_in, full_page=False)

            # Mesure toast
            info_in = await get_toast_info(page)
            btn_in = await get_btn_flash(page, name)

            # Attente fade-out (anim totale = 4s)
            await asyncio.sleep(4.5)
            info_out = await get_toast_info(page)
            shot_out = os.path.join(OUT, f"audit-C-after-fade-{label}.png")
            await page.screenshot(path=shot_out, full_page=False)

            results[label] = {
                "km": km,
                "name": name,
                "toast_at_appear": info_in,
                "toast_after_fade": info_out,
                "btn_drawer_flash": btn_in,
            }

        # Test STACK : reset, puis force palier high pour potentiellement déclencher plusieurs unlock d'un coup
        await reset_unlocks(page)
        await asyncio.sleep(0.5)
        # km=30 d'un coup → tous les unlocks <=30 doivent apparaître (sauf ceux déjà dans _revealedUnlocks)
        await force_palier(page, 30)
        await asyncio.sleep(0.8)
        stack_info = await get_toast_info(page)
        shot_stack = os.path.join(OUT, "audit-C-stack-jump-to-km30.png")
        await page.screenshot(path=shot_stack, full_page=False)
        results["stack_test_km30"] = {
            "toast_count": stack_info["count"],
            "toast_texts": stack_info["texts"],
            "toast_positions": stack_info["positions"],
            "revealed_unlocks": stack_info["revealed"],
        }

        # Capture quelques logs console pertinents
        results["console_relevant"] = [m for m in console_msgs if any(k in m.lower() for k in ["unlock", "error", "warn"])][:20]
        results["console_total"] = len(console_msgs)

        await browser.close()

    # Dump JSON
    out_json = os.path.join(OUT, "audit-C-notif-results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("=== AUDIT C : NOTIFICATION UNLOCK ===")
    print(json.dumps(results, indent=2, ensure_ascii=False)[:8000])

asyncio.run(main())
