import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.game import battle_start, battle_select, battle_finish

print("=" * 70)
print("INSPECTING MULTI-ATTACK DECISIONS IN LIVE MATCHES")
print("=" * 70)

attack_decisions = []

for g in range(50):
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

            if ctx_name == "MAIN":
                attack_opts = [
                    (i, opt) for i, opt in enumerate(obs_cls.select.option)
                    if main.option_type_name(opt) == "ATTACK"
                ]
                if len(attack_opts) > 1:
                    player = obs_cls.current.players[obs_cls.current.yourIndex]
                    act_pkmn = player.active[0] if player.active else None
                    act_cdata = main.CARD_BY_ID.get(getattr(act_pkmn, "id", -1))
                    act_name = getattr(act_cdata, "name", "None") if act_cdata else "None"
                    act_e = len(getattr(act_pkmn, "energyCards", []))
                    act_hp = getattr(act_pkmn, "hp", 0)

                    opp_player = obs_cls.current.players[1 - obs_cls.current.yourIndex]
                    opp_pkmn = opp_player.active[0] if opp_player.active else None
                    opp_cdata = main.CARD_BY_ID.get(getattr(opp_pkmn, "id", -1))
                    opp_name = getattr(opp_cdata, "name", "None") if opp_cdata else "None"
                    opp_hp = getattr(opp_pkmn, "hp", 0)
                    opp_bench_count = len(opp_player.bench or [])

                    attacks_info = []
                    for idx, opt in attack_opts:
                        v4_score = main.v4_score_action(obs_cls, opt, "MAIN")
                        aid = getattr(opt, "attackId", None)
                        attacks_info.append({
                            "opt_idx": idx,
                            "attack_id": aid,
                            "v4_score": v4_score
                        })

                    attack_decisions.append({
                        "game": g, "step": step,
                        "active_name": act_name, "active_hp": act_hp, "active_energy": act_e,
                        "opp_name": opp_name, "opp_hp": opp_hp, "opp_bench_count": opp_bench_count,
                        "attacks": attacks_info
                    })

            choice = main.agent(obs)
            obs = battle_select(choice)
            step += 1
    finally:
        battle_finish()

print(f"Total multi-attack decisions captured: {len(attack_decisions)}")
print("\nSample Multi-Attack Decision States:")
for d in attack_decisions[:10]:
    print(f"Game {d['game']}, Step {d['step']}: Active={d['active_name']} (HP={d['active_hp']}, E={d['active_energy']}) vs OppActive={d['opp_name']} (HP={d['opp_hp']}, Bench={d['opp_bench_count']})")
    for a in d['attacks']:
        print(f"    Opt {a['opt_idx']}: AttackId={a['attack_id']}, V4_Score={a['v4_score']}")
