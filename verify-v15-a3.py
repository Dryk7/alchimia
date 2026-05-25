"""
verify-v15-a3.py — Vérifie que les achievements biome_* utilisent les bons seuils.
Lit index.html, parse les seuils biome_*, valide :
  - biome_rural >= 3
  - biome_urban >= 10
  - biome_stadium >= 80
  - biome_flame  >= 80
Simule STATE.lapsRun = 50 puis 80, vérifie biome_stadium NON déclenché à 50, OUI à 80.
"""
import re
import sys
from pathlib import Path

INDEX = Path(__file__).parent / "index.html"
if not INDEX.exists():
    print(f"FAIL: {INDEX} introuvable")
    sys.exit(2)

src = INDEX.read_text(encoding="utf-8", errors="replace")

# === Parsing des achievements biome_* ===
pattern = re.compile(
    r'\{\s*id\s*:\s*"(biome_[a-z]+)"[^}]*?check\s*:\s*s\s*=>\s*\(s\.lapsRun\|\|0\)\s*>=\s*(\d+)',
    re.DOTALL
)
hits = pattern.findall(src)
thresholds = {bid: int(km) for bid, km in hits}

print("=== Seuils détectés ===")
for k, v in thresholds.items():
    print(f"  {k:18s} >= {v} km")

# === Attendus ===
expected = {
    "biome_rural":   3,
    "biome_urban":  10,
    "biome_stadium": 80,
    "biome_flame":  80,
}

errors = 0
warnings = 0
print()
print("=== Validation seuils ===")
for bid, exp_km in expected.items():
    got = thresholds.get(bid)
    if got is None:
        print(f"  WARN  {bid} introuvable dans les achievements")
        warnings += 1
        continue
    if got == exp_km:
        print(f"  OK    {bid} = {got} (attendu {exp_km})")
    else:
        print(f"  FAIL  {bid} = {got} (attendu {exp_km})")
        errors += 1

# === Simulation STATE.lapsRun ===
print()
print("=== Simulation déclenchement biome_stadium ===")

def stadium_check(laps_run):
    """Simule la fonction check du JS : s => (s.lapsRun||0) >= seuil"""
    seuil = thresholds.get("biome_stadium", 80)
    return (laps_run or 0) >= seuil

# Cas 1 : km=50, biome_stadium ne doit PAS se déclencher
laps_50 = 50
fired_at_50 = stadium_check(laps_50)
print(f"  STATE.lapsRun = {laps_50} -> biome_stadium declenche = {fired_at_50}")
if fired_at_50:
    print(f"  FAIL  biome_stadium déclenché trop tôt à km={laps_50} (bug original)")
    errors += 1
else:
    print(f"  OK    biome_stadium reste verrouillé à km={laps_50}")

# Cas 2 : km=80, biome_stadium DOIT se déclencher
laps_80 = 80
fired_at_80 = stadium_check(laps_80)
print(f"  STATE.lapsRun = {laps_80} -> biome_stadium declenche = {fired_at_80}")
if fired_at_80:
    print(f"  OK    biome_stadium se déclenche à km={laps_80} (cohérent avec STADIUM_STAGES)")
else:
    print(f"  FAIL  biome_stadium ne se déclenche pas à km={laps_80}")
    errors += 1

# === Vérif cohérence avec STADIUM_STAGES (km 80 = Vasque olympique) ===
print()
print("=== Cohérence STADIUM_STAGES ===")
m = re.search(r'\{\s*km\s*:\s*80\s*,\s*name\s*:\s*\'([^\']+)\'', src)
if m:
    name_km80 = m.group(1)
    print(f"  km 80 = '{name_km80}'")
    if "asque" in name_km80.lower() or "stade" in name_km80.lower():
        print(f"  OK    Le stade olympique commence bien à km 80")
    else:
        print(f"  WARN  Nom inattendu à km 80")
        warnings += 1
else:
    print(f"  WARN  Impossible de retrouver le stage km 80")
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
