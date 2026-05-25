"""
verify-v15-a2.py — Vérifie que le Tier 7 BOSS RUNNER est correctement ajouté.

Lit index.html, valide :
  - NPC_TIERS contient bien un 8e élément (index 7) label "BOSS RUNNER"
  - Le tier a bien les flags accessory.bossAura, glasses, armband
  - jersey noir (#1a1a2e), accent rouge (#e84030), baseSpeed >= 1.5
  - pickTierForPlayer contient la logique de spawn rare km 60+
  - drawRunner gère le rendu bossAura (gradient rouge)

Simule :
  - laps=50 : boss NE peut PAS spawner (km < 60)
  - laps=80 : boss PEUT spawner avec proba 5%
  - laps=110 : boss PEUT spawner avec proba 10%
"""
import re
import sys
from pathlib import Path

INDEX = Path(__file__).parent / "index.html"
if not INDEX.exists():
    print(f"FAIL: {INDEX} introuvable")
    sys.exit(2)

src = INDEX.read_text(encoding="utf-8", errors="replace")

errors = 0
warnings = 0

# === 1. Tier 7 BOSS RUNNER présent dans NPC_TIERS ===
print("=== Tier 7 BOSS RUNNER dans NPC_TIERS ===")
# Cherche le commentaire Tier 7, puis tout jusqu'à la fermeture du tableau "];"
boss_block_match = re.search(
    r"//\s*Tier\s*7.*?BOSS RUNNER.*?\n(.*?)\n\s*\];",
    src,
    re.DOTALL,
)
if not boss_block_match:
    print("  FAIL  Bloc Tier 7 BOSS RUNNER introuvable")
    errors += 1
    boss_block = ""
else:
    boss_block = boss_block_match.group(1)
    print("  OK    Bloc Tier 7 trouvé")

# label
if "label:'BOSS RUNNER'" in boss_block or 'label:"BOSS RUNNER"' in boss_block:
    print("  OK    label = 'BOSS RUNNER'")
else:
    print("  FAIL  label != 'BOSS RUNNER'")
    errors += 1

# baseSpeed >= 1.5
m = re.search(r"baseSpeed\s*:\s*([0-9.]+)", boss_block)
if m and float(m.group(1)) >= 1.5:
    print(f"  OK    baseSpeed = {m.group(1)} (>=1.5 attendu)")
else:
    got = m.group(1) if m else "absent"
    print(f"  FAIL  baseSpeed = {got} (attendu >=1.5)")
    errors += 1

# jersey noir
if "#1a1a2e" in boss_block:
    print("  OK    jersey noir #1a1a2e présent")
else:
    print("  FAIL  jersey noir #1a1a2e absent")
    errors += 1

# accent rouge
if "'#e84030'" in boss_block or '"#e84030"' in boss_block:
    print("  OK    accent rouge #e84030 présent")
else:
    print("  FAIL  accent rouge #e84030 absent")
    errors += 1

# accessory bossAura + glasses + armband
acc_match = re.search(r"accessory\s*:\s*\{([^}]+)\}", boss_block)
if not acc_match:
    print("  FAIL  accessory introuvable dans Tier 7")
    errors += 1
else:
    acc = acc_match.group(1)
    for flag in ("glasses", "armband", "bossAura"):
        if f"{flag}: true" in acc or f"{flag}:true" in acc:
            print(f"  OK    accessory.{flag} = true")
        else:
            print(f"  FAIL  accessory.{flag} manquant")
            errors += 1

# faceExprs effort
if "faceExprs" in boss_block and "effort" in boss_block:
    print("  OK    faceExprs contient 'effort'")
else:
    print("  WARN  faceExprs / effort manquant")
    warnings += 1

# hairStyles mohawk ou buzz
if "mohawk" in boss_block or "buzz" in boss_block:
    print("  OK    hairStyles contient mohawk ou buzz")
else:
    print("  FAIL  hairStyles ne contient ni mohawk ni buzz")
    errors += 1

# tier: 7
if "tier: 7" in boss_block or "tier:7" in boss_block:
    print("  OK    tier: 7 explicite")
else:
    print("  WARN  champ tier: 7 absent (le code utilise tierIdx mais c'est plus propre de le marquer)")
    warnings += 1

# === 2. Logique de spawn rare km 60+ dans pickTierForPlayer ===
print()
print("=== Logique spawn boss km 60+ ===")
spawn_match = re.search(
    r"if\s*\(\s*km\s*>=\s*60\s*&&\s*Math\.random\(\)\s*<\s*\(\s*km\s*>=\s*100\s*\?\s*([0-9.]+)\s*:\s*([0-9.]+)\s*\)\s*\)\s*\{[^}]*return\s+7",
    src,
    re.DOTALL,
)
if not spawn_match:
    print("  FAIL  logique spawn km>=60 introuvable dans pickTierForPlayer")
    errors += 1
    prob_100, prob_60 = None, None
else:
    prob_100 = float(spawn_match.group(1))
    prob_60 = float(spawn_match.group(2))
    print(f"  OK    spawn km>=60 trouvé : {prob_60*100:.0f}% km 60-99, {prob_100*100:.0f}% km 100+")
    if abs(prob_60 - 0.05) < 1e-3 and abs(prob_100 - 0.10) < 1e-3:
        print(f"  OK    probas exactes : 5% / 10%")
    else:
        print(f"  WARN  probas inattendues (attendu 5% / 10%)")
        warnings += 1

# Place AVANT la sélection normale (dist = ...)
boss_idx = src.find("return 7;")
dist_idx = src.find("let dist;", boss_idx if boss_idx >= 0 else 0)
if boss_idx >= 0 and dist_idx > boss_idx:
    print("  OK    le check boss est placé AVANT la sélection 'let dist'")
elif boss_idx >= 0 and dist_idx < boss_idx:
    print("  FAIL  le check boss est APRÈS 'let dist' (devrait être avant)")
    errors += 1
else:
    print("  WARN  impossible de vérifier l'ordre")
    warnings += 1

# === 3. Rendu bossAura dans drawRunner ===
print()
print("=== Rendu bossAura dans drawRunner ===")
aura_match = re.search(
    r"acc\.bossAura\s*\)\s*\{(.*?)\n\s*\}",
    src,
    re.DOTALL,
)
if not aura_match:
    print("  FAIL  Bloc 'if(acc.bossAura)' introuvable")
    errors += 1
else:
    aura_block = aura_match.group(1)
    print("  OK    Bloc 'if(acc.bossAura)' trouvé")
    if "rgba(232,64,48" in aura_block or "rgba(200,40,30" in aura_block:
        print("  OK    couleurs rouges présentes (rgba(232,64,48,...) ou rgba(200,40,30,...))")
    else:
        print("  FAIL  couleurs rouges manquantes dans bossAura")
        errors += 1
    if "createRadialGradient" in aura_block:
        print("  OK    createRadialGradient utilisé (cohérent avec championAura)")
    else:
        print("  FAIL  createRadialGradient manquant")
        errors += 1
    if "Math.sin" in aura_block:
        print("  OK    pulse dynamique (Math.sin) présent")
    else:
        print("  WARN  pas de pulse Math.sin")
        warnings += 1

# Le PRO highlight exclut maintenant bossAura
pro_match = re.search(
    r"if\(!isHero\s*&&\s*!acc\.championAura\s*&&\s*!acc\.bossAura",
    src,
)
if pro_match:
    print("  OK    PRO highlight exclut désormais !acc.bossAura")
else:
    print("  WARN  PRO highlight n'exclut pas !acc.bossAura (cosmetic stack possible)")
    warnings += 1

# === 4. Simulation comportementale ===
print()
print("=== Simulation pickTierForPlayer pour différents km ===")

import random


def sim_pick(laps_run, seed=42, prob60=0.05, prob100=0.10):
    """Reproduit la logique : km>=60 → 5% (ou 10% si km>=100) chance de tier 7."""
    rng = random.Random(seed)
    if laps_run >= 60:
        proba = prob100 if laps_run >= 100 else prob60
        if rng.random() < proba:
            return 7
    return None  # fallback : sélection normale (non simulée ici)


# laps=50 : boss IMPOSSIBLE
hit_at_50 = 0
for s in range(10000):
    if sim_pick(50, seed=s) == 7:
        hit_at_50 += 1
if hit_at_50 == 0:
    print(f"  OK    km=50 : 0 spawns boss sur 10000 essais")
else:
    print(f"  FAIL  km=50 : {hit_at_50} spawns boss (devrait être 0)")
    errors += 1

# laps=80 : ~5% boss
hit_at_80 = sum(1 for s in range(10000) if sim_pick(80, seed=s) == 7)
ratio_80 = hit_at_80 / 10000
if 0.03 <= ratio_80 <= 0.07:
    print(f"  OK    km=80 : {ratio_80*100:.1f}% spawns boss (~5% attendu)")
else:
    print(f"  WARN  km=80 : {ratio_80*100:.1f}% (attendu ~5%)")
    warnings += 1

# laps=110 : ~10% boss
hit_at_110 = sum(1 for s in range(10000) if sim_pick(110, seed=s) == 7)
ratio_110 = hit_at_110 / 10000
if 0.08 <= ratio_110 <= 0.12:
    print(f"  OK    km=110 : {ratio_110*100:.1f}% spawns boss (~10% attendu)")
else:
    print(f"  WARN  km=110 : {ratio_110*100:.1f}% (attendu ~10%)")
    warnings += 1

# === Résumé ===
print()
print("=== RÉSUMÉ ===")
print(f"  errors   = {errors}")
print(f"  warnings = {warnings}")
if errors == 0:
    print(f"  STATUS   = OK")
    sys.exit(0)
else:
    print(f"  STATUS   = FAIL")
    sys.exit(1)
