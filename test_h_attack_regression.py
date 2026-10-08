"""
H_ATTACK_SELECT Experimental Benchmark Suite: Isolated High-HP Dynamic Attack Selection.
Tests Hypothesis H_ATTACK_SELECT:
In MAIN / ATTACK contexts, when Active Pokémon is Mega Abomasnow ex and both
Attack 1046 (RNG discard attack, 2 Energy) and Attack 1047 (Flat 200 dmg, 3 Energy) are legal:
1. If Opponent Active HP > 200 AND Player Deck Count > 6:
   Prefer Attack 1046 (+10,000 bonus) to attempt the 1-Hit Knockout against high-HP targets.
2. If Opponent Active HP <= 200 OR Player Deck Count <= 6:
   Prefer Attack 1047 (preserve deck integrity and secure guaranteed lethal).

Strict Isolation Invariants:
- main.py (MIKE V4 Champion) is FROZEN.
- submission_notebook.ipynb is FROZEN.
- Zero changes to other action types (ATTACH, PLAY, EVOLVE, RETREAT).
- Zero changes to other Pokémon attacks (Kyogre, Snover).
- Zero threat modeling, counterfactuals, or bench anchors.
Evaluated over 200 balanced matches against Frozen V4/P0 Control Baseline.
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


def compute_wilson_ci(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.95996
    p = wins / total
    denominator = 1.0 + (z**2) / total
    center = (p + (z**2) / (2 * total)) / denominator
    margin = (z * math.sqrt((p * (1.0 - p) / total) + (z**2) / (4 * (total**2)))) / denominator
    return max(0.0, center - margin) * 100.0, min(1.0, center + margin) * 100.0


@dataclass
class HAttackDecisionRecord:
    experiment_id: str
    game_id: int
    step: int
    turn: int
    player_idx: int
    context: str
    num_options: int
    active_pokemon_name: str
    active_energy: int
    opp_active_name: str
    opp_active_hp: float
    deck_count: int
    is_multi_attack_abomasnow_state: bool
    v4_action_idx: int
    v4_action_desc: str
    v4_score: float
    h_attack_action_idx: int
    h_attack_action_desc: str
    h_attack_score: float
    score_delta: float
    is_override: bool
    final_action_idx: int
    final_action_desc: str
    is_legal: bool
    game_outcome: str = "UNKNOWN"
    is_winning_override: Optional[bool] = None


class HAttackAgent:
    def __init__(self, gating_threshold: float = 150.0):
        self.gating_threshold = gating_threshold
        self.decision_logs: List[HAttackDecisionRecord] = []
        self.fallback_count = 0
        self.contract_errors = 0
        self.current_game_id = 0
        self.current_step = 0
        self.multi_attack_abomasnow_count = 0

    def set_game_context(self, game_id: int, step: int):
        self.current_game_id = game_id
        self.current_step = step

    def _score_h_attack(
        self,
        obs: Any,
        option: Any,
        v4_s: float,
        context_name: str,
        is_abomasnow_multi_attack: bool,
        opp_hp: float,
        deck_count: int,
    ) -> float:
        """
        H_ATTACK_SELECT RULE:
        When Active is Mega Abomasnow ex and both Attack 1046 and 1047 are legal:
        1. If Opponent HP > 200 AND Deck Count > 6:
           Prefer Attack 1046 (+10,000 bonus).
        2. If Opponent HP <= 200 OR Deck Count <= 6:
           Prefer Attack 1047 (+10,000 bonus).
        """
        if not is_abomasnow_multi_attack:
            return v4_s

        typ = main.option_type_name(option)
        aid = getattr(option, "attackId", None)

        if typ == "ATTACK" or context_name == "ATTACK":
            if aid == 1046:
                if opp_hp > 200.0 and deck_count > 6:
                    return v4_s + 10000.0
            elif aid == 1047:
                if opp_hp <= 200.0 or deck_count <= 6:
                    return v4_s + 10000.0

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

            player_idx = obs.current.yourIndex
            player = obs.current.players[player_idx]
            opp_player = obs.current.players[1 - player_idx]

            act_pkmn = player.active[0] if player.active and len(player.active) > 0 else None
            act_name = str(main.safe_get(main.v4_card_data(act_pkmn), "name", "NONE")) if act_pkmn else "NONE"
            act_energy = len(getattr(act_pkmn, "energyCards", [])) if act_pkmn else 0

            opp_pkmn = opp_player.active[0] if opp_player.active and len(opp_player.active) > 0 else None
            opp_name = str(main.safe_get(main.v4_card_data(opp_pkmn), "name", "NONE")) if opp_pkmn else "NONE"
            opp_hp = float(getattr(opp_pkmn, "hp", 0)) if opp_pkmn else 0.0

            deck_count = int(player.deckCount) if hasattr(player, "deckCount") else 0

            # Check if this state has both 1046 and 1047 legal on Mega Abomasnow ex
            attack_opts = [opt for opt in options if main.option_type_name(opt) == "ATTACK" or context_name == "ATTACK"]
            aids = [getattr(opt, "attackId", None) for opt in attack_opts]
            is_abomasnow_multi_attack = (
                "Abomasnow" in act_name
                and 1046 in aids
                and 1047 in aids
            )

            if is_abomasnow_multi_attack:
                self.multi_attack_abomasnow_count += 1

            v4_scored = []
            h_attack_scored = []

            for i, opt in enumerate(options):
                try:
                    v4_s = float(main.v4_score_action(obs, opt, context_name))
                except Exception:
                    v4_s = -10**8
                v4_scored.append((v4_s, -i, i))

                h_s = self._score_h_attack(
                    obs, opt, v4_s, context_name, is_abomasnow_multi_attack, opp_hp, deck_count
                )
                h_attack_scored.append((h_s, -i, i))

            v4_scored.sort(reverse=True)
            h_attack_scored.sort(reverse=True)

            v4_best_idx = v4_scored[0][2]
            v4_best_score = v4_scored[0][0]

            h_best_idx = h_attack_scored[0][2]
            h_best_score = h_attack_scored[0][0]

            h_dict = {item[2]: item[0] for item in h_attack_scored}
            delta = h_dict.get(h_best_idx, -10**8) - h_dict.get(v4_best_idx, -10**8)

            is_override = (
                h_best_idx != v4_best_idx
                and delta > self.gating_threshold
            )

            final_idx = h_best_idx if is_override else v4_best_idx
            primary_scored = h_attack_scored if is_override else v4_scored

            # Action descriptions
            def describe_option(opt):
                if not opt: return "UNKNOWN"
                typ = main.option_type_name(opt)
                if typ == "ATTACK":
                    aid = getattr(opt, "attackId", None)
                    return f"ATTACK_{aid}"
                return typ

            v4_opt = options[v4_best_idx] if 0 <= v4_best_idx < len(options) else None
            h_opt = options[h_best_idx] if 0 <= h_best_idx < len(options) else None
            final_opt = options[final_idx] if 0 <= final_idx < len(options) else None

            v4_desc = describe_option(v4_opt)
            h_desc = describe_option(h_opt)
            final_desc = describe_option(final_opt)

            # Check legality
            min_c = getattr(obs.select, "minCount", 1) or 1
            max_c = getattr(obs.select, "maxCount", 1) or 1
            max_c = max(min_c, min(int(max_c), len(options)))
            is_legal = (0 <= final_idx < len(options))

            turn = getattr(obs.current, "turn", 0)

            record = HAttackDecisionRecord(
                experiment_id="H_ATTACK_SELECT",
                game_id=self.current_game_id,
                step=self.current_step,
                turn=turn,
                player_idx=player_idx,
                context=context_name,
                num_options=len(options),
                active_pokemon_name=act_name,
                active_energy=act_energy,
                opp_active_name=opp_name,
                opp_active_hp=opp_hp,
                deck_count=deck_count,
                is_multi_attack_abomasnow_state=is_abomasnow_multi_attack,
                v4_action_idx=v4_best_idx,
                v4_action_desc=v4_desc,
                v4_score=v4_best_score,
                h_attack_action_idx=h_best_idx,
                h_attack_action_desc=h_desc,
                h_attack_score=h_best_score,
                score_delta=delta,
                is_override=is_override,
                final_action_idx=final_idx,
                final_action_desc=final_desc,
                is_legal=is_legal,
            )
            self.decision_logs.append(record)

            selected = [final_idx]
            if max_c > 1:
                for _, _, idx in primary_scored:
                    if idx != final_idx:
                        selected.append(idx)
                    if len(selected) >= max_c:
                        break

            return main.legal_selection(obs_dict, selected)

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


def run_h_attack_benchmark(total_games: int = 200, csv_out_path: str = "h_attack_decision_audit.csv") -> Dict[str, Any]:
    print("=" * 75)
    print(f"STARTING H_ATTACK_SELECT BENCHMARK: {total_games} GAMES vs FROZEN V4 CONTROL")
    print("=" * 75)

    h_agent = HAttackAgent(gating_threshold=150.0)

    wins, losses, draws = 0, 0, 0
    total_steps = 0
    p0_wins, p0_games = 0, 0
    p1_wins, p1_games = 0, 0
    all_records: List[HAttackDecisionRecord] = []

    t0 = time.time()

    for g in range(1, total_games + 1):
        h_agent.current_game_id = g
        start_len = len(h_agent.decision_logs)

        if g % 2 == 1:
            # H_ATTACK is Player 0
            m = run_controlled_match(h_agent, main.agent)
            res = m["result"]
            outcome = "WIN" if res == 0 else ("LOSS" if res == 1 else "DRAW")
            p0_games += 1
            if outcome == "WIN": p0_wins += 1
        else:
            # H_ATTACK is Player 1
            m = run_controlled_match(main.agent, h_agent)
            res = m["result"]
            outcome = "WIN" if res == 1 else ("LOSS" if res == 0 else "DRAW")
            p1_games += 1
            if outcome == "WIN": p1_wins += 1

        if outcome == "WIN": wins += 1
        elif outcome == "LOSS": losses += 1
        else: draws += 1

        total_steps += m["steps"]

        end_len = len(h_agent.decision_logs)
        for idx in range(start_len, end_len):
            rec = h_agent.decision_logs[idx]
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

    multi_attack_decisions = [r for r in all_records if r.is_multi_attack_abomasnow_state]

    override_cats = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0})
    for r in override_records:
        key = (r.v4_action_desc, r.h_attack_action_desc)
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
        "p0_wins": p0_wins,
        "p0_games": p0_games,
        "p1_wins": p1_wins,
        "p1_games": p1_games,
        "avg_steps": total_steps / total_games,
        "contract_errors": h_agent.contract_errors,
        "fallback_count": h_agent.fallback_count,
        "total_decisions": total_decisions,
        "multi_attack_abomasnow_count": len(multi_attack_decisions),
        "total_overrides": total_overrides,
        "override_rate": override_rate,
        "winning_overrides": winning_overrides,
        "losing_overrides": losing_overrides,
        "override_win_rate": override_win_rate,
        "elapsed_sec": elapsed,
        "override_cats": dict(override_cats),
        "records": all_records,
    }

    # Write CSV audit
    if csv_out_path and all_records:
        csv_file = Path(csv_out_path)
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "game_id", "step", "turn", "player_idx", "context", "num_options",
                "active_pokemon_name", "active_energy", "opp_active_name",
                "opp_active_hp", "deck_count", "is_multi_attack_abomasnow_state",
                "v4_action_idx", "v4_action_desc", "v4_score",
                "h_attack_action_idx", "h_attack_action_desc", "h_attack_score",
                "score_delta", "is_override", "final_action_idx", "final_action_desc",
                "is_legal", "game_outcome", "is_winning_override"
            ])
            writer.writeheader()
            for r in all_records:
                d = asdict(r)
                d.pop("experiment_id", None)
                writer.writerow(d)
        print(f"\nWrote complete decision audit to {csv_file} ({len(all_records)} decisions).")

    print("\n" + "=" * 75)
    print("H_ATTACK_SELECT BENCHMARK RESULTS (200 GAMES vs FROZEN V4)")
    print("=" * 75)
    print(f"Match Record:              {wins}W - {losses}L - {draws}D")
    print(f"Win Rate vs P0 (V4):       {win_rate:.2f}% (95% Wilson CI: [{ci_lower:.2f}%, {ci_upper:.2f}%])")
    print(f"Win Rate as Player 0 (1st):{(p0_wins / p0_games)*100:.1f}% ({p0_wins}/{p0_games})")
    print(f"Win Rate as Player 1 (2nd):{(p1_wins / p1_games)*100:.1f}% ({p1_wins}/{p1_games})")
    print(f"Average Match Length:      {total_steps / total_games:.2f} steps")
    print(f"Contract Errors:           {h_agent.contract_errors}")
    print(f"Fallback Activations:      {h_agent.fallback_count}")
    print(f"Multi-Attack Abomasnow States: {len(multi_attack_decisions)} / {total_decisions} total decisions")
    print(f"Total H_ATTACK Overrides:  {total_overrides} / {total_decisions} ({override_rate:.2f}%)")
    print(f"Override Win Conversion:   {override_win_rate:.1f}% ({winning_overrides} Wins / {losing_overrides} Losses)")
    print(f"Elapsed Time:              {elapsed:.2f}s")
    print("=" * 75)

    if override_cats:
        print("\nOVERRIDE BREAKDOWN:")
        for (v4_t, h_t), d in sorted(override_cats.items(), key=lambda x: x[1]["count"], reverse=True):
            c, w, l = d["count"], d["wins"], d["losses"]
            wp = (w / c) * 100.0 if c > 0 else 0.0
            print(f"  {v4_t:<20} -> {h_t:<20} | Count: {c:<4} | Wins: {w:<4} | Losses: {l:<4} | Win %: {wp:>5.1f}%")
        print("=" * 75)
    else:
        print("\nNo overrides triggered.")
        print("=" * 75)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="H_ATTACK_SELECT Benchmark")
    parser.add_argument("--games", type=int, default=200, help="Total games")
    parser.add_argument("--csv", type=str, default="h_attack_decision_audit.csv", help="CSV audit output path")
    args = parser.parse_args()
    run_h_attack_benchmark(total_games=args.games, csv_out_path=args.csv)
