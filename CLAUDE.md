# FOULÉE — Codebase Guide

> Document principal pour Claude Code et autres agents IA travaillant sur ce projet.
> Lis-le AVANT de toucher au code. Mis à jour 2026-05-22.

---

## Quick context

- **Single-HTML mobile idle-tap running game** ("Du chantier au stade olympique")
- **~28 555 lignes** dans `D:/alchimia/index.html` (CSS + HTML + JS, monolithique)
- **Web Audio procédural** (ProcBGM) + Canvas2D pixel art (RUNNER_2D)
- **Target** : Play Store (TWA) + PWA installable
- **Stack** : vanilla JS, zéro dépendance runtime, vanilla CSS, IIFE patterns
- **Persistance** : localStorage `alchimia.save` + backup IndexedDB (CloudSave)
- **Service worker** : `sw.js` (cache `foulee-v5`, network-first HTML, cache-first assets)
- **Langues** : FR (défaut) + EN, auto-détection via `navigator.language`, API `t()`/`setLang()`/`getLang()`
- **Branding interne** : nom legacy `alchimia` dans la save key et certaines variables (`STATE.alchLevel`, `STATE.alchXp`). Le jeu s'appelle **FOULÉE** côté UX.

---

## Architecture

### Game state — `STATE` global

Défini une fois à la ligne **12166**, exposé via `window.STATE = STATE`. Mutation directe partout dans le fichier. Pas de framework, pas de proxy, pas de réactivité. Le re-render manuel via `renderStats()`, `updateRunnerHUD()`, `renderTeam()`, etc.

```js
const STATE = {
  essence: 30, gold: 0,
  alchLevel: 1, alchXp: 0,         // niveau joueur (legacy nom)
  lapsRun: 0, lapProgress: 0,      // km bouclés / progression du km en cours
  runnerStamina: 1.5,
  upgradeTapValue: 0, upgradeCritChance: 0, upgradeLapBonus: 0,
  upgradeAutoTap: 0, upgradeEndurance: 0, upgradeBaseSpeed: 0,
  upgradeCruiseControl: 0, upgradeEagleEye: 0,
  team: {},                        // { sprinter:{level,cycle,mgr}, ... }
  equipment: {},                   // { shoes:{typeId,rarityId,level,bonus}, ... }
  chests: { wood, iron, gold, legendary },
  skills: { unlocked, pointsSpent },
  records: {}, achievements: {},
  // ... 60+ autres champs (cf docs/STATE-SCHEMA.md)
};
```

### Rendering — `RUNNER_2D` IIFE (~5500 lignes)

IIFE qui s'enregistre dans `window.RUNNER_2D` ligne **28445**. Pilote le canvas `#runner-canvas` en parallax side-scroll.

- **Tick loop** : `requestAnimationFrame` → `tick(dt)` (60 FPS, DPR cap 2)
- **Scènes** : `npcs[]`, `milestones[]`, `hurdles[]`, `rabbit`, `hare`, `rival`, `balloon`, `birds[]`, `confetti[]`, `crowdFlashes[]`, etc.
- **Pipeline rendu** : sky → mountains → stadium tribune → track → NPCs (lanes) → hero → hurdles → particles → weather overlay
- **Couloirs (lanes)** : 5 couloirs, le héros occupe `HERO_LANE_IDX = 2`, NPCs spawnent dans 0/1/3/4
- **API publique** (prod) :
  - `resize()`, `spawnConfetti(count)`, `spawnRabbit()`, `spawnHare()`
  - `getWeather()`, `setWeather(w)`, `spawnBird()`, `spawnBalloon()`
  - `cinematicMode` (flag pour slow-mo)
- **API debug** (gated `?debug=1` ou `localStorage.fouleeDebug='1'`) : `getHurdles()`, `spawnHurdle()`, `forceJump()`, `spawnNpc(tier)`, etc.

### Audio — `ProcBGM` IIFE (~900 lignes)

Synthèse procédurale 100% Web Audio. Plus aucun MP3 (retirés en v5 du service worker, -19 MB).

- **Définie** ligne **13627**, exposée `window.ProcBGM`
- **4 presets** : `intro` (40s arrangement), `early` (loop 0-7 km), `chill` (loop 100 BPM, 6 sections), `stadium` (km 45+ orchestral)
- **6 voix** : kick, snare, hi-hat, bass (detuned), chord pad, melody (saw), arpeggio
- **Preset actuellement actif en jeu** : `chill` (utilisé en permanence — `syncBgmToBiome` route tout vers chill)
- **API** : `ProcBGM.play(preset, vol)`, `ProcBGM.stop()`, `ProcBGM.isPlaying()`, `ProcBGM.currentPreset()`

### SFX — `blip()` + helpers procéduraux

- `blip(freq, dur, type, vol, wet)` ligne **13392** — primitive OSC + gain + reverb par convolution
- Helpers spécialisés : `sfxJump()`, `sfxLand()`, `sfxHurdleCleared(combo)`, `sfxHurdleByKind()`, `sfxHurdleFail()`, `sfxFootstep()`, `sfxSpeedMilestone(lvl)`, `sfxKmBell()`, `sfxStart()`, `sfxSprintKick()`, `sfxMerge()`, `sfxSpawn()`, `sfxClaim()`, `sfxDeny()`, `sfxGrand()`, `sfxBuyScaled()`
- AudioContext partagé : `A.ctx` (objet `A` ligne 13195)

### Upgrades / Skills / NPCs / Chests / Team

| Système | Constant | Ligne | Description |
|---|---|---|---|
| Upgrades tap | `UPGRADES_TAP` | 16506 | 8 upgrades : tapValue, critChance, lapBonus, autoTap, endurance, eagleEye, baseSpeed, cruiseControl |
| Skills actifs | `SKILLS` | 17400 | 4 skills à cooldown : sprint, tailwind, bounty, breath |
| Skill tree passif | `SKILL_TREE` | 21477 | 22 nodes en 5 branches (sprint/power/endurance/luck/team) |
| NPCs | `NPC_TIERS` | 23246 | 7 tiers (promeneur → champion olympique), distribution par km |
| Coffres | `CHEST_TYPES` | 15943 | 4 raretés (wood/iron/gold/legendary) avec rarityWeights |
| Équipement | `ITEM_TYPES` + `RARITIES` | 15469/15476 | 5 slots × 5 raretés (commun → légendaire) |
| Team idle | `TEAM_RUNNERS` | 17945 | 6 runners (sprinter → légende), cycles + managers |
| Biomes | `BIOMES` | 19407 | 5 ambiances : wasteland/rural/urban/stadium/lunar |
| Stades cosmétiques | `STADIUMS` | 19467 | 5 stades unlockables par saison |
| Sceaux | `MODIFIERS` | 12287 | 8 modifiers de prestige (boon + bane) |
| Recettes | `RECIPES` | 11483 | Catalyseurs (legacy système alchimie) |

### Tuto guidé — `ActiveTuto` IIFE

- Ligne **21206**, exposé `window.ActiveTuto`
- 12 étapes scriptées avec overlay sombre + spotlight + bulle + watcher (state poll ou event)
- Storage key : `foulee.activeTutoV1` (valeurs : `done`, `skipped`)
- Tuto hint passif (10 messages textuels) : `foulee.tutoV3`

### Save / Load

- `save()` ligne **20976** : whitelist explicite des champs persistés (>90 props) → JSON → `localStorage.setItem("alchimia.save", json)` + `CloudSave.backup(json)` parallèle (IndexedDB store `foulee-save/saves/main`)
- `load()` ligne **22172** : `JSON.parse` + assignation `??` default pour chaque champ
- Auto-save toutes les 4s (background interval)
- Restore depuis IndexedDB au boot si localStorage vide (browser cleanup)
- Export/import save : `CloudSave.shareExport()` (Web Share API + clipboard fallback, base64 encoded JSON)

### Analytics — `Analytics` IIFE

- No-op par défaut. `Analytics.track(event, props)` push dans buffer 200 events
- 11 events wirés : `session_start`, `km_reached`, `upgrade_bought`, `hurdle_cleared`, `rival_won`, etc.
- `Analytics.setImpl(...)` pour brancher Firebase plus tard (1 ligne)

---

## Conventions

- **`STATE.alchLevel`** = niveau du joueur (nom legacy "alchimia", PAS un niveau d'alchimie — c'est le level XP global)
- **`STATE.alchXp`** = XP cumulée (idem, nom legacy)
- **`STATE.lapsRun`** = km parcourus (jamais "laps" dans la doc UX, toujours "km")
- **`STATE.lapProgress`** = progression 0..1 du km en cours
- **`STATE.gold`** = "gouttes" / "méd(ailles)" côté UX (jamais "or" en texte FR)
- **`STATE.gems`** = monnaie premium ("gemmes" violet)
- **`STATE.essence`** = ressource legacy alchimie (toujours présente mais non-utilisée gameplay actuel)
- **`STATE.upgradeXxx`** (lvl 0+) = niveau de l'upgrade Xxx (tapValue, critChance, etc.)
- **`displayKmh`** = vitesse km/h smoothée affichée (lerp 70/30 chaque frame, cap 35 km/h)
- **`tapBoost`** = `(tapCount / 100) * 2` dans `[0, 2]`, dérivé du tapCount (50 taps actifs = vitesse max)
- **`tapCount`** = compteur 0-100 qui décroît passivement (chaque tap +2)
- **`decorScroll`** = pixels parcourus accumulés (jamais `t * speed` — sinon décor saute)
- **`heroLegPhase`** = accumulateur phase animation jambes (jamais recalculé via `t * pace`)
- **`heroBobPhase`** = idem pour bob vertical
- **`window.RUNNER_2D`** vs `RUNNER_2D` local : toujours préférer `window.RUNNER_2D?.method` depuis l'extérieur de l'IIFE
- **Naming i18n** : `t('upg_tapValue')` via `data-i18n="upg_tapValue"` ou call direct. Fallback FR si i18n pas chargé.
- **Pas d'emoji dans le code source** côté game logic (les emoji `''` dans `CHEST_TYPES` / `ITEM_TYPES` sont volontairement vides → remplacés par SVG inline ailleurs)

---

## How to add a new feature

1. **Trouve la bonne section** dans `index.html` (sépare CSS / HTML / JS — les 3 sont dans le même fichier mais avec balises `<style>` / `<body>` / `<script>` distincts)
2. **Lis le code existant similaire** avant de coder le nouveau. Le projet a 10+ patterns récurrents (cf `docs/ARCHITECTURE.md`)
3. **Réutilise les helpers** : `blip()`, `vibrate()`, `particles()`, `floating()`, `showRunnerBubble()`, `fmtBigNumber()`, `t()`
4. **Persiste si besoin** : ajoute le champ dans `save()` (~ligne 20985) ET `load()` (~ligne 22176) — TOUJOURS les deux
5. **Test local** :
   ```sh
   python -m http.server 8770 --directory D:/alchimia
   # → http://localhost:8770
   ```
6. **0 console errors required** au boot et en gameplay
7. **Mode debug** : `?debug=1` ou `localStorage.setItem('fouleeDebug','1')` puis reload, expose hooks `window.RUNNER_2D.spawnHurdle()` etc.

---

## Common patterns

1. **IIFE module + window expose** :
   ```js
   const X = (() => { ... return { api1, api2 }; })();
   if(typeof window !== 'undefined') window.X = X;
   ```
2. **Lazy state init** : `if(!STATE.foo) STATE.foo = {};` (jamais d'assertion, toujours default)
3. **Mutation directe + re-render explicite** : `STATE.gold += gain; renderStats();`
4. **Cooldown via timestamp** : `if(now - STATE.lastX < COOLDOWN) return;`
5. **localStorage flag avec key namespacée** : `localStorage.getItem('foulee.tutoV3')`
6. **SVG inline pour icônes** : `const ICO = '<svg viewBox="..." width="24" height="24">...</svg>'`
7. **Pattern audio** : `if(A?.ctx){ blip(freq,dur,type,vol,wet); setTimeout(()=>blip(...), 80); }`
8. **Vibration optionnelle** : `vibrate([15, 20, 15])` (la fonction guard `STATE.vibrationEnabled === false`)
9. **Multiplicateurs composés** : `gain = base * comboMul * tapMul * eventMul * equipMul * cardMul * mapMul * skillMul * saisonMul` (lis `tapBoost` ligne 16363 pour l'exemple canonique)
10. **Modal show/hide** : `document.getElementById('xxx-modal')?.classList.add('show')` + handler close via `bindModalClose(id, closeBtnId)`

---

## Pitfalls

- **Concurrent edits** : ce fichier de 28k lignes peut être modifié par plusieurs agents en parallèle. Utilise les outils d'édition atomiques (Edit avec `old_string` unique). Si tu fais un Write complet, tu écrases potentiellement le travail d'un autre agent.
- **Le module THREE.js est mort** : l'importmap est désactivé en commentaire ligne 21. Ne pas l'activer — le pivot Canvas2D est définitif.
- **Plus aucun MP3** : depuis sw.js v5, on a retiré les bandes sonores `.mp3`. Toute référence à `bgmElementFor()`, `fadeAudio()`, `setBgmPhase()` est NO-OP. La BGM passe exclusivement par `ProcBGM`.
- **`lapsRun` peut être 100+** : à 100 km, le chapitre 2 (lunar) se débloque, et `currentBiome()` retourne `lunar`. Ne pas assumer un cap.
- **Sauvegarde legacy** : la save key est `alchimia.save` (jamais renommé pour ne pas casser les sauvegardes des joueurs early access). Idem pour `STATE.alchLevel` / `STATE.alchXp`.
- **Multi-source de vérité de la vitesse** : il y a `displayKmh` (UI), `speed`/`pace` (anim canvas), `runnerBaseSpeed()` (logique upgrades). Modifier l'un sans les autres → desync visuel.
- **Tuto contextuel ≠ Tuto guidé** : 2 systèmes distincts (`tutoV3` 10 hints passifs vs `ActiveTuto` 12 étapes prises par la main). Ne pas confondre.
- **Le bouton `#boost-btn` est legacy hidden** : le vrai tap zone est `#runner-stadium`. Les 2 sont wirés à `tapBoost(e)` pour rétrocompat.
- **`pointerdown` ≠ `click`** : on n'écoute QUE `pointerdown` sur le stade (sinon double-event → désync 50-150ms). Cf ligne 28354 commentaire explicatif.
- **DPR cap 2** : sinon perfs catastrophiques sur écrans 3x retina. Cf `Math.min(window.devicePixelRatio || 1, 2)` dans `resize()`.
- **`window.STATE` peut être `undefined`** dans certains contextes du module IIFE → toujours `window.STATE?.lapsRun || 0`.

---

## Fichiers liés

- `README.md` — pitch public + screenshots + lancement local
- `docs/ARCHITECTURE.md` — diagrammes ASCII + flows détaillés + 10 patterns
- `docs/STATE-SCHEMA.md` — toutes les props `STATE.*` (tableau exhaustif)
- `docs/FEATURES.md` — toutes les features avec localisation lignes
- `LAUNCH-CHECKLIST.md` — état production Play Store
- `manifest.json` — manifeste PWA
- `sw.js` — service worker (cache `foulee-v5`)
- `twa-manifest.json` — config TWA pour Play Store
