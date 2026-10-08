import sys
from pathlib import Path
import pandas as pd
from collections import defaultdict

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.api import LogType
from cg.game import battle_start, battle_select, battle_finish
from ptcg_planning.state_features import extract_state_features

print("=" * 75)
print("DEEP LIVE VALIDATION OF TOP CANDIDATE WEAKNESS DOMAINS (100 MATCHES)")
print("=" * 75)

# Candidate 1: Attack 1046 vs 1047 on Mega Abomasnow ex
# Candidate 2: Energy Attachment Target (Active Oversaturation >=3E vs Bench 0E)
# Candidate 3: Lillie's Determination played before attaching Energy in hand
# Candidate 4: Promotion choice on KO (TO_ACTIVE with multiple bench options)
# Candidate 5: Evolution Target (Active vs Bench when Active is KO-vulnerable)

c1_states = []
c2_states = []
c3_states = []
c4_states = []
c5_states = []

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
                
                # --- Candidate 1: Mega Abomasnow 1046 vs 1047 ---
                act_pkmn = player.active[0] if player.active else None
                act_name = getattr(main.CARD_BY_ID.get(getattr(act_pkmn, "id", -1)), "name", "None") if act_pkmn else "None"
                if "Abomasnow" in act_name:
                    attack_opts = [(i, opt) for i, opt in enumerate(options) if opt_types[i] == "ATTACK"]
                    aids = [getattr(opt, "attackId", None) for _, opt in attack_opts]
                    if 1046 in aids and 1047 in aids:
                        opp_act = opp_player.active[0] if opp_player.active else None
                        opp_hp = getattr(opp_act, "hp", 0) if opp_act else 0
                        opp_name = getattr(main.CARD_BY_ID.get(getattr(opp_act, "id", -1)), "name", "None") if opp_act else "None"
                        c1_states.append({
                            "game": g, "step": step, "opp_name": opp_name, "opp_hp": opp_hp,
                            "deck_count": player.deckCount, "my_hp": getattr(act_pkmn, "hp", 0)
                        })

                # --- Candidate 2: Energy Attachment Target ---
                # Active has >= 3 Energy and Bench has Pokemon with 0 Energy
                attach_indices = [i for i, t in enumerate(opt_types) if t == "ATTACH"]
                if len(attach_indices) > 1 and act_pkmn:
                    act_e = len(getattr(act_pkmn, "energyCards", []))
                    bench_zero_e = [
                        p for p in (player.bench or [])
                        if p is not None and len(getattr(p, "energyCards", [])) == 0
                    ]
                    if act_e >= 3 and len(bench_zero_e) > 0:
                        c2_states.append({
                            "game": g, "step": step, "act_e": act_e,
                            "bench_count": len(player.bench or []),
                            "bench_zero_e_count": len(bench_zero_e),
                            "act_hp": getattr(act_pkmn, "hp", 0),
                            "act_name": act_name
                        })

                # --- Candidate 3: Lillie Supporter played before attaching Energy in hand ---
                play_indices = [i for i, t in enumerate(opt_types) if t == "PLAY"]
                if play_indices and attach_indices:
                    # Check if Lillie is in play_opts
                    for pi in play_indices:
                        c = main.v4_card_from_option(obs_cls, options[pi])
                        cdata = main.v4_card_data(c)
                        cname = getattr(cdata, "name", "")
                        if "Lillie" in str(cname):
                            c3_states.append({
                                "game": g, "step": step, "hand_size": len(player.hand or []),
                                "act_e": len(getattr(act_pkmn, "energyCards", [])) if act_pkmn else 0
                            })
                            break

                # --- Candidate 5: Multi-evolution target ---
                evolve_indices = [i for i, t in enumerate(opt_types) if t == "EVOLVE"]
                if len(evolve_indices) > 1:
                    c5_states.append({
                        "game": g, "step": step, "num_evolve": len(evolve_indices)
                    })

            # --- Candidate 4: Promotion on KO ---
            if ctx_name == "TO_ACTIVE" and len(options) > 1:
                c4_states.append({
                    "game": g, "step": step, "num_options": len(options),
                    "bench_count": len(player.bench or [])
                })

            choice = main.agent(obs)
            obs = battle_select(choice)
            step += 1
    finally:
        battle_finish()

print("RESULTS FROM 100 LIVE MATCHES:")
print("-" * 75)
print(f"Candidate 1 (Mega Abomasnow 1046 vs 1047 choice) : {len(c1_states):4d} states ({len(c1_states)/100:.2f} per game)")
print(f"Candidate 2 (Attach to Bench when Active >=3E)    : {len(c2_states):4d} states ({len(c2_states)/100:.2f} per game)")
print(f"Candidate 3 (Lillie played before Attach in hand)  : {len(c3_states):4d} states ({len(c3_states)/100:.2f} per game)")
print(f"Candidate 4 (Promotion TO_ACTIVE with >=2 bench)  : {len(c4_states):4d} states ({len(c4_states)/100:.2f} per game)")
print(f"Candidate 5 (Multiple EVOLVE targets in MAIN)     : {len(c5_states):4d} states ({len(c5_states)/100:.2f} per game)")
print("-" * 75)

print("\n--- Detailed Breakdown: Candidate 1 (Attack 1046 vs 1047) ---")
if c1_states:
    df1 = pd.DataFrame(c1_states)
    print("Opponent Targets when both attacks are legal:")
    print(df1["opp_name"].value_counts())
    print("\nOpponent HP Distribution when both attacks are legal:")
    print(df1["opp_hp"].describe())
    print("\nStates where Opponent HP > 200 (cannot be KO'd by 1047's 200 dmg, but CAN be KO'd by 1046's 350 dmg):")
    gt200 = df1[df1["opp_hp"] > 200]
    print(f"  Count: {len(gt200)} / {len(df1)} ({len(gt200)/len(df1)*100:.1f}%)")
    for _, row in gt200.head(5).iterrows():
        print(f"    Game {row['game']}, Step {row['step']}: Target={row['opp_name']}, OppHP={row['opp_hp']}, DeckCount={row['deck_count']}")

print("\n--- Detailed Breakdown: Candidate 2 (Attachment when Active >=3E) ---")
if c2_states:
    df2 = pd.DataFrame(c2_states)
    print("Active Pokemon in these states:")
    print(df2["act_name"].value_counts())
    print("Active Energy level:")
    print(df2["act_e"].value_counts())
    print("Active HP distribution:")
    print(df2["act_hp"].describe())

print("\n--- Detailed Breakdown: Candidate 3 (Lillie before Attach) ---")
if c3_states:
    df3 = pd.DataFrame(c3_states)
    print(f"Lillie played before attachment in {len(df3)} states.")
    print("Hand size when Lillie is played:")
    print(df3["hand_size"].value_counts())
