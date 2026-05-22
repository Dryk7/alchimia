# FOULÉE — Checklist pré-launch Play Store

20 items à valider avant publication. Cocher au fur et à mesure.

---

## A — Technique (5)

- [ ] **A1.** Build TWA (Trusted Web Activity) ou Bubblewrap généré, APK/AAB compilé en release
- [ ] **A2.** Clé de signature générée, sauvegardée hors-machine (cloud chiffré + clé USB) et enregistrée sur Play Console
- [ ] **A3.** Test sur 3 appareils Android réels différents (low-end, mid-range, flagship) — pas d'écrans blancs, pas de crash au splash
- [ ] **A4.** Service worker validé : jeu lance offline après premier load, manifeste PWA OK (icon, theme_color, orientation portrait)
- [ ] **A5.** Performance : 60 fps stable au km 50+, pas de fuite mémoire après 30 min de session

## B — Contenu Play Store (5)

- [ ] **B1.** Description longue FR + EN finalisées (max 4000 caractères chacune)
- [ ] **B2.** Description courte FR + EN (max 80 caractères) — hook accrocheur
- [ ] **B3.** 8 screenshots phone (portrait 540x960 ou 1080x1920) sélectionnés et localisés
- [ ] **B4.** Icône hi-res 512x512 PNG, feature graphic 1024x500 PNG, logo de marque
- [ ] **B5.** Vidéo promo 30 s uploadée sur YouTube (lien à coller dans Play Console)

## C — Légal (5)

- [ ] **C1.** Politique de confidentialité rédigée, hébergée sur URL publique, lien renseigné dans Play Console
- [ ] **C2.** Conditions d'utilisation (Terms of Service) publiées et liées
- [ ] **C3.** Questionnaire IARC rempli (rating PEGI / ESRB) — viser PEGI 3
- [ ] **C4.** Data safety form Google complété (aucune collecte → déclaration "no data collected")
- [ ] **C5.** Mentions légales développeur OK (nom, pays, contact email obligatoire pour utilisateurs)

## D — Marketing (5)

- [ ] **D1.** Compte TikTok @foulee.game créé, bio prête, 3 premières vidéos pré-produites
- [ ] **D2.** Press kit envoyé à 10 médias / streamers ciblés (jeuxvideo.com, Frandroid, Numerama, créateurs idle FR)
- [ ] **D3.** Compte Twitter/X + Bluesky créés, post de lancement programmé J-1
- [ ] **D4.** Page itch.io ou site landing créée avec lien Play Store et vidéo embed
- [ ] **D5.** Discord ou canal communautaire ouvert pour les premiers joueurs (feedback rapide pré-/post-launch)

---

## Recommandations finales

- **Soft launch FR uniquement** sur 7 jours avant ouverture EN — corriger les bugs critiques avant scaling.
- **Monitorer Play Console** quotidiennement la première semaine (crashs, ANR, reviews 1 étoile).
- **Répondre à chaque review** dans les 24 h pendant le premier mois.
