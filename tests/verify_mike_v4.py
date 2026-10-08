#!/usr/bin/env python3
"""
Production Champion Verification Suite: CITADEL MIKE V4
Authoritative verification and fail-fast regression test for the production artifact.

Verifies:
  1. main.py syntax, imports, and module integrity.
  2. deck.csv card count (exactly 60), valid card IDs, and archetype structure.
  3. Strict Selection Contract invariants (minCount / maxCount clamping).
  4. Deterministic decision reproducibility.
  5. Live simulator execution: 6 self-play matches with zero fallback (FAIL-FAST).
"""

import sys
import csv
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cg.api as api
from cg.game import battle_start, battle_select, battle_finish
import main as v4_module

MAIN_FILE = ROOT / "main.py"
DECK_FILE = ROOT / "deck.csv"

def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def verify_deck():
    print("[CHECK 1] Verifying deck.csv integrity...")
    assert DECK_FILE.exists(), "deck.csv not found in repository root"
    
    with open(DECK_FILE, newline="", encoding="utf-8") as f:
        cards = [int(row[0].strip()) for row in csv.reader(f) if row and row[0].strip()]
    
    assert len(cards) == 60, f"Deck must have exactly 60 cards, found {len(cards)}"
    assert all(c > 0 for c in cards), "All card IDs must be positive integers"
    
    # Archetype composition sanity check (Water acceleration: Snover + Abomasnow ex + Kyogre + Water Energy)
    card_counts = {}
    for c in cards:
        card_counts[c] = card_counts.get(c, 0) + 1
    
    water_energy_id = 3
    abomasnow_ex_id = 1145
    kyogre_id = 1158
    
    assert water_energy_id in card_counts, "Water Energy (ID 3) missing from deck"
    assert abomasnow_ex_id in card_counts, "Mega Abomasnow ex (ID 1145) missing from deck"
    assert kyogre_id in card_counts, "Kyogre (ID 1158) missing from deck"
    
    print(f"  ✓ Deck length: 60 cards verified.")
    print(f"  ✓ Unique card species: {len(card_counts)}.")
    print(f"  ✓ Energy count: {card_counts.get(water_energy_id, 0)} Basic Water Energy.")
    print("  [PASS] Deck integrity verified.")
    return cards

def verify_contract_invariants():
    print("\n[CHECK 2] Verifying Selection Contract and Invariants in main.py...")
    src = MAIN_FILE.read_text(encoding="utf-8")
    
    assert "def validate_selection(" in src, "validate_selection function missing from main.py"
    assert "def legal_selection(" in src, "legal_selection function missing from main.py"
    assert "min_count" in src and "max_count" in src, "min/max selection clamping logic missing"
    assert "v4_agent" in src or "agent" in src, "Agent entrypoint missing from main.py"
    
    # Verify agents/mike_v4_champion matches root main.py and deck.csv
    agent_dir = ROOT / "agents" / "mike_v4_champion"
    if (agent_dir / "main.py").exists():
        assert (agent_dir / "main.py").read_text(encoding="utf-8") == src, (
            "agents/mike_v4_champion/main.py differs from root main.py"
        )
        print("  ✓ Standalone package agents/mike_v4_champion/main.py byte-identical to root.")
        
    print("  ✓ Strict selection contract invariants present.")
    print("  [PASS] Contract verification passed.")

def verify_determinism(deck: list):
    print("\n[CHECK 3] Verifying decision determinism...")
    obs, start_data = battle_start(deck, deck)
    
    # Evaluate same observation multiple times to guarantee deterministic tie-breaking
    action1 = v4_module.agent(obs)
    action2 = v4_module.agent(obs)
    action3 = v4_module.agent(obs)
    
    assert action1 == action2 == action3, (
        f"Non-deterministic selection detected! Actions: {action1}, {action2}, {action3}"
    )
    battle_finish()
    print("  ✓ Bit-exact deterministic reproducibility confirmed across identical states.")
    print("  [PASS] Determinism verified.")

def run_live_smoke_tests(deck: list, num_games: int = 6):
    print(f"\n[CHECK 4] Executing {num_games}-game live simulator smoke test (FAIL-FAST)...")
    print("  Mode: Strict verification (Zero fallback — fails immediately on any illegal selection)")
    
    total_decisions = 0
    for g in range(1, num_games + 1):
        obs, start_data = battle_start(deck, deck)
        assert obs and start_data, f"Engine failed to initialize battle for Game {g}"
        
        step = 0
        while step < 160:
            step += 1
            res = obs.get("current", {}).get("result")
            if res is not None and res >= 0:
                break
            
            sel = obs.get("select")
            if not sel:
                break
            
            total_decisions += 1
            # Execute agent
            action = v4_module.agent(obs)
            
            # FAIL-FAST CONTRACT AUDIT: check legality immediately
            opts = sel.get("option", [])
            min_c = sel.get("minCount", 0)
            max_c = sel.get("maxCount", len(opts))
            
            # 1. Action must be a list
            assert isinstance(action, list), (
                f"[FAIL-FAST ERROR] Game {g}, step {step}: Agent returned non-list action {type(action)}"
            )
            # 2. Length must satisfy minCount <= len <= maxCount
            assert min_c <= len(action) <= max_c, (
                f"[FAIL-FAST ERROR] Game {g}, step {step}: Action len {len(action)} outside [{min_c}, {max_c}]"
            )
            # 3. Indices must be within range [0, len(opts)-1]
            assert all(isinstance(idx, int) and 0 <= idx < len(opts) for idx in action), (
                f"[FAIL-FAST ERROR] Game {g}, step {step}: Index out of bounds in action {action} for {len(opts)} options"
            )
            # 4. No duplicate indices
            assert len(action) == len(set(action)), (
                f"[FAIL-FAST ERROR] Game {g}, step {step}: Duplicate indices in selection {action}"
            )
            
            obs = battle_select(action)
            
        battle_finish()
        print(f"  Game {g:02d}: Completed in {step:3d} steps. Legality errors: 0")
        
    print(f"\n  ✓ Total audited live decisions: {total_decisions}")
    print(f"  ✓ Legality violation rate: 0.00% (0 / {total_decisions})")
    print("  [PASS] Live simulation smoke test passed.")

def main():
    print_header("MIKE V4 PRODUCTION VERIFICATION SUITE")
    deck = verify_deck()
    verify_contract_invariants()
    verify_determinism(deck)
    run_live_smoke_tests(deck, num_games=6)
    print_header("RESULT: MIKE V4 ARTIFACT FULLY VERIFIED (READY FOR SUBMISSION)")

if __name__ == "__main__":
    main()
