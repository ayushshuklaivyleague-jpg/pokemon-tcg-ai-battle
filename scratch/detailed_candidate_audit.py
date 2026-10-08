"""
Deep investigation into:
1. Rare Candy (16000) vs Kadabra Manual Evolution (6051)
2. Kadabra (6051) vs Dudunsparce (6031)
3. Dawn (3100) vs Hilda (3000)
4. Night Stretcher (13000) vs Sacred Ash (13500)
5. Bench placement: Abra vs Dunsparce
6. Search Disagreements across the whole dataset
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

def detailed_candidate_audit(records):
    print("=" * 80)
    print("DEEP CANDIDATE WEAKNESS AUDIT")
    print("=" * 80)

    # 1. Rare Candy vs Kadabra
    rc_kad_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_rc = any("PLAY(Rare Candy)" in o for o in opts)
        has_kad = any("EVOLVE(Kadabra" in o for o in opts)
        if has_rc and has_kad:
            rc_kad_states.append(r)

    print(f"\n1. RARE CANDY vs KADABRA EVOLUTION STATES: {len(rc_kad_states)} instances")
    rc_picks = Counter(r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"] for r in rc_kad_states)
    for p, cnt in rc_picks.most_common():
        print(f"   Chosen: {p:<45} Count: {cnt}")

    # 2. Kadabra vs Dudunsparce Evolution
    kad_dudun_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_kad = any("EVOLVE(Kadabra" in o for o in opts)
        has_dudun = any("EVOLVE(Dudunsparce" in o for o in opts)
        if has_kad and has_dudun:
            kad_dudun_states.append(r)

    print(f"\n2. KADABRA vs DUDUNSPARCE EVOLUTION STATES: {len(kad_dudun_states)} instances")
    kd_picks = Counter(r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"] for r in kad_dudun_states)
    for p, cnt in kd_picks.most_common():
        print(f"   Chosen: {p:<45} Count: {cnt}")

    # 3. Night Stretcher vs Sacred Ash
    ns_ash_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_ns = any("PLAY(Night Stretcher)" in o for o in opts)
        has_ash = any("PLAY(Sacred Ash)" in o for o in opts)
        if has_ns and has_ash:
            ns_ash_states.append(r)

    print(f"\n3. NIGHT STRETCHER vs SACRED ASH STATES: {len(ns_ash_states)} instances")
    na_picks = Counter(r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"] for r in ns_ash_states)
    for p, cnt in na_picks.most_common():
        print(f"   Chosen: {p:<45} Count: {cnt}")

    # 4. Search vs Heuristic Disagreements
    search_overrides = [r for r in records if "override" in r and r["override"] == "True"]
    print(f"\n4. SEARCH OVERRIDES IN DATASET: {len(search_overrides)} instances")
    so_trans = Counter((r["selected_desc"], r["candidate_desc"]) for r in search_overrides)
    for (sel, cand), cnt in so_trans.most_common(15):
        print(f"   {sel:<40} -> {cand:<40} | Count: {cnt}")

    # 5. Poffin vs Pokepad vs Evolution
    poffin_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_poffin = any("PLAY(Buddy-Buddy Poffin)" in o for o in opts)
        has_evo = any("EVOLVE(" in o for o in opts)
        if has_poffin and has_evo:
            poffin_states.append(r)
    print(f"\n5. POFFIN vs EVOLUTION STATES: {len(poffin_states)} instances")
    poff_picks = Counter(r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"] for r in poffin_states)
    for p, cnt in poff_picks.most_common(10):
        print(f"   Chosen: {p:<45} Count: {cnt}")

if __name__ == "__main__":
    records = load_data()
    detailed_candidate_audit(records)
