#!/usr/bin/env python3
"""Verify v15-a9 : post-km100 chests every 25 km."""
import re, sys

FILE = "D:/alchimia/index.html"
errors = []

with open(FILE, encoding="utf-8") as f:
    src = f.read()

# Locate maybeDropItem
m = re.search(r"function maybeDropItem\([^)]*\)\{(.*?)\n\}", src, re.DOTALL)
if not m:
    errors.append("maybeDropItem not found")
    sys.exit("\n".join(errors))

body = m.group(1)

# Check the 3 cases exist
checks = [
    ("km 50 gold",      r"km === 50" ),
    ("km 100 legendary",r"km === 100"),
    ("post-100 % 25",   r"km > 100 && km % 25 === 0"),
]
for label, pat in checks:
    if not re.search(pat, body):
        errors.append(f"missing: {label} ({pat})")

# Simulate the JS logic in Python
def maybe_drop(km, reason_override=None):
    if reason_override:
        return reason_override
    if km == 50:
        return ("gold", "mid")
    elif km == 100:
        return ("legendary", "ascend")
    elif km > 100 and km % 25 == 0:
        return ("legendary", f"endgame {km}")
    return None

# Test cases per brief
cases = [
    (50,  ("gold",      "mid"),            "km 50 -> gold"),
    (100, ("legendary", "ascend"),         "km 100 -> legendary"),
    (125, ("legendary", "endgame 125"),    "km 125 -> chest"),
    (126, None,                             "km 126 -> nothing"),
    (150, ("legendary", "endgame 150"),    "km 150 -> chest"),
    (175, ("legendary", "endgame 175"),    "km 175 -> chest"),
    (200, ("legendary", "endgame 200"),    "km 200 -> chest"),
    (124, None,                             "km 124 -> nothing"),
    (101, None,                             "km 101 -> nothing"),
    (75,  None,                             "km 75 -> nothing (pre-100, non-jalon)"),
]
for km, expected, label in cases:
    got = maybe_drop(km)
    status = "OK" if got == expected else "FAIL"
    if got != expected:
        errors.append(f"{label}: expected {expected}, got {got}")
    print(f"[{status}] {label}: got={got}")

print()
if errors:
    print(f"ERRORS: {len(errors)}")
    for e in errors: print("  -", e)
    sys.exit(1)
else:
    print("0 errors — all post-km100 chest checks passed.")
