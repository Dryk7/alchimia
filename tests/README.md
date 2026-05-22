# FOULEE - Suite de tests regression

Tests automatises Playwright pour le jeu FOULEE (index.html monolithique).

## Prerequis

```powershell
pip install playwright
playwright install chromium
```

Le serveur local doit tourner sur **http://localhost:8770** :
```powershell
# Depuis D:\alchimia\
./LANCER-FOULEE.bat
```

## Lancer la suite complete

```powershell
# Tests fonctionnels (20 scenarios)
python D:\alchimia\tests\regression-suite.py

# Snapshots visuels (10 scenes)
python D:\alchimia\tests\visual-snapshots.py

# Mode verbeux
python D:\alchimia\tests\regression-suite.py --verbose

# Regenerer les baselines
python D:\alchimia\tests\visual-snapshots.py --update
```

**Exit codes** : `0` = tout OK, `1` = au moins un echec, `2` = erreur d'env.

## Les 20 tests fonctionnels

| # | Test | Ce qui est verifie |
|---|---|---|
| 01 | load sans erreur | Aucune `pageerror` au chargement |
| 02 | bouton start | `#start-btn` clickable et disparait |
| 03 | premier tap | `STATE.totalTaps` augmente |
| 04 | achat upgrade | `buyUpgrade()` ou `.upg-btn` fonctionne |
| 05 | AUTO-COURSE km 3 | baseline speed > 0 |
| 06 | Vision Aigle km 8 | bouton `data-upgrade="eagleEye"` debloque |
| 07 | coffre bois km 1 | `rollChest(1)` ajoute au tableau |
| 08 | coffre argent km 5 | Sur 200 rolls, au moins 1 iron |
| 09 | coffre legendaire km 25 | Sur 500 rolls, au moins 1 legendary |
| 10 | skills bar | `#skills-bar` present dans le DOM |
| 11 | bouton SAUT | `#jump-btn` present |
| 12 | km/h grimpe | `#runner-pace` augmente au burst de taps |
| 13 | Champions T6 km 85 | Palier de tier verifie |
| 14 | Tribune OLA km 25 | State au km 25, stage actif |
| 15 | Escape ferme menu | `ESC` ne crash pas la page |
| 16 | aria-live gold | `#gold-val` a `aria-live="polite"` |
| 17 | vibration | `navigator.vibrate(10)` ne throw pas |
| 18 | save localStorage | `alchimia.save` rempli apres `saveGame()` |
| 19 | daily J7 streak | `dailyStreak === 7` apres J7 (pas de reset) |
| 20 | daily challenge | `STATE.dailyChallenge` est defini |

## Les 10 snapshots visuels

1. `01_splash` - ecran d'accueil
2. `02_km0_fresh` - km 0, partie fraiche
3. `03_km3_autocourse` - declenchement AUTO-COURSE
4. `04_km30_urban` - zone urbaine
5. `05_km70_stade` - zone stade
6. `06_km95_sprint_champion` - sprint avec champion
7. `07_km100_ascension` - ecran ascension
8. `08_km105_lunar` - zone lunaire
9. `09_daily_reward_modal` - modal daily reward
10. `10_daily_challenge_modal` - modal daily challenge

Les baselines sont stockees dans `tests/baselines/`. Les captures du run courant vont dans `tests/snapshots-current/`. La comparaison est volontairement simplifiee : delta de taille de fichier > 15% = diff. Pour une comparaison pixel-perfect ouvrir manuellement les deux images.

## Ajouter un test

Dans `regression-suite.py`, definir une coroutine `async def test_XX_nom(page)` qui :
1. fait `await fresh_load(page)` puis `await click_start_if_present(page)` si besoin
2. utilise `force_km(page, N)` pour sauter a un km donne
3. fait des `assert` qui throw en cas d'echec (message clair)
4. retourne une string (sera affichee en cas de pass)

Puis ajouter `('XX nom du test', test_XX_nom)` au tableau `TESTS`.

## Debug d'une regression

```powershell
# Mode verbose : voir les details
python D:\alchimia\tests\regression-suite.py --verbose

# Debug visuel : modifier headless=True -> headless=False dans regression-suite.py main()
# puis ajouter await page.pause() dans le test qui echoue
```

Pour les snapshots, comparer manuellement :
```
D:\alchimia\tests\baselines\03_km3_autocourse.png   (reference)
D:\alchimia\tests\snapshots-current\03_km3_autocourse.png   (run courant)
```

## Limitations connues

- Le canvas de jeu (course/stade) n'est pas teste pixel-par-pixel : seul l'etat JS (`STATE`) est verifie.
- Les drops aleatoires (coffres) reposent sur la loi des grands nombres (500 rolls).
- Les modals daily peuvent ne pas s'ouvrir si les fonctions `showDailyReward`/`showDailyChallenge` sont renommees - mettre a jour les selecteurs en consequence.
