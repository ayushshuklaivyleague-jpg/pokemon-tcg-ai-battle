"""
Runner to execute games and generate complete telemetry datasets:
- sol_eclipse_decision_audit.csv
- sol_eclipse_weight_usage.csv
"""

import sys
import os
import csv
import time
from pathlib import Path
from collections import defaultdict, Counter

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from cg.game import battle_start, battle_select, battle_finish
import main
from scratch.sol_eclipse_telemetry import (
    InstrumentedSolAgent,
    SOL_DECK,
    sol_weights,
    sol_namespace
)

def run_single_game(agent0, agent1, deck0, deck1, game_id: int, max_steps: int = 160):
    agent0.set_game(game_id, 0)
    agent1.set_game(game_id, 1)

    obs, start_data = battle_start(deck0, deck1)
    if not obs or not start_data:
        raise RuntimeError(f"Game {game_id}: Failed to start battle")

    step = 0
    agents = [agent0, agent1]

    while step < max_steps:
        step += 1
        res = obs.get("current", {}).get("result")
        if res is not None and res >= 0:
            break

        player_idx = obs.get("current", {}).get("yourIndex", 0)
        current_agent = agents[player_idx]

        action = current_agent.decide(obs)
        obs = battle_select(action)

    battle_finish()
    final_res = obs.get("current", {}).get("result", -1)
    return final_res, step

class StandardAgentWrapper:
    def __init__(self, agent_fn, name="Opponent"):
        self.agent_fn = agent_fn
        self.name = name

    def set_game(self, game_id: int, player_idx: int):
        pass

    def decide(self, obs_dict):
        return self.agent_fn(obs_dict)

def main_runner(num_games: int = 60):
    print(f"Starting Telemetry Run with {num_games} complete games...", flush=True)
    t0 = time.time()

    audited_agent = InstrumentedSolAgent("SolEclipse_Audited")
    sol_control = StandardAgentWrapper(sol_namespace["agent"], "SolEclipse_Control")
    v4_control = StandardAgentWrapper(main.agent, "MikeV4_Control")

    all_records = []
    game_results = []

    # Run balanced games:
    # 1. Sol (P0) vs Sol (P1)
    # 2. Sol (P1) vs Sol (P0)
    # 3. Sol (P0) vs Mike V4 (P1)
    # 4. Sol (P1) vs Mike V4 (P0)
    for g in range(1, num_games + 1):
        start_rec_idx = len(audited_agent.records)

        if g % 4 == 1:
            res, steps = run_single_game(audited_agent, sol_control, SOL_DECK, SOL_DECK, g)
            outcome = "WIN" if res == 0 else ("LOSS" if res == 1 else "DRAW")
            opp_name = "SolEclipse_Mirror"
            p_pos = 0
        elif g % 4 == 2:
            res, steps = run_single_game(sol_control, audited_agent, SOL_DECK, SOL_DECK, g)
            outcome = "WIN" if res == 1 else ("LOSS" if res == 0 else "DRAW")
            opp_name = "SolEclipse_Mirror"
            p_pos = 1
        elif g % 4 == 3:
            res, steps = run_single_game(audited_agent, v4_control, SOL_DECK, main.DECK, g)
            outcome = "WIN" if res == 0 else ("LOSS" if res == 1 else "DRAW")
            opp_name = "Mike_V4"
            p_pos = 0
        else:
            res, steps = run_single_game(v4_control, audited_agent, main.DECK, SOL_DECK, g)
            outcome = "WIN" if res == 1 else ("LOSS" if res == 0 else "DRAW")
            opp_name = "Mike_V4"
            p_pos = 1

        game_results.append((g, opp_name, p_pos, outcome, steps))

        # Tag all decisions from this game with outcome
        end_rec_idx = len(audited_agent.records)
        for idx in range(start_rec_idx, end_rec_idx):
            audited_agent.records[idx]["game_outcome"] = outcome
            audited_agent.records[idx]["opponent_deck"] = opp_name

        if g % 5 == 0 or g == num_games:
            w_cnt = sum(1 for _, _, _, out, _ in game_results if out == "WIN")
            print(f"  Completed Game {g:02d}/{num_games} -> Sol Wins: {w_cnt}/{g} ({w_cnt/g*100:.1f}%) | Last Steps: {steps}", flush=True)

    elapsed = time.time() - t0
    total_decisions = len(audited_agent.records)
    print(f"\nCompleted {num_games} games in {elapsed:.2f}s.", flush=True)
    print(f"Total decision records collected: {total_decisions}", flush=True)
    print(f"Total Search Invocations: {audited_agent.total_search_invocations}", flush=True)
    print(f"Total Search Overrides: {audited_agent.total_search_overrides}", flush=True)
    print(f"Total Courage Overrides: {audited_agent.total_courage_overrides}", flush=True)

    # Write sol_eclipse_decision_audit.csv
    csv_path = HERE / "sol_eclipse_decision_audit.csv"
    if audited_agent.records:
        fieldnames = list(audited_agent.records[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(audited_agent.records)
        print(f"Wrote {len(audited_agent.records)} records to {csv_path}", flush=True)

    # Analyze weight usage
    weight_usage_data = []

    for w_name, w_val in sol_weights.items():
        relevance_count = 0
        winning_picks = 0
        losing_picks = 0

        for r in audited_agent.records:
            ctx = r["context"]
            sel = r["selected_desc"]
            
            # Map weights precisely to where they participate in decisions
            matched = False
            if w_name in ("play_abra_early", "play_abra_need", "play_abra_extra") and "PLAY(Abra)" in sel:
                matched = True
            elif w_name in ("play_dun_first_early", "play_dun_first_late", "play_dun_second", "play_dun_ex") and ("PLAY(Dunsparce" in sel):
                matched = True
            elif w_name.startswith("poffin") and "PLAY(Buddy-Buddy Poffin)" in sel:
                matched = True
            elif w_name.startswith("pokepad") and "PLAY(Poke Pad)" in sel:
                matched = True
            elif w_name == "rare_candy" and "PLAY(Rare Candy)" in sel:
                matched = True
            elif w_name.startswith("hammer") and "PLAY(Enhanced Hammer)" in sel:
                matched = True
            elif w_name == "boss_kill" and ("PLAY(Boss's Orders)" in sel or "SWITCH" in ctx):
                matched = True
            elif w_name.startswith("dawn") and "PLAY(Dawn)" in sel:
                matched = True
            elif w_name == "hilda" and "PLAY(Hilda)" in sel:
                matched = True
            elif w_name == "xerosic" and "PLAY(Xerosic" in sel:
                matched = True
            elif w_name == "lana" and "PLAY(Lana" in sel:
                matched = True
            elif w_name.startswith("night_stretcher") and "PLAY(Night Stretcher)" in sel:
                matched = True
            elif w_name.startswith("sacred_ash") and "PLAY(Sacred Ash)" in sel:
                matched = True
            elif w_name.startswith("nz_") and "PLAY(Neutralization Zone)" in sel:
                matched = True
            elif w_name.startswith("attack") and "ATTACK" in sel:
                matched = True
            elif w_name.startswith("retreat") and "RETREAT" in sel:
                matched = True
            elif w_name.startswith("evolve") and "EVOLVE" in sel:
                matched = True
            elif w_name in ("energy_abra", "energy_retreat") and "ATTACH" in sel and "Energy" in sel:
                matched = True
            elif w_name == "ability_dudun" and "ABILITY(Dudunsparce)" in sel:
                matched = True

            if matched:
                relevance_count += 1
                if r["game_outcome"] == "WIN": winning_picks += 1
                else: losing_picks += 1

        weight_usage_data.append({
            "weight_name": w_name,
            "baked_value": w_val,
            "decision_frequency": relevance_count,
            "win_correlation_rate": round(winning_picks / max(1, relevance_count) * 100, 1) if relevance_count > 0 else 0.0,
            "status": "ACTIVE" if relevance_count > 0 else "DEAD_OR_UNREACHABLE"
        })

    # Write sol_eclipse_weight_usage.csv
    w_csv_path = HERE / "sol_eclipse_weight_usage.csv"
    with open(w_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["weight_name", "baked_value", "decision_frequency", "win_correlation_rate", "status"])
        writer.writeheader()
        writer.writerows(weight_usage_data)
    print(f"Wrote weight usage data to {w_csv_path}", flush=True)

if __name__ == "__main__":
    main_runner(60)
