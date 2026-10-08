import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.api import LogType
from cg.game import battle_start, battle_select, battle_finish

print("=" * 70)
print("INSPECTING MEGA ABOMASNOW EX ATTACKS: 1046 vs 1047")
print("=" * 70)

# Let's inspect when 1046 vs 1047 are both available:
# What are the logs when 1046 is used? What are the logs when 1047 is used?
# How much damage is dealt to active? How much energy is discarded?

records_1046 = []
records_1047 = []

for g in range(50):
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
                
                if "Abomasnow" in act_name and len(attack_opts) > 1:
                    # Both attacks are legal!
                    opt_1046 = [i for i, opt in attack_opts if getattr(opt, "attackId", None) == 1046]
                    opt_1047 = [i for i, opt in attack_opts if getattr(opt, "attackId", None) == 1047]
                    
                    if opt_1046 and opt_1047:
                        # Test what V4 does (V4 picks 1047)
                        opp_act = opp_player.active[0] if opp_player.active else None
                        opp_hp_before = getattr(opp_act, "hp", 0)
                        act_e_before = len(getattr(act_pkmn, "energyCards", []))
                        
                        choice = [opt_1047[0]]
                        obs_next = battle_select(choice)
                        obs_next_cls = main.to_observation_class(obs_next)
                        
                        opp_act_after = obs_next_cls.current.players[1 - player_idx].active[0] if obs_next_cls.current.players[1 - player_idx].active else None
                        opp_hp_after = getattr(opp_act_after, "hp", 0) if opp_act_after else 0
                        dmg = max(0, opp_hp_before - opp_hp_after)
                        act_pkmn_after = obs_next_cls.current.players[player_idx].active[0] if obs_next_cls.current.players[player_idx].active else None
                        act_e_after = len(getattr(act_pkmn_after, "energyCards", [])) if act_pkmn_after else 0
                        
                        logs = [LogType(l.type).name for l in (obs_next_cls.logs or []) if hasattr(l, "type")]
                        
                        records_1047.append({
                            "game": g, "opp_hp_before": opp_hp_before, "dmg": dmg,
                            "energy_before": act_e_before, "energy_after": act_e_after,
                            "logs": logs
                        })
                        obs = obs_next
                        continue

            choice = main.agent(obs)
            obs = battle_select(choice)
    finally:
        battle_finish()

print(f"Captured {len(records_1047)} states where BOTH 1046 and 1047 were legal on Mega Abomasnow ex:")
for r in records_1047[:10]:
    print(f"  Opp HP Before={r['opp_hp_before']}, Damage Dealt={r['dmg']}, Energy: {r['energy_before']} -> {r['energy_after']}")
    print(f"    Logs: {r['logs']}")
