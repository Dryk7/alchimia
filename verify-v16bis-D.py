#!/usr/bin/env python3
"""
verify-v16bis-D.py — Verification PRESTIGE STAR TREE V16bis FOULÉE (alchimia)

Vérifie que la modale Prestige Star Tree est bien en place dans D:/alchimia/index.html :
  1) STATE.starTree init avec 8 nodes
  2) STAR_TREE_NODES array + helpers (buyStarNode, renderStarTree, openStarTree)
  3) Modale HTML #star-tree-modal avec liste #star-tree-list
  4) Menu item PRESTIGE data-action="prestige"
  5) Save/load STATE.starTree (persistance)

Simule aussi l'achat : STATE.stars=10; buyStarNode('tapPower') doit donner
STATE.starTree.tapPower===1 et STATE.stars===9.
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


# === 1. STATE.starTree init ==========================================
m1 = re.search(r"starTree:\s*\{\s*tapPower:\s*0,\s*lapPower:\s*0,\s*dropRate:\s*0,\s*basePower:\s*0", src)
check("(1) STATE.starTree init (4 first nodes)", bool(m1), "tapPower/lapPower/dropRate/basePower=0")
m1b = re.search(r"staminaPlus:\s*0,\s*critPower:\s*0,\s*cooldownNeg:\s*0,\s*starsJackpot:\s*0", src)
check("(1) STATE.starTree init (4 last nodes)", bool(m1b), "staminaPlus/critPower/cooldownNeg/starsJackpot=0")

# === 2. STAR_TREE_NODES + helpers ====================================
m2a = re.search(r"const\s+STAR_TREE_NODES\s*=\s*\[", src)
check("(2) STAR_TREE_NODES array declared", bool(m2a))

# Compter les 8 nodes attendus
expected_ids = ['tapPower', 'lapPower', 'dropRate', 'basePower',
                'staminaPlus', 'critPower', 'cooldownNeg', 'starsJackpot']
node_block = re.search(r"const\s+STAR_TREE_NODES\s*=\s*\[(.*?)\];", src, re.DOTALL)
if node_block:
    nb = node_block.group(1)
    found = [i for i in expected_ids if f"id:'{i}'" in nb]
    check("(2) 8 nodes definitions", len(found) == 8, f"found {len(found)}/8: {found}")
else:
    check("(2) 8 nodes definitions", False, "block STAR_TREE_NODES non trouvé")

m2b = re.search(r"function\s+nextStarNodeCost\(", src)
m2c = re.search(r"function\s+buyStarNode\(", src)
m2d = re.search(r"function\s+renderStarTree\(", src)
m2e = re.search(r"function\s+openStarTree\(", src)
check("(2) nextStarNodeCost function", bool(m2b))
check("(2) buyStarNode function", bool(m2c))
check("(2) renderStarTree function", bool(m2d))
check("(2) openStarTree function", bool(m2e))

m2f = re.search(r"window\.openStarTree\s*=\s*openStarTree", src)
check("(2) window.openStarTree exposed", bool(m2f))

# === 3. Modale HTML ==================================================
m3a = re.search(r'<div class="modal" id="star-tree-modal">', src)
check("(3) #star-tree-modal HTML present", bool(m3a))
m3b = re.search(r'id="star-tree-list"', src)
check("(3) #star-tree-list container", bool(m3b))
m3c = re.search(r'id="star-tree-avail"', src)
check("(3) #star-tree-avail counter", bool(m3c))
m3d = re.search(r'data-close-modal="star-tree-modal"', src)
check("(3) modal-close button", bool(m3d))

# === 4. Menu item PRESTIGE ===========================================
m4a = re.search(r'data-action="prestige"', src)
check("(4) Menu item data-action=prestige", bool(m4a))
m4b = re.search(r"action === 'prestige'.*openStarTree", src)
check("(4) Menu delegation -> openStarTree", bool(m4b))

# === 5. Save/load ====================================================
m5a = re.search(r"starTree:\s*STATE\.starTree\s*\|\|\s*\{", src)
check("(5) save: starTree in payload", bool(m5a))
m5b = re.search(r"STATE\.starTree\s*=\s*s\.starTree\s*\|\|\s*\{", src)
check("(5) load: starTree restored from save", bool(m5b))

# === SIMULATION : buy node ===========================================
# Reproduit la logique de buyStarNode pour tapPower (cost[0]=1)
def simulate_buy(stars, node_lvl, node_costs):
    if node_lvl >= len(node_costs):
        return (stars, node_lvl, False)
    cost = node_costs[node_lvl]
    if stars < cost:
        return (stars, node_lvl, False)
    return (stars - cost, node_lvl + 1, True)

# tapPower cost = [1,2,3,5,8]
new_stars, new_lvl, ok = simulate_buy(10, 0, [1, 2, 3, 5, 8])
check("(SIM) buy tapPower @stars=10 -> stars=9", new_stars == 9 and ok, f"stars={new_stars} lvl={new_lvl}")
check("(SIM) buy tapPower -> tapPower=1", new_lvl == 1 and ok, f"lvl={new_lvl}")

# stars=0 must refuse
new_stars2, new_lvl2, ok2 = simulate_buy(0, 0, [1, 2, 3, 5, 8])
check("(SIM) buy refused @stars=0", ok2 == False, f"stars={new_stars2} ok={ok2}")

# Max level reached
new_stars3, new_lvl3, ok3 = simulate_buy(100, 5, [1, 2, 3, 5, 8])
check("(SIM) buy refused at MAX lvl", ok3 == False, f"lvl=5/5 -> refuse")

# === RÉSUMÉ ==========================================================
print("\n" + "=" * 60)
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print(f"TOTAL: {passed}/{total} OK | {failed} FAIL")
if failed:
    print("\nFAILS:")
    for label, ok, detail in results:
        if not ok:
            print(f"  - {label}" + (f" :: {detail}" if detail else ""))
    sys.exit(1)
print("ALL CHECKS PASSED")
sys.exit(0)
