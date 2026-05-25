"""
verify-v15-a11.py — Vérifie le SFX différencié par rareté pour l'upgrade d'item (vague 14c).
Vérifie :
  - sfxItemUpgrade existe en tant que fonction
  - window.sfxItemUpgrade est exposé
  - Les 4 raretés (uncommon/rare/epic/legendary) sont mappées
  - Les fréquences C5/E5/G5/C6 sont présentes (523/659/784/1047)
  - upgradeItem appelle sfxItemUpgrade(item.rarityId)
  - ascendItem appelle sfxItemUpgrade(nextRarity)
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

print("=== Vérif sfxItemUpgrade défini ===")
# 1. fonction sfxItemUpgrade définie
m_func = re.search(r'function\s+sfxItemUpgrade\s*\(\s*rarity\s*\)', src)
if m_func:
    print("  OK    function sfxItemUpgrade(rarity) trouvée")
else:
    print("  FAIL  function sfxItemUpgrade(rarity) introuvable")
    errors += 1

# 2. window.sfxItemUpgrade exposé
m_win = re.search(r'window\.sfxItemUpgrade\s*=\s*sfxItemUpgrade', src)
if m_win:
    print("  OK    window.sfxItemUpgrade = sfxItemUpgrade")
else:
    print("  FAIL  window.sfxItemUpgrade non exposé")
    errors += 1

# 3. Mappings raretés -> notes
print()
print("=== Vérif mapping raretés ===")
for rarity in ("uncommon", "rare", "epic", "legendary"):
    p = re.compile(rf"{rarity}\s*:\s*\[\[", re.IGNORECASE)
    if p.search(src):
        print(f"  OK    rarity '{rarity}' mappée")
    else:
        print(f"  FAIL  rarity '{rarity}' introuvable dans le mapping")
        errors += 1

# 4. Fréquences C5/E5/G5/C6
print()
print("=== Vérif fréquences notes ===")
for freq, label in [(523, "C5"), (659, "E5"), (784, "G5"), (1047, "C6")]:
    if re.search(rf"\b{freq}\b", src):
        print(f"  OK    {freq} Hz ({label}) présent")
    else:
        print(f"  FAIL  {freq} Hz ({label}) absent")
        errors += 1

# 5. upgradeItem appelle sfxItemUpgrade(item.rarityId)
print()
print("=== Vérif intégration upgradeItem ===")
m_up = re.search(
    r'function\s+upgradeItem\s*\([^)]*\)\s*\{[^}]*?sfxItemUpgrade\s*\(\s*item\.rarityId\s*\)',
    src, re.DOTALL
)
if m_up:
    print("  OK    upgradeItem appelle sfxItemUpgrade(item.rarityId)")
else:
    # Fallback search
    if "sfxItemUpgrade(item.rarityId)" in src:
        print("  OK    sfxItemUpgrade(item.rarityId) trouvé dans le code")
    else:
        print("  FAIL  upgradeItem n'appelle pas sfxItemUpgrade(item.rarityId)")
        errors += 1

# 6. ascendItem appelle sfxItemUpgrade(nextRarity)
print()
print("=== Vérif intégration ascendItem ===")
m_as = re.search(
    r'function\s+ascendItem\s*\([^)]*\)\s*\{.*?sfxItemUpgrade\s*\(\s*nextRarity\s*\)',
    src, re.DOTALL
)
if m_as:
    print("  OK    ascendItem appelle sfxItemUpgrade(nextRarity)")
else:
    if "sfxItemUpgrade(nextRarity)" in src:
        print("  OK    sfxItemUpgrade(nextRarity) trouvé dans le code")
    else:
        print("  FAIL  ascendItem n'appelle pas sfxItemUpgrade(nextRarity)")
        errors += 1

# 7. Simulation : typeof window.sfxItemUpgrade === 'function'
print()
print("=== Simulation typeof window.sfxItemUpgrade ===")
# Si la fonction est définie ET assignée à window, alors typeof === 'function'
sim_ok = bool(m_func) and bool(m_win)
if sim_ok:
    print("  OK    typeof window.sfxItemUpgrade === 'function' (simulation)")
else:
    print("  FAIL  typeof window.sfxItemUpgrade !== 'function'")
    errors += 1

# 8. Vérif différenciation : nombre de notes croissant
print()
print("=== Vérif progression notes par rareté ===")
# Extrait la section sfxItemUpgrade
m_section = re.search(
    r'function\s+sfxItemUpgrade\s*\([^)]*\)\s*\{(.*?)\n\}',
    src, re.DOTALL
)
if m_section:
    section = m_section.group(1)
    counts = {}
    for rarity in ("uncommon", "rare", "epic", "legendary"):
        m_arr = re.search(rf"{rarity}\s*:\s*(\[.*?\])(?=,\s*\w+\s*:|\s*\}})", section, re.DOTALL)
        if m_arr:
            arr_str = m_arr.group(1)
            n = len(re.findall(r'\[\s*\d+', arr_str))
            counts[rarity] = n
            print(f"  {rarity:10s} -> {n} note(s)")
    expected_counts = {"uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}
    for r, exp in expected_counts.items():
        got = counts.get(r)
        if got == exp:
            pass
        elif got is None:
            print(f"  FAIL  {r} : aucune note trouvée")
            errors += 1
        else:
            print(f"  FAIL  {r} : {got} notes (attendu {exp})")
            errors += 1
else:
    print("  WARN  Section sfxItemUpgrade non extractible")
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
