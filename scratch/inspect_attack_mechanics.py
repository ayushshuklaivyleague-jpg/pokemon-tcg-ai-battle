import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.api import LogType
from cg.game import battle_start, battle_select, battle_finish

print("=" * 70)
print("INSPECTING ATTACK EFFECTS AND MECHANICS IN CG ENGINE")
print("=" * 70)

attack_effects = {}

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
            choice = main.agent(obs)
            
            if ctx_name == "MAIN" and choice and len(choice) > 0:
                selected_opt = options[choice[0]]
                if main.option_type_name(selected_opt) == "ATTACK":
                    aid = getattr(selected_opt, "attackId", None)
                    act_pkmn = player.active[0] if player.active else None
                    act_name = getattr(main.CARD_BY_ID.get(getattr(act_pkmn, "id", -1)), "name", "None") if act_pkmn else "None"
                    act_e_before = len(getattr(act_pkmn, "energyCards", []))
                    
                    opp_act = opp_player.active[0] if opp_player.active else None
                    opp_hp_before = getattr(opp_act, "hp", 0)

                    obs_next = battle_select(choice)
                    obs_next_cls = main.to_observation_class(obs_next)
                    
                    logs = obs_next_cls.logs or []
                    log_types = [LogType(l.type).name for l in logs if hasattr(l, "type")]
                    
                    opp_act_after = obs_next_cls.current.players[1 - player_idx].active[0] if obs_next_cls.current.players[1 - player_idx].active else None
                    opp_hp_after = getattr(opp_act_after, "hp", 0) if opp_act_after else 0
                    dmg_to_active = max(0, opp_hp_before - opp_hp_after)
                    
                    act_pkmn_after = obs_next_cls.current.players[player_idx].active[0] if obs_next_cls.current.players[player_idx].active else None
                    act_e_after = len(getattr(act_pkmn_after, "energyCards", [])) if act_pkmn_after else 0
                    
                    if aid not in attack_effects:
                        attack_effects[aid] = {
                            "pokemon": act_name,
                            "attack_id": aid,
                            "dmg_samples": [],
                            "energy_cost_observed": act_e_before,
                            "energy_discard_observed": act_e_before - act_e_after,
                            "logs_sample": log_types,
                        }
                    attack_effects[aid]["dmg_samples"].append(dmg_to_active)
                    
                    obs = obs_next
                    continue

            obs = battle_select(choice)
    finally:
        battle_finish()

for aid, info in sorted(attack_effects.items()):
    dmgs = info["dmg_samples"]
    avg_dmg = sum(dmgs) / len(dmgs) if dmgs else 0
    print(f"Attack ID {aid}: Pokemon={info['pokemon']}, Count={len(dmgs)}, Avg Damage={avg_dmg:.1f} (samples: {dmgs[:8]}), Energy Before={info['energy_cost_observed']}, Discard={info['energy_discard_observed']}")
    print(f"   Logs: {info['logs_sample'][:8]}")
