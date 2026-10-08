import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.api import LogType
from cg.game import battle_start, battle_select, battle_finish

print("=" * 70)
print("DEEP DIVE: MEGA ABOMASNOW EX ATTACK 1046 vs 1047")
print("=" * 70)

# Let's check what happens when 1046 is chosen:
# How many times does 1046 deal damage? What are the MOVE_CARD logs?
# Does 1046 discard cards from deck, or hand, or energy?

samples_1046 = []

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
                
                if "Abomasnow" in act_name:
                    opt_1046 = [i for i, opt in attack_opts if getattr(opt, "attackId", None) == 1046]
                    if opt_1046:
                        # Inspect board state before 1046
                        opp_act = opp_player.active[0] if opp_player.active else None
                        opp_name = getattr(main.CARD_BY_ID.get(getattr(opp_act, "id", -1)), "name", "None") if opp_act else "None"
                        opp_hp_before = getattr(opp_act, "hp", 0)
                        deck_count_before = player.deckCount
                        hand_count_before = len(player.hand or [])
                        act_e_before = len(getattr(act_pkmn, "energyCards", []))

                        choice = [opt_1046[0]]
                        obs_next = battle_select(choice)
                        obs_next_cls = main.to_observation_class(obs_next)
                        
                        opp_act_after = obs_next_cls.current.players[1 - player_idx].active[0] if obs_next_cls.current.players[1 - player_idx].active else None
                        opp_hp_after = getattr(opp_act_after, "hp", 0) if opp_act_after else 0
                        dmg = max(0, opp_hp_before - opp_hp_after)
                        deck_count_after = obs_next_cls.current.players[player_idx].deckCount
                        
                        samples_1046.append({
                            "opp_name": opp_name,
                            "opp_hp_before": opp_hp_before,
                            "dmg": dmg,
                            "deck_change": deck_count_before - deck_count_after,
                            "act_e_before": act_e_before,
                        })
                        obs = obs_next
                        continue

            choice = main.agent(obs)
            obs = battle_select(choice)
    finally:
        battle_finish()

print(f"Captured {len(samples_1046)} executions of 1046:")
for s in samples_1046:
    print(f"  Target={s['opp_name']} (HP={s['opp_hp_before']}) -> Damage={s['dmg']}, Deck Discarded={s['deck_change']}, Energy={s['act_e_before']}")
