"""
H_XEROSIC Experimental Benchmark Suite: Isolated Supporter Genome Prioritization.
Tests Hypothesis H_XEROSIC:
Demote WEIGHTS["xerosic"] from 3250 to 2950.
This changes exactly one genome priority value:
- When Xerosic and Dawn (3100) or Hilda (3000) are simultaneously held in hand,
  prioritize self-development (Dawn/Hilda) over opponent hand disruption (Xerosic).
- When Xerosic is held without Dawn or Hilda, Xerosic is still played as normal.

Evaluated over 200 balanced head-to-head matches against the Frozen Sol Eclipse Control Baseline
(100 games as Player 0, 100 games as Player 1).
All other weights, search layers, courage guards, and deck cards are strictly identical.
"""

import sys
import os
import re
import csv
import time
import math
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict

# Set stdout encoding if needed
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cg.api as api
from cg.game import battle_start, battle_select, battle_finish

# Load the unmodified Sol Eclipse code and deck
source_file = HERE / "codex_sol_eclipse_alakazam.py"
raw_code = source_file.read_text(encoding="utf-8")

main_match = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)

if not main_match or not deck_match:
    raise RuntimeError("Failed to parse codex_sol_eclipse_alakazam.py")

main_source = main_match.group(1)
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]


def compute_wilson_ci(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.95996
    p = wins / total
    denominator = 1.0 + (z**2) / total
    center = (p + (z**2) / (2 * total)) / denominator
    margin = (z * math.sqrt((p * (1.0 - p) / total) + (z**2) / (4 * (total**2)))) / denominator
    return max(0.0, center - margin) * 100.0, min(1.0, center + margin) * 100.0


def create_agent_instance(xerosic_weight: int):
    """
    Creates an isolated instance of the Sol Eclipse agent with the specified xerosic weight.
    All other weights, search layers, and guards are 100% identical.
    """
    ns = {"__file__": str(source_file)}
    exec(main_source, ns)
    
    # Apply isolated weight change
    ns["WEIGHTS"]["xerosic"] = xerosic_weight
    ns["W"]["xerosic"] = xerosic_weight
    
    return ns


# Instantiate Control (3250) and Candidate (2950)
control_ns = create_agent_instance(3250)
candidate_ns = create_agent_instance(2950)

print(f"Control W['xerosic']: {control_ns['WEIGHTS']['xerosic']}")
print(f"Candidate W['xerosic']: {candidate_ns['WEIGHTS']['xerosic']}")


def describe_opt(ns, obs, opt) -> str:
    if opt is None:
        return "None"
    card_table = ns["card_table"]
    
    def cname(cid: int) -> str:
        c = card_table.get(cid)
        return c.name if c else f"Card_{cid}"

    t = opt.type
    if t == api.OptionType.NUMBER:
        return f"NUMBER({opt.number})"
    elif t == api.OptionType.YES:
        return "YES"
    elif t == api.OptionType.NO:
        return "NO"
    elif t == api.OptionType.END:
        return "END_TURN"
    elif t == api.OptionType.CARD:
        c = ns["get_card"](obs, opt.area, opt.index, opt.playerIndex)
        return f"CARD({cname(c.id) if c else 'None'} in {opt.area})"
    elif t == api.OptionType.PLAY:
        c = ns["get_card"](obs, api.AreaType.HAND, opt.index, obs.current.yourIndex)
        return f"PLAY({cname(c.id) if c else 'None'})"
    elif t == api.OptionType.ATTACH:
        c = ns["get_card"](obs, api.AreaType.HAND, opt.index, obs.current.yourIndex)
        tgt = ns["get_card"](obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)
        return f"ATTACH({cname(c.id) if c else 'None'} -> {cname(tgt.id) if tgt else 'None'}@{opt.inPlayArea})"
    elif t == api.OptionType.EVOLVE:
        c = ns["get_card"](obs, api.AreaType.HAND, opt.index, obs.current.yourIndex)
        tgt = ns["get_card"](obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)
        return f"EVOLVE({cname(c.id) if c else 'None'} on {cname(tgt.id) if tgt else 'None'})"
    elif t == api.OptionType.ABILITY:
        c = ns["get_card"](obs, opt.area, opt.index, obs.current.yourIndex)
        return f"ABILITY({cname(c.id) if c else 'None'})"
    elif t == api.OptionType.RETREAT:
        return "RETREAT"
    elif t == api.OptionType.ATTACK:
        atk_names = {1070: "Teleportation", 1071: "Super Psy Bolt", 1072: "Powerful Hand"}
        return f"ATTACK({atk_names.get(opt.attackId, opt.attackId)})"
    return f"{opt.type}"


@dataclass
class HXerosicDecisionRecord:
    game_id: int
    step: int
    turn: int
    player_idx: int
    context: str
    num_options: int
    legal_options: str
    is_supporter_competition: bool
    control_action: str
    candidate_action: str
    control_desc: str
    candidate_desc: str
    is_override: bool
    hand_size: int
    deck_count: int
    my_prizes: int
    opp_prizes: int
    my_active: str
    my_bench: str
    opp_active: str
    opp_bench: str
    game_outcome: str = "UNKNOWN"
    is_winning_override: Optional[bool] = None


class HXerosicAuditedAgent:
    def __init__(self, candidate_ns, control_ns):
        self.cand_ns = candidate_ns
        self.ctrl_ns = control_ns
        self.records: List[HXerosicDecisionRecord] = []
        self.current_game_id = 0
        self.current_step = 0
        self.player_idx = 0
        self.contract_errors = 0
        self.fallback_count = 0

    def set_game(self, game_id: int, player_idx: int):
        self.current_game_id = game_id
        self.player_idx = player_idx
        self.current_step = 0

    def decide(self, obs_dict: Dict[str, Any]) -> List[int]:
        self.current_step += 1
        select = obs_dict.get("select")
        if select is None:
            # Initialization
            return self.cand_ns["agent"](obs_dict)

        obs = self.cand_ns["to_observation_class"](obs_dict)
        state = obs.current
        sel = obs.select
        my_idx = state.yourIndex
        my_p = state.players[my_idx]
        op_p = state.players[1 - my_idx]

        # 1. Compute Candidate Action
        cand_action = self.cand_ns["agent"](obs_dict)
        
        # 2. Compute Control Action for shadow audit
        ctrl_action = self.ctrl_ns["agent"](obs_dict)

        # 3. Check for supporter competition & override
        cand_desc = "None"
        ctrl_desc = "None"
        if sel and sel.option:
            cand_idx = cand_action[0] if cand_action else 0
            ctrl_idx = ctrl_action[0] if ctrl_action else 0
            cand_opt = sel.option[cand_idx] if 0 <= cand_idx < len(sel.option) else None
            ctrl_opt = sel.option[ctrl_idx] if 0 <= ctrl_idx < len(sel.option) else None
            cand_desc = describe_opt(self.cand_ns, obs, cand_opt)
            ctrl_desc = describe_opt(self.ctrl_ns, obs, ctrl_opt)

        is_override = (cand_action != ctrl_action)

        legal_options_desc = [describe_opt(self.cand_ns, obs, o) for o in sel.option]
        supporter_names = ["Hilda", "Dawn", "Xerosic", "Lana", "Boss's Orders", "Lillie"]
        is_sup_comp = (sel.context == api.SelectContext.MAIN and
                       sum(1 for opt in legal_options_desc if any(f"PLAY({s}" in opt for s in supporter_names)) >= 2)

        # Board strings
        my_act = my_p.active[0] if my_p.active else None
        op_act = op_p.active[0] if op_p.active else None
        cname = lambda cid: self.cand_ns["card_table"].get(cid).name if self.cand_ns["card_table"].get(cid) else f"Card_{cid}"

        my_act_str = f"{cname(my_act.id)} HP:{my_act.hp} En:{len(my_act.energies)}" if my_act else "None"
        op_act_str = f"{cname(op_act.id)} HP:{op_act.hp} En:{len(op_act.energies)}" if op_act else "None"
        my_bench_str = "/".join([f"{cname(b.id)} HP:{b.hp} En:{len(b.energies)}" for b in my_p.bench if b]) or "Empty"
        op_bench_str = "/".join([f"{cname(b.id)} HP:{b.hp} En:{len(b.energies)}" for b in op_p.bench if b]) or "Empty"

        rec = HXerosicDecisionRecord(
            game_id=self.current_game_id,
            step=self.current_step,
            turn=state.turn,
            player_idx=my_idx,
            context=api.SelectContext(sel.context).name if hasattr(sel.context, "name") else str(sel.context),
            num_options=len(sel.option),
            legal_options=" | ".join(legal_options_desc),
            is_supporter_competition=is_sup_comp,
            control_action=str(ctrl_action),
            candidate_action=str(cand_action),
            control_desc=ctrl_desc,
            candidate_desc=cand_desc,
            is_override=is_override,
            hand_size=len(my_p.hand) if my_p.hand else my_p.handCount,
            deck_count=my_p.deckCount,
            my_prizes=len(my_p.prize),
            opp_prizes=len(op_p.prize),
            my_active=my_act_str,
            my_bench=my_bench_str,
            opp_active=op_act_str,
            opp_bench=op_bench_str,
            game_outcome="UNKNOWN",
            is_winning_override=None
        )
        self.records.append(rec)

        # Validate action contract
        min_c = int(sel.minCount or 0)
        max_c = min(int(sel.maxCount or len(sel.option)), len(sel.option))
        if not isinstance(cand_action, list) or len(cand_action) < min_c or len(cand_action) > max_c or any(i < 0 or i >= len(sel.option) for i in cand_action):
            self.contract_errors += 1
            self.fallback_count += 1
            cand_action = list(range(min(max(1, min_c), len(sel.option))))

        return cand_action


class StandardSolAgent:
    def __init__(self, ns):
        self.ns = ns

    def set_game(self, game_id: int, player_idx: int):
        pass

    def decide(self, obs_dict):
        return self.ns["agent"](obs_dict)


def run_controlled_game(agent0, agent1, max_steps: int = 160) -> Tuple[int, int]:
    obs, start_data = battle_start(SOL_DECK, SOL_DECK)
    if not obs or not start_data:
        raise RuntimeError("Failed to start battle")

    step = 0
    agents = [agent0, agent1]

    while step < max_steps:
        step += 1
        res = obs.get("current", {}).get("result")
        if res is not None and res >= 0:
            break

        player_idx = obs.get("current", {}).get("yourIndex", 0)
        cur_agent = agents[player_idx]

        action = cur_agent.decide(obs)
        obs = battle_select(action)

    battle_finish()
    final_res = obs.get("current", {}).get("result", -1)
    return final_res, step


def run_h_xerosic_benchmark(total_games: int = 200, csv_out_path: str = "h_xerosic_decision_audit.csv"):
    print("=" * 80)
    print(f"STARTING H_XEROSIC BENCHMARK: {total_games} BALANCED HEAD-TO-HEAD MATCHES")
    print("Candidate (W['xerosic'] = 2950) vs Control Baseline (W['xerosic'] = 3250)")
    print("=" * 80, flush=True)

    cand_agent = HXerosicAuditedAgent(candidate_ns, control_ns)
    ctrl_agent = StandardSolAgent(control_ns)

    wins = 0
    losses = 0
    draws = 0
    p0_wins = 0
    p0_games = 0
    p1_wins = 0
    p1_games = 0
    total_steps = 0

    all_records: List[HXerosicDecisionRecord] = []
    game_override_counts = defaultdict(int)
    game_outcomes_dict = {}

    t0 = time.time()

    for g in range(1, total_games + 1):
        start_rec_idx = len(cand_agent.records)

        if g % 2 == 1:
            # Candidate is Player 0
            cand_agent.set_game(g, 0)
            res, steps = run_controlled_game(cand_agent, ctrl_agent)
            outcome = "WIN" if res == 0 else ("LOSS" if res == 1 else "DRAW")
            p0_games += 1
            if outcome == "WIN": p0_wins += 1
        else:
            # Candidate is Player 1
            cand_agent.set_game(g, 1)
            res, steps = run_controlled_game(ctrl_agent, cand_agent)
            outcome = "WIN" if res == 1 else ("LOSS" if res == 0 else "DRAW")
            p1_games += 1
            if outcome == "WIN": p1_wins += 1

        if outcome == "WIN": wins += 1
        elif outcome == "LOSS": losses += 1
        else: draws += 1

        total_steps += steps
        game_outcomes_dict[g] = outcome

        # Process records for this game
        end_rec_idx = len(cand_agent.records)
        for idx in range(start_rec_idx, end_rec_idx):
            rec = cand_agent.records[idx]
            rec.game_outcome = outcome
            if rec.is_override:
                rec.is_winning_override = (outcome == "WIN")
                game_override_counts[g] += 1
            all_records.append(rec)

        if g % 20 == 0 or g == total_games:
            wr = (wins / g) * 100.0
            print(f"  Game {g:03d}/{total_games} -> Candidate: {wins}W - {losses}L - {draws}D (Win Rate: {wr:.1f}%) | Steps: {steps}", flush=True)

    elapsed = time.time() - t0
    win_rate = (wins / total_games) * 100.0
    ci_lower, ci_upper = compute_wilson_ci(wins, total_games)

    total_decisions = len(all_records)
    override_records = [r for r in all_records if r.is_override]
    total_overrides = len(override_records)
    override_rate = (total_overrides / max(1, total_decisions)) * 100.0

    sup_comp_records = [r for r in all_records if r.is_supporter_competition]
    total_sup_comp = len(sup_comp_records)

    xerosic_candidate_selections = [r for r in all_records if "PLAY(Xerosic" in r.candidate_desc]
    xerosic_control_selections = [r for r in all_records if "PLAY(Xerosic" in r.control_desc]

    winning_overrides = sum(1 for r in override_records if r.is_winning_override)
    losing_overrides = total_overrides - winning_overrides
    override_win_rate = (winning_overrides / max(1, total_overrides)) * 100.0 if total_overrides > 0 else 0.0

    # Games where override occurred
    override_games = set(r.game_id for r in override_records)
    override_game_wins = sum(1 for g in override_games if game_outcomes_dict[g] == "WIN")
    override_game_losses = sum(1 for g in override_games if game_outcomes_dict[g] == "LOSS")
    override_game_draws = sum(1 for g in override_games if game_outcomes_dict[g] == "DRAW")
    override_game_wr = (override_game_wins / max(1, len(override_games))) * 100.0

    # Non-override games
    non_override_games = set(range(1, total_games + 1)) - override_games
    non_override_wins = sum(1 for g in non_override_games if game_outcomes_dict[g] == "WIN")
    non_override_losses = sum(1 for g in non_override_games if game_outcomes_dict[g] == "LOSS")
    non_override_draws = sum(1 for g in non_override_games if game_outcomes_dict[g] == "DRAW")
    non_override_wr = (non_override_wins / max(1, len(non_override_games))) * 100.0

    # Action transitions
    action_transitions = Counter((r.control_desc, r.candidate_desc) for r in override_records)

    # Output CSV
    csv_file = Path(csv_out_path)
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "game_id", "step", "turn", "player_idx", "context", "num_options",
            "legal_options", "is_supporter_competition", "control_action", "candidate_action",
            "control_desc", "candidate_desc", "is_override", "hand_size", "deck_count",
            "my_prizes", "opp_prizes", "my_active", "my_bench", "opp_active", "opp_bench",
            "game_outcome", "is_winning_override"
        ])
        writer.writeheader()
        for r in all_records:
            writer.writerow(asdict(r))

    print("\n" + "=" * 80)
    print("H_XEROSIC EMPIRICAL BENCHMARK RESULTS (200 GAMES HEAD-TO-HEAD)")
    print("=" * 80)
    print(f"Match Record:                  {wins}W - {losses}L - {draws}D")
    print(f"Candidate Win Rate vs Control: {win_rate:.2f}% (95% Wilson CI: [{ci_lower:.2f}%, {ci_upper:.2f}%])")
    print(f"Win Rate as Player 0 (1st):    {(p0_wins / p0_games)*100:.1f}% ({p0_wins}/{p0_games})")
    print(f"Win Rate as Player 1 (2nd):    {(p1_wins / p1_games)*100:.1f}% ({p1_wins}/{p1_games})")
    print(f"Average Game Length:           {total_steps / total_games:.2f} steps")
    print(f"Contract / Runtime Errors:     {cand_agent.contract_errors}")
    print(f"Fallback Activations:          {cand_agent.fallback_count}")
    print(f"Total Decisions Instrument:    {total_decisions}")
    print(f"Multi-Supporter States:        {total_sup_comp} ({total_sup_comp/total_decisions*100:.1f}%)")
    print(f"Control Xerosic Plays:         {len(xerosic_control_selections)}")
    print(f"Candidate Xerosic Plays:       {len(xerosic_candidate_selections)}")
    print(f"Total Decisions Overridden:    {total_overrides} / {total_decisions} ({override_rate:.2f}%)")
    print(f"Override Decision Win Conv:    {override_win_rate:.1f}% ({winning_overrides}W / {losing_overrides}L)")
    print(f"Override Games Count:          {len(override_games)} / {total_games} ({len(override_games)/total_games*100:.1f}%)")
    print(f"Override Games Win Rate:       {override_game_wr:.1f}% ({override_game_wins}W - {override_game_losses}L - {override_game_draws}D)")
    print(f"Non-Override Games Win Rate:   {non_override_wr:.1f}% ({non_override_wins}W - {non_override_losses}L - {non_override_draws}D)")
    print(f"Elapsed Benchmark Time:        {elapsed:.2f}s")
    print("=" * 80)

    print("\nACTION TRANSITIONS BREAKDOWN (Control -> Candidate):")
    for (ctrl_t, cand_t), count in action_transitions.most_common():
        print(f"  {ctrl_t:<35} -> {cand_t:<35} | Count: {count:>3}")
    print("=" * 80)

    return {
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
        "total_decisions": total_decisions,
        "total_sup_comp": total_sup_comp,
        "control_xerosic_count": len(xerosic_control_selections),
        "candidate_xerosic_count": len(xerosic_candidate_selections),
        "total_overrides": total_overrides,
        "override_rate": override_rate,
        "winning_overrides": winning_overrides,
        "losing_overrides": losing_overrides,
        "override_win_rate": override_win_rate,
        "override_games_count": len(override_games),
        "override_game_wins": override_game_wins,
        "override_game_losses": override_game_losses,
        "override_game_draws": override_game_draws,
        "override_game_wr": override_game_wr,
        "non_override_games_count": len(non_override_games),
        "non_override_wins": non_override_wins,
        "non_override_losses": non_override_losses,
        "non_override_draws": non_override_draws,
        "non_override_wr": non_override_wr,
        "action_transitions": dict(action_transitions),
        "elapsed_sec": elapsed,
        "contract_errors": cand_agent.contract_errors,
        "fallback_count": cand_agent.fallback_count
    }


if __name__ == "__main__":
    run_h_xerosic_benchmark(200, "h_xerosic_decision_audit.csv")
