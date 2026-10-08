"""
Optimized Parallel H_HILDA Benchmark Suite.
Runs 200 balanced head-to-head matches between Candidate (W['hilda'] = 3150)
and Control (W['hilda'] = 3000) across worker processes.

Captures all required metrics:
- total decisions
- Dawn-vs-Hilda competition states
- Hilda selections & Dawn selections
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


def create_agent_instance(hilda_weight: int):
    ns = {"__file__": str(source_file)}
    exec(main_source, ns)
    ns["WEIGHTS"]["hilda"] = hilda_weight
    ns["W"]["hilda"] = hilda_weight
    return ns


def describe_opt(ns, obs_cls, opt) -> str:
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
        c = ns["get_card"](obs_cls, opt.area, opt.index, opt.playerIndex)
        return f"CARD({cname(c.id) if c else 'None'} in {opt.area})"
    elif t == api.OptionType.PLAY:
        c = ns["get_card"](obs_cls, api.AreaType.HAND, opt.index, obs_cls.current.yourIndex)
        return f"PLAY({cname(c.id) if c else 'None'})"
    elif t == api.OptionType.ATTACH:
        c = ns["get_card"](obs_cls, api.AreaType.HAND, opt.index, obs_cls.current.yourIndex)
        tgt = ns["get_card"](obs_cls, opt.inPlayArea, opt.inPlayIndex, obs_cls.current.yourIndex)
        return f"ATTACH({cname(c.id) if c else 'None'} -> {cname(tgt.id) if tgt else 'None'}@{opt.inPlayArea})"
    elif t == api.OptionType.EVOLVE:
        c = ns["get_card"](obs_cls, api.AreaType.HAND, opt.index, obs_cls.current.yourIndex)
        tgt = ns["get_card"](obs_cls, opt.inPlayArea, opt.inPlayIndex, obs_cls.current.yourIndex)
        return f"EVOLVE({cname(c.id) if c else 'None'} on {cname(tgt.id) if tgt else 'None'})"
    elif t == api.OptionType.ABILITY:
        c = ns["get_card"](obs_cls, opt.area, opt.index, obs_cls.current.yourIndex)
        return f"ABILITY({cname(c.id) if c else 'None'})"
    elif t == api.OptionType.RETREAT:
        return "RETREAT"
    elif t == api.OptionType.ATTACK:
        atk_names = {1070: "Teleportation", 1071: "Super Psy Bolt", 1072: "Powerful Hand"}
        return f"ATTACK({atk_names.get(opt.attackId, opt.attackId)})"
    return f"{opt.type}"


@dataclass
class HHildaDecisionRecord:
    game_id: int
    step: int
    turn: int
    player_idx: int
    context: str
    num_options: int
    legal_options: str
    is_dawn_hilda_comp: bool
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
    cand_ns = create_agent_instance(3150)
    ctrl_ns = create_agent_instance(3000)

    records: List[HHildaDecisionRecord] = []
    contract_errors = 0
    fallback_count = 0

    obs, start_data = battle_start(SOL_DECK, SOL_DECK)
    if not obs or not start_data:
        raise RuntimeError(f"Game {game_id}: Failed to start battle")

    step = 0
    max_steps = 160
    cand_idx = 0 if cand_is_p0 else 1

    cand_hilda_plays = 0
    ctrl_hilda_plays = 0
    cand_dawn_plays = 0
    ctrl_dawn_plays = 0

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

            # Shadow Control Action: evaluate when Hilda or Dawn is in hand in MAIN context
            legal_options_desc = [describe_opt(cand_ns, obs_cls, o) for o in sel.option]
            has_hilda_or_dawn = any("PLAY(Hilda" in opt or "PLAY(Dawn" in opt for opt in legal_options_desc)

            if has_hilda_or_dawn and sel.context == api.SelectContext.MAIN:
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

            has_dawn = any("PLAY(Dawn" in opt for opt in legal_options_desc)
            has_hilda = any("PLAY(Hilda" in opt for opt in legal_options_desc)
            is_dh_comp = (sel.context == api.SelectContext.MAIN and has_dawn and has_hilda)

            if "PLAY(Hilda" in cand_desc: cand_hilda_plays += 1
            if "PLAY(Dawn" in cand_desc: cand_dawn_plays += 1

            my_act = my_p.active[0] if my_p.active else None
            op_act = op_p.active[0] if op_p.active else None
            cname = lambda cid: cand_ns["card_table"].get(cid).name if cand_ns["card_table"].get(cid) else f"Card_{cid}"

            my_act_str = f"{cname(my_act.id)} HP:{my_act.hp} En:{len(my_act.energies)}" if my_act else "None"
            op_act_str = f"{cname(op_act.id)} HP:{op_act.hp} En:{len(op_act.energies)}" if op_act else "None"
            my_bench_str = "/".join([f"{cname(b.id)} HP:{b.hp} En:{len(b.energies)}" for b in my_p.bench if b]) or "Empty"
            op_bench_str = "/".join([f"{cname(b.id)} HP:{b.hp} En:{len(b.energies)}" for b in op_p.bench if b]) or "Empty"

            rec = HHildaDecisionRecord(
                game_id=game_id,
                step=step,
                turn=state.turn,
                player_idx=player_idx,
                context=api.SelectContext(sel.context).name if hasattr(sel.context, "name") else str(sel.context),
                num_options=len(sel.option),
                legal_options=" | ".join(legal_options_desc),
                is_dawn_hilda_comp=is_dh_comp,
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
            # Track control supporter plays
            if select and select.get("context") == api.SelectContext.MAIN:
                c_idx = action[0] if action else 0
                if 0 <= c_idx < len(select.get("option", [])):
                    opt = select["option"][c_idx]
                    if opt.get("type") == api.OptionType.PLAY:
                        # Inspect card
                        c_card = ctrl_ns["get_card"](ctrl_ns["to_observation_class"](obs), api.AreaType.HAND, opt.get("index"), player_idx)
                        if c_card:
                            if c_card.id == ctrl_ns["Hilda"]: ctrl_hilda_plays += 1
                            elif c_card.id == ctrl_ns["Dawn"]: ctrl_dawn_plays += 1

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
        "step_count": step,
        "contract_errors": contract_errors,
        "fallback_count": fallback_count,
        "cand_hilda_plays": cand_hilda_plays,
        "ctrl_hilda_plays": ctrl_hilda_plays,
        "cand_dawn_plays": cand_dawn_plays,
        "ctrl_dawn_plays": ctrl_dawn_plays,
        "records": records
    }


def main():
    total_matches = 200
    p0_count = 100
    p1_count = 100
    max_workers = 6

    print("=" * 80, flush=True)
    print("STARTING PARALLEL H_HILDA BENCHMARK: 200 MATCHES (6 WORKERS)", flush=True)
    print("Candidate (W['hilda'] = 3150) vs Control Baseline (W['hilda'] = 3000)", flush=True)
    print("=" * 80, flush=True)

    tasks = []
    for i in range(p0_count):
        tasks.append((i + 1, True))
    for i in range(p1_count):
        tasks.append((p0_count + i + 1, False))

    match_results = []
    all_decisions: List[HHildaDecisionRecord] = []

    t0 = time.time()

    wins = 0
    losses = 0
    draws = 0
    p0_wins = 0
    p1_wins = 0

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_match = {
            executor.submit(run_single_benchmark_game, mid, is_p0): mid
            for mid, is_p0 in tasks
        }

        for future in concurrent.futures.as_completed(future_to_match):
            res = future.result()
            match_results.append(res)
            all_decisions.extend(res["records"])

            out = res["outcome"]
            if out == "WIN":
                wins += 1
                if res["cand_is_p0"]:
                    p0_wins += 1
                else:
                    p1_wins += 1
            elif out == "LOSS":
                losses += 1
            else:
                draws += 1

            completed = len(match_results)
            if completed % 10 == 0 or completed == total_matches:
                current_wr = (wins / completed) * 100.0
                print(f"  Progress: {completed:03d}/{total_matches} -> {wins}W - {losses}L - {draws}D (Current Win Rate: {current_wr:.1f}%) [Last Game: {res['game_id']} {out} in {res['step_count']} steps]", flush=True)

    total_time = time.time() - t0

    # Wilson Confidence Interval
    ci_low, ci_high = compute_wilson_ci(wins, total_matches)

    # Categorize games
    override_games = [m for m in match_results if any(r.is_override for r in m["records"])]
    non_override_games = [m for m in match_results if not any(r.is_override for r in m["records"])]

    ov_wins = sum(1 for m in override_games if m["outcome"] == "WIN")
    ov_losses = sum(1 for m in override_games if m["outcome"] == "LOSS")
    ov_draws = sum(1 for m in override_games if m["outcome"] == "DRAW")

    non_ov_wins = sum(1 for m in non_override_games if m["outcome"] == "WIN")
    non_ov_losses = sum(1 for m in non_override_games if m["outcome"] == "LOSS")
    non_ov_draws = sum(1 for m in non_override_games if m["outcome"] == "DRAW")

    total_decisions_count = len(all_decisions)
    total_dh_comp = sum(1 for d in all_decisions if d.is_dawn_hilda_comp)
    total_cand_hilda = sum(m["cand_hilda_plays"] for m in match_results)
    total_ctrl_hilda = sum(m["ctrl_hilda_plays"] for m in match_results)
    total_cand_dawn = sum(m["cand_dawn_plays"] for m in match_results)
    total_ctrl_dawn = sum(m["ctrl_dawn_plays"] for m in match_results)
    total_overrides_count = sum(1 for d in all_decisions if d.is_override)

    # Transition counter
    transitions = Counter()
    for d in all_decisions:
        if d.is_override:
            transitions[(d.control_desc, d.candidate_desc)] += 1

    print("\n" + "=" * 80, flush=True)
    print("H_HILDA EMPIRICAL BENCHMARK RESULTS (200 GAMES HEAD-TO-HEAD)", flush=True)
    print("=" * 80, flush=True)
    print(f"Match Record:                  {wins}W - {losses}L - {draws}D", flush=True)
    print(f"Candidate Win Rate vs Control: {(wins/total_matches)*100:.2f}% (95% Wilson CI: [{ci_low:.2f}%, {ci_high:.2f}%])", flush=True)
    decisive_total = wins + losses
    decisive_wr = (wins / max(1, decisive_total)) * 100.0
    print(f"Decisive (Non-Draw) Win Rate:  {decisive_wr:.2f}% ({wins}W / {losses}L)", flush=True)
    print(f"Win Rate as Player 0 (1st):    {(p0_wins/p0_count)*100:.1f}% ({p0_wins}/{p0_count})", flush=True)
    print(f"Win Rate as Player 1 (2nd):    {(p1_wins/p1_count)*100:.1f}% ({p1_wins}/{p1_count})", flush=True)
    print(f"Average Game Length:           {sum(m['step_count'] for m in match_results)/total_matches:.2f} steps", flush=True)
    print(f"Contract / Runtime Errors:     {sum(m['contract_errors'] for m in match_results)}", flush=True)
    print(f"Fallback Activations:          {sum(m['fallback_count'] for m in match_results)}", flush=True)
    print(f"Total Decisions Instrumented:  {total_decisions_count}", flush=True)
    print(f"Dawn vs Hilda Comp States:     {total_dh_comp} ({(total_dh_comp/max(1, total_decisions_count))*100:.2f}%)", flush=True)
    print(f"Control Hilda Plays:           {total_ctrl_hilda}", flush=True)
    print(f"Candidate Hilda Plays:         {total_cand_hilda} (+{total_cand_hilda - total_ctrl_hilda})", flush=True)
    print(f"Control Dawn Plays:            {total_ctrl_dawn}", flush=True)
    print(f"Candidate Dawn Plays:          {total_cand_dawn} ({total_cand_dawn - total_ctrl_dawn})", flush=True)
    print(f"Total Decisions Overridden:    {total_overrides_count} / {total_decisions_count} ({(total_overrides_count/max(1, total_decisions_count))*100:.2f}%)", flush=True)
    print(f"Override Games Count:          {len(override_games)} / {total_matches} ({(len(override_games)/total_matches)*100:.1f}%)", flush=True)
    print(f"Override Games Record:         {ov_wins}W - {ov_losses}L - {ov_draws}D (Decisive WR: {(ov_wins/max(1, ov_wins+ov_losses))*100:.1f}%)", flush=True)
    print(f"Non-Override Games Record:     {non_ov_wins}W - {non_ov_losses}L - {non_ov_draws}D (Decisive WR: {(non_ov_wins/max(1, non_ov_wins+non_ov_losses))*100:.1f}%)", flush=True)
    print(f"Elapsed Benchmark Time:        {total_time:.2f}s", flush=True)
    print("=" * 80, flush=True)

    print("\nACTION TRANSITIONS BREAKDOWN (Control -> Candidate):", flush=True)
    for (ctrl_act, cand_act), cnt in transitions.most_common(20):
        print(f"  {ctrl_act:<35} -> {cand_act:<35} | Count: {cnt:>3}", flush=True)
    print("=" * 80, flush=True)

    # Save CSV
    csv_file = HERE / "h_hilda_decision_audit.csv"
    if all_decisions:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(all_decisions[0]).keys()))
            writer.writeheader()
            for d in all_decisions:
                writer.writerow(asdict(d))
        print(f"\nWrote full decision telemetry to {csv_file}", flush=True)


if __name__ == "__main__":
    main()
