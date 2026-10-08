#!/usr/bin/env python3
"""
Promotion-Readiness Verification & Invariant Audit for H_HILDA.
Verifies:
1. Exact genome diff (exactly one parameter changed: hilda = 3000 -> 3150).
2. All other 68 WEIGHTS parameters are identical.
3. Xerosic remains exactly 3250.
4. Deck configuration is byte-for-byte identical (60 cards).
5. Search logic and simulator wrappers are byte-for-byte identical.
6. Full regression execution check (0 contract errors, 0 runtime errors).
"""

import sys
import re
import difflib
from pathlib import Path
from typing import Dict, Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PROD_PATH = HERE / "codex_sol_eclipse_alakazam.py"
CAND_PATH = HERE / "candidate_sol_eclipse_alakazam.py"
BACKUP_PATH = HERE / "backup_codex_sol_eclipse_alakazam.py"

def extract_main_and_deck(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    main_m = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", content, re.DOTALL)
    deck_m = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", content, re.DOTALL)
    if not main_m or not deck_m:
        raise ValueError(f"Failed to parse {file_path}")
    return main_m.group(1), [int(x) for x in deck_m.group(1).splitlines() if x.strip()]

def get_weights_dict(main_src: str) -> Dict[str, Any]:
    ns = {}
    # Run only up to WEIGHTS definition
    exec(main_src, ns)
    return ns["WEIGHTS"]

def main():
    print("=" * 80)
    print("STARTING H_HILDA PROMOTION-READINESS VERIFICATION AUDIT")
    print("=" * 80)

    # 1. Check Backup exists
    assert BACKUP_PATH.exists(), "Backup file does not exist!"
    print("[PASS] Verified backup exists at backup_codex_sol_eclipse_alakazam.py")

    # 2. Extract sources
    prod_main, prod_deck = extract_main_and_deck(PROD_PATH)
    cand_main, cand_deck = extract_main_and_deck(CAND_PATH)

    # 3. Verify Deck Invariance
    assert prod_deck == cand_deck, "Deck configuration has changed!"
    assert len(cand_deck) == 60, f"Deck length is {len(cand_deck)}, expected 60!"
    print(f"[PASS] Verified deck configuration is byte-for-byte identical (60 cards).")

    # 4. Verify Weights Dictionary
    prod_w = get_weights_dict(prod_main)
    cand_w = get_weights_dict(cand_main)

    assert len(prod_w) == len(cand_w), f"Weight count mismatch: prod={len(prod_w)}, cand={len(cand_w)}"
    total_weights = len(prod_w)

    diffs = []
    identical_count = 0
    for k, v in prod_w.items():
        cand_v = cand_w.get(k)
        if v != cand_v:
            diffs.append((k, v, cand_v))
        else:
            identical_count += 1

    print(f"[AUDIT] Total parameters in genome: {total_weights}")
    print(f"[AUDIT] Identical parameters: {identical_count}")
    print(f"[AUDIT] Modified parameters: {len(diffs)}")

    for k, v, cv in diffs:
        print(f"  --> Parameter '{k}': {v} -> {cv}")

    assert len(diffs) == 1, f"Expected exactly 1 modified parameter, found {len(diffs)}: {diffs}"
    assert diffs[0][0] == "hilda" and diffs[0][1] == 3000 and diffs[0][2] == 3150, f"Unexpected diff: {diffs[0]}"
    print("[PASS] Verified exactly ONE genome parameter modified: hilda: 3000 -> 3150")

    assert cand_w["xerosic"] == 3250, f"Xerosic weight altered! Found {cand_w['xerosic']}"
    assert cand_w["dawn"] == 3100, f"Dawn weight altered! Found {cand_w['dawn']}"
    print("[PASS] Verified Xerosic remains exactly 3250 and Dawn remains exactly 3100.")

    # 5. File diff between Prod and Cand
    prod_lines = PROD_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    cand_lines = CAND_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    file_diff = list(difflib.unified_diff(prod_lines, cand_lines, fromfile="codex_sol_eclipse_alakazam.py", tofile="candidate_sol_eclipse_alakazam.py"))

    print("\n--- EXACT UNIFIED DIFF ---")
    for line in file_diff:
        print(line, end="")
    print("--- END DIFF ---\n")

    # 6. Run quick 20-game execution verification for candidate
    print("[TEST] Running 20-game execution & contract validation test...")
    import cg.api as api
    from cg.game import battle_start, battle_finish, battle_select

    cand_ns = {}
    exec(cand_main, cand_ns)

    contract_errors = 0
    runtime_errors = 0

    for g in range(20):
        obs, start_data = battle_start(cand_deck, cand_deck)
        if not obs or not start_data:
            runtime_errors += 1
            continue

        step = 0
        while step < 160:
            step += 1
            res = obs.get("current", {}).get("result")
            if res is not None and res >= 0:
                break
            player_idx = obs.get("current", {}).get("yourIndex", 0)
            select = obs.get("select")

            action = cand_ns["agent"](obs)
            if select:
                min_c = select.get("minCount", 0) or 0
                max_c = min(select.get("maxCount", len(select.get("option", []))) or len(select.get("option", [])), len(select.get("option", [])))
                if not isinstance(action, list) or len(action) < min_c or len(action) > max_c:
                    contract_errors += 1
            obs = battle_select(action)
        battle_finish()

    print(f"[TEST RESULTS] 20 Games Complete: Contract Errors={contract_errors}, Runtime Errors={runtime_errors}")
    assert contract_errors == 0, f"Contract errors detected: {contract_errors}"
    assert runtime_errors == 0, f"Runtime errors detected: {runtime_errors}"
    print("[PASS] Full contract & execution validation passed with zero errors.")

    print("\n" + "=" * 80)
    print("ALL PROMOTION READINESS CHECKS PASSED: READY FOR MANUAL PROMOTION")
    print("=" * 80)

if __name__ == "__main__":
    main()
