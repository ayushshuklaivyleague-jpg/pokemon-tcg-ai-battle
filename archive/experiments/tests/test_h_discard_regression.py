"""
H_DISCARD Experimental Benchmark Suite: Isolated Discard Resource-Preservation.
Tests Hypothesis H_DISCARD:
In DISCARD_ENERGY contexts, if Basic Water Energy and either Waitress or
Lillie's Determination are simultaneously legal discard candidates,
prefer discarding the Basic Water Energy.
This rule applies ONLY when both resource categories are simultaneously legal candidates.
No other changes (no MAIN scoring, no TO_HAND, no attack selection, no retreat logic,
no KO logic, no threat model, no counterfactual logic, no energy attachment logic,
no other V4 behavior changes).
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
class HDiscardDecisionRecord:
    experiment_id: str
    game_id: int
    step: int
    turn: int
    player_idx: int
    context: str
    num_options: int
    all_legal_candidates_str: str
    is_simultaneous_candidate_state: bool
    v4_action_idx: int
    v4_action_desc: str
    v4_score: float
    h_discard_action_idx: int
    h_discard_action_desc: str
    h_discard_score: float
    score_delta: float
    is_override: bool
    final_action_idx: int
    final_action_desc: str
    is_legal: bool
    hand_state: str
    my_active_name: str
    my_active_hp: float
    my_active_energy: int
    my_bench_state: str
    opp_active_name: str
    opp_active_hp: float
    opp_active_energy: int
    opp_bench_state: str
    game_outcome: str = "UNKNOWN"
    is_winning_override: Optional[bool] = None


class HDiscardAgent:
    def __init__(self, gating_threshold: float = 150.0):
        self.gating_threshold = gating_threshold
        self.decision_logs: List[HDiscardDecisionRecord] = []
        self.fallback_count = 0
        self.contract_errors = 0
        self.current_game_id = 0
        self.current_step = 0
        self.simultaneous_candidate_prompt_count = 0

    def set_game_context(self, game_id: int, step: int):
        self.current_game_id = game_id
        self.current_step = step

    def _resolve_option_card(self, obs: Any, opt: Any, player: Any) -> Tuple[Optional[Any], str]:
        """
        Accurately resolve the card and its descriptive name for any option.
        """
        card = None
        area = main.safe_get(opt, "area", None)
        index = main.safe_get(opt, "index", 0)
        energy_idx = main.safe_get(opt, "energyIndex", None)

        try:
            # Active energy
            if area == 4 and player.active and len(player.active) > 0 and player.active[0] is not None:
                pkmn = player.active[0]
                if energy_idx is not None and hasattr(pkmn, "energyCards") and energy_idx < len(pkmn.energyCards):
                    card = pkmn.energyCards[energy_idx]
                else:
                    card = pkmn
            # Bench energy or pokemon
            elif area == 5 and player.bench and index < len(player.bench) and player.bench[index] is not None:
                pkmn = player.bench[index]
                if energy_idx is not None and hasattr(pkmn, "energyCards") and energy_idx < len(pkmn.energyCards):
                    card = pkmn.energyCards[energy_idx]
                else:
                    card = pkmn
            # Hand card
            elif area == 2 and player.hand and index < len(player.hand) and player.hand[index] is not None:
                card = player.hand[index]
            else:
                card = main.v4_card_from_option(obs, opt)
        except Exception:
            card = main.v4_card_from_option(obs, opt)

        if card is None:
            card = main.v4_card_from_option(obs, opt)

        cdata = main.v4_card_data(card) if card else None
        name = str(main.safe_get(cdata, "name", "UNKNOWN")) if cdata else "UNKNOWN"
        return card, name

    def _is_basic_water_energy(self, card: Any, name: str) -> bool:
        if "Basic {W} Energy" in name or "Water Energy" in name:
            return True
        if card is not None and getattr(card, "id", None) == 3:
            return True
        if card is not None and main.v4_is_energy(card):
            return True
        return False

    def _is_draw_supporter(self, card: Any, name: str) -> bool:
        if "Waitress" in name or "Lillie" in name:
            return True
        if card is not None and getattr(card, "id", None) in (1227, 1235):
            return True
        return False

    def _score_h_discard(
        self,
        obs: Any,
        option: Any,
        v4_s: float,
        context_name: str,
        simultaneous_active: bool,
        card: Any,
        card_name: str,
    ) -> float:
        """
        H_DISCARD RULE:
        Target: DISCARD_ENERGY (and discard prompts).
        If Basic Water Energy and either Waitress or Lillie's Determination
        are simultaneously legal discard candidates, prefer discarding Basic Water Energy.
        Important: Applies ONLY when both resource categories are simultaneously legal candidates.
        """
        if not simultaneous_active:
            return v4_s

        if context_name in ("DISCARD_ENERGY", "DISCARD", "DISCARD_ENERGY_CARD", "DISCARD_CARD_OR_ATTACHED_CARD"):
            if self._is_basic_water_energy(card, card_name):
                return v4_s + 25000.0  # Top priority discard
            elif self._is_draw_supporter(card, card_name):
                return v4_s - 25000.0  # Preserve draw supporter

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
            player_idx = obs.current.yourIndex
            player = obs.current.players[player_idx]

            # Resolve all legal candidate options
            opt_cards = []
            has_basic_water = False
            has_draw_supp = False
            candidates_desc = []

            for i, opt in enumerate(options):
                c, cname = self._resolve_option_card(obs, opt, player)
                opt_typ = main.option_type_name(opt)
                opt_cards.append((c, cname, opt_typ))

                if self._is_basic_water_energy(c, cname):
                    has_basic_water = True
                if self._is_draw_supporter(c, cname):
                    has_draw_supp = True

                candidates_desc.append(f"[{i}]{opt_typ}({cname})")

            is_simultaneous = (
                context_name in ("DISCARD_ENERGY", "DISCARD", "DISCARD_ENERGY_CARD", "DISCARD_CARD_OR_ATTACHED_CARD")
                and has_basic_water
                and has_draw_supp
            )

            if is_simultaneous:
                self.simultaneous_candidate_prompt_count += 1

            v4_scored = []
            h_discard_scored = []

            for i, opt in enumerate(options):
                try:
                    v4_s = float(main.v4_score_action(obs, opt, context_name))
                except Exception:
                    v4_s = -10**8
                v4_scored.append((v4_s, -i, i))

                c, cname, _ = opt_cards[i]
                h_s = self._score_h_discard(
                    obs, opt, v4_s, context_name, is_simultaneous, c, cname
                )
                h_discard_scored.append((h_s, -i, i))

            v4_scored.sort(reverse=True)
            h_discard_scored.sort(reverse=True)

            v4_best_idx = v4_scored[0][2]
            v4_best_score = v4_scored[0][0]

            h_best_idx = h_discard_scored[0][2]
            h_best_score = h_discard_scored[0][0]

            h_dict = {item[2]: item[0] for item in h_discard_scored}
            delta = h_dict.get(h_best_idx, -10**8) - h_dict.get(v4_best_idx, -10**8)

            is_override = (
                h_best_idx != v4_best_idx
                and delta > self.gating_threshold
            )

            final_idx = h_best_idx if is_override else v4_best_idx
            primary_scored = h_discard_scored if is_override else v4_scored

            v4_desc = opt_cards[v4_best_idx][1] if 0 <= v4_best_idx < len(opt_cards) else "UNKNOWN"
            h_desc = opt_cards[h_best_idx][1] if 0 <= h_best_idx < len(opt_cards) else "UNKNOWN"
            final_desc = opt_cards[final_idx][1] if 0 <= final_idx < len(opt_cards) else "UNKNOWN"

            # Check legality
            min_c = getattr(obs.select, "minCount", 1) or 1
            max_c = getattr(obs.select, "maxCount", 1) or 1
            max_c = max(min_c, min(int(max_c), len(options)))
            is_legal = (0 <= final_idx < len(options))

            # Hand state
            hand_cards = [
                str(main.safe_get(main.v4_card_data(c), "name", "UNKNOWN"))
                for c in (player.hand or []) if c is not None
            ]
            hand_str = "; ".join(hand_cards)

            # Bench state
            my_bench_str = f"count={state.my_bench_count}, total_energy={state.my_bench_total_energy}"
            opp_bench_str = f"count={state.opp_bench_count}"

            opp_player = obs.current.players[1 - player_idx]
            opp_active_pkmn = opp_player.active[0] if opp_player.active and len(opp_player.active) > 0 else None
            opp_active_name = str(main.safe_get(main.v4_card_data(opp_active_pkmn), "name", "NONE")) if opp_active_pkmn else "NONE"

            my_active_pkmn = player.active[0] if player.active and len(player.active) > 0 else None
            my_active_name = str(main.safe_get(main.v4_card_data(my_active_pkmn), "name", "NONE")) if my_active_pkmn else "NONE"

            turn = getattr(obs.current, "turn", 0)

            record = HDiscardDecisionRecord(
                experiment_id="H_DISCARD",
                game_id=self.current_game_id,
                step=self.current_step,
                turn=turn,
                player_idx=player_idx,
                context=context_name,
                num_options=len(options),
                all_legal_candidates_str="; ".join(candidates_desc),
                is_simultaneous_candidate_state=is_simultaneous,
                v4_action_idx=v4_best_idx,
                v4_action_desc=v4_desc,
                v4_score=v4_best_score,
                h_discard_action_idx=h_best_idx,
                h_discard_action_desc=h_desc,
                h_discard_score=h_best_score,
                score_delta=delta,
                is_override=is_override,
                final_action_idx=final_idx,
                final_action_desc=final_desc,
                is_legal=is_legal,
                hand_state=hand_str,
                my_active_name=my_active_name,
                my_active_hp=state.my_active_hp,
                my_active_energy=state.my_active_energy,
                my_bench_state=my_bench_str,
                opp_active_name=opp_active_name,
                opp_active_hp=state.opp_active_hp,
                opp_active_energy=state.opp_active_energy,
                opp_bench_state=opp_bench_str,
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


def run_h_discard_benchmark(total_games: int = 200, csv_out_path: str = "h_discard_decision_audit.csv") -> Dict[str, Any]:
    print("=" * 75)
    print(f"STARTING H_DISCARD BENCHMARK: {total_games} GAMES vs FROZEN V4 CONTROL")
    print("=" * 75)

    h_agent = HDiscardAgent(gating_threshold=150.0)

    wins, losses, draws = 0, 0, 0
    total_steps = 0
    p0_wins, p0_games = 0, 0
    p1_wins, p1_games = 0, 0
    all_records: List[HDiscardDecisionRecord] = []

    t0 = time.time()

    for g in range(1, total_games + 1):
        h_agent.current_game_id = g
        start_len = len(h_agent.decision_logs)

        if g % 2 == 1:
            # H_DISCARD is Player 0
            m = run_controlled_match(h_agent, main.agent)
            res = m["result"]
            outcome = "WIN" if res == 0 else ("LOSS" if res == 1 else "DRAW")
            p0_games += 1
            if outcome == "WIN": p0_wins += 1
        else:
            # H_DISCARD is Player 1
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

    discard_decisions = [r for r in all_records if "DISCARD" in r.context]
    simultaneous_decisions = [r for r in all_records if r.is_simultaneous_candidate_state]

    override_cats = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0})
    for r in override_records:
        key = (r.v4_action_desc, r.h_discard_action_desc)
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
        "discard_decisions_count": len(discard_decisions),
        "simultaneous_candidate_count": len(simultaneous_decisions),
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
                "all_legal_candidates_str", "is_simultaneous_candidate_state",
                "v4_action_idx", "v4_action_desc", "v4_score",
                "h_discard_action_idx", "h_discard_action_desc", "h_discard_score",
                "score_delta", "is_override", "final_action_idx", "final_action_desc",
                "is_legal", "hand_state", "my_active_name", "my_active_hp",
                "my_active_energy", "my_bench_state", "opp_active_name",
                "opp_active_hp", "opp_active_energy", "opp_bench_state",
                "game_outcome", "is_winning_override"
            ])
            writer.writeheader()
            for r in all_records:
                d = asdict(r)
                d.pop("experiment_id", None)
                writer.writerow(d)
        print(f"\nWrote complete decision audit to {csv_file} ({len(all_records)} decisions).")

    print("\n" + "=" * 75)
    print("H_DISCARD BENCHMARK RESULTS (200 GAMES vs FROZEN V4)")
    print("=" * 75)
    print(f"Match Record:              {wins}W - {losses}L - {draws}D")
    print(f"Win Rate vs P0 (V4):       {win_rate:.2f}% (95% Wilson CI: [{ci_lower:.2f}%, {ci_upper:.2f}%])")
    print(f"Win Rate as Player 0 (1st):{(p0_wins / p0_games)*100:.1f}% ({p0_wins}/{p0_games})")
    print(f"Win Rate as Player 1 (2nd):{(p1_wins / p1_games)*100:.1f}% ({p1_wins}/{p1_games})")
    print(f"Average Match Length:      {total_steps / total_games:.2f} steps")
    print(f"Contract Errors:           {h_agent.contract_errors}")
    print(f"Fallback Activations:      {h_agent.fallback_count}")
    print(f"Total Discard Prompts:     {len(discard_decisions)} / {total_decisions} total decisions")
    print(f"Simultaneous Prompts:      {len(simultaneous_decisions)} (both Basic Energy + Draw Supporter legal)")
    print(f"Total H_DISCARD Overrides: {total_overrides} / {total_decisions} ({override_rate:.2f}%)")
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
        print("\nNo overrides triggered (0 simultaneous legal candidates).")
        print("=" * 75)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="H_DISCARD Benchmark")
    parser.add_argument("--games", type=int, default=200, help="Total games")
    parser.add_argument("--csv", type=str, default="h_discard_decision_audit.csv", help="CSV audit output path")
    args = parser.parse_args()
    run_h_discard_benchmark(total_games=args.games, csv_out_path=args.csv)
