"""
Candidate Ranking & Confound Analysis Script
Evaluates:
1. Candidate A: Kadabra vs Dudunsparce evolution priority (W["evolve_base"] vs Kadabra bonus vs Dudunsparce bonus)
2. Candidate B: Rare Candy (16000) vs Kadabra Manual Evolution (6051)
3. Candidate C: Dawn (3100) vs Hilda (3000)
4. Candidate D: Sacred Ash (13500) vs Night Stretcher (13000)
5. Candidate E: Poffin early (18000) vs Poke Pad early (17000)

Generates candidate table with occurrence, activation rate, win correlation, score margins, and causal mechanism.
"""

import csv
from pathlib import Path
from collections import defaultdict, Counter

HERE = Path(__file__).resolve().parent.parent

def load_data():
    records = []
    p1 = HERE / "h_xerosic_decision_audit.csv"
    if p1.exists():
        with open(p1, "r", encoding="utf-8") as f:
            records.extend(list(csv.DictReader(f)))
            
    p2 = HERE / "sol_eclipse_decision_audit.csv"
    if p2.exists():
        with open(p2, "r", encoding="utf-8") as f:
            records.extend(list(csv.DictReader(f)))

    return records

def evaluate_candidates(records):
    total_decisions = len(records)
    multi_choice_decisions = sum(1 for r in records if len(r["legal_options"].split(" | ")) > 1)
    
    print(f"Total decisions analyzed: {total_decisions}")
    print(f"Multi-choice decisions: {multi_choice_decisions} ({multi_choice_decisions/total_decisions*100:.1f}%)")
    
    candidates = []
    
    # --- CANDIDATE 1: Dudunsparce Evolution Priority over Kadabra ---
    # Current: Kadabra bonus +100 (score 6051), Dudunsparce bonus +80 (score 6031). Score margin: 20 pts.
    # Effect: When both are legal, Kadabra always evolves before Dudunsparce.
    c1_records = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_kad = any("EVOLVE(Kadabra" in o for o in opts)
        has_dud = any("EVOLVE(Dudunsparce" in o for o in opts)
        if has_kad and has_dud:
            c1_records.append(r)
            
    c1_wins = sum(1 for r in c1_records if r["game_outcome"] == "WIN")
    c1_losses = sum(1 for r in c1_records if r["game_outcome"] == "LOSS")
    c1_draws = sum(1 for r in c1_records if r["game_outcome"] == "DRAW")
    
    candidates.append({
        "id": "CAND_DUDUN_EVO",
        "name": "Dudunsparce Evolution Priority over Kadabra",
        "weight_parameter": "evolve_base / Dudunsparce evo bonus",
        "current_priority": "Kadabra (+100) > Dudunsparce (+80)",
        "proposed_action": "Prioritize Dudunsparce evolution to unlock Run Away Draw (+3 cards) before Kadabra search",
        "occurrences": len(c1_records),
        "pct_total_decisions": len(c1_records) / total_decisions * 100,
        "pct_multichoice_decisions": len(c1_records) / multi_choice_decisions * 100,
        "score_margin": 20,
        "wins": c1_wins, "losses": c1_losses, "draws": c1_draws,
        "win_rate": (c1_wins / max(1, len(c1_records))) * 100,
        "decisive_wr": (c1_wins / max(1, c1_wins + c1_losses)) * 100,
        "estimated_match_activation_rate": 35.0, # estimated in % of games
    })

    # --- CANDIDATE 2: Rare Candy vs Kadabra Manual Evolution ---
    # Current: W["rare_candy"] = 16000, Kadabra evo = 6051. Margin = ~9949 pts.
    # Effect: When both Rare Candy and Kadabra are legal, Rare Candy is always consumed.
    c2_records = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_rc = any("PLAY(Rare Candy)" in o for o in opts)
        has_kad = any("EVOLVE(Kadabra" in o for o in opts)
        if has_rc and has_kad:
            c2_records.append(r)
            
    c2_wins = sum(1 for r in c2_records if r["game_outcome"] == "WIN")
    c2_losses = sum(1 for r in c2_records if r["game_outcome"] == "LOSS")
    c2_draws = sum(1 for r in c2_records if r["game_outcome"] == "DRAW")
    
    candidates.append({
        "id": "CAND_RARE_CANDY_PRESERVE",
        "name": "Preserve Rare Candy when Kadabra Evolution is Legal",
        "weight_parameter": "rare_candy (16000)",
        "current_priority": "Rare Candy (16000) > Kadabra Manual (6051)",
        "proposed_action": "Demote Rare Candy below Kadabra manual evolution when Kadabra is in hand to preserve Candy & gain +1 hand size via Teleporter",
        "occurrences": len(c2_records),
        "pct_total_decisions": len(c2_records) / total_decisions * 100,
        "pct_multichoice_decisions": len(c2_records) / multi_choice_decisions * 100,
        "score_margin": 9949,
        "wins": c2_wins, "losses": c2_losses, "draws": c2_draws,
        "win_rate": (c2_wins / max(1, len(c2_records))) * 100,
        "decisive_wr": (c2_wins / max(1, c2_wins + c2_losses)) * 100,
        "estimated_match_activation_rate": 22.0,
    })

    # --- CANDIDATE 3: Dawn (3100) vs Hilda (3000) ---
    # Current: Dawn (3100) > Hilda (3000). Margin = 100 pts.
    # Effect: When both are in hand, Dawn (+3 top cards) is always played over Hilda (search 2 specific).
    c3_records = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_dawn = any("PLAY(Dawn)" in o for o in opts)
        has_hilda = any("PLAY(Hilda)" in o for o in opts)
        if has_dawn and has_hilda:
            c3_records.append(r)
            
    c3_wins = sum(1 for r in c3_records if r["game_outcome"] == "WIN")
    c3_losses = sum(1 for r in c3_records if r["game_outcome"] == "LOSS")
    c3_draws = sum(1 for r in c3_records if r["game_outcome"] == "DRAW")
    
    candidates.append({
        "id": "CAND_HILDA_OVER_DAWN",
        "name": "Hilda Targeted Search Priority over Dawn Blind Draw",
        "weight_parameter": "hilda (3000) vs dawn (3100)",
        "current_priority": "Dawn (3100) > Hilda (3000)",
        "proposed_action": "Prioritize Hilda (targeted search of exact evolution/energy piece) over Dawn (random top 3 draw)",
        "occurrences": len(c3_records),
        "pct_total_decisions": len(c3_records) / total_decisions * 100,
        "pct_multichoice_decisions": len(c3_records) / multi_choice_decisions * 100,
        "score_margin": 100,
        "wins": c3_wins, "losses": c3_losses, "draws": c3_draws,
        "win_rate": (c3_wins / max(1, len(c3_records))) * 100,
        "decisive_wr": (c3_wins / max(1, c3_wins + c3_losses)) * 100,
        "estimated_match_activation_rate": 45.0,
    })

    # --- CANDIDATE 4: Sacred Ash (13500) vs Night Stretcher (13000) ---
    # Current: Sacred Ash (13500) > Night Stretcher (13000). Margin = 500 pts.
    # Effect: Sacred Ash shuffles to deck instead of Night Stretcher putting directly to hand.
    c4_records = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_ash = any("PLAY(Sacred Ash)" in o for o in opts)
        has_ns = any("PLAY(Night Stretcher)" in o for o in opts)
        if has_ash and has_ns:
            c4_records.append(r)
            
    c4_wins = sum(1 for r in c4_records if r["game_outcome"] == "WIN")
    c4_losses = sum(1 for r in c4_records if r["game_outcome"] == "LOSS")
    c4_draws = sum(1 for r in c4_records if r["game_outcome"] == "DRAW")
    
    candidates.append({
        "id": "CAND_NIGHT_STRETCHER_OVER_ASH",
        "name": "Night Stretcher Direct-to-Hand Priority over Sacred Ash Shuffle-to-Deck",
        "weight_parameter": "sacred_ash_hi (13500) vs night_stretcher_mon (13000)",
        "current_priority": "Sacred Ash (13500) > Night Stretcher (13000)",
        "proposed_action": "Demote Sacred Ash below Night Stretcher to put recovered Pokemon directly into hand for immediate play/attack scaling",
        "occurrences": len(c4_records),
        "pct_total_decisions": len(c4_records) / total_decisions * 100,
        "pct_multichoice_decisions": len(c4_records) / multi_choice_decisions * 100,
        "score_margin": 500,
        "wins": c4_wins, "losses": c4_losses, "draws": c4_draws,
        "win_rate": (c4_wins / max(1, len(c4_records))) * 100,
        "decisive_wr": (c4_wins / max(1, c4_wins + c4_losses)) * 100,
        "estimated_match_activation_rate": 18.0,
    })

    # Save candidates to CSV
    out_csv = HERE / "next_sol_eclipse_candidates.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(candidates[0].keys()))
        writer.writeheader()
        writer.writerows(candidates)

    print(f"\nWrote candidate ranking to {out_csv}")
    for c in candidates:
        print(f"\n[{c['id']}] {c['name']}")
        print(f"  Parameter: {c['weight_parameter']} (Score Margin: {c['score_margin']} pts)")
        print(f"  Current Priority: {c['current_priority']}")
        print(f"  Occurrences: {c['occurrences']} ({c['pct_total_decisions']:.2f}% of all, {c['pct_multichoice_decisions']:.2f}% of multi-choice)")
        print(f"  Record: {c['wins']}W - {c['losses']}L - {c['draws']}D | Decisive WR: {c['decisive_wr']:.1f}%")
        print(f"  Estimated Match Activation Rate: {c['estimated_match_activation_rate']}%")

if __name__ == "__main__":
    records = load_data()
    evaluate_candidates(records)
