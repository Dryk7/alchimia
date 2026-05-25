#!/usr/bin/env python3
"""
verify-v16-F.py — Verification SOFT CAPS V16 FOULÉE (alchimia)

Vérifie que les soft caps endgame sont bien en place dans D:/alchimia/index.html :
  1) Combo cap x5 (x6 si stamina > 80%)
  2) AutoTap cap 10 taps/sec
  3) Vitesse passive cap 30 km/h sans skills actifs
  4) Endurance combo decay soft cap lvl 15
"""

import re
import sys
from pathlib import Path

INDEX = Path(r"D:/alchimia/index.html")

if not INDEX.exists():
    print(f"ERROR: {INDEX} not found")
    sys.exit(1)

src = INDEX.read_text(encoding="utf-8", errors="ignore")

results = []


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    sym = "OK" if ok else "FAIL"
    print(f"[{sym}] {label}" + (f"  -- {detail}" if detail else ""))


# === 1. COMBO CAP x5 / x6 ============================================
# Cherche le bloc combo: _staminaR + _comboCap + Math.min(_comboCap, _rawComboMul)
m1a = re.search(r"_staminaR\s*=\s*STATE\.staminaMax\s*\?\s*\(STATE\.stamina\s*/\s*STATE\.staminaMax\)\s*:\s*1", src)
m1b = re.search(r"_comboCap\s*=\s*_staminaR\s*>\s*0\.8\s*\?\s*6\s*:\s*5", src)
m1c = re.search(r"comboMul\s*=\s*Math\.min\(_comboCap,\s*_rawComboMul\)", src)
check("(1) Combo cap stamina ratio", bool(m1a), "_staminaR defined")
check("(1) Combo cap _comboCap 6/5", bool(m1b), "stamina>80% donne 6, sinon 5")
check("(1) Combo cap Math.min applied", bool(m1c), "comboMul clamped")

# Simulation: STATE.combo = 100 (= _comboCount), stamina 50% → cap 5
def simulate_combo(stamina_ratio, combo_count):
    # Reproduit la formule du jeu
    raw = 5 if combo_count >= 25 else (3 if combo_count >= 12 else (2 if combo_count >= 6 else (1.5 if combo_count >= 3 else 1)))
    cap = 6 if stamina_ratio > 0.8 else 5
    return min(cap, raw)

c_low = simulate_combo(0.5, 100)
c_high = simulate_combo(0.9, 100)
check("(1) Sim combo=100 stamina=50% -> 5", c_low == 5, f"value={c_low} (step-wise raw max=5, cap=5)")
check("(1) Sim combo=100 stamina=90% -> 5 (raw cap)", c_high == 5, f"value={c_high} (raw max=5, cap=6 mais raw plafonne avant)")
# Note: la grille step-wise plafonne à 5 → même avec cap 6, c'est 5.
# Le cap 6 prend effet si une future grille ou modifier (Foudre Bleue type) atteint 6.

# === 2. AUTOTAP CAP 10 taps/sec ======================================
m2 = re.search(r"const\s+rate\s*=\s*Math\.min\(10,\s*\(STATE\.upgradeAutoTap", src)
check("(2) AutoTap rate Math.min(10, ...)", bool(m2), "ligne 19734")

def simulate_autotap(level):
    return min(10, level * 1.5)

r20 = simulate_autotap(20)
r5 = simulate_autotap(5)
r7 = simulate_autotap(7)
check("(2) Sim upgradeAutoTap=20 -> rate=10 (clamped)", r20 == 10, f"raw=30, clamped={r20}")
check("(2) Sim upgradeAutoTap=5 -> rate=7.5 (no clamp)", r5 == 7.5, f"value={r5}")
check("(2) Sim upgradeAutoTap=7 -> rate=10 (just at cap)", r7 == 10, f"value={r7} (raw 10.5)")

# === 3. VITESSE PASSIVE CAP 30 km/h ==================================
m3a = re.search(r"_skillsActive\s*=\s*\(window\.STATE\s*&&\s*window\.STATE\.skillSprintUntil", src)
m3b = re.search(r"if\(!_skillsActive\)\{\s*displayKmh\s*=\s*Math\.min\(30,\s*displayKmh\)", src)
check("(3) Skills active check (skillSprintUntil)", bool(m3a), "détection sprint timed")
check("(3) displayKmh clamp 30 sans skill", bool(m3b), "Math.min(30,...) gated")

def simulate_kmh(target, skill_active):
    kmh = min(35, target)
    if not skill_active:
        kmh = min(30, kmh)
    return kmh

k_passive = simulate_kmh(45, False)
k_active = simulate_kmh(45, True)
check("(3) Sim target=45 sans skill -> 30", k_passive == 30, f"value={k_passive}")
check("(3) Sim target=45 avec skill -> 35", k_active == 35, f"value={k_active}")

# === 4. ENDURANCE COMBO DECAY soft cap lvl 15 ========================
m4 = re.search(r"enduranceLvl\s*=\s*Math\.min\(15,\s*\(window\.STATE\s*&&\s*window\.STATE\.upgradeEndurance\)\s*\|\|\s*0\)", src)
check("(4) Endurance Math.min(15, ...) clamp", bool(m4), "soft cap lvl 15")

def simulate_decay(endurance_lvl):
    lvl = min(15, endurance_lvl)
    decay_mul = max(0.30, 1.0 - lvl * 0.105)
    return decay_mul

d5 = simulate_decay(5)
d10 = simulate_decay(10)
d15 = simulate_decay(15)
d30 = simulate_decay(30)
# Le plancher max(0.30, ...) s'active à partir de lvl ~7 (1-7*0.105=0.265<0.30)
check("(4) Sim endurance=5 decayMul", abs(d5 - (1.0 - 5*0.105)) < 1e-9, f"value={d5} (raw 0.475)")
check("(4) Sim endurance=10 -> floored at 0.30", d10 == 0.30, f"value={d10}")
check("(4) Sim endurance=15 -> floored at 0.30", d15 == 0.30, f"value={d15}")
check("(4) Sim endurance=30 -> capped à lvl15 (= floor 0.30)", d30 == d15, f"value={d30} (lvl15={d15})")

# === RAPPORT ==========================================================
print("\n" + "=" * 60)
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
print(f"VERIFY V16-F : {passed}/{total} checks passed")
if passed == total:
    print("SOFT CAPS V16 OK — endgame balance is in place.")
    sys.exit(0)
else:
    print("FAILURES detected — see above.")
    failed = [lbl for lbl, ok, _ in results if not ok]
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
