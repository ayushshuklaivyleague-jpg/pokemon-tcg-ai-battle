import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.api import LogType
from cg.game import battle_start, battle_select, battle_finish

print("=" * 70)
print("INSPECTING ALL ATTACKS: KYOGRE (1042 vs 1043) & SNOVER (1044 vs 1045)")
print("=" * 70)

# Let's inspect Kyogre:
# Attack 1042 vs 1043:
# What are the requirements and effects?

def test_attack_choice(pkmn_name, target_aid):
    records = []
    for g in range(30):
        obs, _ = battle_start(main.DECK, main.DECK)
        try:
            while True:
                res = obs.get("current", {}).get("result", None)
                if res is not None and res != -1:
                    break
                select = obs.get("select")
                if not select:
                    break

                ctx = select.get("context")
                ctx_name = main.SelectContext(ctx).name if ctx is not None else "NONE"
                obs_cls = main.to_observation_class(obs)
                player_idx = obs_cls.current.yourIndex
                player = obs_cls.current.players[player_idx]
                opp_player = obs_cls.current.players[1 - player_idx]

                options = obs_cls.select.option
                
                if ctx_name == "MAIN":
                    attack_opts = [
                        (i, opt) for i, opt in enumerate(options)
                        if main.option_type_name(opt) == "ATTACK"
                    ]
                    act_pkmn = player.active[0] if player.active else None
                    act_name = getattr(main.CARD_BY_ID.get(getattr(act_pkmn, "id", -1)), "name", "None") if act_pkmn else "None"
                    
                    if pkmn_name in act_name:
                        target_opts = [i for i, opt in attack_opts if getattr(opt, "attackId", None) == target_aid]
                        if target_opts:
                            opp_act = opp_player.active[0] if opp_player.active else None
                            opp_hp_before = getattr(opp_act, "hp", 0)
                            act_e_before = len(getattr(act_pkmn, "energyCards", []))
                            opp_bench_before = [getattr(p, "hp", 0) for p in (opp_player.bench or [])]
                            
                            choice = [target_opts[0]]
                            obs_next = battle_select(choice)
                            obs_next_cls = main.to_observation_class(obs_next)
                            
                            opp_act_after = obs_next_cls.current.players[1 - player_idx].active[0] if obs_next_cls.current.players[1 - player_idx].active else None
                            opp_hp_after = getattr(opp_act_after, "hp", 0) if opp_act_after else 0
                            dmg = max(0, opp_hp_before - opp_hp_after)
                            opp_bench_after = [getattr(p, "hp", 0) for p in (obs_next_cls.current.players[1 - player_idx].bench or [])]
                            bench_dmg = sum(max(0, b1 - b2) for b1, b2 in zip(opp_bench_before, opp_bench_after))
                            
                            act_pkmn_after = obs_next_cls.current.players[player_idx].active[0] if obs_next_cls.current.players[player_idx].active else None
                            act_e_after = len(getattr(act_pkmn_after, "energyCards", [])) if act_pkmn_after else 0
                            
                            logs = [LogType(l.type).name for l in (obs_next_cls.logs or []) if hasattr(l, "type")]
                            
                            records.append({
                                "opp_hp_before": opp_hp_before, "dmg_active": dmg,
                                "dmg_bench": bench_dmg,
                                "energy_before": act_e_before, "energy_after": act_e_after,
                                "logs": logs
                            })
                            obs = obs_next
                            continue

                choice = main.agent(obs)
                obs = battle_select(choice)
        finally:
            battle_finish()
    return records

print("--- Testing Kyogre Attack 1042 ---")
r_1042 = test_attack_choice("Kyogre", 1042)
print(f"Count: {len(r_1042)}")
for r in r_1042[:5]:
    print(f"  Active Dmg={r['dmg_active']}, Bench Dmg={r['dmg_bench']}, Energy: {r['energy_before']} -> {r['energy_after']}")

print("\n--- Testing Kyogre Attack 1043 ---")
r_1043 = test_attack_choice("Kyogre", 1043)
print(f"Count: {len(r_1043)}")
for r in r_1043[:5]:
    print(f"  Active Dmg={r['dmg_active']}, Bench Dmg={r['dmg_bench']}, Energy: {r['energy_before']} -> {r['energy_after']}")

print("\n--- Testing Snover Attack 1044 ---")
r_1044 = test_attack_choice("Snover", 1044)
print(f"Count: {len(r_1044)}")
for r in r_1044[:5]:
    print(f"  Active Dmg={r['dmg_active']}, Bench Dmg={r['dmg_bench']}, Energy: {r['energy_before']} -> {r['energy_after']}")

print("\n--- Testing Snover Attack 1045 ---")
r_1045 = test_attack_choice("Snover", 1045)
print(f"Count: {len(r_1045)}")
for r in r_1045[:5]:
    print(f"  Active Dmg={r['dmg_active']}, Bench Dmg={r['dmg_bench']}, Energy: {r['energy_before']} -> {r['energy_after']}")
