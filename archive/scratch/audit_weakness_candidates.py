import sys
from pathlib import Path
import pandas as pd
from collections import defaultdict

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.game import battle_start, battle_select, battle_finish
from ptcg_planning.state_features import extract_state_features

print("=" * 70)
print("AUDITING LIVE SIMULATOR DECISIONS ACROSS 100 MATCHES")
print("=" * 70)

events = defaultdict(list)
context_counts = defaultdict(int)
multi_choice_counts = defaultdict(int)
main_combinations = defaultdict(int)
attach_target_breakdown = defaultdict(int)
supporter_attach_breakdown = defaultdict(int)
evolve_target_breakdown = defaultdict(int)
attack_selection_breakdown = defaultdict(int)

for g in range(100):
    obs, _ = battle_start(main.DECK, main.DECK)
    try:
        step = 0
        while True:
            res = obs.get("current", {}).get("result", None)
            if res is not None and res != -1:
                break
            select = obs.get("select")
            if not select:
                break

            ctx = select.get("context")
            ctx_name = main.SelectContext(ctx).name if ctx is not None else "NONE"
            context_counts[ctx_name] += 1

            options = select.get("option", [])
            if len(options) > 1:
                multi_choice_counts[ctx_name] += 1

            obs_cls = main.to_observation_class(obs)
            player_idx = obs_cls.current.yourIndex
            player = obs_cls.current.players[player_idx]
            opp_player = obs_cls.current.players[1 - player_idx]
            state = extract_state_features(obs_cls)

            if ctx_name == "MAIN":
                opt_types = [main.option_type_name(o) for o in obs_cls.select.option]
                unique_types = tuple(sorted(set(opt_types)))
                main_combinations[unique_types] += 1

                # 1. ATTACH targets
                attach_indices = [i for i, t in enumerate(opt_types) if t == "ATTACH"]
                if len(attach_indices) > 1:
                    # Check targets of attach options
                    targets = []
                    for ai in attach_indices:
                        opt = obs_cls.select.option[ai]
                        area = getattr(opt, "inPlayArea", None)
                        idx = getattr(opt, "inPlayIndex", 0)
                        targets.append((area, idx))
                    act_pkmn = player.active[0] if player.active else None
                    act_e = len(act_pkmn.energyCards) if act_pkmn and hasattr(act_pkmn, "energyCards") else 0
                    attach_target_breakdown[f"active_e={act_e}, bench_count={len(player.bench or [])}"] += 1
                    events["multi_attach_targets"].append({
                        "game": g, "step": step, "active_e": act_e,
                        "bench_count": len(player.bench or []), "targets": targets
                    })

                # 2. Supporter + Attach co-occurrence
                play_indices = [i for i, t in enumerate(opt_types) if t == "PLAY"]
                if play_indices and attach_indices:
                    supp_cards = []
                    for pi in play_indices:
                        opt = obs_cls.select.option[pi]
                        c = main.v4_card_from_option(obs_cls, opt)
                        if c and main.v4_is_supporter(c):
                            cdata = main.v4_card_data(c)
                            cname = getattr(cdata, "name", "None") if cdata else "None"
                            supp_cards.append(cname)
                    if supp_cards:
                        supporter_attach_breakdown[tuple(sorted(supp_cards))] += 1
                        events["supporter_and_attach"].append({
                            "game": g, "step": step, "supporters": supp_cards,
                            "hand_size": len(player.hand or [])
                        })

                # 3. Evolution targets
                evolve_indices = [i for i, t in enumerate(opt_types) if t == "EVOLVE"]
                if len(evolve_indices) > 1:
                    evolve_target_breakdown[len(evolve_indices)] += 1
                    events["multi_evolve"].append({
                        "game": g, "step": step, "num_evolve": len(evolve_indices)
                    })

                # 4. Multi-attack in MAIN
                attack_indices = [i for i, t in enumerate(opt_types) if t == "ATTACK"]
                if len(attack_indices) > 1:
                    attack_selection_breakdown[len(attack_indices)] += 1
                    events["multi_attack"].append({
                        "game": g, "step": step, "num_attacks": len(attack_indices)
                    })

            # Check ATTACK context
            if ctx_name == "ATTACK" and len(options) > 1:
                events["attack_context_multi"].append({
                    "game": g, "step": step, "num_options": len(options)
                })

            choice = main.agent(obs)
            obs = battle_select(choice)
            step += 1
    finally:
        battle_finish()

print("\n--- Context Frequencies & Multi-Choice Rates ---")
for ctx, total in sorted(context_counts.items(), key=lambda x: x[1], reverse=True):
    mc = multi_choice_counts[ctx]
    mc_pct = (mc / total) * 100.0 if total > 0 else 0.0
    print(f"  {ctx:<25} | Total: {total:5d} | Multi-Choice: {mc:5d} ({mc_pct:5.1f}%)")

print("\n--- Action Combinations in MAIN Context ---")
for comb, count in sorted(main_combinations.items(), key=lambda x: x[1], reverse=True):
    print(f"  {str(comb):<55} : {count:4d}")

print("\n--- Candidate 1: Multiple ATTACH Targets (Active vs Bench) ---")
print(f"Total occurrences in 100 matches: {len(events['multi_attach_targets'])}")
for k, v in sorted(attach_target_breakdown.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {k:<45} : {v:4d}")

print("\n--- Candidate 2: Supporter + Attach Co-occurrence in MAIN ---")
print(f"Total occurrences in 100 matches: {len(events['supporter_and_attach'])}")
for k, v in sorted(supporter_attach_breakdown.items(), key=lambda x: x[1], reverse=True):
    print(f"  {str(k):<45} : {v:4d}")

print("\n--- Candidate 3: Multiple EVOLVE Targets in MAIN ---")
print(f"Total occurrences in 100 matches: {len(events['multi_evolve'])}")
for k, v in sorted(evolve_target_breakdown.items(), key=lambda x: x[1], reverse=True):
    print(f"  {k} evolution options : {v:4d}")

print("\n--- Candidate 4: Multi-Attack Choices in MAIN / ATTACK ---")
print(f"Total occurrences in MAIN: {len(events['multi_attack'])}, in ATTACK ctx: {len(events['attack_context_multi'])}")
