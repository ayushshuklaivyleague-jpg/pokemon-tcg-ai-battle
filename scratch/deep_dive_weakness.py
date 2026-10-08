"""
Deep-dive counterfactual and failure mode investigation.
Analyzes specific competitive situations:
1. Supporter priority (Dawn vs Hilda vs Xerosic vs Lana)
2. Dudunsparce activation priority (30000 vs trainers)
3. Evolution vs Item priority (evolve_base 5951 vs poffin 18000 / pokepad 17000)
4. Energy attachment target selection
5. Teleportation vs Retreat
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict

HERE = Path(__file__).resolve().parent.parent

def deep_dive():
    with open(HERE / "sol_eclipse_decision_audit.csv", "r", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    print("=" * 80)
    print("SOL ECLIPSE DEEP DIVE BOTTLENECK INVESTIGATION")
    print("=" * 80)

    # 1. SUPPORTER COMPETITION
    supporter_names = ["Hilda", "Dawn", "Xerosic", "Lana", "Boss's Orders", "Lillie"]
    supporter_duels = []

    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        legal_supporters = [opt for opt in opts if any(f"PLAY({s}" in opt for s in supporter_names)]
        if len(legal_supporters) >= 2:
            supporter_duels.append((r, legal_supporters))

    print(f"\n1. MULTI-SUPPORTER COMPETITION STATES: {len(supporter_duels)} instances")
    sup_chosen = Counter()
    sup_combinations = Counter()
    sup_outcome_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0})

    for r, sups in supporter_duels:
        chosen = r["selected_desc"]
        sups_tuple = tuple(sorted([s.split("(")[1].split(")")[0] for s in sups]))
        sup_combinations[sups_tuple] += 1
        sup_chosen[chosen] += 1
        sup_outcome_stats[chosen]["total"] += 1
        if r["game_outcome"] == "WIN":
            sup_outcome_stats[chosen]["wins"] += 1
        else:
            sup_outcome_stats[chosen]["losses"] += 1

    print("\n  Supporter combinations encountered:")
    for combo, cnt in sup_combinations.most_common(8):
        print(f"    {' + '.join(combo)}: {cnt} times")

    print("\n  Supporter chosen in multi-supporter states:")
    for sup, cnt in sup_chosen.most_common():
        stats = sup_outcome_stats[sup]
        wr = (stats["wins"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"    {sup:<35} Chosen: {cnt:>3} | WR: {wr:>5.1f}% ({stats['wins']}W / {stats['losses']}L)")

    # 2. DUDUNSPARCE DRAW TIMING (Score 30,000)
    # Dudunsparce triggers at score 30,000, which is higher than playing Poffin (18,000), Poke Pad (17,000), etc.
    dudun_records = [r for r in records if "ABILITY(Dudunsparce)" in r["selected_desc"]]
    print(f"\n2. DUDUNSPARCE ABILITY TRIGGER: {len(dudun_records)} instances")
    dudun_hand_sizes = Counter(int(r["hand_size"]) for r in dudun_records)
    print("  Hand sizes when Dudunsparce used:")
    for hs in sorted(dudun_hand_sizes.keys()):
        print(f"    Hand size {hs}: {dudun_hand_sizes[hs]} times")

    # 3. EVOLUTION VS TRAINER SEQUENCING
    # Does the agent play Poffin/Poke Pad (17k-18k) before Evolving (5.9k)?
    simultaneous_evo_trainer = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_evo = any("EVOLVE" in opt for opt in opts)
        has_trainer = any("PLAY(Buddy-Buddy Poffin)" in opt or "PLAY(Poke Pad)" in opt for opt in opts)
        if has_evo and has_trainer:
            simultaneous_evo_trainer.append(r)

    print(f"\n3. SIMULTANEOUS EVOLUTION & SEARCH TRAINER (Poffin/PokePad): {len(simultaneous_evo_trainer)} instances")
    evo_trainer_chosen = Counter(r["selected_desc"].split("(")[0] for r in simultaneous_evo_trainer)
    for act, cnt in evo_trainer_chosen.most_common():
        print(f"    {act:<20} Chosen: {cnt:>3} ({cnt/len(simultaneous_evo_trainer)*100:.1f}%)")

    # 4. ENERGY ATTACHMENT VS EVOLUTION / SUPPORTER
    simultaneous_energy_trainer = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_attach = any("ATTACH" in opt for opt in opts)
        has_trainer = any("PLAY(" in opt and not any(p in opt for p in ("Abra", "Dunsparce")) for opt in opts)
        if has_attach and has_trainer:
            simultaneous_energy_trainer.append(r)

    print(f"\n4. SIMULTANEOUS ENERGY ATTACH & TRAINER PLAY: {len(simultaneous_energy_trainer)} instances")
    en_tr_chosen = Counter(r["selected_desc"].split("(")[0] for r in simultaneous_energy_trainer)
    for act, cnt in en_tr_chosen.most_common():
        print(f"    {act:<20} Chosen: {cnt:>3} ({cnt/len(simultaneous_energy_trainer)*100:.1f}%)")

    # 5. TO_HAND CONTEXT SEARCH CHOICES
    to_hand_records = [r for r in records if r["context"] == "TO_HAND"]
    print(f"\n5. TO_HAND CONTEXT SEARCH PICKS: {len(to_hand_records)} instances")
    to_hand_picks = Counter(r["selected_desc"] for r in to_hand_records)
    for p, cnt in to_hand_picks.most_common(12):
        print(f"    {p:<40} {cnt:>3}")

    # 6. POKEPAD / HILDA SUPPORTER TARGETS
    # What does Poke Pad search for?
    # Context TO_HAND cards chosen from deck/discard
    print("=" * 80)

if __name__ == "__main__":
    deep_dive()
