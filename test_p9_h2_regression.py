"""
P9-H2 Experimental Benchmark Suite: Isolated State-Adaptive Search Resolution.
Tests Hypothesis H2: In TO_HAND search prompts, when player's bench is empty (my_bench_count == 0)
and a legal Basic Pokémon is among the available search targets, prioritize that Basic Pokémon
over high-stage evolutions or other cards.
No other changes (no MAIN changes, no KO logic, no threat logic, no counterfactuals).
Evaluated over 200 balanced matches against Frozen P0 Control Baseline.
"""

import os
import sys
import csv
import math
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, asdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.game import battle_start, battle_select, battle_finish
from ptcg_planning.state_features import extract_state_features, StateFeatures
from test_ptcg_regression import DecisionRecord


def compute_wilson_ci(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.95996
    p = wins / total
    denominator = 1.0 + (z**2) / total
    center = (p + (z**2) / (2 * total)) / denominator
    margin = (z * math.sqrt((p * (1.0 - p) / total) + (z**2) / (4 * (total**2)))) / denominator
    return max(0.0, center - margin) * 100.0, min(1.0, center + margin) * 100.0


class P9H2Agent:
    def __init__(self, gating_threshold: float = 150.0):
        self.gating_threshold = gating_threshold
        self.decision_logs: List[DecisionRecord] = []
        self.fallback_count = 0
        self.contract_errors = 0
        self.current_game_id = 0
        self.current_step = 0
        self.empty_bench_searches_with_basic = 0

    def set_game_context(self, game_id: int, step: int):
        self.current_game_id = game_id
        self.current_step = step

    def _score_h2(self, obs: Any, option: Any, v4_s: float, context_name: str, state: StateFeatures) -> float:
        """
        P9-H2 ONLY:
        When context is TO_HAND (or deck search), player's bench is empty (my_bench_count == 0),
        and the card is a Basic Pokémon, elevate its score by +20,000 to ensure it is retrieved
        over Stage 1/2 evolutions or other cards.
        """
        if context_name == "TO_HAND" and state.my_bench_count == 0:
            card = main.v4_card_from_option(obs, option)
            if card is not None and main.v4_is_pokemon(card):
                cd = main.v4_card_data(card)
                stage = main.safe_get(cd, "stage", 0) if cd else main.safe_get(card, "stage", 0)
                if stage == 0 or stage == "BASIC" or stage == "Basic":
                    return v4_s + 20000.0  # Top priority: secure bench anchor

        return v4_s

    def choose_action(self, obs_dict: Dict[str, Any]) -> List[int]:
        if not isinstance(obs_dict, dict):
            return []
        if "select" not in obs_dict or obs_dict.get("select") is None:
            return list(main.DECK)

        try:
            obs = main.to_observation_class(obs_dict)
            if obs.select is None or not obs.select.option:
                return []

            options = list(obs.select.option)
            try:
                context_name = main.SelectContext(obs.select.context).name
            except Exception:
                context_name = "UNKNOWN"

            state = extract_state_features(obs)

            # Check if this prompt is an empty-bench search with basic available
            if context_name == "TO_HAND" and state.my_bench_count == 0:
                has_basic = False
                for opt in options:
                    c = main.v4_card_from_option(obs, opt)
                    if c is not None and main.v4_is_pokemon(c):
                        cd = main.v4_card_data(c)
                        stg = main.safe_get(cd, "stage", 0) if cd else main.safe_get(c, "stage", 0)
                        if stg == 0 or stg == "BASIC" or stg == "Basic":
                            has_basic = True
                            break
                if has_basic:
                    self.empty_bench_searches_with_basic += 1

            v4_scored = []
            h2_scored = []

            for i, opt in enumerate(options):
                try:
                    v4_s = float(main.v4_score_action(obs, opt, context_name))
                except Exception:
                    v4_s = -10**8
                v4_scored.append((v4_s, -i, i))

                h2_s = self._score_h2(obs, opt, v4_s, context_name, state)
                h2_scored.append((h2_s, -i, i))

            v4_scored.sort(reverse=True)
            h2_scored.sort(reverse=True)

            v4_best_idx = v4_scored[0][2]
            v4_best_score = v4_scored[0][0]

            h2_best_idx = h2_scored[0][2]
            h2_best_score = h2_scored[0][0]

            h2_dict = {item[2]: item[0] for item in h2_scored}
            delta = h2_dict.get(h2_best_idx, -10**8) - h2_dict.get(v4_best_idx, -10**8)

            is_override = (
                h2_best_idx != v4_best_idx
                and delta > self.gating_threshold
            )

            final_idx = h2_best_idx if is_override else v4_best_idx
            primary_scored = h2_scored if is_override else v4_scored

            v4_opt = options[v4_best_idx] if 0 <= v4_best_idx < len(options) else None
            h2_opt = options[h2_best_idx] if 0 <= h2_best_idx < len(options) else None
            final_opt = options[final_idx] if 0 <= final_idx < len(options) else None

            v4_type = main.option_type_name(v4_opt) if v4_opt else "UNKNOWN"
            h2_type = main.option_type_name(h2_opt) if h2_opt else "UNKNOWN"
            final_type = main.option_type_name(final_opt) if final_opt else "UNKNOWN"

            v4_c = main.v4_card_from_option(obs, v4_opt) if v4_opt else None
            h2_c = main.v4_card_from_option(obs, h2_opt) if h2_opt else None
            v4_desc = str(main.safe_get(main.v4_card_data(v4_c), "name", "UNKNOWN")) if v4_c else v4_type
            h2_desc = str(main.safe_get(main.v4_card_data(h2_c), "name", "UNKNOWN")) if h2_c else h2_type

            record = DecisionRecord(
                experiment_id="P9-H2",
                game_id=self.current_game_id,
                step=self.current_step,
                player_idx=main.safe_get(obs.current, "yourIndex", 0),
                context=context_name,
                my_active_hp=state.my_active_hp,
                opp_active_hp=state.opp_active_hp,
                my_energy=state.my_active_energy,
                opp_energy=state.opp_active_energy,
                v4_action_idx=v4_best_idx,
                v4_action_type=v4_desc,
                v4_score=v4_best_score,
                plan_action_idx=h2_best_idx,
                plan_action_type=h2_desc,
                plan_score=h2_best_score,
                score_delta=delta,
                is_override=is_override,
                final_action_idx=final_idx,
                final_action_type=h2_desc if is_override else v4_desc,
            )
            self.decision_logs.append(record)

            max_c = getattr(obs.select, "maxCount", 1) or 1
            min_c = getattr(obs.select, "minCount", 1) or 1
            max_c = max(min_c, min(int(max_c), len(options)))

            selected = [final_idx]
            if max_c > 1:
                for _, _, idx in primary_scored:
                    if idx != final_idx:
                        selected.append(idx)
                    if len(selected) >= max_c:
                        break

            return main.legal_selection(obs, selected)

        except Exception:
            self.fallback_count += 1
            return main.agent(obs_dict)


def run_controlled_match(agent_0, agent_1, max_steps=160):
    obs, _ = battle_start(main.DECK, main.DECK)
    steps = 0
    errors = 0
    try:
        while steps < max_steps:
            res = obs.get("current", {}).get("result", None)
            if res is not None and res != -1:
                return {"result": res, "steps": steps, "errors": errors}

            select = obs.get("select")
            if select is None:
                return {"result": res, "steps": steps, "errors": errors}

            your_idx = obs.get("current", {}).get("yourIndex", 0)
            cur_agent = agent_0 if your_idx == 0 else agent_1
            if hasattr(cur_agent, "set_game_context"):
                cur_agent.set_game_context(cur_agent.current_game_id, steps)
                choice = cur_agent.choose_action(obs)
            else:
                choice = cur_agent(obs)

            options = select.get("option", [])
            min_c = int(select.get("minCount", 0) or 0)
            max_c = min(int(select.get("maxCount", len(options)) or len(options)), len(options))

            if not isinstance(choice, list) or len(choice) < min_c or len(choice) > max_c or len(choice) != len(set(choice)) or any(i < 0 or i >= len(options) for i in choice):
                errors += 1
                choice = list(range(min(max(1, min_c), len(options))))

            obs = battle_select(choice)
            steps += 1

        return {"result": obs.get("current", {}).get("result", -1), "steps": steps, "errors": errors}
    finally:
        battle_finish()


def run_p9_h2_benchmark(total_games: int = 200) -> Dict[str, Any]:
    print("=" * 75)
    print(f"STARTING P9-H2 BENCHMARK: {total_games} GAMES vs FROZEN V4 CONTROL")
    print("=" * 75)

    h2_agent = P9H2Agent(gating_threshold=150.0)

    wins, losses, draws = 0, 0, 0
    total_steps = 0
    p0_wins, p0_games = 0, 0
    p1_wins, p1_games = 0, 0
    all_records: List[DecisionRecord] = []

    t0 = time.time()

    for g in range(1, total_games + 1):
        h2_agent.current_game_id = g
        start_len = len(h2_agent.decision_logs)

        if g % 2 == 1:
            # H2 is Player 0
            m = run_controlled_match(h2_agent, main.agent)
            res = m["result"]
            outcome = "WIN" if res == 0 else ("LOSS" if res == 1 else "DRAW")
            p0_games += 1
            if outcome == "WIN": p0_wins += 1
        else:
            # H2 is Player 1
            m = run_controlled_match(main.agent, h2_agent)
            res = m["result"]
            outcome = "WIN" if res == 1 else ("LOSS" if res == 0 else "DRAW")
            p1_games += 1
            if outcome == "WIN": p1_wins += 1

        if outcome == "WIN": wins += 1
        elif outcome == "LOSS": losses += 1
        else: draws += 1

        total_steps += m["steps"]

        end_len = len(h2_agent.decision_logs)
        for idx in range(start_len, end_len):
            rec = h2_agent.decision_logs[idx]
            rec.game_outcome = outcome
            if rec.is_override:
                rec.is_winning_override = (outcome == "WIN")
            all_records.append(rec)

        if g % 50 == 0 or g == total_games:
            wr = (wins / g) * 100.0
            print(f"  Game {g:03d}/{total_games} -> {wins}W - {losses}L - {draws}D (Win Rate: {wr:.1f}%) | Steps: {m['steps']}")

    elapsed = time.time() - t0
    win_rate = (wins / total_games) * 100.0
    ci_lower, ci_upper = compute_wilson_ci(wins, total_games)

    total_decisions = len(all_records)
    override_records = [r for r in all_records if r.is_override]
    total_overrides = len(override_records)
    override_rate = (total_overrides / max(1, total_decisions)) * 100.0

    winning_overrides = sum(1 for r in override_records if r.is_winning_override)
    losing_overrides = total_overrides - winning_overrides
    override_win_rate = (winning_overrides / max(1, total_overrides)) * 100.0 if total_overrides > 0 else 0.0

    override_cats = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0})
    for r in override_records:
        key = (r.v4_action_type, r.plan_action_type)
        override_cats[key]["count"] += 1
        if r.is_winning_override: override_cats[key]["wins"] += 1
        else: override_cats[key]["losses"] += 1

    stats = {
        "games": total_games,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p0_wr": (p0_wins / p0_games) * 100.0,
        "p1_wr": (p1_wins / p1_games) * 100.0,
        "avg_steps": total_steps / total_games,
        "contract_errors": h2_agent.contract_errors,
        "total_decisions": total_decisions,
        "empty_bench_searches_with_basic": h2_agent.empty_bench_searches_with_basic,
        "total_overrides": total_overrides,
        "override_rate": override_rate,
        "winning_overrides": winning_overrides,
        "losing_overrides": losing_overrides,
        "override_win_rate": override_win_rate,
        "elapsed_sec": elapsed,
        "override_cats": dict(override_cats),
        "records": all_records,
    }

    print("\n" + "=" * 75)
    print("P9-H2 BENCHMARK RESULTS (200 GAMES vs FROZEN V4)")
    print("=" * 75)
    print(f"Match Record:              {wins}W - {losses}L - {draws}D")
    print(f"Win Rate vs P0 (V4):       {win_rate:.2f}% (95% Wilson CI: [{ci_lower:.2f}%, {ci_upper:.2f}%])")
    print(f"Win Rate as Player 0 (1st):{(p0_wins / p0_games)*100:.1f}% ({p0_wins}/{p0_games})")
    print(f"Win Rate as Player 1 (2nd):{(p1_wins / p1_games)*100:.1f}% ({p1_wins}/{p1_games})")
    print(f"Average Match Length:      {total_steps / total_games:.2f} steps")
    print(f"Contract Errors:           {h2_agent.contract_errors}")
    print(f"Empty-Bench Searches (w/ Basic): {h2_agent.empty_bench_searches_with_basic}")
    print(f"Total H2 Search Overrides: {total_overrides} / {total_decisions} ({override_rate:.2f}%)")
    print(f"Override Win Conversion:   {override_win_rate:.1f}% ({winning_overrides} Wins / {losing_overrides} Losses)")
    print(f"Elapsed Time:              {elapsed:.2f}s")
    print("=" * 75)

    print("\nOVERRIDE BREAKDOWN:")
    for (v4_t, h2_t), d in sorted(override_cats.items(), key=lambda x: x[1]["count"], reverse=True):
        c, w, l = d["count"], d["wins"], d["losses"]
        wp = (w / c) * 100.0 if c > 0 else 0.0
        print(f"  {v4_t:<20} -> {h2_t:<20} | Count: {c:<4} | Wins: {w:<4} | Losses: {l:<4} | Win %: {wp:>5.1f}%")
    print("=" * 75)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P9-H2 Benchmark")
    parser.add_argument("--games", type=int, default=200, help="Total games")
    args = parser.parse_args()
    run_p9_h2_benchmark(total_games=args.games)
