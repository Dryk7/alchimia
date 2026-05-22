"""AUDIT UX NOUVEAU JOUEUR — FOULÉE
Simule un joueur qui n'a JAMAIS lancé le jeu et capture chaque friction d'onboarding.
Sortie : screenshots + log timestampé des bulles tuto + métriques.
Ne modifie RIEN dans le code du jeu.
"""
import asyncio, sys, io, time, json
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OUT = 'D:/alchimia/screenshots/playthrough'
URL = 'http://localhost:8770'

# Journal global des observations
log = []
t0 = None

def stamp():
    return round(time.time() - t0, 2) if t0 else 0.0

def note(tag, msg, friction=None):
    e = {'t': stamp(), 'tag': tag, 'msg': msg}
    if friction: e['friction'] = friction
    log.append(e)
    print(f'[T={e["t"]:>5.2f}s] {tag:<20} | {msg}' + (f'  >> FRICTION: {friction}' if friction else ''))


async def grab_visible_text(page, sel):
    try:
        return await page.evaluate(f'''(()=>{{
            const el = document.querySelector({json.dumps(sel)});
            if(!el) return null;
            const cs = getComputedStyle(el);
            if(cs.display === "none" || cs.visibility === "hidden" || parseFloat(cs.opacity) < 0.1) return null;
            return (el.innerText || el.textContent || "").trim().slice(0, 400);
        }})()''')
    except Exception:
        return None


async def collect_tutos(page):
    """Capture toute bulle/hint/tuto/overlay actuellement visible."""
    return await page.evaluate('''(()=>{
        const out = {};
        const candidates = {
            active_tuto_bubble: '.active-tuto-bubble',
            active_tuto_eyebrow: '.active-tuto-eyebrow',
            active_tuto_text: '.active-tuto-text',
            tuto_hint: '#tuto-hint',
            tuto_msg: '#tuto-msg',
            giga_step_active: '.giga-step.active',
            runner_bubble: '#runner-bubble',
            unlock_cinematic: '#unlock-cinematic',
            story_intro: '#story-intro',
            opening_cinematic: '#opening-cinematic',
            stat_gold: '#stat-gold',
            stat_km: '#stat-km',
            chests_modal: '#chests-modal.show',
        };
        for(const [k, sel] of Object.entries(candidates)){
            const el = document.querySelector(sel);
            if(!el) continue;
            const cs = getComputedStyle(el);
            if(cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.1) continue;
            out[k] = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 300);
        }
        out._state = {
            lapsRun: (window.STATE?.lapsRun)||0,
            totalTaps: (window.STATE?.totalTaps)||0,
            gold: (window.STATE?.gold)||0,
            chestsOwned: Object.keys(window.STATE?.chests||{}).length,
        };
        out._tutoOverlayVisible = !!document.querySelector('.active-tuto-overlay');
        out._bodyHasActiveTuto = document.body.classList.contains('active-tuto-running');
        return out;
    })()''')


async def shot(page, name):
    path = f'{OUT}/UX-{name}.png'
    await page.screenshot(path=path)
    return path


async def main():
    global t0
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        page = await ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))

        # ─── 0. Première arrivée (clear localStorage avant reload) ───
        await page.goto(URL)
        await page.evaluate('localStorage.clear(); sessionStorage.clear();')
        t0 = time.time()
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(1200)
        note('00-FIRST-LOAD', 'Page chargée, localStorage clean')
        tutos = await collect_tutos(page)
        note('00-OBS', f'Overlays visibles: {list(tutos.keys())[:6]}')
        await shot(page, '00-first-load')

        # ─── 1. Opening cinematic (s'il existe) ───
        for sec in (1.5, 3, 5):
            await page.wait_for_timeout(int((sec - stamp()) * 1000) if sec - stamp() > 0 else 100)
            tutos = await collect_tutos(page)
            visible = [k for k in tutos.keys() if k.startswith('_') is False]
            note(f'01-CINE-{sec}s', f'Overlays: {visible}')
        await shot(page, '01-splash-ready')

        # Recherche du bouton "PRENDRE LE DÉPART"
        start_btn = await grab_visible_text(page, '#start-btn')
        note('02-START-BTN', f'Texte: "{start_btn}"',
             friction=None if start_btn else 'Bouton start invisible/absent')

        # ─── 2. Click PRENDRE LE DÉPART ───
        await page.evaluate('document.getElementById("start-btn")?.click();')
        await page.wait_for_timeout(1500)
        note('02-CLICK-START', 'Clicked #start-btn')
        await shot(page, '02-after-start-click')

        # ─── 3. GIGA TUTO : capture chaque étape ───
        for step in range(8):
            await page.wait_for_timeout(700)
            tutos = await collect_tutos(page)
            txt = tutos.get('giga_step_active', '')
            note(f'03-GIGA-step{step}', f'Contenu: "{txt[:110]}..."' if len(txt) > 110 else f'Contenu: "{txt}"')
            await shot(page, f'03-giga-step{step}')
            # Click SUIVANT pour avancer (sauf au dernier où le bouton = C'EST PARTI)
            await page.evaluate('document.getElementById("giga-next")?.click();')
            await page.wait_for_timeout(400)

        await page.wait_for_timeout(2000)  # laisse story disparaître + ActiveTuto démarrer
        note('03-GIGA-END', 'Giga-tuto terminé, ActiveTuto devrait démarrer')

        # ─── 4. ActiveTuto step 1 : BIENVENUE ───
        tutos = await collect_tutos(page)
        bubble = tutos.get('active_tuto_bubble', '')
        note('04-ACTIVE-TUTO-1', f'Bulle: "{bubble[:150]}"',
             friction='Encore un tuto APRES les 8 cartes giga' if bubble else None)
        await shot(page, '04-active-tuto-bienvenue')

        # Click COMMENCER
        clicked = await page.evaluate('(()=>{const b=document.getElementById("tuto-next"); if(b){b.click(); return true;} return false;})()')
        note('04-CLICK-COMMENCER', f'#tuto-next clické: {clicked}')
        await page.wait_for_timeout(700)

        # ─── 5. ActiveTuto step 2 : TAP demande premier tap ───
        tutos = await collect_tutos(page)
        bubble = tutos.get('active_tuto_bubble', '')
        note('05-ACTIVE-TUTO-2', f'Bulle: "{bubble[:150]}"')
        await shot(page, '05-active-tuto-tap-instruction')

        # ─── 6. Premier tap réel ───
        await page.evaluate('document.getElementById("runner-stadium")?.click();')
        await page.wait_for_timeout(700)
        tutos = await collect_tutos(page)
        st = tutos.get('_state', {})
        note('06-FIRST-TAP', f'totalTaps={st.get("totalTaps")} gold={st.get("gold")} bulleVisible={"active_tuto_bubble" in tutos}')
        await shot(page, '06-after-first-tap')

        # Bulle après 1 tap ?
        bubble_after_tap = tutos.get('active_tuto_bubble', '')
        friction_first_tap = None
        if not bubble_after_tap:
            friction_first_tap = 'Aucun feedback bulle tuto post-1er-tap, le joueur peut être perdu'
        note('06-FEEDBACK-1TAP', f'Bulle après 1 tap: "{bubble_after_tap[:120]}"', friction=friction_first_tap)

        # 5 taps supplémentaires (step 2 attend >= 6)
        for _ in range(6):
            await page.evaluate('document.getElementById("runner-stadium")?.click();')
            await page.wait_for_timeout(120)
        await page.wait_for_timeout(700)
        tutos = await collect_tutos(page)
        note('06-AFTER-6TAPS', f'Bulle: "{tutos.get("active_tuto_bubble","")[:120]}"')
        await shot(page, '06-after-6taps')

        # Click OK / COMPRIS pour passer les steps "info" (COMBO, GOUTTES)
        for _ in range(3):
            ok = await page.evaluate('(()=>{const b=document.getElementById("tuto-next"); if(b){b.click(); return true;} return false;})()')
            if not ok: break
            await page.wait_for_timeout(600)
            tutos = await collect_tutos(page)
            note('06b-NEXT-STEP', f'Bulle: "{tutos.get("active_tuto_bubble","")[:100]}"')

        # ─── 7. km 1 (force pour gagner du temps) ───
        await page.evaluate('STATE.lapsRun = 1; STATE.gold = 200; if(typeof updateUI==="function") updateUI();')
        await page.wait_for_timeout(800)
        tutos = await collect_tutos(page)
        note('07-KM1', f'lapsRun=1, bulle="{tutos.get("active_tuto_bubble","")[:100]}" hint="{tutos.get("tuto_hint","")[:80]}"')
        await shot(page, '07-km1')

        # Continue à cliquer "tuto-next" / "CONTINUER" si présent
        for i in range(3):
            ok = await page.evaluate('(()=>{const b=document.getElementById("tuto-next"); if(b){b.click(); return true;} return false;})()')
            if not ok: break
            await page.wait_for_timeout(500)

        # ─── 8. km 3 : UNLOCK AUTO-COURSE — moment clé ───
        # Tap juste avant pour atteindre km 3 et déclencher la cinematic
        await page.evaluate('STATE.lapsRun = 2.99;')
        await page.wait_for_timeout(300)
        # Force lapsRun à 3 et déclenche l'unlock si une fonction existe
        await page.evaluate('''
            STATE.lapsRun = 3;
            STATE.gold = (STATE.gold||0) + 500;
            if(typeof updateUI === "function") updateUI();
            if(typeof showUnlockCinematic === "function") {
                try { showUnlockCinematic("auto-course"); } catch(e) {}
            }
            // Trigger end-of-lap si fonction existe
            if(typeof onLapComplete === "function") { try { onLapComplete(3); } catch(e){} }
        ''')
        await page.wait_for_timeout(1500)
        tutos = await collect_tutos(page)
        note('08-KM3-UNLOCK', f'Auto-course unlock — overlays: {[k for k in tutos.keys() if not k.startswith("_")]}')
        await shot(page, '08-km3-autocourse-unlock')

        # Y a-t-il une vraie célébration ?
        cine_visible = await page.evaluate('!!document.querySelector("#unlock-cinematic") && getComputedStyle(document.querySelector("#unlock-cinematic")).display !== "none"')
        note('08-CELEBRATION', f'Cinematic visible: {cine_visible}',
             friction=None if cine_visible else 'Pas de cinematic visible au déblocage auto-course')

        await page.wait_for_timeout(2000)
        await shot(page, '08b-km3-after-cine')

        # ─── 9. km 5 : premier coffre argent ───
        await page.evaluate('''
            STATE.lapsRun = 5;
            STATE.chests = STATE.chests || {};
            STATE.chests.silver = (STATE.chests.silver||0) + 1;
            if(typeof updateUI === "function") updateUI();
            if(typeof triggerChestDrop === "function"){ try{ triggerChestDrop("silver"); }catch(e){} }
        ''')
        await page.wait_for_timeout(1200)
        tutos = await collect_tutos(page)
        st = tutos.get('_state', {})
        note('09-KM5-CHEST', f'lapsRun=5, chestsOwned={st.get("chestsOwned")}, bulle="{tutos.get("active_tuto_bubble","")[:100]}"')
        await shot(page, '09-km5-chest-drop')

        # Tente d'ouvrir le coffre via le menu (un nouveau joueur sait-il où il est ?)
        menu_chest_visible = await page.evaluate('''(()=>{
            const el = document.querySelector('.menu-item[data-action="chests"]');
            if(!el) return {found: false};
            const cs = getComputedStyle(el);
            const unlockKm = el.dataset.unlockKm;
            return {found: true, visible: cs.display !== "none" && cs.opacity > 0.3, unlockKm};
        })()''')
        note('09-CHEST-MENU', f'Menu coffres: {menu_chest_visible}',
             friction=f'Menu Coffres caché jusqu\'à km {menu_chest_visible.get("unlockKm")} mais 1er coffre droppé à km 5' if menu_chest_visible.get('unlockKm') and int(menu_chest_visible.get('unlockKm', 0)) > 5 else None)

        # ─── 10. km 8 : haie + Vision d'Aigle débloquée ───
        await page.evaluate('''
            STATE.lapsRun = 8;
            if(typeof updateUI === "function") updateUI();
        ''')
        await page.wait_for_timeout(800)
        tutos = await collect_tutos(page)
        note('10-KM8', f'lapsRun=8, hint="{tutos.get("tuto_hint","")[:120]}"')
        await shot(page, '10-km8-hurdle-eagle')

        # Vision d'Aigle est-elle visible/accessible ?
        eagle_state = await page.evaluate('''(()=>{
            const btn = document.querySelector('.upg-btn[data-upgrade="eagleEye"]');
            if(!btn) return {found: false};
            const cs = getComputedStyle(btn);
            return {found: true, visible: cs.display !== "none" && parseFloat(cs.opacity) > 0.3, disabled: btn.disabled || btn.classList.contains("locked")};
        })()''')
        note('10-EAGLE-EYE', f'Vision Aigle bouton: {eagle_state}',
             friction='Joueur ne saurait pas que Vision Aigle existe sans ouvrir Upgrades' if eagle_state.get('visible') and not tutos.get('active_tuto_bubble') else None)

        # ─── 11. Tente d'ouvrir Upgrades + acheter ───
        upgrade_tab = await page.evaluate('''(()=>{
            const b = document.querySelector('.tab-btn[data-tab="upgrades"]');
            if(!b) return {found: false};
            b.click();
            return {found: true};
        })()''')
        await page.wait_for_timeout(700)
        note('11-OPEN-UPGRADES', f'Onglet upgrades: {upgrade_tab}')
        await shot(page, '11-upgrades-tab-open')

        # Tente d'acheter PUISSANCE (tapValue)
        buy = await page.evaluate('''(()=>{
            const b = document.querySelector('.upg-btn[data-upgrade="tapValue"]');
            if(!b) return {found: false};
            const before = STATE.upgradeTapValue || 0;
            b.click();
            return {found: true, before, after: STATE.upgradeTapValue || 0, gold: STATE.gold};
        })()''')
        await page.wait_for_timeout(500)
        note('11-BUY-PUISSANCE', f'Achat: {buy}',
             friction=None if buy.get('after', 0) > buy.get('before', -1) else 'Achat ne semble pas passer (pas de gold ? bouton caché ?)')
        await shot(page, '11-after-buy-puissance')

        # ─── 12. Tente d'ouvrir un coffre ───
        # Forcer un coffre puis essayer d'ouvrir le menu Coffres si possible
        open_chest = await page.evaluate('''(()=>{
            STATE.chests = STATE.chests || {};
            STATE.chests.bronze = (STATE.chests.bronze||0) + 2;
            STATE.chests.silver = (STATE.chests.silver||0) + 1;
            // Force le menu coffres à apparaître pour le test
            if(typeof openChestsModal === "function"){
                try{ openChestsModal(); return {modalOpened: true}; }catch(e){ return {error: String(e)}; }
            }
            return {modalOpened: false, reason: "openChestsModal absent"};
        })()''')
        await page.wait_for_timeout(900)
        note('12-OPEN-CHEST-MODAL', f'{open_chest}')
        await shot(page, '12-chests-modal')

        # Lis le contenu du modal
        chest_content = await grab_visible_text(page, '#chests-body')
        note('12-CHEST-MODAL-CONTENT', f'"{(chest_content or "")[:200]}..."',
             friction='Explications du système de coffres manquantes/cryptiques' if not chest_content or 'rareté' not in (chest_content or '').lower() else None)

        # Tente de cliquer le 1er chest-open
        clicked_chest = await page.evaluate('''(()=>{
            const b = document.querySelector('.chest-open:not(.disabled):not([disabled])');
            if(!b) return {found: false};
            b.click();
            return {found: true, label: b.textContent.trim().slice(0,40)};
        })()''')
        await page.wait_for_timeout(1500)
        note('12-CLICK-CHEST-OPEN', f'{clicked_chest}',
             friction='Aucun bouton "ouvrir" visible pour un nouveau joueur' if not clicked_chest.get('found') else None)
        await shot(page, '12b-chest-opened')

        # Ferme le modal
        await page.evaluate('document.getElementById("chests-close")?.click(); document.querySelectorAll(".modal.show").forEach(m=>m.classList.remove("show"));')
        await page.wait_for_timeout(500)

        # ─── 13. Tente d'utiliser un skill ───
        skills = await page.evaluate('''(()=>{
            const btns = [...document.querySelectorAll('.skill-btn')];
            return btns.map(b => ({
                skill: b.dataset.skill,
                ready: b.classList.contains('ready'),
                visible: getComputedStyle(b).display !== 'none' && parseFloat(getComputedStyle(b).opacity) > 0.3,
            }));
        })()''')
        note('13-SKILLS', f'Skills disponibles: {skills}')

        # Trigger un skill ready
        skill_use = await page.evaluate('''(()=>{
            const b = document.querySelector('.skill-btn.ready');
            if(!b) return {found: false};
            b.click();
            return {found: true, skill: b.dataset.skill};
        })()''')
        await page.wait_for_timeout(700)
        note('13-USE-SKILL', f'{skill_use}',
             friction='Aucun skill visible/ready → joueur ne sait pas que ça existe' if not skill_use.get('found') and not any(s.get('visible') for s in skills) else None)
        await shot(page, '13-after-skill-use')

        # ─── DUMP du journal ───
        report = {
            'errors_count': len(errors),
            'errors': errors[:5],
            'log': log,
        }
        out_json = f'{OUT}/UX-new-player-log.json'
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f'\n=== JOURNAL écrit dans {out_json} ({len(log)} events, {len(errors)} errors) ===')

        await browser.close()


asyncio.run(main())
