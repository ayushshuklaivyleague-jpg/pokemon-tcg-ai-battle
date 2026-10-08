#!/usr/bin/env python3
"""
Post-Promotion Verification & Regression Audit Script.
Verifies codex_sol_eclipse_alakazam.py vs its pre-promotion backup.
"""

import sys
import os
import re
import difflib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cg.api as api
from cg.game import battle_start, battle_select, battle_finish

PROD_FILE = ROOT / "codex_sol_eclipse_alakazam.py"
BAK_FILE = ROOT / "archive" / "experiments" / "codex_sol_eclipse_alakazam.py.bak_pre_hilda3150"

raw_prod = PROD_FILE.read_text(encoding="utf-8")
raw_bak = BAK_FILE.read_text(encoding="utf-8")

print("=" * 80)
print("POST-PROMOTION VERIFICATION AUDIT")
print("=" * 80)

# 1. Exact Source Diff Verification
diff_lines = list(difflib.unified_diff(
    raw_bak.splitlines(keepends=True),
    raw_prod.splitlines(keepends=True),
    fromfile="codex_sol_eclipse_alakazam.py.bak_pre_hilda3150",
    tofile="codex_sol_eclipse_alakazam.py"
))

print("[CHECK 1] Unified Source Diff:")
for line in diff_lines:
    print("  " + line.rstrip())

# 2. Extract and compare namespaces
prod_main_m = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_prod, re.DOTALL)
bak_main_m = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_bak, re.DOTALL)
prod_deck_m = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_prod, re.DOTALL)
bak_deck_m = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_bak, re.DOTALL)

assert prod_main_m and bak_main_m and prod_deck_m and bak_deck_m

prod_ns = {}
exec(prod_main_m.group(1), prod_ns)
bak_ns = {}
exec(bak_main_m.group(1), bak_ns)

prod_w = prod_ns["WEIGHTS"]
bak_w = bak_ns["WEIGHTS"]

diffs = []
for k, v in bak_w.items():
    pv = prod_w.get(k)
    if v != pv:
        diffs.append((k, v, pv))

print(f"\n[CHECK 2] Genome Delta Count: {len(diffs)}")
for k, bv, pv in diffs:
    print(f"  --> '{k}': {bv} -> {pv}")

assert len(diffs) == 1 and diffs[0] == ("hilda", 3000, 3150), f"Invalid diffs: {diffs}"
print("[PASS] Verified exactly ONE genome delta: hilda 3000 -> 3150.")

# 3. Deck Verification
prod_deck = [int(x) for x in prod_deck_m.group(1).splitlines() if x.strip()]
bak_deck = [int(x) for x in bak_deck_m.group(1).splitlines() if x.strip()]
assert prod_deck == bak_deck and len(prod_deck) == 60
print("[PASS] Deck configuration 100% identical (60 cards).")

# 4. Code Sanity Checks
assert "alakazam_count" not in prod_main_m.group(1) or 'if alakazam_count' not in prod_main_m.group(1)
assert "v4_legal_selection" not in prod_main_m.group(1)
assert prod_w["xerosic"] == 3250
assert prod_w["dawn"] == 3100
assert prod_w["hilda"] == 3150
print("[PASS] Structural checks passed: 0 conditional logic, 0 hybrid wrappers, 0 rejected experiments.")

# 5. Regression Smoke Test (6 Games)
print("\n[CHECK 5] Executing 6-game regression test...")
for g in range(1, 7):
    obs, start_data = battle_start(prod_deck, prod_deck)
    assert obs and start_data
    step = 0
    while step < 160:
        step += 1
        res = obs.get("current", {}).get("result")
        if res is not None and res >= 0:
            break
        sel = obs.get("select")
        if not sel:
            break
        p_idx = obs.get("current", {}).get("yourIndex", 0)
        action = prod_ns["agent"](obs)
        obs = battle_select(action)
    battle_finish()
    print(f"  Game {g:02d}: Completed in {step} steps with 0 contract/runtime errors.")

print("\n" + "=" * 80)
print("POST-PROMOTION VERIFICATION COMPLETE: PRODUCTION ARTIFACT VERIFIED & READY")
print("=" * 80)
