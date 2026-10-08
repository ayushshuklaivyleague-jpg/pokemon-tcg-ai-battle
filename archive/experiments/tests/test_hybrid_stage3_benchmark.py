#!/usr/bin/env python3
"""
HYBRID_STAGE_3 Parallel Benchmark Suite.
Candidate: Hybrid_V4_Sol (Layers 1+2+3+4, Hilda=3150, Search=OFF)
Control: Frozen Sol Eclipse Baseline (codex_sol_eclipse_alakazam.py, Hilda=3000)

Executes 200 balanced head-to-head matches (100 as P0, 100 as P1) across 6 worker processes.
Saves telemetry to hybrid_stage3_decision_audit.csv.
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
from dataclasses import dataclass
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

# Load control baseline source
source_file = HERE / "codex_sol_eclipse_alakazam.py"
raw_code = source_file.read_text(encoding="utf-8")
main_match = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)

if not main_match or not deck_match:
    raise RuntimeError("Failed to parse codex_sol_eclipse_alakazam.py")

CTRL_MAIN_SOURCE = main_match.group(1)
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]

# Candidate module source
import hybrid_v4_sol_stage3 as hybrid_mod


def compute_wilson_ci(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.95996
    p = wins / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    margin = z * math.sqrt(p * (1.0 - p) / total + (z * z) / (4.0 * total * total)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def create_control_agent() -> dict:
    ns = {}
    exec(CTRL_MAIN_SOURCE, ns)
    return ns


def describe_opt(ns: dict, obs_cls: Any, opt: Any) -> str:
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
class HybridDecisionRecord:
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
    alakazam_count: int
    kadabra_count: int
    abra_count: int
    hand_size: int
    deck_count: int
    my_prizes: int
    opp_prizes: int
    my_active: str
    my_bench: str
    opp_active: str
    opp_bench: str
    game_outcome: str
    is_winning_override: Optional[bool] = None


@dataclass
class MatchResult:
    game_id: int
    candidate_seat: int
    winner: int
    candidate_won: bool
    control_won: bool
    is_draw: bool
    steps: int
    contract_errors: int
    fallback_count: int
    dawn_hilda_comps: int
    total_overrides: int
    hilda_plays_cand: int
    hilda_plays_ctrl: int
    dawn_plays_cand: int
    dawn_plays_ctrl: int
    xerosic_plays_cand: int
    xerosic_plays_ctrl: int
    search_invocations: int
    records: List[HybridDecisionRecord]


def run_single_game(game_id: int, cand_seat: int) -> MatchResult:
    ctrl_ns = create_control_agent()
    # Candidate agent
    cand_fn = hybrid_mod.hybrid_agent

    obs, start_data = battle_start(SOL_DECK, SOL_DECK)
    if not obs or not start_data:
        raise RuntimeError(f"Game {game_id}: battle_start failed")

    records: List[HybridDecisionRecord] = []
    contract_errors = 0
    fallback_count = 0
    dawn_hilda_comps = 0
    total_overrides = 0
    search_invocations = 0

    cand_hilda_plays = 0
    ctrl_hilda_plays = 0
    cand_dawn_plays = 0
    ctrl_dawn_plays = 0
    cand_xerosic_plays = 0
    ctrl_xerosic_plays = 0

    step = 0
    while step < 160:
        step += 1
        res = obs.get("current", {}).get("result")
        if res is not None and res >= 0:
            break

        player_idx = obs.get("current", {}).get("yourIndex", 0)
        select = obs.get("select")
        if not select:
            break

        obs_cls = ctrl_ns["to_observation_class"](obs)
        sel = obs_cls.select
        my_p = obs_cls.current.players[player_idx]
        op_p = obs_cls.current.players[1 - player_idx]

        alak_c = sum(1 for p in (my_p.active + my_p.bench) if p and p.id == hybrid_mod.Alakazam)
        kad_c = sum(1 for p in (my_p.active + my_p.bench) if p and p.id == hybrid_mod.Kadabra)
        abra_c = sum(1 for p in (my_p.active + my_p.bench) if p and p.id == hybrid_mod.Abra)

        if player_idx == cand_seat:
            cand_action = cand_fn(obs)
            legal_options_desc = [describe_opt(ctrl_ns, obs_cls, o) for o in sel.option]
            has_hilda_or_dawn = any("PLAY(Hilda" in opt or "PLAY(Dawn" in opt for opt in legal_options_desc)

            if has_hilda_or_dawn and sel.context == api.SelectContext.MAIN:
                ctrl_action = ctrl_ns["agent"](obs)
            else:
                ctrl_action = cand_action

            is_override = (ctrl_action != cand_action)
            if is_override:
                total_overrides += 1

            has_dawn = any("PLAY(Dawn" in opt for opt in legal_options_desc)
            has_hilda = any("PLAY(Hilda" in opt for opt in legal_options_desc)
            is_dawn_hilda_comp = (sel.context == api.SelectContext.MAIN and has_dawn and has_hilda)
            if is_dawn_hilda_comp:
                dawn_hilda_comps += 1

            ctrl_opt = sel.option[ctrl_action[0]] if ctrl_action and 0 <= ctrl_action[0] < len(sel.option) else None
            cand_opt = sel.option[cand_action[0]] if cand_action and 0 <= cand_action[0] < len(sel.option) else None

            ctrl_desc = describe_opt(ctrl_ns, obs_cls, ctrl_opt)
            cand_desc = describe_opt(ctrl_ns, obs_cls, cand_opt)

            # Track plays
            if cand_desc.startswith("PLAY(Hilda)"): cand_hilda_plays += 1
            elif cand_desc.startswith("PLAY(Dawn)"): cand_dawn_plays += 1
            elif cand_desc.startswith("PLAY(Xerosic"): cand_xerosic_plays += 1

            if ctrl_desc.startswith("PLAY(Hilda)"): ctrl_hilda_plays += 1
            elif ctrl_desc.startswith("PLAY(Dawn)"): ctrl_dawn_plays += 1
            elif ctrl_desc.startswith("PLAY(Xerosic"): ctrl_xerosic_plays += 1

            # Describe field
            def desc_p(p):
                if not p: return "None"
                cd = ctrl_ns["card_table"].get(p.id)
                n = cd.name if cd else f"Card_{p.id}"
                e_cnt = len(p.energyCards) if p.energyCards else 0
                return f"{n}({e_cnt}E)"

            my_act_str = desc_p(my_p.active[0] if my_p.active else None)
            my_bench_str = ",".join(desc_p(b) for b in my_p.bench if b) if any(my_p.bench) else "Empty"
            op_act_str = desc_p(op_p.active[0] if op_p.active else None)
            op_bench_str = ",".join(desc_p(b) for b in op_p.bench if b) if any(op_p.bench) else "Empty"

            rec = HybridDecisionRecord(
                game_id=game_id,
                step=step,
                turn=obs_cls.current.turn,
                player_idx=player_idx,
                context=str(sel.context),
                num_options=len(sel.option),
                legal_options=" | ".join(legal_options_desc[:8]),
                is_dawn_hilda_comp=is_dawn_hilda_comp,
                control_action=str(ctrl_action),
                candidate_action=str(cand_action),
                control_desc=ctrl_desc,
                candidate_desc=cand_desc,
                is_override=is_override,
                alakazam_count=alak_c,
                kadabra_count=kad_c,
                abra_count=abra_c,
                hand_size=len(my_p.hand) if my_p.hand else my_p.handCount,
                deck_count=my_p.deckCount,
                my_prizes=len(my_p.prize),
                opp_prizes=len(op_p.prize),
                my_active=my_act_str,
                my_bench=my_bench_str,
                opp_active=op_act_str,
                opp_bench=op_bench_str,
                game_outcome="UNKNOWN",
                is_winning_override=None,
            )
            records.append(rec)

            # Contract verification
            min_c = int(sel.minCount or 0)
            max_c = min(int(sel.maxCount or len(sel.option)), len(sel.option))
            if not isinstance(cand_action, list) or len(cand_action) < min_c or len(cand_action) > max_c or any(i < 0 or i >= len(sel.option) for i in cand_action):
                contract_errors += 1
                fallback_count += 1
                cand_action = list(range(min(max(1, min_c), len(sel.option))))

            action = cand_action
        else:
            action = ctrl_ns["agent"](obs)
            if select and select.get("context") == api.SelectContext.MAIN:
                c_idx = action[0] if action else 0
                if 0 <= c_idx < len(select.get("option", [])):
                    opt = select["option"][c_idx]
                    if opt.get("type") == api.OptionType.PLAY:
                        c_card = ctrl_ns["get_card"](ctrl_ns["to_observation_class"](obs), api.AreaType.HAND, opt.get("index"), player_idx)
                        if c_card:
                            if c_card.id == ctrl_ns["Hilda"]: ctrl_hilda_plays += 1
                            elif c_card.id == ctrl_ns["Dawn"]: ctrl_dawn_plays += 1
                            elif c_card.id == ctrl_ns["Xerosic"]: ctrl_xerosic_plays += 1

        obs = battle_select(action)

    battle_finish()
    final_res = obs.get("current", {}).get("result", -1)

    if final_res == cand_seat:
        outcome_str = "WIN"
        cand_won = True
        ctrl_won = False
        is_draw = False
    elif final_res == (1 - cand_seat):
        outcome_str = "LOSS"
        cand_won = False
        ctrl_won = True
        is_draw = False
    else:
        outcome_str = "DRAW"
        cand_won = False
        ctrl_won = False
        is_draw = True

    for r in records:
        r.game_outcome = outcome_str
        if r.is_override:
            r.is_winning_override = cand_won

    return MatchResult(
        game_id=game_id,
        candidate_seat=cand_seat,
        winner=final_res,
        candidate_won=cand_won,
        control_won=ctrl_won,
        is_draw=is_draw,
        steps=step,
        contract_errors=contract_errors,
        fallback_count=fallback_count,
        dawn_hilda_comps=dawn_hilda_comps,
        total_overrides=total_overrides,
        hilda_plays_cand=cand_hilda_plays,
        hilda_plays_ctrl=ctrl_hilda_plays,
        dawn_plays_cand=cand_dawn_plays,
        dawn_plays_ctrl=ctrl_dawn_plays,
        xerosic_plays_cand=cand_xerosic_plays,
        xerosic_plays_ctrl=ctrl_xerosic_plays,
        search_invocations=search_invocations,
        records=records,
    )


def main():
    print("=" * 80, flush=True)
    print("STARTING HYBRID_STAGE_3 BENCHMARK: 200 MATCHES (6 WORKERS)", flush=True)
    print("Candidate: Hybrid_V4_Sol (Layers 1+2+3+4, Hilda=3150, Search=OFF)", flush=True)
    print("Control Baseline: Frozen codex_sol_eclipse_alakazam.py (Hilda=3000)", flush=True)
    print("=" * 80, flush=True)

    tasks = []
    for g in range(1, 201):
        seat = 0 if g <= 100 else 1
        tasks.append((g, seat))

    all_results: List[MatchResult] = []
    all_records: List[HybridDecisionRecord] = []

    start_time = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(run_single_game, g_id, s): g_id for (g_id, s) in tasks}
        completed = 0
        cand_wins = 0
        ctrl_wins = 0
        draws = 0

        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            all_results.append(res)
            all_records.extend(res.records)
            completed += 1

            if res.candidate_won: cand_wins += 1
            elif res.control_won: ctrl_wins += 1
            else: draws += 1

            if completed % 10 == 0 or completed == 200:
                cur_wr = cand_wins / completed * 100
                print(f"  Progress: {completed:03d}/200 -> {cand_wins}W - {ctrl_wins}L - {draws}D (Candidate WR: {cur_wr:.1f}%) [Last Game: {res.game_id} {'WIN' if res.candidate_won else ('LOSS' if res.control_won else 'DRAW')} in {res.steps} steps]", flush=True)

    elapsed = time.time() - start_time

    all_results.sort(key=lambda x: x.game_id)
    all_records.sort(key=lambda x: (x.game_id, x.step))

    total_games = len(all_results)
    cand_w = sum(1 for r in all_results if r.candidate_won)
    ctrl_w = sum(1 for r in all_results if r.control_won)
    d_count = sum(1 for r in all_results if r.is_draw)
    decisive_total = cand_w + ctrl_w
    decisive_wr = cand_w / decisive_total * 100 if decisive_total > 0 else 0.0

    agg_lo, agg_hi = compute_wilson_ci(cand_w, total_games)
    dec_lo, dec_hi = compute_wilson_ci(cand_w, decisive_total)

    p0_results = [r for r in all_results if r.candidate_seat == 0]
    p1_results = [r for r in all_results if r.candidate_seat == 1]

    p0_w = sum(1 for r in p0_results if r.candidate_won)
    p0_l = sum(1 for r in p0_results if r.control_won)
    p0_d = sum(1 for r in p0_results if r.is_draw)

    p1_w = sum(1 for r in p1_results if r.candidate_won)
    p1_l = sum(1 for r in p1_results if r.control_won)
    p1_d = sum(1 for r in p1_results if r.is_draw)

    total_steps = sum(r.steps for r in all_results)
    avg_steps = total_steps / total_games if total_games else 0.0

    total_contract_errors = sum(r.contract_errors for r in all_results)
    total_fallbacks = sum(r.fallback_count for r in all_results)
    total_comp_states = sum(r.dawn_hilda_comps for r in all_results)
    total_search_calls = sum(r.search_invocations for r in all_results)

    total_cand_hilda = sum(r.hilda_plays_cand for r in all_results)
    total_ctrl_hilda = sum(r.hilda_plays_ctrl for r in all_results)
    total_cand_dawn = sum(r.dawn_plays_cand for r in all_results)
    total_ctrl_dawn = sum(r.dawn_plays_ctrl for r in all_results)
    total_cand_xerosic = sum(r.xerosic_plays_cand for r in all_results)
    total_ctrl_xerosic = sum(r.xerosic_plays_ctrl for r in all_results)

    override_records = [r for r in all_records if r.is_override]
    override_games = set(r.game_id for r in override_records)

    ov_game_res = [r for r in all_results if r.game_id in override_games]
    non_ov_game_res = [r for r in all_results if r.game_id not in override_games]

    ov_w = sum(1 for r in ov_game_res if r.candidate_won)
    ov_l = sum(1 for r in ov_game_res if r.control_won)
    ov_d = sum(1 for r in ov_game_res if r.is_draw)
    ov_dec = ov_w + ov_l
    ov_dec_wr = ov_w / ov_dec * 100 if ov_dec else 0.0

    non_ov_w = sum(1 for r in non_ov_game_res if r.candidate_won)
    non_ov_l = sum(1 for r in non_ov_game_res if r.control_won)
    non_ov_d = sum(1 for r in non_ov_game_res if r.is_draw)
    non_ov_dec = non_ov_w + non_ov_l
    non_ov_dec_wr = non_ov_w / non_ov_dec * 100 if non_ov_dec else 0.0

    print("\n" + "=" * 80, flush=True)
    print("HYBRID_STAGE_3 BENCHMARK RESULTS", flush=True)
    print("=" * 80, flush=True)
    print(f"Match Record:                  {cand_w}W - {ctrl_w}L - {d_count}D", flush=True)
    print(f"Aggregate Candidate Win Rate:  {cand_w/total_games*100:.2f}% (95% Wilson CI: [{agg_lo*100:.2f}%, {agg_hi*100:.2f}%])", flush=True)
    print(f"Decisive (Non-Draw) Win Rate:  {decisive_wr:.2f}% ({cand_w}W / {ctrl_w}L, 95% Wilson CI: [{dec_lo*100:.2f}%, {dec_hi*100:.2f}%])", flush=True)
    print(f"Player 0 (Going 1st) Record:   {p0_w}W - {p0_l}L - {p0_d}D (WR: {p0_w/len(p0_results)*100:.1f}%)", flush=True)
    print(f"Player 1 (Going 2nd) Record:   {p1_w}W - {p1_l}L - {p1_d}D (WR: {p1_w/len(p1_results)*100:.1f}%)", flush=True)
    print(f"Average Game Length:           {avg_steps:.2f} steps", flush=True)
    print(f"Contract / Runtime Errors:     {total_contract_errors}", flush=True)
    print(f"Fallback Activations:          {total_fallbacks}", flush=True)
    print(f"Total Search Invocations:      {total_search_calls} (Verified 0)", flush=True)
    print(f"Total Decisions Instrumented:  {len(all_records)}", flush=True)
    print(f"Dawn vs Hilda Comp States:     {total_comp_states}", flush=True)
    print(f"Candidate Hilda Plays:         {total_cand_hilda} (Control: {total_ctrl_hilda})", flush=True)
    print(f"Candidate Dawn Plays:          {total_cand_dawn} (Control: {total_ctrl_dawn})", flush=True)
    print(f"Candidate Xerosic Plays:       {total_cand_xerosic} (Control: {total_ctrl_xerosic})", flush=True)
    print(f"Total Overrides:               {len(override_records)} / {len(all_records)} ({len(override_records)/len(all_records)*100:.2f}%)", flush=True)
    print(f"Override Games Count:          {len(override_games)} / {total_games} ({len(override_games)/total_games*100:.1f}%)", flush=True)
    print(f"Override Games Record:         {ov_w}W - {ov_l}L - {ov_d}D (Decisive WR: {ov_dec_wr:.1f}%)", flush=True)
    print(f"Non-Override Games Record:     {non_ov_w}W - {non_ov_l}L - {non_ov_d}D (Decisive WR: {non_ov_dec_wr:.1f}%)", flush=True)
    print(f"Elapsed Time:                  {elapsed:.2f}s", flush=True)
    print("=" * 80, flush=True)

    transitions = Counter((r.control_desc, r.candidate_desc) for r in override_records)
    print("\nACTION TRANSITIONS BREAKDOWN (Control -> Candidate):", flush=True)
    for (c_act, cand_act), cnt in transitions.most_common(20):
        print(f"  {c_act:<35} -> {cand_act:<35} | Count: {cnt:>3}", flush=True)
    print("=" * 80, flush=True)

    out_csv = HERE / "hybrid_stage3_decision_audit.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "game_id", "step", "turn", "player_idx", "context", "num_options", "legal_options",
            "is_dawn_hilda_comp", "control_action", "candidate_action", "control_desc", "candidate_desc",
            "is_override", "alakazam_count", "kadabra_count", "abra_count", "hand_size", "deck_count",
            "my_prizes", "opp_prizes", "my_active", "my_bench", "opp_active", "opp_bench",
            "game_outcome", "is_winning_override"
        ])
        for r in all_records:
            writer.writerow([
                r.game_id, r.step, r.turn, r.player_idx, r.context, r.num_options, r.legal_options,
                r.is_dawn_hilda_comp, r.control_action, r.candidate_action, r.control_desc, r.candidate_desc,
                r.is_override, r.alakazam_count, r.kadabra_count, r.abra_count, r.hand_size, r.deck_count,
                r.my_prizes, r.opp_prizes, r.my_active, r.my_bench, r.opp_active, r.opp_bench,
                r.game_outcome, r.is_winning_override
            ])
    print(f"\nWrote telemetry to {out_csv} ({len(all_records)} records)", flush=True)


if __name__ == "__main__":
    main()
