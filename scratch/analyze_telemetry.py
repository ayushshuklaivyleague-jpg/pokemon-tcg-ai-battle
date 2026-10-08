"""
Comprehensive analysis of sol_eclipse_decision_audit.csv and sol_eclipse_weight_usage.csv.
Performs Phase 3 (Bottleneck Ranking) and Phase 4 (Counterfactual Analysis).
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict, Counter
import math

HERE = Path(__file__).resolve().parent.parent

def analyze_audit():
    audit_csv = HERE / "sol_eclipse_decision_audit.csv"
    if not audit_csv.exists():
        print(f"File not found: {audit_csv}")
        return

    with open(audit_csv, "r", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    total_decisions = len(records)
    print("=" * 80)
    print(f"SOL ECLIPSE DECISION AUDIT ANALYSIS ({total_decisions} DECISIONS)")
    print("=" * 80)

    # 1. Context Breakdown
    contexts = Counter(r["context"] for r in records)
    print("\n1. DECISIONS BY CONTEXT:")
    for ctx, count in contexts.most_common():
        pct = (count / total_decisions) * 100
        print(f"  {ctx:<30} {count:>5} ({pct:>5.1f}%)")

    # 2. Search Layer Analysis
    search_invoked = [r for r in records if r["search_invoked"].lower() == "true"]
    search_overrides = [r for r in records if r["search_override"].lower() == "true"]
    courage_overrides = [r for r in records if r["courage_override"].lower() == "true"]

    print("\n2. SEARCH & GUARD TELEMETRY:")
    print(f"  Total Search Invocations: {len(search_invoked)} / {total_decisions} ({len(search_invoked)/max(1,total_decisions)*100:.1f}%)")
    print(f"  Total Search Overrides:   {len(search_overrides)} / {max(1,len(search_invoked))} invoked ({len(search_overrides)/max(1,len(search_invoked))*100:.1f}%)")
    print(f"  Total Courage Overrides:  {len(courage_overrides)} / {total_decisions} ({len(courage_overrides)/max(1,total_decisions)*100:.1f}%)")

    if search_overrides:
        print("\n  Top Search Overrides (Heuristic -> Search Pick):")
        so_counts = Counter((r["heuristic_top_desc"], r["selected_desc"]) for r in search_overrides)
        for (h_desc, s_desc), count in so_counts.most_common(10):
            print(f"    {h_desc} -> {s_desc} (x{count})")

    if courage_overrides:
        print("\n  Top Courage Overrides:")
        co_counts = Counter((r["heuristic_top_desc"], r["selected_desc"]) for r in courage_overrides)
        for (h_desc, s_desc), count in co_counts.most_common(10):
            print(f"    {h_desc} -> {s_desc} (x{count})")

    # 3. Action Type in MAIN context
    main_records = [r for r in records if r["context"] == "MAIN"]
    main_actions = Counter(r["selected_desc"].split("(")[0] for r in main_records)
    print("\n3. MAIN CONTEXT ACTION BREAKDOWN:")
    for act, count in main_actions.most_common():
        pct = (count / max(1, len(main_records))) * 100
        print(f"  {act:<30} {count:>5} ({pct:>5.1f}%)")

    # 4. Detailed Investigation: Evolution Sequencing
    evolves = [r for r in main_records if "EVOLVE" in r["selected_desc"]]
    print(f"\n4. EVOLUTIONS ({len(evolves)} total):")
    evolve_targets = Counter(r["selected_desc"] for r in evolves)
    for desc, cnt in evolve_targets.most_common():
        print(f"  {desc:<45} {cnt:>4}")

    # 5. Detailed Investigation: Energy Attachments
    attaches = [r for r in main_records if "ATTACH" in r["selected_desc"]]
    print(f"\n5. ENERGY ATTACHMENTS ({len(attaches)} total):")
    attach_targets = Counter(r["selected_desc"] for r in attaches)
    for desc, cnt in attach_targets.most_common():
        print(f"  {desc:<45} {cnt:>4}")

    # 6. Detailed Investigation: Trainer Plays
    trainers = [r for r in main_records if "PLAY" in r["selected_desc"] and not any(p in r["selected_desc"] for p in ("Abra", "Dunsparce", "Dudunsparce"))]
    print(f"\n6. TRAINER PLAYS ({len(trainers)} total):")
    trainer_counts = Counter(r["selected_desc"] for r in trainers)
    for desc, cnt in trainer_counts.most_common():
        print(f"  {desc:<45} {cnt:>4}")

    # 7. Detailed Investigation: Abilities (Dudunsparce Draw)
    abilities = [r for r in main_records if "ABILITY" in r["selected_desc"]]
    print(f"\n7. ABILITY ACTIVATIONS ({len(abilities)} total):")
    for desc, cnt in Counter(r["selected_desc"] for r in abilities).most_common():
        print(f"  {desc:<45} {cnt:>4}")

    # 8. Detailed Investigation: Attacks
    attacks = [r for r in main_records if "ATTACK" in r["selected_desc"]]
    print(f"\n8. ATTACKS ({len(attacks)} total):")
    for desc, cnt in Counter(r["selected_desc"] for r in attacks).most_common():
        print(f"  {desc:<45} {cnt:>4}")

    # 9. Multi-option competition analysis in MAIN context
    # Where 2+ options had non-negative scores and competed
    competing_records = []
    for r in main_records:
        all_s = [float(x) for x in r["all_scores"].split(",") if x]
        pos_s = [s for s in all_s if s > 0]
        if len(pos_s) >= 2:
            competing_records.append(r)

    print(f"\n9. COMPETITIVE MAIN DECISIONS (2+ valid positive actions): {len(competing_records)} / {len(main_records)} ({len(competing_records)/max(1,len(main_records))*100:.1f}%)")

    # 10. Losses analysis & Bottleneck discovery
    losing_records = [r for r in records if r["game_outcome"] == "LOSS"]
    print(f"\n10. DECISIONS IN LOSSES ({len(losing_records)} records):")
    
    # Check energy attachment in losses vs wins
    # Check supporter choice when multiple supporters in hand
    # Check poffin vs pokepad vs hilda sequencing

if __name__ == "__main__":
    analyze_audit()
