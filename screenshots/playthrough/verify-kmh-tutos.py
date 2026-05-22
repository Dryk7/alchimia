"""Vérifie :
1) Compteur km/h visible dans le HUD
2) Bulle tuto au 1er spawn lapin
3) Bulle tuto au 1er spawn lièvre
"""
import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto('http://localhost:8770')
        await page.evaluate('''
            localStorage.setItem("foulee.storySeen","1");
            localStorage.setItem("foulee.tutoV3","done");
            localStorage.setItem("foulee.activeTutoV1","done");
            // Reset tuto rabbit/hare pour les voir
            localStorage.removeItem("foulee.tutoRabbit");
            localStorage.removeItem("foulee.tutoHare");
        ''')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.evaluate('''
            document.getElementById("start-btn")?.click();
            if(window.STATE){
                STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;
                STATE.totalTaps=20; STATE.lapsRun=10;
            }
        ''')
        await page.wait_for_timeout(1500)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
        await page.wait_for_timeout(500)

        # === 1) km/h visible ?
        pace_info = await page.evaluate('''(()=>{
            const el = document.getElementById("runner-pace");
            if(!el) return {found: false};
            const r = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            return {
                found: true,
                visible: cs.display !== 'none' && r.width > 0 && r.height > 0,
                text: el.textContent,
                top: Math.round(r.top),
                left: Math.round(r.left),
                fontSize: cs.fontSize,
                color: cs.color
            };
        })()''')
        print(f'[KM/H] {pace_info}')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/KMH-visible.png', clip={'x':0,'y':0,'width':540,'height':120})

        # === 2) Spawn lapin → bulle tuto
        await page.evaluate('window.SPAWN_RABBIT && window.SPAWN_RABBIT();')
        await page.wait_for_timeout(300)
        bub_rabbit = await page.evaluate('''(()=>{
            const b = document.querySelector('.runner-bubble');
            if(!b) return {found: false};
            const r = b.getBoundingClientRect();
            return {found: true, text: b.textContent, top: Math.round(r.top), visible: r.height > 0};
        })()''')
        print(f'[LAPIN] {bub_rabbit}')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/TUTO-rabbit.png', clip={'x':0,'y':0,'width':540,'height':400})

        # Wait pour que la bulle s'efface
        await page.wait_for_timeout(4500)

        # === 3) Spawn lièvre → bulle tuto
        await page.evaluate('window.SPAWN_HARE && window.SPAWN_HARE();')
        await page.wait_for_timeout(300)
        bub_hare = await page.evaluate('''(()=>{
            const b = document.querySelector('.runner-bubble');
            if(!b) return {found: false};
            const r = b.getBoundingClientRect();
            return {found: true, text: b.textContent, top: Math.round(r.top), visible: r.height > 0};
        })()''')
        print(f'[LIÈVRE] {bub_hare}')
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/TUTO-hare.png', clip={'x':0,'y':0,'width':540,'height':400})

        # === 4) Re-spawn lapin → cette fois PAS de bulle (déjà vue)
        await page.wait_for_timeout(4500)
        await page.evaluate('window.SPAWN_RABBIT && window.SPAWN_RABBIT();')
        await page.wait_for_timeout(300)
        bub_again = await page.evaluate('''document.querySelector('.runner-bubble') ? document.querySelector('.runner-bubble').textContent : 'AUCUNE BULLE' ''')
        print(f'[LAPIN-2ND] {bub_again}')

        await browser.close()

asyncio.run(main())
