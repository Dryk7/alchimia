# FOULÉE — STATE Schema

> Référence exhaustive des propriétés `STATE.*`. Source : déclaration ligne 12166 + tous les `STATE.xxx = ...` du fichier + whitelist `save()` ligne 20985.
> Colonne **Persisté** : ✓ = inclus dans `save()` et hydraté par `load()` / ✗ = runtime-only / (m) = persisté indirectement via migration.

---

## Économie & ressources

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `gold` | number | 0 | Monnaie principale ("gouttes" / "médailles" côté UX). Gagnée par tap, lap completion, team idle, quêtes, chests. | ✓ |
| `essence` | number | 30 | Ressource legacy alchimie. Plus utilisée gameplay actif mais persistée. | ✓ |
| `gems` | number | 0 | Monnaie premium ("gemmes"). Gagnée par daily, achievements, achetable via shop. Sert à acheter boosts/packs. | ✓ |
| `stars` | number | 0 | Étoiles permanentes (prestige). Gagnées par ascension à 100 km. | ✓ |
| `totalStars` | number | 0 | Lifetime stars (somme historique). | ✓ |
| `totalGoldEarned` | number | 0 | Compteur cumulatif gouttes gagnées (pour achievements). | ✓ |

## Progression coureur

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `alchLevel` | number | 1 | Niveau XP global du joueur (nom legacy "alchimia"). | ✓ |
| `alchXp` | number | 0 | XP cumulée vers le niveau suivant. | ✓ |
| `lapsRun` | number | 0 | Km bouclés (entiers). Au-delà de 100 = chapitre 2 lunar débloqué. | ✓ |
| `lapProgress` | number | 0 | Progression 0..1 du km en cours. À 1 → completeLap() puis reset à 0. | ✓ |
| `runnerStamina` | number | 1.5 | Endurance du coureur. Baisse 0.075/sec, sous 0.5 = ralentissement visible. | ✓ |
| `totalTaps` | number | 0 | Compteur cumulatif de taps. | ✓ |
| `bestKmh` | number | 0 | Record personnel km/h (déclenche grant chest gold quand battu). | ✓ |
| `firstKmRewarded` | bool | false | Flag bonus "premier km" déjà donné. | ✓ |
| `_autoCourseUnlocked` | bool | false | Flag déblocage auto-course (km 3). | ✓ |

## Upgrades tap (Cookie Clicker style)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `upgradeTapValue` | number | 0 | Lvl PUISSANCE : +1 goutte/tap par level (cf UPGRADES_TAP.tapValue). | ✓ |
| `upgradeCritChance` | number | 0 | Lvl CRIT : +1% crit base par level (cap 60% total). MaxLvl 55. | ✓ |
| `upgradeLapBonus` | number | 0 | Lvl LAP BONUS : multiplie bonus de fin de km. | ✓ |
| `upgradeAutoTap` | number | 0 | Lvl AUTO-TAP : taps automatiques par seconde. | ✓ |
| `upgradeEndurance` | number | 0 | Lvl ENDURANCE : capacité stamina + decay slower. MaxLvl 20. | ✓ |
| `upgradeEagleEye` | number | 0 | Lvl VISION D'AIGLE : voir haies +15%/lvl plus tôt. MaxLvl 15. Unlock km 8. | ✓ |
| `upgradeBaseSpeed` | number | 0 | Lvl VITESSE BASE : ×1.10/lvl sur idle baseline. MaxLvl 15. | ✓ |
| `upgradeCruiseControl` | number | 0 | Lvl PILOTE AUTO (ultimate) : +5% baseline tapBoost passif. MaxLvl 15. Unlock km 30. | ✓ |

## Skills actifs (4, à la Clicker Heroes)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `skillsLastUsed` | object | {} | Map skillId → timestamp dernière activation (pour cooldown). | ✓ |
| `skillSprintUntil` | number | 0 | Timestamp fin du sprint actif (×10 gouttes/tap pendant 30s). | ✓ |
| `skillTailwindUntil` | number | 0 | Timestamp fin du tailwind (cycles équipe ÷3 pendant 60s). | ✓ |
| `skillBreathUntil` | number | 0 | Timestamp fin du breath (équipe ×5 pendant 45s). | ✓ |

## Skill tree passif (22 nodes en 5 branches)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `skills` | object | `{unlocked:{}, pointsSpent:0}` | État de l'arbre. `unlocked[nodeId] = true` quand acheté. | ✓ |
| `_stMul`, `_stSpeedMul`, `_stTapMul`, `_stStamMax`, `_stStamBump`, etc. | numbers | 0/1 | Effets passifs réappliqués au boot via `applyUpgrades()`. Préfixe `_st`. | ✗ (recompute) |

## Team idle (6 coureurs)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `team` | object | {} | Map runnerId → `{ level, cycle, mgr }`. Runners : sprinter, relayeur, hurdler, marathonien, pistard, légende. | ✓ |

## Équipement (5 slots)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `equipment` | object | {} | Map typeId → `{ typeId, rarityId, level, bonus }`. Types : shoes, jersey, headband, watch, wristband. | ✓ |

## Coffres (4 raretés)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `chests` | object | `{wood:0,iron:0,gold:0,legendary:0}` | Nombre de coffres en attente par rareté. Reçu : 1/km (wood), tous les 5 km (iron), record km/h (gold), cap 25/50/75/100 (legendary). | ✓ |

## Cartes Star (deck system)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `cardsOwned` | array | [] | Liste des cardIds possédés. | ✓ |
| `cardsDeck` | array | [] | CardIds équipés (deck actif, max ~5). | ✓ |

## Saison / Prestige

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `saison` | number | 1 | Saison actuelle. Incrémentée à chaque ascension (100 km). | ✓ |
| `saisonBonus` | number | 0 | Bonus permanent gagné. | ✓ |
| `ascensions` | number | 0 | Nombre total d'ascensions. | ✓ |
| `upgrades` | object | {} | Map upgradeId → lvl pour Sanctum (Verbum Cordis, Lapis Mater, etc., legacy alchimie). | ✓ |
| `activeModifierId` | string\|null | null | Sceau Mystique choisi (phoenix, frost, hourglass, mercury, etc.). | ✓ |
| `recipes` | object | {} | Map recipeId → timestamp découverte (legacy Grand Œuvre). | ✓ |
| `perkGoldMul`, `perkCritBase`, `perkXpMul`, `perkAutoBase` | numbers | 0 | Perks de saison persistés. | ✓ |

## Stades & Biomes

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `selectedStadiumId` | string\|null | null | Stade cosmétique choisi (municipal/olympic/coliseum/sunset/cosmic). | ✓ |
| `currentStadiumId` | string | 'municipal' | Stade en cours (peut différer si run en parallèle). | ✓ |
| `stadiumProgress` | object | {} | Snapshot progression par stade (gold, team, upgrades, lapsRun). Permet de switch sans perdre. | ✓ |
| `chapter` | number | 1 | Chapitre narratif (1 = terre, 2 = lunar à partir de 100 km). | (calculé) |

## Daily & Engagement

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `dailyLast` | number | 0 | Timestamp dernière daily claim. | ✓ |
| `dailyStreak` | number | 0 | Streak actuel. | ✓ |
| `dailyCycles` | number | 0 | Cycles complétés (= 7 jours). | ✓ |
| `dailyQuests` | object\|null | null | Quêtes daily roll du jour. | ✓ |
| `dailyChallenge` | object\|null | null | Challenge spécial du jour (stamina-low / no-hurdle-miss / etc.). | ✓ |

## Quêtes & Achievements

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `quests` | array | [] | Quêtes actuelles (legacy templates). | partiel (id+claimed) |
| `achievements` | object | {} | Map achievementId → timestamp unlock. 57 hauts faits au total. | ✓ |
| `masterQuestDone` | object | {} | Map questId → bool (méta-quêtes). | ✓ |
| `codexUnlocks` | object | {} | Map "chain_tier" → timestamp (lore legacy). | ✓ |
| `totals` | object | `{produced:[0,0,0], merged:[0,0,0], maxTier:[0,0,0]}` | Compteurs legacy alchimie (3 chains). | ✓ |
| `firstReached` | array | [0,0,0] | Par chain, palier max atteint (legacy). | ✓ |

## Achievement stat counters (week 3)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `hurdlesCleared` | number | 0 | Haies sautées avec succès. | ✓ |
| `bestHurdleStreak` | number | 0 | Plus longue série de haies sans rater. | ✓ |
| `triplesCleared` | number | 0 | Haies triples sautées. | ✓ |
| `tallsCleared` | number | 0 | Haies hautes sautées. | ✓ |
| `widesCleared` | number | 0 | Haies larges sautées. | ✓ |
| `rivalsWon` | number | 0 | Rivals battus (dépassement). | ✓ |
| `rivalsLost` | number | 0 | Rivals subis (te doublent). | ✓ |
| `bestRivalStreak` | number | 0 | Plus longue série rivals battus consécutifs. | ✓ |
| `totalUpgradesBought` | number | 0 | Compteur global d'upgrades achetés. | ✓ |
| `rabbitsCaught` | number | 0 | Lapins dorés attrapés. | ✓ |
| `haresCaught` | number | 0 | Lièvres attrapés. | ✓ |
| `npcOvertakeCount` | number | 0 | NPCs dépassés par le héros. | ✓ |

## Combo

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `comboCount` | number | 0 | (legacy) Combo de fusion. | ✗ |
| `bestCombo` | number | 0 | Record combo (tap streak). | ✓ |
| `lastMergeTime` | number | 0 | (legacy) | ✗ |

## Boutique premium / IAP

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `shopBoostX2Until` | number | 0 | Timestamp fin du boost ×2 gouttes (24h). | ✓ |
| `lastAdAt` | number | 0 | Timestamp dernier rewarded ad. | ✓ |
| `starterPackClaimed` | bool | false | Starter pack réclamé. | ✓ |
| `starterPackDeclined` | bool | false | Starter pack décliné (ne plus reproposer). | ✓ |

## Cosmétique / Skins

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `ownedSkins` | object | {} | Map skinId → bool. Skins : base, ninja, cyber, rainbow, etc. | ✓ |
| `selectedSkinId` | string | 'base' | Skin actif. | ✓ |

## Records

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `records` | object | {} | Map catégorie → record (5 catégories : progression, vitesse, haies, rivaux, bonus). | ✓ |

## Session & timing

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `sessionStartMs` | number | `Date.now()` | Start de la session courante. | ✗ |
| `sessionMs` | number | 0 | Durée session active. | ✓ |
| `lastSaveTime` | number | `Date.now()` | Timestamp dernière save. | ✓ |
| `lastOfflineMs` | number | 0 | Durée offline calculée pour idle catch-up. | ✗ |
| `totalPlayMs` | number | 0 | Cumul lifetime de temps joué (cap 8h pour offline calc). | ✓ |

## Audio settings

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `audio` | bool | true | Master audio toggle. | ✓ |
| `bgmUserVolume` | number | 0.55 | Volume BGM 0..1 (depuis slider). | (localStorage) |
| `sfxUserVolume` | number | 0.35 | Volume SFX 0..1. | (localStorage) |
| `vibrationEnabled` | bool | true | Vibration mobile toggle. | (localStorage) |

## Modificateurs runtime (events / map)

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `activeEvents` | object | {} | Events aléatoires actifs (Pluie d'Étoiles, etc.). | ✓ |
| `lastEvent` | string\|null | null | Dernier event déclenché. | ✗ |
| `eventCdMul`, `eventRegenMul` | number | 1 | Cached event modifiers. | ✗ (recompute) |
| `tapMul`, `tapMulUntil` | number | 1/0 | Boost or temporaire (médaille dorée). | ✓ |

## Cache UI / private flags

| Propriété | Type | Default | Description | Persisté |
|---|---|---|---|---|
| `_resetting` | bool | false | Bloque save() pendant reset. | ✗ |
| `_lastAlmostReady` | bool | undef | Flash shop quand achat presque possible. | ✗ |
| `_lastShopAffordable` | number | undef | Memoize affordable count. | ✗ |
| `_codexNav` | object | undef | Position navigation codex. | ✗ |
| `selectedCodex` | string\|null | null | Sélection page codex. | ✗ |
| `_lastAutoSpawnAt` | number | 0 | Cooldown auto-spawn items (legacy recipes). | ✗ |
| `upgradeRegenMul`, `upgradeEssenceMaxMul`, `upgradeCdMul` | numbers | 1 | Cached upgrade effects. | ✗ (recompute) |

---

## Résumé statistiques

- **Total propriétés `STATE.*` identifiées** : ~95
- **Persistées dans save()** : ~75 (whitelist explicite ligne 20985)
- **Runtime-only** : ~20 (caches, flags UI, timers transitoires)
- **Recomputed à load** : appliqués via `applyUpgrades()` après hydratation

Pour ajouter une nouvelle prop persistante : éditer **save()** (ligne ~20985) ET **load()** (ligne ~22176). TOUJOURS les deux, sinon perte au refresh.
