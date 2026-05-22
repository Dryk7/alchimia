"""Audit complet du jeu : joue de A à Z, capture toutes les écrans, modals, états.
Sortie : D:/alchimia/screenshots/playthrough/*.png + audit-report.md"""
import asyncio
import io
import sys
from playwright.async_api import async_playwright

# Force UTF-8 stdout for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
REPORT = []
def log(msg):
    print(msg)
    REPORT.append(msg)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        errors = []
        warns = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: warns.append(f'{m.type}:{m.text}') if m.type in ('warning','error') else None)

        # ===== ÉTAPE 1 : FIRST LAUNCH (sans localstorage) =====
        await page.goto('http://localhost:8770')
        await page.evaluate('localStorage.clear();')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/01-first-launch.png')

        # Skip intro / story
        await page.evaluate('localStorage.setItem("foulee.storySeen","1");')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/02-intro-screen.png')

        # Click start
        await page.evaluate('document.getElementById("start-btn")?.click();')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/03-just-started.png')

        # Refuser pack starter si présent
        await page.evaluate('STATE.starterPackDeclined = true; STATE.starterPackClaimed = true; document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="none";});')
        await page.wait_for_timeout(400)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/04-clean-game-km0.png')

        # ===== ÉTAPE 2 : TAP MASSIF AU DÉBUT (KM 0-5) =====
        # Simule 30 taps via clic sur canvas
        for _ in range(30):
            await page.evaluate('window.dispatchEvent(new Event("pointerdown"));')
            await page.evaluate('if(typeof handleTap === "function") handleTap();')
            await page.wait_for_timeout(50)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/05-after-30-taps.png')

        # ===== ÉTAPE 3 : KM 2 = première lap, premier rival =====
        await page.evaluate('STATE.lapsRun = 2;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/06-km2-first-lap.png')

        # ===== ÉTAPE 4 : KM 5 = haies premier seuil =====
        await page.evaluate('STATE.lapsRun = 5; STATE.gold = 5000;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/07-km5-hurdles.png')

        # ===== ÉTAPE 5 : KM 12 = transition urbaine =====
        await page.evaluate('STATE.lapsRun = 12; STATE.gold = 50000;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/08-km12-urban.png')

        # ===== ÉTAPE 6 : KM 25 = transition urbain dense =====
        await page.evaluate('STATE.lapsRun = 25; STATE.gold = 200000;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/09-km25-urban-dense.png')

        # ===== ÉTAPE 7 : KM 30 = unlock cruise control =====
        await page.evaluate('STATE.lapsRun = 30; STATE.gold = 600000;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/10-km30-cruise-unlock.png')

        # ===== ÉTAPE 8 : KM 55 = stadium international =====
        await page.evaluate('STATE.lapsRun = 55; STATE.gold = 5000000; STATE.gems = 100; STATE.alchLevel = 15;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/11-km55-stadium.png')

        # ===== ÉTAPE 9 : KM 80 = stade olympique vasque =====
        await page.evaluate('STATE.lapsRun = 80; STATE.gold = 20000000; STATE.gems = 200; STATE.stars = 15; STATE.alchLevel = 25;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/12-km80-olympic.png')

        # ===== ÉTAPE 10 : KM 100+ = endgame chap1 =====
        await page.evaluate('STATE.lapsRun = 105; STATE.gold = 100000000; STATE.gems = 500; STATE.stars = 30; STATE.alchLevel = 40;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/13-km100-endgame.png')

        # ===== ÉTAPE 11 : CHAPTER 2 LUNAIRE =====
        await page.evaluate('STATE.lapsRun = 105; STATE.chapter = 2;')
        await page.wait_for_timeout(800)
        await page.screenshot(path='D:/alchimia/screenshots/playthrough/14-chapter2-lunar.png')
        # Reset chapter
        await page.evaluate('STATE.chapter = 1;')

        # ===== ÉTAPE 12 : AUDIT TOUS LES MODALS =====
        # Reset position to km 50 for relevant content
        await page.evaluate('STATE.lapsRun = 50; STATE.gold = 5000000; STATE.gems = 200; STATE.stars = 15; STATE.alchLevel = 25;')
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="";});')
        await page.wait_for_timeout(300)

        modals = [
            ('menu-modal', 'document.getElementById("menu-modal").classList.add("show")'),
            ('settings-modal', 'document.getElementById("settings-modal").classList.add("show")'),
            ('credits-modal', 'document.getElementById("credits-modal").classList.add("show")'),
            ('guide-modal', 'document.getElementById("help-toggle")?.click()'),
            ('records-modal', 'if(typeof openRecords === "function") openRecords()'),
            ('shop-modal', 'if(typeof openShopModal === "function") openShopModal()'),
            ('daily-modal', 'if(typeof openDailyModal === "function") openDailyModal()'),
            ('quests-daily-modal', 'if(typeof openQuestsModal === "function") openQuestsModal()'),
            ('stats-modal', 'if(typeof renderStatsBody === "function") renderStatsBody(); document.getElementById("stats-modal").classList.add("show")'),
            ('saison-modal', 'if(typeof openSaisonModal === "function") openSaisonModal()'),
            ('wardrobe-modal', 'if(typeof openWardrobe === "function") openWardrobe()'),
            ('equip-modal', 'if(typeof openEquip === "function") openEquip()'),
            ('cards-modal', 'if(typeof openCardCollection === "function") openCardCollection()'),
            ('chests-modal', 'if(typeof openChestsModal === "function") openChestsModal()'),
            ('map-stadiums-modal', 'if(typeof openMapStadiums === "function") openMapStadiums()'),
            ('runner-profile-modal', 'if(typeof openRunnerProfile === "function") openRunnerProfile()'),
            ('achievements-modal', 'if(typeof openAchievements === "function") openAchievements()'),
            ('skill-tree-modal', 'if(typeof openSkillTree === "function") openSkillTree()'),
            ('reset-confirm-modal', 'document.getElementById("reset-confirm-modal").classList.add("show")'),
        ]

        for modal_id, opener in modals:
            await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="";});')
            await page.wait_for_timeout(120)
            try:
                await page.evaluate(opener)
                await page.wait_for_timeout(350)
                vis = await page.evaluate(f'(()=>{{const m=document.getElementById("{modal_id}");return m && m.classList.contains("show");}})()')
                if not vis:
                    await page.evaluate(f'document.getElementById("{modal_id}")?.classList.add("show")')
                    await page.wait_for_timeout(250)
                await page.screenshot(path=f'D:/alchimia/screenshots/playthrough/modal-{modal_id}.png')
                log(f'OK modal {modal_id}')
            except Exception as e:
                log(f'SKIP {modal_id}: {str(e)[:80]}')

        # ===== ÉTAPE 13 : EXAMINE LE DOM POUR EMOJIS / INCOHÉRENCES =====
        await page.evaluate('document.querySelectorAll(".modal.show").forEach(m=>{m.classList.remove("show"); m.style.display="";});')
        await page.wait_for_timeout(200)

        emoji_audit = await page.evaluate('''(()=>{
            const out = { byElement: [], total: 0, uniqueEmojis: new Set() };
            const emojiRegex = /[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}\\u{1F000}-\\u{1F02F}\\u{1F0A0}-\\u{1F0FF}\\u{1F100}-\\u{1F64F}\\u{1F900}-\\u{1F9FF}]/gu;
            const walk = (node) => {
                if (node.nodeType === 3) {
                    const matches = node.textContent.match(emojiRegex);
                    if (matches) {
                        matches.forEach(m => out.uniqueEmojis.add(m));
                        out.total += matches.length;
                        const parent = node.parentElement;
                        if (parent) {
                            out.byElement.push({
                                el: parent.tagName + (parent.id ? '#' + parent.id : '') + (parent.className && typeof parent.className === 'string' ? '.' + parent.className.split(' ').slice(0,2).join('.') : ''),
                                text: node.textContent.trim().slice(0, 60),
                                emojis: matches.join(' '),
                            });
                        }
                    }
                }
                for (const c of node.childNodes) walk(c);
            };
            walk(document.body);
            return {
                total: out.total,
                unique: [...out.uniqueEmojis],
                samples: out.byElement.slice(0, 50),
            };
        })()''')
        log('\n===== EMOJI AUDIT =====')
        log(f'Total emojis visibles : {emoji_audit["total"]}')
        log(f'Emojis uniques : {len(emoji_audit["unique"])}')
        log(f'Liste : {" ".join(emoji_audit["unique"])}')
        log('\nSamples (max 50) :')
        for s in emoji_audit['samples'][:50]:
            log(f'  {s["emojis"]} dans {s["el"]} : "{s["text"]}"')

        # ===== ÉTAPE 14 : DESIGN AUDIT (couleurs, fonts, harmonie) =====
        design_audit = await page.evaluate('''(()=>{
            const styles = new Set();
            const fonts = new Set();
            const borderColors = new Set();
            const bgColors = new Set();
            document.querySelectorAll('button, .modal-content, .pill, .upg-btn, .menu-item').forEach(el => {
                const cs = getComputedStyle(el);
                fonts.add(cs.fontFamily);
                borderColors.add(cs.borderColor);
                bgColors.add(cs.backgroundColor);
            });
            return {
                fonts: [...fonts],
                borderColors: [...borderColors].slice(0, 30),
                bgColors: [...bgColors].slice(0, 30),
            };
        })()''')
        log('\n===== DESIGN AUDIT =====')
        log(f'Fonts utilisées : {len(design_audit["fonts"])}')
        for f in design_audit['fonts']: print(f'  {f}')
        log(f'Couleurs de bordure variées : {len(design_audit["borderColors"])}')
        for c in design_audit['borderColors']: print(f'  {c}')

        # ===== ÉTAPE 15 : Z-index conflicts =====
        z_audit = await page.evaluate('''(()=>{
            const out = [];
            document.querySelectorAll('*').forEach(el => {
                const z = getComputedStyle(el).zIndex;
                if (z !== 'auto' && parseInt(z) >= 100) {
                    out.push({id: el.id || el.tagName, z: z, cls: (el.className && typeof el.className === 'string') ? el.className.slice(0, 40) : ''});
                }
            });
            return out.sort((a,b) => parseInt(b.z) - parseInt(a.z)).slice(0, 30);
        })()''')
        log('\n===== Z-INDEX AUDIT =====')
        for x in z_audit:
            log(f'  z={x["z"]} : {x["id"]} ({x["cls"]})')

        # ===== ÉTAPE 16 : SCROLLABILITY MODALS =====
        scroll_audit = await page.evaluate('''(()=>{
            const out = [];
            document.querySelectorAll('.modal').forEach(m => {
                const inner = m.querySelector('.modal-content, .menu-list, .modal-body');
                if (inner) {
                    const cs = getComputedStyle(inner);
                    out.push({
                        id: m.id,
                        innerScrollY: cs.overflowY,
                        maxHeight: cs.maxHeight,
                        height: cs.height,
                    });
                }
            });
            return out;
        })()''')
        log('\n===== SCROLLABILITY MODALS =====')
        for s in scroll_audit:
            log(f'  {s["id"]}: overflow={s["innerScrollY"]} maxH={s["maxHeight"]}')

        # ===== ÉTAPE 17 : OVERFLOW HORIZONTAL =====
        overflow_audit = await page.evaluate('''(()=>{
            const docW = document.documentElement.clientWidth;
            const out = [];
            document.querySelectorAll('*').forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.right > docW + 2) {
                    out.push({id: el.id || el.tagName, cls: (el.className && typeof el.className === 'string') ? el.className.slice(0, 40) : '', right: Math.round(r.right), docW: docW});
                }
            });
            return out.slice(0, 20);
        })()''')
        log('\n===== OVERFLOW HORIZONTAL =====')
        for o in overflow_audit:
            log(f'  {o["id"]} ({o["cls"]}) : right={o["right"]} > viewport={o["docW"]}')

        # ===== ERRORS =====
        log(f'\n===== ERRORS ({len(errors)}) =====')
        for e in errors[:10]: print(f'  - {e[:200]}')
        log(f'\n===== WARNINGS ({len(warns)}) =====')
        for w in warns[:15]: print(f'  - {w[:200]}')

        await browser.close()
        log('\n[DONE] Tous screenshots dans D:/alchimia/screenshots/playthrough/')

        # Write report
        with open('D:/alchimia/screenshots/playthrough/audit-report.md', 'w', encoding='utf-8') as f:
            f.write('# Audit complet FOULÉE\n\n```\n')
            f.write('\n'.join(REPORT))
            f.write('\n```\n')

asyncio.run(main())
