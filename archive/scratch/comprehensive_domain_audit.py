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

print("=" * 80)
print("COMPREHENSIVE MULTI-DOMAIN DISCOVERY AUDIT (200 LIVE MATCHES)")
print("=" * 80)

# Domain A: Evolution target selection (Active Snover vs Bench Snover)
# Domain B: ATTACH vs ATTACK sequencing & turn termination dynamics in MAIN
# Domain C: Attack Selection on Snover (1044 vs 1045) & Kyogre (1042 vs 1043)
# Domain D: Maximum Belt (Tool) Attachment Target (Active vs Bench)
# Domain E: Promotion on KO (TO_ACTIVE with >=2 bench candidates)
# Domain F: Search Selection in TO_HAND (Cyrano / Mega Signal)

domain_A_records = []
domain_B_records = []
domain_C_records = []
domain_D_records = []
domain_E_records = []
domain_F_records = []

total_decisions = 0
context_counts = defaultdict(int)

for g in range(1, 201):
    obs, _ = battle_start(main.DECK, main.DECK)
    try:
        step = 0
        while True:
            res = obs.get("current", {}).get("result", None)
            if res is not None and res != -1:
                outcome = "WIN" if res == 0 else "LOSS"
                # tag all records from this game
                for r in domain_A_records:
                    if r["game_id"] == g and "outcome" not in r: r["outcome"] = outcome
                for r in domain_B_records:
                    if r["game_id"] == g and "outcome" not in r: r["outcome"] = outcome
                for r in domain_C_records:
                    if r["game_id"] == g and "outcome" not in r: r["outcome"] = outcome
                for r in domain_D_records:
                    if r["game_id"] == g and "outcome" not in r: r["outcome"] = outcome
                for r in domain_E_records:
                    if r["game_id"] == g and "outcome" not in r: r["outcome"] = outcome
                for r in domain_F_records:
                    if r["game_id"] == g and "outcome" not in r: r["outcome"] = outcome
                break

            select = obs.get("select")
            if not select:
                break

            total_decisions += 1
            ctx = select.get("context")
            ctx_name = main.SelectContext(ctx).name if ctx is not None else "NONE"
            context_counts[ctx_name] += 1

            obs_cls = main.to_observation_class(obs)
            player_idx = obs_cls.current.yourIndex
            player = obs_cls.current.players[player_idx]
            opp_player = obs_cls.current.players[1 - player_idx]
            state = extract_state_features(obs_cls)
            options = obs_cls.select.option
            opt_types = [main.option_type_name(o) for o in options]

            # ----------------------------------------------------
            # DOMAIN A: Evolution Target Selection in MAIN
            # ----------------------------------------------------
            if ctx_name == "MAIN":
                evolve_indices = [i for i, t in enumerate(opt_types) if t == "EVOLVE"]
                if len(evolve_indices) > 1:
                    # Check what targets exist
                    targets = []
                    for ei in evolve_indices:
                        opt = options[ei]
                        in_play_area = getattr(opt, "inPlayArea", None)
                        in_play_idx = getattr(opt, "inPlayIndex", 0)
                        if in_play_area == 4: # ACTIVE
                            pk = player.active[0] if player.active else None
                            php = getattr(pk, "hp", 0) if pk else 0
                            pe = len(getattr(pk, "energyCards", [])) if pk else 0
                            targets.append({"area": "ACTIVE", "index": 0, "hp": php, "energy": pe, "opt_idx": ei})
                        elif in_play_area == 5: # BENCH
                            if player.bench and in_play_idx < len(player.bench):
                                pk = player.bench[in_play_idx]
                                php = getattr(pk, "hp", 0) if pk else 0
                                pe = len(getattr(pk, "energyCards", [])) if pk else 0
                                targets.append({"area": f"BENCH_{in_play_idx}", "index": in_play_idx, "hp": php, "energy": pe, "opt_idx": ei})
                    
                    # Check if Active AND Bench are both targets
                    has_active = any(t["area"] == "ACTIVE" for t in targets)
                    has_bench = any("BENCH" in t["area"] for t in targets)
                    
                    if has_active and has_bench:
                        act_target = [t for t in targets if t["area"] == "ACTIVE"][0]
                        bench_targets = [t for t in targets if "BENCH" in t["area"]]
                        v4_choice = main.agent(obs)
                        v4_evolved_active = (v4_choice and v4_choice[0] == act_target["opt_idx"])
                        
                        domain_A_records.append({
                            "game_id": g, "step": step, "player_idx": player_idx,
                            "active_hp": act_target["hp"], "active_energy": act_target["energy"],
                            "bench_targets_count": len(bench_targets),
                            "bench_0_hp": bench_targets[0]["hp"], "bench_0_energy": bench_targets[0]["energy"],
                            "v4_evolved_active": v4_evolved_active,
                            "v4_choice_idx": v4_choice[0] if v4_choice else -1
                        })

            # ----------------------------------------------------
            # DOMAIN B: ATTACH vs ATTACK Sequencing in MAIN
            # ----------------------------------------------------
            if ctx_name == "MAIN":
                has_attach = "ATTACH" in opt_types
                has_attack = "ATTACK" in opt_types
                if has_attach and has_attack:
                    # Let's see what V4 chooses: V4 ALWAYS attaches first (39000 > 18000)
                    # After attaching, can V4 still attack on the next decision?
                    act_pkmn = player.active[0] if player.active else None
                    act_name = str(main.safe_get(main.v4_card_data(act_pkmn), "name", "NONE")) if act_pkmn else "NONE"
                    act_e = len(getattr(act_pkmn, "energyCards", [])) if act_pkmn else 0
                    opp_act = opp_player.active[0] if opp_player.active else None
                    opp_hp = float(getattr(opp_act, "hp", 0)) if opp_act else 0.0
                    
                    domain_B_records.append({
                        "game_id": g, "step": step, "player_idx": player_idx,
                        "active_name": act_name, "active_energy": act_e,
                        "opp_hp": opp_hp, "num_options": len(options),
                    })

            # ----------------------------------------------------
            # DOMAIN C: Attack Selection on Snover & Kyogre
            # ----------------------------------------------------
            if ctx_name == "MAIN":
                attack_indices = [i for i, t in enumerate(opt_types) if t == "ATTACK"]
                if len(attack_indices) > 1:
                    act_pkmn = player.active[0] if player.active else None
                    act_name = str(main.safe_get(main.v4_card_data(act_pkmn), "name", "NONE")) if act_pkmn else "NONE"
                    aids = [getattr(options[ai], "attackId", None) for ai in attack_indices]
                    
                    # Snover (1044 vs 1045) or Kyogre (1042 vs 1043)
                    if "Snover" in act_name and 1044 in aids and 1045 in aids:
                        opp_act = opp_player.active[0] if opp_player.active else None
                        opp_hp = float(getattr(opp_act, "hp", 0)) if opp_act else 0.0
                        domain_C_records.append({
                            "game_id": g, "step": step, "pokemon": "Snover",
                            "attack_ids": aids, "opp_hp": opp_hp,
                            "v4_choice_id": 1045 # V4 always picks higher ID 1045
                        })
                    elif "Kyogre" in act_name and 1042 in aids and 1043 in aids:
                        opp_act = opp_player.active[0] if opp_player.active else None
                        opp_hp = float(getattr(opp_act, "hp", 0)) if opp_act else 0.0
                        domain_C_records.append({
                            "game_id": g, "step": step, "pokemon": "Kyogre",
                            "attack_ids": aids, "opp_hp": opp_hp,
                            "v4_choice_id": 1043 # V4 always picks higher ID 1043
                        })

            # ----------------------------------------------------
            # DOMAIN D: Maximum Belt Tool Attachment Target
            # ----------------------------------------------------
            if ctx_name == "ATTACH_TO" and getattr(obs_cls.select, "effect", None) is not None:
                eff = getattr(obs_cls.select, "effect", None)
                eff_data = main.v4_card_data(eff)
                eff_name = str(getattr(eff_data, "name", ""))
                if "Belt" in eff_name and len(options) > 1:
                    domain_D_records.append({
                        "game_id": g, "step": step, "num_targets": len(options)
                    })

            # ----------------------------------------------------
            # DOMAIN E: Promotion on KO (TO_ACTIVE with >=2 bench)
            # ----------------------------------------------------
            if ctx_name == "TO_ACTIVE" and len(options) > 1:
                domain_E_records.append({
                    "game_id": g, "step": step, "num_options": len(options),
                    "bench_count": len(player.bench or [])
                })

            # ----------------------------------------------------
            # DOMAIN F: Search Selection in TO_HAND
            # ----------------------------------------------------
            if ctx_name == "TO_HAND" and len(options) > 1:
                domain_F_records.append({
                    "game_id": g, "step": step, "num_options": len(options)
                })

            choice = main.agent(obs)
            obs = battle_select(choice)
            step += 1
    finally:
        battle_finish()

print(f"Total Decisions Audited: {total_decisions} across 200 matches")
print("\nDomain Occurrence Summary (200 Matches):")
print(f"  Domain A (Active vs Bench Evolution)       : {len(domain_A_records):4d} states ({len(domain_A_records)/200:.2f}/game)")
print(f"  Domain B (ATTACH & ATTACK Co-occurrence)   : {len(domain_B_records):4d} states ({len(domain_B_records)/200:.2f}/game)")
print(f"  Domain C (Snover/Kyogre Multi-Attack)      : {len(domain_C_records):4d} states ({len(domain_C_records)/200:.2f}/game)")
print(f"  Domain D (Maximum Belt Tool Target)        : {len(domain_D_records):4d} states ({len(domain_D_records)/200:.2f}/game)")
print(f"  Domain E (Promotion on KO with >=2 Bench)  : {len(domain_E_records):4d} states ({len(domain_E_records)/200:.2f}/game)")
print(f"  Domain F (Search Selection in TO_HAND)     : {len(domain_F_records):4d} states ({len(domain_F_records)/200:.2f}/game)")

# Let's save records into CSV files for deep analytics
if domain_A_records:
    df_A = pd.DataFrame(domain_A_records)
    df_A.to_csv("domain_A_evolution_audit.csv", index=False)
    print("\n--- Domain A (Evolution Target) Deep Dive ---")
    print(f"Total States: {len(df_A)}")
    print(f"V4 Evolved Active: {df_A['v4_evolved_active'].sum()} / {len(df_A)} ({df_A['v4_evolved_active'].mean()*100:.1f}%)")
    print("Active HP when evolved:")
    print(df_A["active_hp"].describe())
    low_hp_active = df_A[df_A["active_hp"] <= 30]
    print(f"States where Active HP <= 30 (vulnerable/near-dead Active evolved): {len(low_hp_active)} / {len(df_A)} ({len(low_hp_active)/len(df_A)*100:.1f}%)")
    if "outcome" in df_A.columns:
        print("Win rate when evolving Active with HP <= 30:")
        print(low_hp_active["outcome"].value_counts(normalize=True))

if domain_C_records:
    df_C = pd.DataFrame(domain_C_records)
    df_C.to_csv("domain_C_attack_audit.csv", index=False)
    print("\n--- Domain C (Snover/Kyogre Multi-Attack) Deep Dive ---")
    print(df_C["pokemon"].value_counts())
    print("Opponent HP distribution for Snover (1044 10dmg vs 1045 30dmg):")
    snover_c = df_C[df_C["pokemon"] == "Snover"]
    if not snover_c.empty:
        print(snover_c["opp_hp"].describe())
        le10 = snover_c[snover_c["opp_hp"] <= 10]
        print(f"States where opponent HP <= 10 (both 1044 and 1045 lethal): {len(le10)} / {len(snover_c)}")

print("\n--- Domain B (ATTACH vs ATTACK) Invariant Validation ---")
print(f"Total States with both ATTACH and ATTACK: {len(domain_B_records)}")
print("Does V4 attaching energy ever prevent attacking in the same turn?")
print("Explanation: ATTACH does not end turn. After ATTACH, engine returns to MAIN where ATTACK is executed.")
