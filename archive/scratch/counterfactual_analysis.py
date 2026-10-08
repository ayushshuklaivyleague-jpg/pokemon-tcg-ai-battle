"""
Counterfactual analysis of Xerosic's Machinations and Supporter sequencing in losses.
"""

import csv
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent.parent

def analyze_losses():
    with open(HERE / "sol_eclipse_decision_audit.csv", "r", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    # Inspect games where Xerosic was played
    xerosic_games = set(r["game_id"] for r in records if "PLAY(Xerosic" in r["selected_desc"])
    all_games = set(r["game_id"] for r in records)
    
    # Calculate game-level win rates
    game_outcomes = {}
    for r in records:
        game_outcomes[r["game_id"]] = r["game_outcome"]

    xerosic_wins = sum(1 for g in xerosic_games if game_outcomes[g] == "WIN")
    xerosic_losses = sum(1 for g in xerosic_games if game_outcomes[g] == "LOSS")
    
    non_xerosic_games = all_games - xerosic_games
    non_xerosic_wins = sum(1 for g in non_xerosic_games if game_outcomes[g] == "WIN")
    non_xerosic_losses = sum(1 for g in non_xerosic_games if game_outcomes[g] == "LOSS")

    print(f"Games where Xerosic played: {len(xerosic_games)} games -> {xerosic_wins}W - {xerosic_losses}L ({xerosic_wins/len(xerosic_games)*100:.1f}% WR)")
    print(f"Games where Xerosic NOT played: {len(non_xerosic_games)} games -> {non_xerosic_wins}W - {non_xerosic_losses}L ({non_xerosic_wins/len(non_xerosic_games)*100:.1f}% WR)")

    # Inspect specific turns where Xerosic was played over Dawn or Hilda
    print("\nTurns where Xerosic was picked over Dawn/Hilda in LOSSES:")
    for r in records:
        if r["game_outcome"] != "LOSS": continue
        if "PLAY(Xerosic" not in r["selected_desc"]: continue
        opts = r["legal_options"].split(" | ")
        has_dawn = any("PLAY(Dawn)" in opt for opt in opts)
        has_hilda = any("PLAY(Hilda)" in opt for opt in opts)
        if has_dawn or has_hilda:
            print(f"  Game {r['game_id']} Step {r['step']} Turn {r['turn']}: Picked Xerosic over {'Dawn' if has_dawn else ''} {'Hilda' if has_hilda else ''} | Hand: {r['hand_size']} | My Active: {r['my_active']} | My Bench: {r['my_bench']}")

if __name__ == "__main__":
    analyze_losses()
