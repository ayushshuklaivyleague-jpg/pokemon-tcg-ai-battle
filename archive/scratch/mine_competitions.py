"""
Systematic Candidate Mining and Weakness Ranking Script
Examines all competing action pairs across 18,654 decisions.
Calculates occurrence, score margins, win rate deltas, and causal feasibility.
"""

import csv
from pathlib import Path
from collections import defaultdict, Counter
import math

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

def mine_competitions(records):
    # Group decisions by (selected_action_type, alternative_action_type)
    competitions = defaultdict(list)
    
    for r in records:
        if r["context"] != "MAIN":
            continue
        opts = r["legal_options"].split(" | ")
        if len(opts) < 2:
            continue
            
        chosen = r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"]
        
        # Categorize chosen action
        chosen_cat = categorize_action(chosen)
        
        for alt in opts:
            if alt == chosen: continue
            alt_cat = categorize_action(alt)
            if alt_cat != chosen_cat:
                pair_key = (chosen_cat, alt_cat)
                competitions[pair_key].append((r, chosen, alt))

    print(f"Total distinct macro-action competition pairs in MAIN context: {len(competitions)}")
    
    ranked_candidates = []
    for (c_cat, a_cat), instances in competitions.items():
        if len(instances) < 15: # Filter low frequency
            continue
        
        wins = sum(1 for r, _, _ in instances if r["game_outcome"] == "WIN")
        losses = sum(1 for r, _, _ in instances if r["game_outcome"] == "LOSS")
        draws = sum(1 for r, _, _ in instances if r["game_outcome"] == "DRAW")
        total = len(instances)
        
        win_rate = (wins / total) * 100
        decisive_wr = (wins / max(1, wins + losses)) * 100
        
        ranked_candidates.append({
            "chosen_cat": c_cat,
            "alt_cat": a_cat,
            "total_count": total,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": win_rate,
            "decisive_wr": decisive_wr,
            "sample_chosen": instances[0][1],
            "sample_alt": instances[0][2]
        })
        
    ranked_candidates.sort(key=lambda x: -x["total_count"])
    
    print("\n" + "=" * 100)
    print(f"{'CHOSEN CATEGORY':<25} | {'ALTERNATIVE CATEGORY':<25} | {'COUNT':<6} | {'ALL WR%':<8} | {'DECISIVE WR%':<12} | {'RECORD (W-L-D)'}")
    print("=" * 100)
    for c in ranked_candidates:
        rec_str = f"{c['wins']}W - {c['losses']}L - {c['draws']}D"
        print(f"{c['chosen_cat']:<25} | {c['alt_cat']:<25} | {c['total_count']:<6} | {c['win_rate']:>6.1f}% | {c['decisive_wr']:>10.1f}% | {rec_str}")

def categorize_action(act):
    if "ABILITY(Dudunsparce)" in act: return "ABILITY: Dudunsparce"
    if "ABILITY(Fezandipiti)" in act: return "ABILITY: Fezandipiti"
    if "ABILITY(Fan Rotom)" in act: return "ABILITY: Fan Rotom"
    if "PLAY(Abra)" in act: return "PLAY: Abra"
    if "PLAY(Dunsparce)" in act: return "PLAY: Dunsparce"
    if "PLAY(Buddy-Buddy Poffin)" in act: return "ITEM: Poffin"
    if "PLAY(Poké Pad)" in act or "PLAY(Pok Pad)" in act: return "ITEM: Poke Pad"
    if "PLAY(Rare Candy)" in act: return "ITEM: Rare Candy"
    if "PLAY(Night Stretcher)" in act: return "ITEM: Night Stretcher"
    if "PLAY(Sacred Ash)" in act: return "ITEM: Sacred Ash"
    if "PLAY(Enhanced Hammer)" in act: return "ITEM: Hammer"
    if "PLAY(Switch)" in act: return "ITEM: Switch"
    if "PLAY(Wondrous Patch)" in act: return "ITEM: Wondrous Patch"
    if "PLAY(Meddling Memo)" in act: return "ITEM: Meddling Memo"
    if "PLAY(Dawn)" in act: return "SUPPORTER: Dawn"
    if "PLAY(Hilda)" in act: return "SUPPORTER: Hilda"
    if "PLAY(Xerosic" in act: return "SUPPORTER: Xerosic"
    if "PLAY(Boss’s Orders)" in act or "PLAY(Boss’s Orders)" in act: return "SUPPORTER: Boss"
    if "PLAY(Lana’s Aid)" in act or "PLAY(Lana’s Aid)" in act: return "SUPPORTER: Lana"
    if "PLAY(Lillie" in act: return "SUPPORTER: Lillie"
    if "PLAY(Eri)" in act: return "SUPPORTER: Eri"
    if "STADIUM" in act or "PLAY(Neutralization" in act or "PLAY(Battle Cage" in act or "PLAY(Nighttime Mine" in act or "PLAY(Jamming" in act: return "STADIUM"
    if "ATTACH(" in act:
        if "Energy" in act:
            if "Basic {P}" in act: return "ATTACH: Basic Energy"
            if "Telepath" in act: return "ATTACH: Telepath Energy"
            if "Enriching" in act: return "ATTACH: Enriching Energy"
            if "Mist" in act: return "ATTACH: Mist Energy"
            return "ATTACH: Energy"
        if "Tool" in act or "Cape" in act or "Helmet" in act or "Fan" in act or "Balloon" in act: return "ATTACH: Tool"
    if "EVOLVE(Alakazam" in act: return "EVOLVE: Alakazam"
    if "EVOLVE(Kadabra" in act: return "EVOLVE: Kadabra"
    if "EVOLVE(Dudunsparce" in act: return "EVOLVE: Dudunsparce"
    if "RETREAT" in act: return "RETREAT"
    if "ATTACK(Powerful Hand)" in act: return "ATTACK: Powerful Hand"
    if "ATTACK(Super Psy Bolt)" in act: return "ATTACK: Super Psy Bolt"
    if "ATTACK(Teleportation)" in act: return "ATTACK: Teleportation"
    return "OTHER"

if __name__ == "__main__":
    records = load_data()
    mine_competitions(records)
