import asyncio, sys, io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        await ctx.add_init_script("try { localStorage.setItem('foulee.openingSeen','1'); localStorage.setItem('foulee.storySeen','1'); localStorage.setItem('foulee.tutoV3','done'); localStorage.setItem('foulee.activeTutoV1','done'); } catch(e){}")
        await page.goto('http://localhost:8770', wait_until='networkidle', timeout=20000)
        await page.evaluate('document.getElementById("start-btn")?.click(); if(window.STATE){STATE.starterPackDeclined=true; STATE.starterPackClaimed=true;}')
        await page.wait_for_timeout(2000)
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')

        # Extra global check: scan ALL fixed/absolute elements for overflow
        global_check = await page.evaluate('''(()=>{
            const out = [];
            const docW = document.documentElement.clientWidth;
            document.querySelectorAll('*').forEach(el => {
                if(!el.offsetParent && el.tagName !== 'BODY') return;
                const cs = getComputedStyle(el);
                if(cs.position !== 'fixed' && cs.position !== 'absolute') return;
                const r = el.getBoundingClientRect();
                if(r.right > docW + 4 && r.width > 5 && r.width < docW){
                    let p = el.parentElement;
                    let inScroll = false;
                    let parentTransformed = false;
                    while(p && p !== document.body){
                        const ps = getComputedStyle(p);
                        if((ps.overflowX === 'auto' || ps.overflowX === 'scroll')){ inScroll = true; break; }
                        if(ps.transform && ps.transform !== 'none'){ parentTransformed = true; break; }
                        p = p.parentElement;
                    }
                    if(!inScroll && !parentTransformed){
                        out.push({el: el.tagName+(el.id?'#'+el.id:'')+(el.className?'.'+(''+el.className).split(' ')[0]:''), right: Math.round(r.right), width: Math.round(r.width), pos: cs.position});
                    }
                }
            });
            return out.slice(0, 15);
        })()''')
        if global_check:
            print('[GLOBAL fixed/absolute overflow]')
            for g in global_check: print(f'  {g}')

        all_anomalies = []
        for km in [0, 3, 8, 25, 50, 70, 100, 105]:
            await page.evaluate(f'if(window.STATE){{STATE.lapsRun = {km}; STATE.totalTaps = 200;}}')
            await page.wait_for_timeout(1200)
            anomalies = await page.evaluate('''(()=>{
                const out = [];
                const docW = document.documentElement.clientWidth;
                const docH = document.documentElement.clientHeight;
                // Helper: check if any ancestor is a scrollable container (intentional overflow)
                const hasScrollableAncestor = (el) => {
                    let p = el.parentElement;
                    while(p && p !== document.body){
                        const ps = getComputedStyle(p);
                        if((ps.overflowX === 'auto' || ps.overflowX === 'scroll') && p.scrollWidth > p.clientWidth + 2) return true;
                        p = p.parentElement;
                    }
                    return false;
                };
                document.querySelectorAll('header *, .runner-hud-overlay *, .tabs-strip *, button, .modal').forEach(el => {
                    if(!el.offsetParent) return;
                    const r = el.getBoundingClientRect();
                    const cs = getComputedStyle(el);
                    if(r.right > docW + 4 && r.width > 5){
                        const transform = cs.transform;
                        const intentionalOffscreen = transform && transform !== 'none' && (transform.includes('translateX') || transform.includes('matrix'));
                        const inScrollable = hasScrollableAncestor(el);
                        if(!intentionalOffscreen && !inScrollable){
                            out.push({issue:'overflow_R', el: el.tagName+(el.id?'#'+el.id:'')+(el.className?'.'+(''+el.className).split(' ')[0]:''), right: Math.round(r.right), width: Math.round(r.width)});
                        }
                    }
                    if(parseFloat(cs.opacity) === 0 && cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 10 && r.height > 10){
                        // Check if parent has opacity:0 too - then it's a hidden container
                        let parent = el.parentElement;
                        let parentInvisible = false;
                        while(parent){
                            if(parseFloat(getComputedStyle(parent).opacity) === 0){ parentInvisible = true; break; }
                            parent = parent.parentElement;
                        }
                        if(!parentInvisible){
                            out.push({issue:'zombie_invisible', el: el.tagName+(el.id?'#'+el.id:'')+(el.className?'.'+(''+el.className).split(' ')[0]:'')});
                        }
                    }
                });
                // Additional checks: stuck modals, HUD overlap, tooltip clipping
                document.querySelectorAll('.modal').forEach(m => {
                    const cs = getComputedStyle(m);
                    const r = m.getBoundingClientRect();
                    if(cs.display !== 'none' && parseFloat(cs.opacity) > 0.5 && r.width > 20 && !m.classList.contains('show')){
                        out.push({issue:'modal_stuck_open', el: 'MODAL#'+(m.id||'?')});
                    }
                });
                // Check #saut button (SAUT) overlap with other elements
                const saut = document.querySelector('#saut-btn, [data-action="saut"], .saut-btn');
                if(saut && saut.offsetParent){
                    const sr = saut.getBoundingClientRect();
                    document.querySelectorAll('.runner-hud-overlay > *, header button').forEach(other => {
                        if(other === saut || !other.offsetParent) return;
                        const or = other.getBoundingClientRect();
                        if(sr.right > or.left && sr.left < or.right && sr.bottom > or.top && sr.top < or.bottom){
                            out.push({issue:'saut_overlap', other: other.tagName+(other.id?'#'+other.id:'')});
                        }
                    });
                }
                return out.slice(0, 12);
            })()''')
            if anomalies:
                all_anomalies.append((km, anomalies))
                print(f'[km {km}] {len(anomalies)} anomalies')
                for a in anomalies: print(f'  {a}')

        print(f'\nTotal: {sum(len(a[1]) for a in all_anomalies)} anomalies sur {len(all_anomalies)} km')
        await browser.close()

asyncio.run(main())
