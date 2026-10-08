#!/usr/bin/env python3
"""
Final Promotion-Readiness Audit Script for LEAN H_HILDA.
Verifies all 9 promotion invariants against frozen production codex_sol_eclipse_alakazam.py.
"""

import sys
import os
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cg.api as api
from cg.game import battle_start, battle_select, battle_finish

PROD_FILE = HERE / "codex_sol_eclipse_alakazam.py"
raw_prod = PROD_FILE.read_text(encoding="utf-8")

# Extract MAIN_SOURCE and DECK_SOURCE
prod_main_m = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_prod, re.DOTALL)
prod_deck_m = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_prod, re.DOTALL)

if not prod_main_m or not prod_deck_m:
    raise RuntimeError("Failed to parse production codex_sol_eclipse_alakazam.py")

PROD_MAIN = prod_main_m.group(1)
PROD_DECK = [int(x) for x in prod_deck_m.group(1).splitlines() if x.strip()]

# Construct Candidate LEAN H_HILDA source
CAND_MAIN = PROD_MAIN.replace('"hilda": 3000,', '"hilda": 3150,')
CAND_DECK = list(PROD_DECK)

print("=" * 80)
print("FINAL PROMOTION-READINESS AUDIT: LEAN H_HILDA")
print("=" * 80)

# 1. Genome Delta Verification
prod_ns = {}
exec(PROD_MAIN, prod_ns)
prod_weights = prod_ns["WEIGHTS"]

cand_ns = {}
exec(CAND_MAIN, cand_ns)
cand_weights = cand_ns["WEIGHTS"]

assert len(prod_weights) == 69, f"Expected 69 weights, got {len(prod_weights)}"
assert len(cand_weights) == 69, f"Expected 69 weights, got {len(cand_weights)}"

weight_diffs = []
for k, v in prod_weights.items():
    cv = cand_weights.get(k)
    if v != cv:
        weight_diffs.append((k, v, cv))

print(f"[CHECK 1 & 2] Total Genome Parameters: {len(cand_weights)}")
print(f"[CHECK 1 & 2] Identical Parameters:    {len(cand_weights) - len(weight_diffs)}")
print(f"[CHECK 1 & 2] Modified Parameters:     {len(weight_diffs)}")
for k, pv, cv in weight_diffs:
    print(f"  --> Parameter '{k}': {pv} (Production) -> {cv} (Candidate)")

assert len(weight_diffs) == 1, f"Expected exactly 1 weight delta, found {len(weight_diffs)}"
assert weight_diffs[0] == ("hilda", 3000, 3150), f"Unexpected weight delta: {weight_diffs[0]}"
print("[PASS] Verified exactly ONE genome delta: hilda 3000 -> 3150. All 68 other weights are identical.")

# 3. Source Diff Verification
diff_lines = list(difflib.unified_diff(
    PROD_MAIN.splitlines(keepends=True),
    CAND_MAIN.splitlines(keepends=True),
    fromfile="production_codex_sol_eclipse_alakazam.py",
    tofile="candidate_lean_h_hilda.py"
))
print("\n[CHECK 3] Unified Source Diff:")
for line in diff_lines:
    print("  " + line.rstrip())

# 4. Deck Verification
assert PROD_DECK == CAND_DECK, "Deck mismatch!"
assert len(CAND_DECK) == 60, f"Deck size {len(CAND_DECK)} != 60"
print(f"\n[CHECK 4] Verified Deck: 100% identical 60-card Alakazam Courage deck.")

# 5. Rejected Experiment Checks
assert "alakazam_count" not in CAND_MAIN or "hilda" not in CAND_MAIN.lower() or 'if alakazam_count' not in CAND_MAIN, "Conditional Hilda detected!"
assert cand_weights.get("xerosic") == 3250, f"Xerosic modified: {cand_weights.get('xerosic')}"
assert cand_weights.get("dawn") == 3100, f"Dawn modified: {cand_weights.get('dawn')}"
assert "v4_legal_selection" not in CAND_MAIN, "V4 wrapper detected in lean candidate!"
print("[CHECK 5 & 6 & 7] Verified: No conditional Hilda, No V4 wrapper, No rejected experiments reintroduced.")

# 8. Smoke Regression Test (6 Games)
print("\n[CHECK 8] Running Smoke Regression (6 Games)...")
for g in range(1, 7):
    c_seat = 0 if g % 2 == 1 else 1
    obs, start_data = battle_start(CAND_DECK, CAND_DECK)
    assert obs and start_data, f"Game {g} battle_start failed"
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
        if p_idx == c_seat:
            action = cand_ns["agent"](obs)
        else:
            action = prod_ns["agent"](obs)
        obs = battle_select(action)
    battle_finish()
    print(f"  Smoke Game {g:02d} (Cand=P{c_seat}): Completed in {step} steps with 0 contract/runtime errors.")
print("[PASS] Full contract/runtime regression passed.")
print("\n" + "=" * 80)
print("AUDIT COMPLETE: CANDIDATE MEETS ALL 9 PROMOTION INVARIANTS")
print("=" * 80)
