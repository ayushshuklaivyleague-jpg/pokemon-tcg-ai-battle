"""
Exhaustive genome & decision mining script across 18,654 combined decisions.
Analyzes every competing action category in Sol Eclipse:
1. Energy attachment target selection (Active Abra vs Bench Abra vs Kadabra vs Alakazam)
2. Evolution line sequencing (Evolve Dudunsparce vs Evolve Kadabra vs Evolve Alakazam vs Rare Candy)
3. Trainer play vs Evolution timing (Item search before evolution vs evolving first)
4. Dawn vs Hilda choice when Xerosic is not chosen
5. Night Stretcher vs Sacred Ash recycling priorities
6. Bench placement & Pokemon play choices (Abra vs Dunsparce priority)
7. Neutralization Zone timing vs EX/Non-EX
8. Attack selection (Powerful Hand vs Super Psy Bolt vs Teleportation)
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict
import math

HERE = Path(__file__).resolve().parent.parent

def load_data():
    records = []
    # Load 15,012 records from H_XEROSIC benchmark
    p1 = HERE / "h_xerosic_decision_audit.csv"
    if p1.exists():
        with open(p1, "r", encoding="utf-8") as f:
            records.extend(list(csv.DictReader(f)))
            
    # Load 3,642 records from original audit
    p2 = HERE / "sol_eclipse_decision_audit.csv"
    if p2.exists():
        with open(p2, "r", encoding="utf-8") as f:
            records.extend(list(csv.DictReader(f)))

    print(f"Total dataset records loaded: {len(records)}")
    return records


def analyze_candidates(records):
    print("=" * 80)
    print("SOL ECLIPSE DEEP MINING & CANDIDATE BOTTLENECK DISCOVERY")
    print("=" * 80)

    # 1. ENERGY ATTACHMENT TARGET PRIORITIES
    # Inspect when ATTACH is legal for multiple targets
    attach_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        attach_opts = [o for o in opts if "ATTACH(" in o]
        if len(attach_opts) >= 2:
            attach_states.append((r, attach_opts))

    print(f"\n1. MULTI-TARGET ENERGY ATTACHMENT STATES: {len(attach_states)} instances")
    attach_chosen = Counter()
    attach_wr = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "total": 0})
    for r, opts in attach_states:
        chosen = r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"]
        attach_chosen[chosen] += 1
        outcome = r["game_outcome"]
        attach_wr[chosen]["total"] += 1
        if outcome == "WIN": attach_wr[chosen]["wins"] += 1
        elif outcome == "LOSS": attach_wr[chosen]["losses"] += 1
        else: attach_wr[chosen]["draws"] += 1

    for act, cnt in attach_chosen.most_common(12):
        st = attach_wr[act]
        wr = (st["wins"] / max(1, st["total"])) * 100
        dec_wr = (st["wins"] / max(1, st["wins"] + st["losses"])) * 100
        print(f"    {act:<50} Count: {cnt:>4} | All WR: {wr:>5.1f}% | Decisive WR: {dec_wr:>5.1f}% ({st['wins']}W / {st['losses']}L / {st['draws']}D)")

    # 2. EVOLUTION COMPETITIONS (Kadabra vs Dudunsparce vs Alakazam)
    evo_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        evo_opts = [o for o in opts if "EVOLVE(" in o]
        if len(evo_opts) >= 2:
            evo_states.append((r, evo_opts))

    print(f"\n2. MULTI-EVOLUTION STATES (e.g. Kadabra vs Dudunsparce): {len(evo_states)} instances")
    evo_chosen = Counter()
    evo_wr = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "total": 0})
    for r, opts in evo_states:
        chosen = r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"]
        evo_chosen[chosen] += 1
        outcome = r["game_outcome"]
        evo_wr[chosen]["total"] += 1
        if outcome == "WIN": evo_wr[chosen]["wins"] += 1
        elif outcome == "LOSS": evo_wr[chosen]["losses"] += 1
        else: evo_wr[chosen]["draws"] += 1

    for act, cnt in evo_chosen.most_common(10):
        st = evo_wr[act]
        wr = (st["wins"] / max(1, st["total"])) * 100
        dec_wr = (st["wins"] / max(1, st["wins"] + st["losses"])) * 100
        print(f"    {act:<50} Count: {cnt:>4} | All WR: {wr:>5.1f}% | Decisive WR: {dec_wr:>5.1f}% ({st['wins']}W / {st['losses']}L / {st['draws']}D)")

    # 3. DAWN VS HILDA DIRECT DUELS (when Xerosic is not chosen)
    dawn_hilda_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_dawn = any("PLAY(Dawn)" in o for o in opts)
        has_hilda = any("PLAY(Hilda)" in o for o in opts)
        if has_dawn and has_hilda:
            dawn_hilda_states.append(r)

    print(f"\n3. DAWN VS HILDA DIRECT COMPETITION STATES: {len(dawn_hilda_states)} instances")
    dh_chosen = Counter()
    dh_wr = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "total": 0})
    for r in dawn_hilda_states:
        chosen = r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"]
        dh_chosen[chosen] += 1
        outcome = r["game_outcome"]
        dh_wr[chosen]["total"] += 1
        if outcome == "WIN": dh_wr[chosen]["wins"] += 1
        elif outcome == "LOSS": dh_wr[chosen]["losses"] += 1
        else: dh_wr[chosen]["draws"] += 1

    for act, cnt in dh_chosen.most_common(8):
        st = dh_wr[act]
        wr = (st["wins"] / max(1, st["total"])) * 100
        dec_wr = (st["wins"] / max(1, st["wins"] + st["losses"])) * 100
        print(f"    {act:<50} Count: {cnt:>4} | All WR: {wr:>5.1f}% | Decisive WR: {dec_wr:>5.1f}% ({st['wins']}W / {st['losses']}L / {st['draws']}D)")

    # 4. BASIC POKEMON PLAY FROM HAND (Abra vs Dunsparce)
    basic_comp_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_abra = any("PLAY(Abra)" in o for o in opts)
        has_dun = any("PLAY(Dunsparce)" in o for o in opts)
        if has_abra and has_dun:
            basic_comp_states.append(r)

    print(f"\n4. BASIC POKEMON BENCH PLACEMENT (Abra vs Dunsparce): {len(basic_comp_states)} instances")
    b_chosen = Counter()
    b_wr = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "total": 0})
    for r in basic_comp_states:
        chosen = r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"]
        b_chosen[chosen] += 1
        outcome = r["game_outcome"]
        b_wr[chosen]["total"] += 1
        if outcome == "WIN": b_wr[chosen]["wins"] += 1
        elif outcome == "LOSS": b_wr[chosen]["losses"] += 1
        else: b_wr[chosen]["draws"] += 1

    for act, cnt in b_chosen.most_common(8):
        st = b_wr[act]
        wr = (st["wins"] / max(1, st["total"])) * 100
        dec_wr = (st["wins"] / max(1, st["wins"] + st["losses"])) * 100
        print(f"    {act:<50} Count: {cnt:>4} | All WR: {wr:>5.1f}% | Decisive WR: {dec_wr:>5.1f}% ({st['wins']}W / {st['losses']}L / {st['draws']}D)")

    # 5. RECYCLING CARDS (Night Stretcher vs Sacred Ash)
    recycle_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_ns = any("PLAY(Night Stretcher)" in o for o in opts)
        has_ash = any("PLAY(Sacred Ash)" in o for o in opts)
        if has_ns and has_ash:
            recycle_states.append(r)

    print(f"\n5. RECYCLING ITEM COMPETITION (Night Stretcher vs Sacred Ash): {len(recycle_states)} instances")
    rc_chosen = Counter()
    rc_wr = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "total": 0})
    for r in recycle_states:
        chosen = r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"]
        rc_chosen[chosen] += 1
        outcome = r["game_outcome"]
        rc_wr[chosen]["total"] += 1
        if outcome == "WIN": rc_wr[chosen]["wins"] += 1
        elif outcome == "LOSS": rc_wr[chosen]["losses"] += 1
        else: rc_wr[chosen]["draws"] += 1

    for act, cnt in rc_chosen.most_common(8):
        st = rc_wr[act]
        wr = (st["wins"] / max(1, st["total"])) * 100
        dec_wr = (st["wins"] / max(1, st["wins"] + st["losses"])) * 100
        print(f"    {act:<50} Count: {cnt:>4} | All WR: {wr:>5.1f}% | Decisive WR: {dec_wr:>5.1f}% ({st['wins']}W / {st['losses']}L / {st['draws']}D)")

    # 6. ATTACK SELECTION (Powerful Hand vs Teleportation vs Super Psy Bolt)
    atk_states = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        atk_opts = [o for o in opts if "ATTACK(" in o]
        if len(atk_opts) >= 2:
            atk_states.append((r, atk_opts))

    print(f"\n6. MULTI-ATTACK SELECTION STATES: {len(atk_states)} instances")

    # 7. NIGHT STRETCHER / POKEPAD TARGET SELECTION in TO_HAND
    to_hand_records = [r for r in records if r["context"] == "TO_HAND"]
    print(f"\n7. TO_HAND CONTEXT DECISIONS: {len(to_hand_records)} instances")
    th_picks = Counter(r["candidate_desc"] if "candidate_desc" in r and r["candidate_desc"] != "None" else r["selected_desc"] for r in to_hand_records)
    for p, cnt in th_picks.most_common(12):
        print(f"    {p:<50} {cnt:>4}")

    print("=" * 80)

if __name__ == "__main__":
    records = load_data()
    analyze_candidates(records)
