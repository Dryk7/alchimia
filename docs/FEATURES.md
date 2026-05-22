# FOULÉE — Features Catalog

> Liste exhaustive des features du jeu. Référence lignes pointent vers `D:/alchimia/index.html`.
> Légende status : **actif** (en prod) / **désactivé** (code présent mais NO-OP / pas wiré) / **planifié** (TODO).

---

## Gameplay core

### Tap-to-run (cœur du jeu)
Tape sur `#runner-stadium` pour faire courir le héros. Chaque tap incrémente `tapCount` (cap 100), qui décroît passivement. `tapBoost` dérivé pilote la vitesse visuelle ET la progression `lapProgress`. Crit 5%-60% double les gouttes.
- **Code** : `tapBoost()` ligne 16332, handler `pointerdown` ligne 22580 + 28356
- **Status** : actif

### Progression 100 km (chantier → stade olympique → lunar)
Le joueur progresse de 0 à 100 km, traversant 5 biomes (wasteland → rural → urban → stadium → lunar). À 100 km, ascension possible pour gagner des étoiles permanentes.
- **Code** : `BIOMES` ligne 19407, `currentBiome()` ligne 19449, `completeLap()` ligne 18902
- **Status** : actif

### Speed cap progressif
Les 3 premiers km ont des vitesses max progressives (7 → 13 → 22 → 35 km/h) pour onboarding. `speedCapByLap` dans le tick canvas.
- **Code** : ligne 24721
- **Status** : actif

### Idle progression
Le héros avance passivement même sans tap. Baseline = 4 min/km, ralentit exponentiellement (×1/1.015^laps). Premiers 3 km : full tap mode (idle quasi nul).
- **Code** : ligne 24642 (fallback in canvas tick)
- **Status** : actif

### Combo system
Taps rapides (<TAP_COMBO_WINDOW) montent le compteur combo. 4 tiers : ×1.5 (3+), ×2 (6+), ×3 (12+), ×5 (25+). Applique au gold ET au lapProgress push.
- **Code** : ligne 16336-16347 + `updateComboDisplay()` ligne 16468
- **Status** : actif

### Stamina & Tired state
Stamina baseline 1.5, baisse 0.075/sec, montée +0.14/tap. Sous 0.5 = ralentissement progressif (jusqu'à ×0.3 vitesse à stam=0.3). Skill tree node `_stNoTired` désactive l'effet.
- **Code** : ligne 16329 (bumpStamina), ligne 24713 (staminaMul)
- **Status** : actif

### Haies à sauter (style Idle Slayer)
Haies drift vers le héros (5 kinds : single, double, triple, tall, wide). Bouton SAUT pour les franchir. 3 ratés consécutifs = sanction durcie. Combo de haies sautées tracké.
- **Code** : `hurdles[]` ligne 23120, spawn/tick dans RUNNER_2D IIFE
- **Status** : actif

### Rivaux (ghosts qui défient)
Spawn périodique d'un rival qui arrive derrière. Si tu accélères au-dessus = dépassement (bonus). S'il te dépasse = perte. 5 types stylistiques.
- **Code** : `RIVAL_TYPES` ligne 23131, `rival` state ligne 23126
- **Status** : actif

### Lapin doré & Lièvre bonus
Événements rares : un lapin doré (puis lièvre au km 30+) traverse l'écran. Tap dessus = burst gold + boost vitesse temporaire.
- **Code** : `spawnRabbit()` ligne 23479, `onRabbitCaught/onHareCaught` ligne 28374
- **Status** : actif

### Saut (jump button)
Bouton dédié + détection collision avec hurdles. Apex/landing/takeoff visuels distincts.
- **Code** : `heroJumpY/heroJumpVY` ligne 23138, `sfxJump()` ligne 13447
- **Status** : actif

### NPCs progressifs (7 tiers)
Coureurs ambient dans les couloirs voisins. Distribution par km : promeneurs (km 0-2) → joggers → semi-pros → champions olympiques (km 85+) avec médaille + drapeau pays. NPCs "fromBehind" qui te doublent si inactif.
- **Code** : `NPC_TIERS` ligne 23246, `pickTierForPlayer()` ligne 23357
- **Status** : actif

### Météo dynamique
5 conditions : sunny (55%), cloudy (20%), windy (13%), rainy (8%), foggy (4%). Effets visuels (rain drops, lightning, fog gradient, wind sway). Choisie au load.
- **Code** : `pickWeather()` ligne 23147, weather state ligne 23155
- **Status** : actif

---

## Économie & progression

### Gouttes (gold)
Monnaie principale. Gagnée par tap, lap completion, team idle, daily, achievements, chests scrap.
- **Code** : `STATE.gold`, partout
- **Status** : actif

### Gemmes (premium)
Monnaie premium violette. Gagnée par daily, achievements, achetable via shop.
- **Code** : `STATE.gems`, shop modal ~ligne 17696
- **Status** : actif

### Étoiles (prestige)
Reset à 100 km contre étoiles permanentes. `calcTransmuteStars()` calcule selon fusions + paliers + achievements + gold non-dépensé.
- **Code** : `calcTransmuteStars()` ligne 12421
- **Status** : actif (legacy nom "transmute" hérité d'alchimie)

### Upgrades tap (8 upgrades Cookie Clicker style)
**Code** : `UPGRADES_TAP` ligne 16506, `buyUpgrade()` ligne 16564

| Upgrade | Base cost | Factor | Max | Unlock km | Effet |
|---|---|---|---|---|---|
| PUISSANCE (tapValue) | 80 | 1.45 | ∞ | 0 | +1 goutte/tap par lvl |
| CRIT (critChance) | 350 | 1.50 | 55 | 0 | +1% crit/lvl (cap 60%) |
| LAP BONUS | 400 | 1.45 | ∞ | 0 | Multiplie bonus fin de km |
| AUTO TAP | 2500 | 1.55 | ∞ | 0 | Taps automatiques/sec |
| ENDURANCE | 800 | 1.50 | 20 | 0 | Stamina max + decay slower |
| VISION D'AIGLE (eagleEye) | 1500 | 1.45 | 15 | 8 | Voir haies +15%/lvl plus tôt |
| VITESSE BASE (baseSpeed) | 3000 | 1.55 | 15 | 0 | ×1.10/lvl idle baseline |
| PILOTE AUTO (cruiseControl) | 50000 | 1.45 | 15 | 30 | +5% tapBoost passif (ULTIMATE) |

**Status** : actif

### Skills actifs (4, à la Clicker Heroes)
**Code** : `SKILLS` ligne 17400, `activateSkill()` ligne 17463

| Skill | Couleur | Cooldown | Durée | Unlock km | Effet |
|---|---|---|---|---|---|
| SPRINT | rouge | 240s | 30s | 0 | ×10 gouttes/tap |
| VENT (tailwind) | bleu | 360s | 60s | 5 | Cycles équipe ÷3 |
| PRIME (bounty) | or | 1800s | instant | 20 | +2h team production |
| SOUFFLE (breath) | vert | 450s | 45s | 50 | Équipe ×5 |

**Status** : actif

### Skill tree passif (22 nodes en 5 branches)
**Code** : `SKILL_TREE` ligne 21477, `SkillTree` IIFE ligne 21542
Branches : SPRINT, POWER, ENDURANCE, LUCK, TEAM. 1 point gagné par 5 km.
**Status** : actif

### Team idle (6 coureurs)
**Code** : `TEAM_RUNNERS` ligne 17945

| Runner | Base cost | Cycle | Unlock | Rôle |
|---|---|---|---|---|
| Sprinter | 8 | 1.5s | km 0 | Rapide |
| Relayeur | 80 | 4s | km 5 | Polyvalent |
| Hurdler | 800 | 8s | km 20 | Puissant |
| Marathonien | 10 000 | 18s | km 50 | Endurant |
| Pistard | 120 000 | 30s | km 100 | Synergie ×1.05/lvl team |
| Légende | 2M | 60s | saison 2 | Légendaire (le GOAT) |

Chaque runner a un **manager** achetable qui auto-collect les cycles.
**Status** : actif

### Coffres (4 raretés)
**Code** : `CHEST_TYPES` ligne 15943

| Coffre | Couleur | Weight drop | Sources |
|---|---|---|---|
| Bronze (wood) | #c87838 | 60% | 1 par km bouclé |
| Argent (iron) | #6a6a6a | 25% | Tous les 5 km |
| Or (gold) | #e8a830 | 12% | Record km/h battu |
| Légendaire | #c84030 | 3% | Cap milestone 25/50/75/100 km |

Chaque coffre roule un item via `_rollItemFromChest()`. Reveal anim + équipe/scrap choice.
**Status** : actif

### Équipement (5 slots × 5 raretés)
**Code** : `ITEM_TYPES` ligne 15469, `RARITIES` ligne 15476

| Slot | Stat | Base bonus | Multipliers raretés |
|---|---|---|---|
| Chaussures (shoes) | speed | 0.02 | commun ×1, inhabituel ×2, rare ×4, épique ×8, légendaire ×16 |
| Maillot (jersey) | goldMul | 0.03 | — |
| Bandeau (headband) | critRate | 0.005 | — |
| Chrono (watch) | xpMul | 0.03 | — |
| Brassard (wristband) | staminaMul | 0.04 | — |

**Status** : actif

### Cartes Star (deck system)
Cartes collectables avec effets passifs. Deck équipable. Effects : tap+, team+, crit+, goldAll+, tapBig (5% ×100), etc.
- **Code** : `STATE.cardsOwned/cardsDeck`, `deckBonus()`, `deckAllMul()`
- **Status** : actif

### Stades cosmétiques (5)
**Code** : `STADIUMS` ligne 19467

| Stade | Min saison | Palette |
|---|---|---|
| Municipal | 1 | rouge + vert clair |
| Olympique | 2 | rouge profond + vert |
| Coliseum | 3 | beige + or |
| Couchant | 5 | rouge couchant + or |
| Cosmique | 8 | violet + bleu nuit |

**Status** : actif

### Saison / Ascension (100 km)
À 100 km : cinématique épique → choix Sceau Mystique (1 parmi 3) → reset gold/lapsRun/team/upgrades, conserve stars/équipement/achievements.
- **Code** : `MODIFIERS` ligne 12287, `triggerEpicKm100()` ligne 16642, reset logic ligne 17143
- **Status** : actif

### 8 Sceaux Mystiques (modifiers)
**Code** : `MODIFIERS` ligne 12287
Phoenix, Frost, Hourglass, Mercury, Poverty, Adept, Thunder, Night. Boon + bane appliqués via `modifierEffect()`.
**Status** : actif

### Sanctum (legacy alchimie, 6 upgrades permanents)
**Code** : `UPGRADES` ligne 12411 (Verbum Cordis, Lapis Mater, Mercurio, Sol Aurum, Fulmen, Anima Mundi + Spiritus Iungens)
**Status** : actif (legacy code, partiellement utilisé)

### Recettes du Grand Œuvre (legacy alchimie)
**Code** : `RECIPES` ligne 11483. Catalyseurs uniques par run, reset au prestige.
**Status** : actif (legacy)

---

## Engagement & Daily

### Daily reward (cycle 7 jours)
Récompenses progressives par jour de streak.
- **Code** : `STATE.dailyLast/dailyStreak/dailyCycles`, daily modal ~ligne 17287
- **Status** : actif

### Daily quests
Quêtes rerollées chaque jour avec rewards (gouttes + gems).
- **Code** : `STATE.dailyQuests`
- **Status** : actif

### Daily challenge
Challenge spécial du jour (ex: stamina-low, no-hurdle-miss).
- **Code** : `STATE.dailyChallenge`
- **Status** : actif

### Achievements (57 hauts faits)
8 catégories : économie (5), taps (4), km (7), biomes (4), combo (4), vitesse (5), haies (8), rivaux (4), upgrades (6), level/saison/daily (8), secrets (2).
- **Code** : `ACHIEVEMENTS` array ~ligne 10250, `checkAchievements()` ~ligne 10319
- **Status** : actif

### Records locaux (leaderboard local)
5 catégories : Progression, Vitesse, Haies, Rivaux, Bonus.
- **Code** : `STATE.records`
- **Status** : actif

### Events aléatoires (legacy alchimie, 7 events)
Pluie d'Étoiles, Conjonction Astrale, Marée d'Esprit, Souffle d'Or, Comète, Nuit Profonde, Sourire de Lune.
- **Code** : `STATE.activeEvents`, events logic ~ligne 12685
- **Status** : actif (legacy)

### Médaille dorée (Golden Batches Cookie Clicker style)
Médaille apparaît toutes les 45-90s sur le stade. Tap dessus = bonus +production OU ×10 tap/30s.
- **Code** : ligne 17580+
- **Status** : actif

---

## UI / UX

### Splash intro + cinématique
Splash logo → ouverture cinématique avec ouroboros animé (legacy DA) → CTA "PRENDRE LE DÉPART".
- **Code** : `#intro` element + intro script ~ligne 8430
- **Status** : actif

### Tuto contextuel passif (10 hints, tutoV3)
Hints textuels qui apparaissent contextuellement, faded après 8s, hidden après 25s.
- **Code** : ligne 28503-28560, storage key `foulee.tutoV3`
- **Status** : actif

### ActiveTuto guidé (12 étapes)
Onboarding pris par la main avec overlay sombre + spotlight + bulle.
- **Code** : `ActiveTuto` IIFE ligne 21206, storage key `foulee.activeTutoV1`
- **Status** : actif

### Tooltips long-press (tap & hold)
Bulle d'explication contextuelle au long press. Système `.foulee-tooltip` via attributs `data-tooltip-title` / `data-tooltip`.
- **Code** : CSS ligne 31+, JS wiring
- **Status** : actif

### Menu modal (hub)
Accès aux modals : profil, daily, shop premium, saison, équipement, vestiaire, coffres, cartes, stades, runner profile, guide.
- **Code** : `.menu-item` handlers ligne 22659
- **Status** : actif

### Tabs drawer (bottom sheet)
Slide-up depuis le bas. Onglets : Upgrades, Team, Stats, Records.
- **Code** : ligne 22626
- **Status** : actif

### HUD top stats
Gold, gems, level XP, km, km/h, combo badge.
- **Code** : `#stat-gold`, `#stat-gems`, etc., `updateRunnerHUD()`, `renderStats()`
- **Status** : actif

### Skills bar (verticale flottante droite)
4 boutons skills empilés verticalement avec cooldown fill animation.
- **Code** : CSS ligne 2947+, `renderSkillsBar()` ligne 17544
- **Status** : actif

### Combo display (tiered badge)
Badge `×1.5 / ×2 / ×3 / ×5` qui scale + change couleur par tier.
- **Code** : ligne 16468
- **Status** : actif

### Floating "+X" tap pop
Popup `+gain` qui float depuis le tap location.
- **Code** : ligne 16377
- **Status** : actif

### Bubble du coureur
Pop bubble au-dessus du héros pour annonces ("LAPIN DORÉ !", "RECORD KM/H !", etc.).
- **Code** : `showRunnerBubble()` ligne 19861
- **Status** : actif

### Cinématique épique km 100
Flash blanc + godrays + sparkles + texte hero "Tu n'es plus un coureur. Tu es LE coureur." + CTA ascension.
- **Code** : `triggerEpicKm100()` ligne 16642
- **Status** : actif

### Cinématique unlock (auto-course km 3)
Pop + flash + bubble pour unlock majeurs.
- **Code** : ~ligne 16637
- **Status** : actif

### Photographer flash
Flash sporadique de photographes dans la tribune (km 70+).
- **Code** : `photographerFlash` ligne 23173
- **Status** : actif

### Mexican wave (ola)
Vague autonome qui traverse la tribune (caps km + spontanée toutes les 12-15s).
- **Code** : `olaActive/olaWavePos` ligne 23103
- **Status** : actif

### Confetti
Bursts au passage de tier, victoire rival, ascension.
- **Code** : `spawnConfettiBurst()` ligne 23193, `RUNNER_2D.spawnConfetti(n)`
- **Status** : actif

### Particules ambient (pétales, feuilles, poussière)
Selon biome : poussière en wasteland, feuilles auto en rural, etc.
- **Code** : `ambientParticles`, `leaves[]` ligne 23162+
- **Status** : actif

### Papillons (km 30+, tier 3+)
Butterflies qui virevoltent.
- **Code** : `butterflies[]` ligne 23172
- **Status** : actif

### Sweat + footprints
Gouttes de sueur au sprint, empreintes au sol qui s'estompent.
- **Code** : `spawnSweat()` ligne 23176, `spawnFootprint()` ligne 23188
- **Status** : actif

### Camera shake
Shake au tap (cap 2.5).
- **Code** : `cameraShake` ligne 23169
- **Status** : actif

### Crowd flash
Flashs photo dans la foule (km 70+).
- **Code** : `crowdFlashes[]` ligne 23111
- **Status** : actif

### Drapeaux supporters
Drapeaux fixes oscillant dans la tribune.
- **Code** : `crowdFlags` ligne 23109
- **Status** : actif

### Oiseaux & montgolfière ambient
Birds (max 3) qui volent, balloon coloré occasionnel.
- **Code** : `birds[]`, `balloon` ligne 23158-23160
- **Status** : actif

### Étoiles filantes (biome cosmic)
Shooting stars en biome lunar.
- **Code** : `shootingStars[]` ligne 23167
- **Status** : actif

---

## Audio

### BGM procédural (ProcBGM, preset 'chill')
6 voix (kick, snare, hat, bass, chord, melody) + extras (arpeggio, melody2, shaker) synthétisées en temps réel. 100 BPM, 24 bars (~57s loop), 4 sections (verse, chorus, bridge, outro).
- **Code** : `ProcBGM` IIFE ligne 13627
- **Status** : actif

### Presets BGM disponibles
- `intro` : 40s arrangement riche (20 bars / 124 BPM)
- `early` : loop 0-7 km (4 bars / 112 BPM)
- `chill` : loop 100 BPM, 24 bars (preset par défaut)
- `stadium` : km 45+ grandiose (8 bars / 88 BPM)
- **Status** : `chill` actif, autres disponibles mais pas appelés en prod

### MP3 ambient retirés (v5)
Bandes sonores `.mp3` retirées du service worker (-19 MB). Toute logique MP3 (`bgmElementFor`, `fadeAudio`, `setBgmPhase`) est NO-OP.
- **Status** : désactivé (volontairement)

### SFX procéduraux
Tap, jump, land, hurdle cleared (4 kinds), hurdle fail, footstep, speed milestone, km bell, start, sprint kick, merge, spawn, claim, deny, grand (cinématique), buy scaled.
- **Code** : ligne 13447-14620
- **Status** : actif

### Reverb par convolution
Reverb wet sur tous les blip() via `A.reverb` ConvolverNode.
- **Code** : ligne 13195-13205
- **Status** : actif

### Sprint beat tick
Drums layered qui s'intensifie pendant SPRINT skill.
- **Code** : `tickSprintBeat()` ligne 14546
- **Status** : actif

---

## Monétisation / Premium

### Shop premium (gems-based)
Pack gemmes ×2 24h, pack gouttes, pack étoiles.
- **Code** : `SHOP_ITEMS` ligne 12610, `openShopModal()` ~ligne 17680
- **Status** : actif (no IAP wiring — stub pour Play Billing)

### Starter pack offer
Proposé après le 10e tap. Si claimé : bonus de démarrage massif. Si décliné : ne plus reproposer.
- **Code** : `STATE.starterPackClaimed/Declined`, `maybeShowStarterPack()` ~ligne 17861
- **Status** : actif

### Rewarded ads
Bouton "Watch ad → +1000 gouttes" avec cooldown 1h.
- **Code** : `STATE.lastAdAt`, ad button ~ligne 17790
- **Status** : actif (stub, à brancher AdMob TWA)

### Shop boost ×2 24h
Pack premium qui double les gouttes pendant 24h. Cumulable.
- **Code** : `STATE.shopBoostX2Until`, `getShopBoostMul()` ~ligne 17768
- **Status** : actif

---

## Infrastructure

### Save auto toutes les 4s
- **Code** : `save()` ligne 20976, setInterval boot
- **Status** : actif

### CloudSave lite (IndexedDB backup)
Redondance localStorage. Restore automatique au boot si localStorage vide.
- **Code** : `CloudSave` IIFE ligne 21090
- **Status** : actif

### Export/import save shareable
Web Share API (FR clipboard fallback). Base64 encoded JSON.
- **Code** : `CloudSave.shareExport()` ligne 21128
- **Status** : actif

### Google Play Games Saved Games (stub)
Préparé pour future intégration TWA + Play Services.
- **Code** : `CloudSave.gpgsAvailable()` ligne 21149
- **Status** : planifié

### i18n FR/EN
Auto-détection `navigator.language`. 60+ chaînes traduites. Override via settings.
- **Code** : ligne 8444+, `t()`, `setLang()`, `getLang()`
- **Status** : actif (~80 chaînes secondaires restantes à traduire — cf LAUNCH-CHECKLIST.md)

### Analytics stub (Firebase-ready)
`Analytics.track(event, props)` no-op par défaut, buffer 200 events.
- **Code** : `Analytics` IIFE ~ligne 22100
- **Status** : actif (stub, à brancher Firebase via `setImpl()`)

### Service Worker offline-first
Cache `foulee-v5`. Network-first pour HTML, cache-first pour assets statiques.
- **Code** : `sw.js`
- **Status** : actif

### PWA install prompt
Capture `beforeinstallprompt`, propose install après 60s de session.
- **Code** : ligne 23012
- **Status** : actif

### Apple iOS PWA support
Meta `apple-mobile-web-app-capable`, `apple-touch-icon`.
- **Code** : ligne 11-14
- **Status** : actif

### TWA (Trusted Web Activity) pour Play Store
Config `twa-manifest.json`. Bundler via Bubblewrap.
- **Code** : `twa-manifest.json`
- **Status** : actif (prêt build)

### Accessibility (semaine 4)
- Dark mode (filter invert + hue-rotate)
- Large text (+15% root font)
- Color-blind safe (motifs ajoutés aux hurdles markers)
- **Code** : CSS ligne 100-118, `setAccessibility()` ligne 22102
- **Status** : actif

### GPU layer promotion canvas
`will-change:transform`, `translateZ(0)`, `backface-visibility:hidden` pour isoler le canvas.
- **Code** : CSS ligne 87
- **Status** : actif

### Gradient cache (rendering optim)
`_gradCache` Map pour ne pas recréer les CanvasGradient identiques chaque frame. Invalidé au resize.
- **Code** : ligne 23068
- **Status** : actif

### Debug mode (`?debug=1` ou `localStorage.fouleeDebug=1`)
Expose hooks `window.RUNNER_2D._debugMode`, `spawnHurdle()`, `forceJump()`, `spawnNpc()`, etc.
- **Code** : ligne 28434-28495
- **Status** : actif

### Privacy & légal
- `privacy-policy.html` (RGPD/COPPA/Play Store conforme)
- `terms.html` (CGU FR)
- **Status** : actif (TODO : remplacer email contact placeholder, cf LAUNCH-CHECKLIST.md)

---

## Features désactivées (code présent, non-utilisé)

### THREE.js 3D rendering
Importmap commenté en HTML. Module 3D mort en bas de page. Pivot Canvas2D définitif.
- **Code** : commentaire ligne 20-30
- **Status** : désactivé

### Bandes sonores MP3 adaptatives
HTMLAudioElement avec crossfade selon phase. Retiré au sw.js v5 pour gagner 19 MB.
- **Code** : `bgmElementFor()` ligne 13232, `fadeAudio()` 13280, `setBgmPhase()` 13281 — tous NO-OP
- **Status** : désactivé

### Tooltips legacy (modèle alchimia)
Système alternatif tooltip remplacé par `.foulee-tooltip`.
- **Status** : désactivé (CSS résiduel)

---

## Features planifiées (TODO)

- **Firebase Analytics réel** (1 ligne : `Analytics.setImpl(...)`)
- **AdMob TWA rewarded ads** (stub déjà présent)
- **Google Play Games Services Saved Games** (stub présent)
- **Traduction EN restante** (~80 chaînes secondaires)
- **2 secrets achievements** (déclencheurs cachés à wirer)
- **Photo mode / share** (capture canvas + Web Share API)

---

## Récapitulatif numérique

- **Lignes index.html** : 28 555
- **Features actives** : ~70
- **Features désactivées** (code présent) : 3
- **Features planifiées** : 6
- **Constantes data tables** : 12 (UPGRADES_TAP, SKILLS, NPC_TIERS, CHEST_TYPES, ITEM_TYPES, RARITIES, TEAM_RUNNERS, BIOMES, STADIUMS, MODIFIERS, RECIPES, SKILL_TREE)
- **IIFE modules** : 6 (ProcBGM, RUNNER_2D, ActiveTuto, CloudSave, Analytics, SkillTree)
- **Propriétés STATE** : ~95 (~75 persistées)
- **SFX procéduraux** : ~30 fonctions
- **Modals** : ~15 (menu, daily, shop, équip, vestiaire, coffres, cartes, stade picker, profile, codex, saison, modifier choice, etc.)
- **Achievements** : 57
- **Quest templates legacy** : 28+5 records
