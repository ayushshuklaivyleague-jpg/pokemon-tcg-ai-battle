"""
Optimized Parallel H_XEROSIC Benchmark Suite.
Runs 200 balanced head-to-head matches between Candidate (W['xerosic'] = 2950)
and Control (W['xerosic'] = 3250) across worker processes.

Captures all required metrics:
- total decisions
- Xerosic/Hilda/Dawn competition states
- Xerosic selections
- actual overrides caused by the weight change
- action transitions
- game outcomes (overall, P0, P1)
- contract/runtime errors
- fallback activations
- game length
- exact activation rate and match-level outcomes for override games
- 95% Wilson CI
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
import concurrent.futures

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cg.api as api
from cg.game import battle_start, battle_select, battle_finish

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
    ns = {"__file__": str(source_file)}
    exec(main_source, ns)
    ns["WEIGHTS"]["xerosic"] = xerosic_weight
    ns["W"]["xerosic"] = xerosic_weight
    return ns


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


def run_single_benchmark_game(game_id: int, cand_is_p0: bool) -> Dict[str, Any]:
    cand_ns = create_agent_instance(2950)
    ctrl_ns = create_agent_instance(3250)

    records: List[HXerosicDecisionRecord] = []
    contract_errors = 0
    fallback_count = 0

    obs, start_data = battle_start(SOL_DECK, SOL_DECK)
    if not obs or not start_data:
        raise RuntimeError(f"Game {game_id}: Failed to start battle")

    step = 0
    max_steps = 160
    cand_idx = 0 if cand_is_p0 else 1

    while step < max_steps:
        step += 1
        res = obs.get("current", {}).get("result")
        if res is not None and res >= 0:
            break

        player_idx = obs.get("current", {}).get("yourIndex", 0)
        select = obs.get("select")

        if select is None:
            if player_idx == cand_idx:
                action = cand_ns["agent"](obs)
            else:
                action = ctrl_ns["agent"](obs)
            obs = battle_select(action)
            continue

        if player_idx == cand_idx:
            obs_cls = cand_ns["to_observation_class"](obs)
            state = obs_cls.current
            sel = obs_cls.select
            my_p = state.players[player_idx]
            op_p = state.players[1 - player_idx]

            # Candidate Action
            cand_action = cand_ns["agent"](obs)

            # Shadow Control Action: only execute if Xerosic is in hand in MAIN context
            legal_options_desc = [describe_opt(cand_ns, obs_cls, o) for o in sel.option]
            has_xerosic_in_opts = any("PLAY(Xerosic" in opt for opt in legal_options_desc)

            if has_xerosic_in_opts and sel.context == api.SelectContext.MAIN:
                ctrl_action = ctrl_ns["agent"](obs)
            else:
                ctrl_action = cand_action

            cand_desc = "None"
            ctrl_desc = "None"
            if sel and sel.option:
                c_idx = cand_action[0] if cand_action else 0
                ct_idx = ctrl_action[0] if ctrl_action else 0
                cand_opt = sel.option[c_idx] if 0 <= c_idx < len(sel.option) else None
                ctrl_opt = sel.option[ct_idx] if 0 <= ct_idx < len(sel.option) else None
                cand_desc = describe_opt(cand_ns, obs_cls, cand_opt)
                ctrl_desc = describe_opt(ctrl_ns, obs_cls, ctrl_opt)

            is_override = (cand_action != ctrl_action)

            supporter_names = ["Hilda", "Dawn", "Xerosic", "Lana", "Boss's Orders", "Lillie"]
            is_sup_comp = (sel.context == api.SelectContext.MAIN and
                           sum(1 for opt in legal_options_desc if any(f"PLAY({s}" in opt for s in supporter_names)) >= 2)

            my_act = my_p.active[0] if my_p.active else None
            op_act = op_p.active[0] if op_p.active else None
            cname = lambda cid: cand_ns["card_table"].get(cid).name if cand_ns["card_table"].get(cid) else f"Card_{cid}"

            my_act_str = f"{cname(my_act.id)} HP:{my_act.hp} En:{len(my_act.energies)}" if my_act else "None"
            op_act_str = f"{cname(op_act.id)} HP:{op_act.hp} En:{len(op_act.energies)}" if op_act else "None"
            my_bench_str = "/".join([f"{cname(b.id)} HP:{b.hp} En:{len(b.energies)}" for b in my_p.bench if b]) or "Empty"
            op_bench_str = "/".join([f"{cname(b.id)} HP:{b.hp} En:{len(b.energies)}" for b in op_p.bench if b]) or "Empty"

            rec = HXerosicDecisionRecord(
                game_id=game_id,
                step=step,
                turn=state.turn,
                player_idx=player_idx,
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
            records.append(rec)

            min_c = int(sel.minCount or 0)
            max_c = min(int(sel.maxCount or len(sel.option)), len(sel.option))
            if not isinstance(cand_action, list) or len(cand_action) < min_c or len(cand_action) > max_c or any(i < 0 or i >= len(sel.option) for i in cand_action):
                contract_errors += 1
                fallback_count += 1
                cand_action = list(range(min(max(1, min_c), len(sel.option))))

            action = cand_action
        else:
            action = ctrl_ns["agent"](obs)

        obs = battle_select(action)

    battle_finish()
    final_res = obs.get("current", {}).get("result", -1)

    if final_res == cand_idx:
        outcome = "WIN"
    elif final_res == (1 - cand_idx):
        outcome = "LOSS"
    else:
        outcome = "DRAW"

    for r in records:
        r.game_outcome = outcome
        if r.is_override:
            r.is_winning_override = (outcome == "WIN")

    return {
        "game_id": game_id,
        "cand_is_p0": cand_is_p0,
        "outcome": outcome,
        "steps": step,
        "contract_errors": contract_errors,
        "fallback_count": fallback_count,
        "records": [asdict(r) for r in records]
    }


def run_parallel_benchmark(total_games: int = 200, workers: int = 6):
    print("=" * 80)
    print(f"STARTING PARALLEL H_XEROSIC BENCHMARK: {total_games} MATCHES ({workers} WORKERS)")
    print("Candidate (W['xerosic'] = 2950) vs Control Baseline (W['xerosic'] = 3250)")
    print("=" * 80, flush=True)

    tasks = [(g, (g % 2 == 1)) for g in range(1, total_games + 1)]
    
    t0 = time.time()
    results = []
    completed = 0
    wins = 0
    losses = 0
    draws = 0

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_benchmark_game, g_id, is_p0): (g_id, is_p0) for g_id, is_p0 in tasks}
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if res["outcome"] == "WIN": wins += 1
            elif res["outcome"] == "LOSS": losses += 1
            else: draws += 1

            if completed % 10 == 0 or completed == total_games:
                wr = (wins / completed) * 100.0
                print(f"  Progress: {completed:03d}/{total_games} -> {wins}W - {losses}L - {draws}D (Current Win Rate: {wr:.1f}%) [Last Game: {res['game_id']} {res['outcome']} in {res['steps']} steps]", flush=True)

    elapsed = time.time() - t0
    results.sort(key=lambda x: x["game_id"])

    all_records = []
    p0_wins = sum(1 for r in results if r["cand_is_p0"] and r["outcome"] == "WIN")
    p0_games = sum(1 for r in results if r["cand_is_p0"])
    p1_wins = sum(1 for r in results if not r["cand_is_p0"] and r["outcome"] == "WIN")
    p1_games = sum(1 for r in results if not r["cand_is_p0"])
    total_steps = sum(r["steps"] for r in results)
    total_contract_errors = sum(r["contract_errors"] for r in results)
    total_fallbacks = sum(r["fallback_count"] for r in results)

    for r in results:
        all_records.extend(r["records"])

    win_rate = (wins / total_games) * 100.0
    ci_lower, ci_upper = compute_wilson_ci(wins, total_games)

    total_decisions = len(all_records)
    override_records = [r for r in all_records if r["is_override"]]
    total_overrides = len(override_records)
    override_rate = (total_overrides / max(1, total_decisions)) * 100.0

    sup_comp_records = [r for r in all_records if r["is_supporter_competition"]]
    total_sup_comp = len(sup_comp_records)

    xerosic_candidate_selections = [r for r in all_records if "PLAY(Xerosic" in r["candidate_desc"]]
    xerosic_control_selections = [r for r in all_records if "PLAY(Xerosic" in r["control_desc"]]

    winning_overrides = sum(1 for r in override_records if r["is_winning_override"])
    losing_overrides = total_overrides - winning_overrides
    override_win_rate = (winning_overrides / max(1, total_overrides)) * 100.0 if total_overrides > 0 else 0.0

    override_games = set(r["game_id"] for r in override_records)
    game_outcomes_dict = {r["game_id"]: r["outcome"] for r in results}

    override_game_wins = sum(1 for g in override_games if game_outcomes_dict[g] == "WIN")
    override_game_losses = sum(1 for g in override_games if game_outcomes_dict[g] == "LOSS")
    override_game_draws = sum(1 for g in override_games if game_outcomes_dict[g] == "DRAW")
    override_game_wr = (override_game_wins / max(1, len(override_games))) * 100.0 if override_games else 0.0

    non_override_games = set(range(1, total_games + 1)) - override_games
    non_override_wins = sum(1 for g in non_override_games if game_outcomes_dict[g] == "WIN")
    non_override_losses = sum(1 for g in non_override_games if game_outcomes_dict[g] == "LOSS")
    non_override_draws = sum(1 for g in non_override_games if game_outcomes_dict[g] == "DRAW")
    non_override_wr = (non_override_wins / max(1, len(non_override_games))) * 100.0 if non_override_games else 0.0

    action_transitions = Counter((r["control_desc"], r["candidate_desc"]) for r in override_records)

    csv_file = HERE / "h_xerosic_decision_audit.csv"
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
            writer.writerow(r)

    print("\n" + "=" * 80)
    print("H_XEROSIC EMPIRICAL BENCHMARK RESULTS (200 GAMES HEAD-TO-HEAD)")
    print("=" * 80)
    print(f"Match Record:                  {wins}W - {losses}L - {draws}D")
    print(f"Candidate Win Rate vs Control: {win_rate:.2f}% (95% Wilson CI: [{ci_lower:.2f}%, {ci_upper:.2f}%])")
    print(f"Win Rate as Player 0 (1st):    {(p0_wins / p0_games)*100:.1f}% ({p0_wins}/{p0_games})")
    print(f"Win Rate as Player 1 (2nd):    {(p1_wins / p1_games)*100:.1f}% ({p1_wins}/{p1_games})")
    print(f"Average Game Length:           {total_steps / total_games:.2f} steps")
    print(f"Contract / Runtime Errors:     {total_contract_errors}")
    print(f"Fallback Activations:          {total_fallbacks}")
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


if __name__ == "__main__":
    run_parallel_benchmark(200, workers=6)
