"""
Detailed inspection of the top competition pairs, score margins, and exact weights.
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

def inspect_competitions(records):
    # Top specific action pairs (not macro categories)
    pair_counts = Counter()
    pair_records = defaultdict(list)
    
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        if len(opts) < 2: continue
        
        chosen = r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"]
        
        for alt in opts:
            if alt == chosen: continue
            pair_key = (chosen, alt)
            pair_counts[pair_key] += 1
            pair_records[pair_key].append(r)
            
    print(f"Top 30 Exact Action Competitions in dataset:")
    print("=" * 110)
    print(f"{'CHOSEN ACTION':<40} | {'COMPETING ALTERNATIVE':<40} | {'COUNT':<5} | {'WR%':<6} | {'DEC WR%':<8}")
    print("=" * 110)
    
    for (c_act, a_act), cnt in pair_counts.most_common(40):
        insts = pair_records[(c_act, a_act)]
        wins = sum(1 for r in insts if r["game_outcome"] == "WIN")
        losses = sum(1 for r in insts if r["game_outcome"] == "LOSS")
        draws = sum(1 for r in insts if r["game_outcome"] == "DRAW")
        wr = (wins / len(insts)) * 100
        dec_wr = (wins / max(1, wins + losses)) * 100
        print(f"{c_act:<40} | {a_act:<40} | {cnt:>5} | {wr:>5.1f}% | {dec_wr:>7.1f}% ({wins}W-{losses}L-{draws}D)")

if __name__ == "__main__":
    records = load_data()
    inspect_competitions(records)
