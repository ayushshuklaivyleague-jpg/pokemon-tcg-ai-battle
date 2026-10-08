import sys
from pathlib import Path
import csv

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.game import battle_start, battle_select, battle_finish
from ptcg_planning.state_features import extract_state_features

print("Generating v4_weakness_candidates.csv from 100 live matches...")

records = []

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
            obs_cls = main.to_observation_class(obs)
            player_idx = obs_cls.current.yourIndex
            player = obs_cls.current.players[player_idx]
            opp_player = obs_cls.current.players[1 - player_idx]
            state = extract_state_features(obs_cls)
            options = obs_cls.select.option

            if ctx_name == "MAIN":
                opt_types = [main.option_type_name(o) for o in options]
                act_pkmn = player.active[0] if player.active else None
                act_name = getattr(main.CARD_BY_ID.get(getattr(act_pkmn, "id", -1)), "name", "None") if act_pkmn else "None"
                opp_act = opp_player.active[0] if opp_player.active else None
                opp_name = getattr(main.CARD_BY_ID.get(getattr(opp_act, "id", -1)), "name", "None") if opp_act else "None"
                opp_hp = getattr(opp_act, "hp", 0) if opp_act else 0

                # 1. Multi-attack on Mega Abomasnow ex
                if "Abomasnow" in act_name:
                    attack_opts = [(i, opt) for i, opt in enumerate(options) if opt_types[i] == "ATTACK"]
                    aids = [getattr(opt, "attackId", None) for _, opt in attack_opts]
                    if 1046 in aids and 1047 in aids:
                        records.append({
                            "game_id": g, "step": step, "domain": "MULTI_ATTACK_ABOMASNOW",
                            "context": "MAIN", "active_pokemon": act_name,
                            "active_energy": len(getattr(act_pkmn, "energyCards", [])),
                            "opp_pokemon": opp_name, "opp_hp": opp_hp,
                            "v4_action": "ATTACK_1047 (Flat 200 Dmg)",
                            "alternative_action": "ATTACK_1046 (RNG up to 350 Dmg)",
                            "is_executable": True,
                            "category": "REAL_ACTIONABLE_WEAKNESS" if opp_hp > 200 else "TACTICAL_CHOICE"
                        })

                # 2. Multi-attach targets
                attach_indices = [i for i, t in enumerate(opt_types) if t == "ATTACH"]
                if len(attach_indices) > 1 and act_pkmn:
                    act_e = len(getattr(act_pkmn, "energyCards", []))
                    bench_zero_e = [
                        p for p in (player.bench or [])
                        if p is not None and len(getattr(p, "energyCards", [])) == 0
                    ]
                    if act_e >= 3 and len(bench_zero_e) > 0:
                        records.append({
                            "game_id": g, "step": step, "domain": "ATTACH_ACTIVE_OVERSATURATION",
                            "context": "MAIN", "active_pokemon": act_name,
                            "active_energy": act_e, "opp_pokemon": opp_name, "opp_hp": opp_hp,
                            "v4_action": "ATTACH_ACTIVE", "alternative_action": "ATTACH_BENCH",
                            "is_executable": True, "category": "LOW_FREQUENCY_CANDIDATE"
                        })

                # 3. Evolution targets
                evolve_indices = [i for i, t in enumerate(opt_types) if t == "EVOLVE"]
                if len(evolve_indices) > 1:
                    records.append({
                        "game_id": g, "step": step, "domain": "MULTI_EVOLVE_TARGETS",
                        "context": "MAIN", "active_pokemon": act_name,
                        "active_energy": len(getattr(act_pkmn, "energyCards", [])),
                        "opp_pokemon": opp_name, "opp_hp": opp_hp,
                        "v4_action": "EVOLVE_ACTIVE", "alternative_action": "EVOLVE_BENCH",
                        "is_executable": True, "category": "TACTICAL_CHOICE"
                    })

            if ctx_name == "TO_ACTIVE" and len(options) > 1:
                records.append({
                    "game_id": g, "step": step, "domain": "PROMOTION_ON_KO",
                    "context": "TO_ACTIVE", "active_pokemon": "KNOCKED_OUT",
                    "active_energy": 0, "opp_pokemon": "UNKNOWN", "opp_hp": 0,
                    "v4_action": "PROMOTE_HIGH_HP_OR_ENERGY", "alternative_action": "PROMOTE_SACRIFICE",
                    "is_executable": True, "category": "LOW_FREQUENCY_CANDIDATE"
                })

            choice = main.agent(obs)
            obs = battle_select(choice)
            step += 1
    finally:
        battle_finish()

csv_path = Path("v4_weakness_candidates.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "game_id", "step", "domain", "context", "active_pokemon", "active_energy",
        "opp_pokemon", "opp_hp", "v4_action", "alternative_action", "is_executable", "category"
    ])
    writer.writeheader()
    for r in records:
        writer.writerow(r)

print(f"Saved {len(records)} candidate weakness records to {csv_path}.")
