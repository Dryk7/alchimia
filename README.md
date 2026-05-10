# ALCHIMIA — Le Cabinet des Trois Voies

Idle / merge gothique-alchimique. Single HTML file, mobile-first.

**Joue en ligne :** [dryk7.github.io/alchimia](https://dryk7.github.io/alchimia/)

---

## Les Trois Voies

Chaque voie monte en 8 paliers (T0 → T7). Fusionne deux items identiques pour atteindre le palier supérieur.

| Voie | Plante (Vegetabilis) | Pierre (Mineralis) | Essence (Spiritualis) |
|---|---|---|---|
| I | Graine | Caillou | Brume |
| II | Bourgeon | Quartz | Étincelle |
| III | Mandragore | Améthyste | Flamme Bleue |
| IV | Fleur Sépulcrale | Géode | Esprit |
| V | Élixir d'Aube | Pierre Runique | Constellation |
| VI | **Panacée** | **Pierre Philosophale** | **Quintessence** |
| VII | Arbre-Monde | Étoile Polaire | Akasha |
| VIII | **Yggdra** | **Eternium** | **Singularité** |

Chaque palier ultime atteint pour la 1ère fois déclenche une cinématique « Grand Œuvre ».

## Systèmes

- **Cabinet** — 5×6 grille, drag & drop pour fusionner
- **Cauldrons** (×3) — un par voie, étincelle requise + cooldown
- **Athanor** — 4ᵉ générateur (débloqué pour 500 couronnes), purification : 3 items → 1 palier supérieur
- **Quêtes** — 28 quêtes par parcours (palier × voie + globales)
- **Hauts Faits** — 34 achievements avec popup gold + onglet codex
- **Évènements aléatoires** — 7 événements (Pluie d'Étoiles, Conjonction Astrale, Marée d'Esprit, Souffle d'Or, Comète, Nuit Profonde, Sourire de Lune)
- **Transmutation** — prestige débloqué à T6 : reset contre Étoiles permanentes
- **Sanctum** — boutique d'upgrades permanents (6 upgrades : Verbum Cordis, Lapis Mater, Mercurio, Sol Aurum, Fulmen, Anima Mundi)
- **Codex** — 24 paliers + 34 hauts faits avec lore
- **Idle/offline** — calcul de progression hors-ligne (cap 8h)
- **Statistiques** — temps de jeu, totaux par voie, transmutations
- **Tooltips long-press** — détail de chaque item

## Stack

- HTML / CSS / JS vanilla, single-file (~5000 lignes)
- Sprites pixel art SVG 32×32 (24 items + 4 générateurs + ornements)
- Canvas pour poussière flottante, bougies animées avec flicker, bulles de cauldron, FX (foudre de fusion, particules attractives, shockwave, cinématique)
- Bande sonore adaptative (3 tracks qui se relaient avec crossfade selon le palier max atteint) :
  - Phase 0–1 (early) : *Forgotten Tomb Ambience* par **kindland** ([CC0](https://creativecommons.org/publicdomain/zero/1.0/) — [opengameart.org](https://opengameart.org/content/forgoten-tomb-ambience))
  - Phase 2–3 (mid–late) : *Long Note Three* par **Kevin MacLeod** ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — [incompetech.com](https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1100424))
  - Phase 4 (cosmic) : *Space Music* par **HitCtrl** ([CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) — [opengameart.org](https://opengameart.org/content/space-music-2))

  SFX synthétisés via Web Audio (cloches harmoniques, sub-bass cinématique, reverb par convolution)
- Vibration API mobile
- LocalStorage save (auto toutes les 4s)

## Direction artistique

- Palette gothique alchimique : noir d'encre, or patiné, parchemin, vert absinthe, bleu cristal, pourpre astral, braise
- Typographie : **Cinzel** (titres), **Cormorant Garamond** (italiques), **IM Fell English** (corps), **VT323** (chiffres)
- Ornements : ouroboros animé (intro), fleurons SVG, cartouches baroques aux coins, symboles alchimiques (sulfur, mercure, sel, soleil, lune)

## Lancer en local

```sh
python -m http.server 8770 --directory D:/alchimia
# → http://localhost:8770
```
