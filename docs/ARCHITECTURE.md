# FOULÉE — Architecture

> Document architecture détaillé. Lis `CLAUDE.md` d'abord pour les conventions.
> Toutes les références de lignes pointent vers `D:/alchimia/index.html`.

---

## 1. Vue d'ensemble — Composants principaux

```
┌─────────────────────────────────────────────────────────────────────┐
│                     D:/alchimia/index.html (28 555 LOC)             │
│                                                                     │
│  <head>                                                             │
│   ├─ meta PWA (manifest, theme-color #c84030, apple-touch)          │
│   ├─ <style> ~7000 lignes CSS                                       │
│   └─ Google Fonts (Nunito, Caveat, VT323)                           │
│                                                                     │
│  <body>                                                             │
│   ├─ #intro             splash + ouverture cinématique              │
│   ├─ #stage                                                         │
│   │   ├─ HUD top        stats (gold, gems, km, kmh)                 │
│   │   ├─ #runner-stadium  <— ZONE TAP PRINCIPALE                    │
│   │   │   ├─ <canvas id="runner-canvas">  ← rendu RUNNER_2D         │
│   │   │   └─ #skills-bar  4 skills actifs (Clicker Heroes style)    │
│   │   ├─ Boutons modaux  (Menu, Profil, Daily, Boutique, ...)       │
│   │   └─ Tabs drawer     Upgrades / Team / Stats / Records          │
│   └─ Modals               (menu, daily, shop, stadium picker, ...)  │
│                                                                     │
│  <script> ~16 000 lignes JS organisées en sections :                │
│   ├─ i18n (FR/EN)              ligne 8444                           │
│   ├─ alchLevel / XP            ligne 9965                           │
│   ├─ RECIPES (legacy)          ligne 11483                          │
│   ├─ STATE global              ligne 12166  ← single source of truth│
│   ├─ MODIFIERS (sceaux)        ligne 12287                          │
│   ├─ UPGRADES (prestige)       ligne 12411                          │
│   ├─ Audio A.ctx + helpers     ligne 13195                          │
│   ├─ blip() SFX primitive      ligne 13392                          │
│   ├─ ProcBGM IIFE              ligne 13627                          │
│   ├─ ITEM_TYPES / RARITIES     ligne 15469                          │
│   ├─ CHEST_TYPES               ligne 15943                          │
│   ├─ tapBoost() main game loop ligne 16332                          │
│   ├─ UPGRADES_TAP              ligne 16506                          │
│   ├─ SKILLS (actifs)           ligne 17400                          │
│   ├─ TEAM_RUNNERS              ligne 17945                          │
│   ├─ BIOMES + STADIUMS         ligne 19407 / 19467                  │
│   ├─ save() / load()           ligne 20976 / 22172                  │
│   ├─ CloudSave IIFE            ligne 21090                          │
│   ├─ ActiveTuto IIFE           ligne 21206                          │
│   ├─ SKILL_TREE                ligne 21477                          │
│   ├─ Analytics IIFE            ligne ~22100                         │
│   ├─ DOM wiring + handlers     ligne ~22570                         │
│   └─ RUNNER_2D IIFE (canvas)   ligne 23056 → 28496                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Flow d'un tap (DOM event → render canvas)

```
1. USER taps #runner-stadium
   │
   ▼
2. EVENT: pointerdown captured (ligne 22580 + 28356)
   │
   ├─ Handler #1 (ligne 22580) → tapBoost(e)   ← GAIN GOLD + COMBO + LAP PROGRESS
   │   │
   │   ├─ Check rabbit/hare hit zones first (capture phase, 28326)
   │   │
   │   ├─ tapBoost() ligne 16332 :
   │   │  ├─ Cooldown check (TAP_COOLDOWN_MS)
   │   │  ├─ _comboCount++ ou reset si > TAP_COMBO_WINDOW
   │   │  ├─ bumpStamina(0.14 + _comboCount * 0.005)
   │   │  ├─ COMPOSE multipliers :
   │   │  │   gain = (1 + STATE.upgradeTapValue)
   │   │  │        * comboMul (1× → 5×)
   │   │  │        * tapMul (skill tree _stTapMul)
   │   │  │        * shopMul (boost premium x2 24h)
   │   │  │        * eventTapMul + eventGoldMul
   │   │  │        * skillSprintTapMul (×10 si SPRINT actif)
   │   │  │        * (1 + equipBonus('goldMul'))
   │   │  │        * (1 + deckBonus('tap') + deckBonus('goldAll'))
   │   │  │        * deckAllMul
   │   │  │        * mapStadiumTapMul (modifier stade)
   │   │  │        * saisonGoldMul
   │   │  │        * bigBangBonus (×100 si proc 5%)
   │   │  ├─ Crit roll : 0.05 + lvl*0.01 + equipCrit + cardCrit, cap 60%
   │   │  ├─ STATE.gold += gain (×5 si crit)
   │   │  ├─ STATE.totalGoldEarned += gain
   │   │  ├─ DOM : tap-pop "+X" floating
   │   │  ├─ blip() SFX (sine G5 normal, D6 crit)
   │   │  ├─ vibrate(5 ou [15,20,15] crit)
   │   │  ├─ STATE.lapProgress += tapPush * (crit ? 2 : 1)
   │   │  │   tapPush = (0.0020 + upgradeTapValue * 0.0003) * starterMul * pushComboMul
   │   │  │   starterMul = 2.0 si lapsRun < 3 (onboarding)
   │   │  ├─ if(lapProgress >= 1) completeLap()
   │   │  ├─ STATE.totalTaps++
   │   │  └─ renderStats() + updateTapStrip() + updateRunnerHUD()
   │   │
   │   └─ DOM ripple : --tap-x, --tap-y → CSS animation stadium-tapped
   │
   └─ Handler #2 (ligne 28356, in RUNNER_2D IIFE) :  ← VITESSE VISUELLE
       tapCount = min(100, tapCount + 2)            (50 taps = max)
       lastTapTime = performance.now()
       heroDashX += 4 (cap 10)
       heroDashBob += 2 (cap 3.5)
       cameraShake += 0.8 (cap 2.5)
       crowdHype += 4 (cap 100)
       crowdHypeFlash = 1

3. NEXT FRAME (tick loop ~60 FPS, ligne 28430 tickRAF) :
   │
   ▼
   tick(dt) calcule :
     ├─ tapCount *= 0.985    (décroissance passive)
     ├─ tapBoost = (tapCount / 100) * 2
     ├─ tapBoost = max(cruiseFloor, tapBoost)   ← cruiseControl floor
     ├─ window._tapBoostForMusic = min(1, tapBoost / 2)
     │
     ├─ Idle progression : STATE.lapProgress += baseIdleProgressPerSec * dt * baseSpeedMul
     │   (ralentit exponentiellement avec laps : difficulty = 1/pow(1.015, laps-3))
     │
     ├─ speedCapByLap = 0.10 → 0.30 → 0.60 → 1.0 (km 0 → 1 → 2 → 3+)
     ├─ speed = visualBaseline + tapBoost * 0.8 * speedCapByLap * slowmo * staminaMul
     ├─ pace  = visualBaseline + tapBoost * 1.0 * speedCapByLap
     ├─ targetKmh = 4 * visualBaseline + tapBoost * 15.5 * speedCapByLap
     ├─ displayKmh = displayKmh * 0.70 + targetKmh * 0.30   ← LERP
     ├─ displayKmh = clamp(displayKmh, 0, 35)
     │
     ├─ decorScroll += pixelsThisFrame   (PIXELS, basé km/h réel)
     ├─ heroLegPhase += pace * dtMul
     ├─ heroBobPhase += pace * dtMul
     │
     ├─ Update NPCs (positions, lanes, dépassements)
     ├─ Update hurdles (drift vers hero, hit detect)
     ├─ Update rabbit / hare / rival / balloon / birds
     ├─ Update particles (confetti, sweat, footprints, butterflies, leaves)
     ├─ Update weather (rain, lightning, fog, wind)
     │
     ▼
   draw() pipeline (ordre Z) :
     1. clear canvas
     2. drawSky(weather, palette, biome)
     3. drawMountains(parallax slow)
     4. drawStadium(tribune, projectors, flags, mexican wave)
     5. drawTrack(lanes, lines, distance markers)
     6. drawNpcs(sorted by Y depth)
     7. drawHero(skin, equipment, dash, jump, leg phase, bob)
     8. drawHurdles(incoming + cleared)
     9. drawRabbit/Hare/Rival overlays
    10. drawParticles
    11. drawWeatherOverlay (rain drops, lightning flash, fog gradient)
    12. drawHUD overlays (combo wave indicator)
```

---

## 3. Flow du save (STATE → JSON → localStorage + IndexedDB)

```
USER ACTION (every 4s autosave, or on cinematic / unlock / quit)
  │
  ▼
save()                                    [ligne 20976]
  ├─ STATE._resetting check                (bail if mid-reset)
  ├─ _snapshotCurrentStadium()             (save progression per stadium)
  ├─ Update STATE.sessionMs, totalPlayMs, lastSaveTime
  │
  ├─ Build WHITELIST snapshot object `s` :
  │   essence, gold, grid, totals, quests,
  │   alchLevel, alchXp, lapsRun, lapProgress, runnerStamina,
  │   upgradeTapValue, upgradeCritChance, upgradeLapBonus,
  │   upgradeAutoTap, upgradeEndurance, upgradeBaseSpeed, upgradeCruiseControl,
  │   team, equipment, chests, skills,
  │   stars, totalStars, ascensions, upgrades, recipes, activeModifierId,
  │   codexUnlocks, masterQuestDone, achievements,
  │   ownedSkins, selectedSkinId, records,
  │   skillsLastUsed, skillSprintUntil, skillTailwindUntil, skillBreathUntil,
  │   dailyQuests, dailyLast, dailyStreak, dailyCycles,
  │   selectedStadiumId, currentStadiumId, stadiumProgress,
  │   cardsOwned, cardsDeck,
  │   bestKmh, firstKmRewarded, _autoCourseUnlocked,
  │   totalGoldEarned, hurdlesCleared, bestHurdleStreak,
  │   triplesCleared, tallsCleared, widesCleared,
  │   rivalsWon, rivalsLost, bestRivalStreak,
  │   totalUpgradesBought, rabbitsCaught, haresCaught,
  │   dailyChallenge, npcOvertakeCount,
  │   gems, shopBoostX2Until, lastAdAt,
  │   starterPackClaimed, starterPackDeclined,
  │   ... (~90 fields total)
  │
  ├─ const json = JSON.stringify(s)
  │
  ├─ localStorage.setItem("alchimia.save", json)   ← MAIN SAVE
  │
  └─ CloudSave.backup(json) (parallèle, async)
       │
       ▼
     IndexedDB :
       db = 'foulee-save'
       store = 'saves'
       key = 'main'
       value = { json, ts: Date.now() }

────────────────────────────────────────────────
LOAD (au boot) :                          [ligne 22172]

  if(localStorage.getItem('alchimia.save')) :
     load() → JSON.parse → field-by-field assign with `??` defaults
  else :
     CloudSave.restore() (depuis IndexedDB)
       → si trouvé : localStorage.setItem('alchimia.save', rec.json)
       → puis load()

────────────────────────────────────────────────
EXPORT shareable :

  CloudSave.shareExport() :
    raw = localStorage.getItem('alchimia.save')
    b64 = btoa(unescape(encodeURIComponent(raw)))
    navigator.share({ text: b64 }) || navigator.clipboard.writeText(b64)
```

---

## 4. Flow de l'audio (action → blip/SFX → A.ctx → speaker)

```
GAME EVENT (tap, hurdle cleared, km bell, ...)
  │
  ▼
sfxXxx() helper                           [ligne 13447-14620]
  │
  ▼
blip(freq, dur, type, vol, wet)            [ligne 13392]
  ├─ if(STATE.audio === false) return
  ├─ if(!A.ctx) return
  │
  ├─ Create OscillatorNode (type: sine/triangle/square/sawtooth)
  ├─ Create GainNode (envelope ADSR via gain.setValueAtTime / linearRampToValueAtTime)
  ├─ Create DelayNode + GainNode for reverb wet (via A.reverb)
  │
  ├─ Connect : osc → gain → A.master (dry) + (gain → A.reverb → A.master) (wet)
  │
  ├─ osc.start(now)
  └─ osc.stop(now + dur)

────────────────────────────────────────────────
BGM (procédurale, ProcBGM IIFE)            [ligne 13627]

ProcBGM.play(preset, vol)
  │
  ▼
_loop() à chaque step (16e note, BPM-driven via setTimeout récursif) :
  │
  ├─ For each voice (kick, snare, hat, clap, bass, melody, chord, arpeggio, melody2, shaker) :
  │    pattern = preset[voice]
  │    note = pattern[step % pattern.length]
  │    if(note !== '-' && note !== '.') :
  │       voiceImpl(note, ...)  ← OscillatorNode dédié par voix
  │
  ├─ step++
  └─ setTimeout(_loop, stepMs)   (stepMs = 60000 / bpm / 4)

────────────────────────────────────────────────
ADAPTIVE BGM (suit le biome) :

syncBgmToBiome()                           [ligne ~13260]
  ├─ ROUTE TOUT vers preset 'chill' (le seul utilisé en prod actuellement)
  ├─ if(ProcBGM.currentPreset() !== 'chill') :
  │      ProcBGM.play('chill', userVolume)
  │
  └─ NB : 'intro', 'early', 'stadium' restent disponibles mais pas appelés
         (fallback si pivot DA future)
```

---

## 5. Dix patterns récurrents

### Pattern 1 — IIFE module + window expose

Utilisé pour `ProcBGM`, `RUNNER_2D`, `CloudSave`, `ActiveTuto`, `Analytics`, `SkillTree`.

```js
// Ligne 13627 (ProcBGM), 21090 (CloudSave), 21206 (ActiveTuto), etc.
const X = (() => {
  // private state
  const private1 = ...;
  function _internalHelper() { ... }
  return { publicMethod1, publicMethod2 };
})();
if(typeof window !== 'undefined') window.X = X;
```

### Pattern 2 — Lazy state init avec default fallback

```js
// Partout dans le code, ex ligne 15968
if(!STATE.chests) STATE.chests = { wood:0, iron:0, gold:0, legendary:0 };
for(const c of CHEST_TYPES) if(typeof STATE.chests[c.id] !== 'number') STATE.chests[c.id] = 0;
```

### Pattern 3 — Multiplicateurs composés (game balance)

```js
// Ligne 16363 (canonique dans tapBoost)
const gain = base * comboMul * tapMul * shopMul * eTapMul * eGoldMul
           * skillTap * equipMul * cardTap * cardAll * bigBangBonus
           * mapTapMul * saisonGoldMul;
```

### Pattern 4 — Cooldown via timestamp Date.now()

```js
// Ligne 16334 (tap cooldown), ligne 17458 (skills)
function skillCooldownRemaining(s){
  const last = (STATE.skillsLastUsed && STATE.skillsLastUsed[s.id]) || 0;
  const ready = last + s.cooldown * 1000;
  return Math.max(0, ready - Date.now());
}
```

### Pattern 5 — Modal show/hide

```js
// Ex ligne 16166
function openChestsModal(){
  if(typeof renderChestsModal === 'function') renderChestsModal();
  document.getElementById('chests-modal')?.classList.add('show');
}
bindModalClose('chests-modal', 'chests-close');
```

### Pattern 6 — SVG inline pour icônes

```js
// Ex ligne 17390 (SKILL_SVG), ligne 16177 (chest SVG)
const ICO = '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">'
          + '<path d="M..."/></svg>';
button.innerHTML = ICO + '<span>' + label + '</span>';
```

### Pattern 7 — Audio layered avec setTimeout

```js
// Ex ligne 16073 (chest open), ligne 17473 (skill activate)
if(A?.ctx){
  blip(440, .15, "triangle", .26, .6);
  setTimeout(()=>blip(660, .15, "triangle", .26, .65), 200);
  setTimeout(()=>blip(990, .2, "sine", .26, .7), 400);
}
```

### Pattern 8 — DOM event delegation par data-attribute

```js
// Ex ligne 22609 (upgrades), ligne 16199 (chest open buttons)
document.querySelectorAll('.upg-btn').forEach(btn => {
  btn.addEventListener('click', e => {
    const id = btn.dataset.upgrade;
    if(id && typeof buyUpgrade === 'function') buyUpgrade(id);
  });
});
```

### Pattern 9 — Floating "+X" / popup notifications

```js
// Ex ligne 16377 (tap gain pop)
const pop = document.createElement('div');
pop.className = 'tap-pop' + (isCrit ? ' crit' : '');
pop.textContent = '+' + fmtBigNumber(gain);
pop.style.left = (evX + (Math.random()-.5)*20) + 'px';
pop.style.top = evY + 'px';
document.body.appendChild(pop);
setTimeout(() => pop.remove(), isCrit ? 1250 : 950);
```

### Pattern 10 — i18n avec fallback FR

```js
// Ligne 8660
function t(key, vars){ /* lookup _dict[lang][key] || _dict.fr[key] || key */ }

// Usage ligne 16555
function upgradeName(id){
  const u = UPGRADES_TAP[id]; if(!u) return id;
  return (typeof t === 'function' && u.nameKey) ? t(u.nameKey) : (u.name || id);
}

// DOM auto-binding
document.querySelectorAll('[data-i18n]').forEach(el => {
  el.textContent = t(el.getAttribute('data-i18n'));
});
```

---

## 6. Boot sequence (DOMContentLoaded → playable)

```
1. <head> parse : style, fonts, manifest, theme-color
2. <body> parse : intro splash visible (#intro), stage caché
3. <script> top-level :
   ├─ const STATE = {...}  ← initialized with defaults
   ├─ window.STATE = STATE
   ├─ All const tables built (NPC_TIERS, CHEST_TYPES, UPGRADES_TAP, SKILLS, etc.)
   ├─ All function defs (no execution yet)
   └─ IIFE modules executed → window.ProcBGM, window.RUNNER_2D (canvas), window.ActiveTuto, etc.
4. DOMContentLoaded :
   ├─ CloudSave.restore() (si localStorage vide)
   ├─ load() ← hydrate STATE depuis localStorage
   ├─ rebuildQuests() / applyUpgrades() / applyProgressiveDisclosure()
   ├─ Wire all DOM handlers (pointerdown on stadium, click on upg-btn, tab btns, etc.)
   ├─ Show #intro splash 1500ms
   ├─ ProcBGM.play('intro', 0.55) si premier start, sinon 'chill'
   └─ User taps START → #intro fades → main loop active
5. Tick loops :
   ├─ RUNNER_2D : requestAnimationFrame (60 FPS render)
   ├─ tickRunnerLap : setInterval ~16ms (idle progression — legacy, partially deprecated)
   ├─ tickSkills : intégré au RAF
   └─ save() : setInterval 4000ms
```

---

## 7. Communication entre modules

- **STATE est la source de vérité** : tous les modules y lisent et y écrivent.
- **window.STATE** est lu par `RUNNER_2D` (IIFE séparé) → couplage faible mais accès global
- **Pas d'event bus** — re-render explicite après mutation (`renderStats()`, `updateTapStrip()`, `renderTeam()`, etc.)
- **Analytics** : single-direction, modules appellent `Analytics.track(event, props)`
- **i18n** : modules appellent `t(key)` (fallback FR si non chargé)
- **Audio** : modules appellent `blip()` ou `sfxXxx()` qui guard sur `A?.ctx`
- **Hooks debug** exposés sur `window.RUNNER_2D` UNIQUEMENT en mode debug (`?debug=1`)
