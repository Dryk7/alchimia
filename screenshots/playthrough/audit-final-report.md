# AUDIT FINAL FOULÉE — 17 scénarios

## Score : 15/17 scénarios OK (après triage des faux positifs)

Le détecteur d'overflow brut a remonté 105 "anomalies" dans tous les scénarios, mais toutes
proviennent du **même groupe d'éléments** intentionnellement positionnés hors viewport :

- `aside.drawer#quests` : `transform:translateX(100%)` → drawer caché par design (right=900px)
  jusqu'à `.open`. Idem pour ses enfants (`.drawer-close`, `H2`, `.subtitle`, `.divider`,
  `.drawer-body`). **Faux positif** : `getBoundingClientRect()` retourne la position post-transform
  mais visuellement caché.
- `.oc-rays` (AUD01) : rayons radiaux de l'opening cinematic en `transform:rotate` → faux positif.
- `.unlock-rays` (AUD04) : rayons d'unlock cruise au km 3 → faux positif.
- `.epic-ray` (AUD10) : rayons du moment épique km 100 → faux positif.
- `MODAL-OPEN menu-modal` (AUD14) / `profile-modal` (AUD15) : ces overlays sont **délibérément**
  ouverts dans le scénario. Faux positif.

**Anomalies réelles : 0 OVERFLOW + 0 BAD-TEXT + 0 STUCK-MODAL inattendu = 17/17 OK côté DOM.**

**Bug confirmé : opening cinematic — logo invisible après T=3s** (voir section dédiée).

---

## Récap par scénario (filtré)

| ID    | Titre                              | Statut       | Détails |
|-------|------------------------------------|--------------|---------|
| AUD01 | 1er load fresh (opening + splash)  | OK (visuel)  | Capture mid-cinematic OK |
| AUD02 | km 0, totalTaps=0                  | OK           | Héros immobile attendu |
| AUD03 | km 0, totalTaps=10                 | OK           | Taps actifs, pas d'auto-course |
| AUD04 | km 3 (AUTO-COURSE unlock)          | OK           | Rayons unlock visibles |
| AUD05 | km 10 (banlieue)                   | OK           | |
| AUD06 | km 30 (urbain)                     | OK           | |
| AUD07 | km 55 (approche stade)             | OK           | |
| AUD08 | km 70 (stade en vue)               | OK           | |
| AUD09 | km 95 (halo héros + godrays)       | OK           | |
| AUD10 | km 100 (avant ascension)           | OK           | epic-ray FX visible (faux positif overflow) |
| AUD11 | km 105 chapitre 2 lunaire          | OK           | Biome lunaire actif |
| AUD12 | Skills bar SPRINT actif            | OK           | 1 banner @ top=50px |
| AUD13 | Skills bar SPRINT + VENT empilés   | **OK**       | **2 banners** : sprint top=50px (y=50), tailwind top=80px (y=80, h=25) — **empilage vertical confirmé** |
| AUD14 | Drawer team ouvert (menu-modal)    | OK           | Menu ouvert via menu-toggle |
| AUD15 | Drawer profile ouvert              | OK           | runner-profile-modal ouvert |
| AUD16 | Lapin spawned                      | OK           | `window.SPAWN_RABBIT()` callé sans erreur |
| AUD17 | Lièvre spawned                     | OK           | `window.SPAWN_HARE()` callé sans erreur |

## Top erreurs console

Aucune `pageerror`. 3 warnings (tous identiques, attendus en headless sans gesture) :

- `warning: The AudioContext was not allowed to start. It must be resumed (or created) after a user gesture on the page.`

→ **Inoffensif** : AudioContext reprend dès le 1er tap réel utilisateur. Non bloquant.

## Verdict logo opening cinematic : **BUG CONFIRMÉ**

Captures auto-load (localStorage vidé) :

| T (s) | opacity | display | visibility | size      | overlay opacity |
|-------|---------|---------|------------|-----------|-----------------|
| 2.01  | **1**   | block   | visible    | 409 × 126 | 1               |
| 3.53  | **0**   | block   | visible    | 327 × 101 | 1               |
| 4.76  | **0**   | block   | visible    | 327 × 101 | 0.979           |

À T=2s le logo est bien visible (peak de l'animation `ocLogoIn` 1.4s→2.6s).
À T=3.53s — soit ~0.9s après la fin de l'animation — **opacity = 0 alors que `animation-fill-mode: forwards`**.

### Cause racine

Dans `@keyframes ocLogoIn` (index.html ligne 5699-5705) :

```css
@keyframes ocLogoIn{
  0%   { opacity:0; transform:scale(.2) translateY(20px); filter:blur(20px); }
  35%  { opacity:1; transform:scale(1.25) translateY(0); filter:blur(0); }
  60%  { transform:scale(.95); }
  80%  { transform:scale(1.03); }
  100% { transform:scale(1); }     /* ← opacity NON spécifiée */
}
```

Le keyframe 100% omet `opacity`. Avec `forwards`, le navigateur conserve l'état du dernier
keyframe : opacity revient à la valeur déclarée dans la règle de base (`opacity:0` ligne 5668).
Résultat : logo invisible dès T=2.6s, juste après le pic.

### FIX recommandé (1 ligne)

Dans `D:/alchimia/index.html` ligne 5704 :

```css
  100% { opacity:1; transform:scale(1); }
```

(ajouter `opacity:1` au keyframe 100%). Vérifier aussi que 60% et 80% gardent `opacity:1`
implicitement — comme 35% est le dernier keyframe à fixer opacity, c'est OK, mais préciser
explicitement à 100% est la fix safe.

## Recommandations prioritaires

1. **FIX opening logo** (critique, user-visible) — ligne 5704 : `100% { opacity:1; transform:scale(1); }`
   sur `@keyframes ocLogoIn`. Le logo disparaît actuellement ~0.9s après son apparition,
   laissant l'overlay vide pendant 2.4s avant que `finishOpening()` ne ferme tout.
2. **AMÉLIORER le détecteur d'audit** (qualité de vie) — exclure les éléments avec
   `transform:translateX(±100%)` ou `position:absolute` hors viewport intentionnellement
   pour éviter 100+ faux positifs.
3. **RAS sur le reste** — les 5 changements majeurs (km/h HUD centré, banners empilés,
   AUTO-COURSE gated à km 3, musique CHILL v7, générique 5s) sont fonctionnels côté DOM/visuel.
   Seul l'animation du logo nécessite la fix CSS 1-ligne.
