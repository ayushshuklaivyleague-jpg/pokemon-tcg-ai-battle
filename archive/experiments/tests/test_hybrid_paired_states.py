#!/usr/bin/env python3
"""
Paired / Matched-State Effect Analysis for HYBRID_STAGE_4 vs Frozen Sol Eclipse Control.

Methodology:
1. Evaluates simulator seed capability: Documents that cg.dll exports 13 functions without an external
   seed setter for BattleStart, so paired analysis is conducted via Trajectory-Level Paired Divergence
   Tracking & State-Conditioned Counterfactual Evaluation.
2. Runs 200 balanced matches (100 as P0, 100 as P1).
3. For each match, captures:
   - State/Game ID and starting seat
   - Policy divergence status (Divergent vs Non-Divergent)
   - First divergence step and turn
   - First divergence action pair (Control Action vs Candidate Action)
   - Board state at first divergence (Alakazam, Kadabra, Abra counts, Hand Size, Prizes, Active)
   - Search invocation status on both sides
   - Search score/values for candidate actions
   - Final match outcome (Candidate Win, Control Win, Draw)
   - Total game length
4. Outputs:
   - hybrid_paired_state_results.csv (200 paired match records)
   - Full statistical aggregates and conditional metrics
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
import pandas as pd
import numpy as np

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
CTRL_MAIN_SOURCE = main_match.group(1)
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]

# Candidate source
CAND_MAIN_SOURCE = CTRL_MAIN_SOURCE.replace('"hilda": 3000,', '"hilda": 3150,')

def compute_wilson_ci(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0: return 0.0, 0.0
    z = 1.95996
    p = wins / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    margin = z * math.sqrt(p * (1.0 - p) / total + (z * z) / (4.0 * total * total)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)

def describe_opt(ns: dict, obs_cls: Any, opt: Any) -> str:
    if opt is None: return "None"
    card_table = ns["card_table"]
    def cname(cid: int) -> str:
        c = card_table.get(cid)
        return c.name if c else f"Card_{cid}"

    t = opt.type
    if t == api.OptionType.NUMBER: return f"NUMBER({opt.number})"
    elif t == api.OptionType.YES: return "YES"
    elif t == api.OptionType.NO: return "NO"
    elif t == api.OptionType.END: return "END_TURN"
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
    elif t == api.OptionType.RETREAT: return "RETREAT"
    elif t == api.OptionType.ATTACK:
        atk_names = {1070: "Teleportation", 1071: "Super Psy Bolt", 1072: "Powerful Hand"}
        return f"ATTACK({atk_names.get(opt.attackId, opt.attackId)})"
    return f"{opt.type}"

@dataclass
class PairedMatchResult:
    game_id: int
    starting_seat: int
    has_divergence: bool
    first_div_step: Optional[int]
    first_div_turn: Optional[int]
    first_div_ctrl_action: str
    first_div_cand_action: str
    total_divergences: int
    alakazam_at_first_div: int
    kadabra_at_first_div: int
    abra_at_first_div: int
    hand_size_at_first_div: int
    my_prizes_at_first_div: int
    opp_prizes_at_first_div: int
    my_active_at_first_div: str
    cand_search_invoked_first_div: bool
    ctrl_search_invoked_first_div: bool
    game_outcome: str
    cand_won: bool
    ctrl_won: bool
    is_draw: bool
    game_length: int

def run_paired_match(game_id: int, cand_seat: int) -> PairedMatchResult:
    ctrl_ns = {}
    exec(CTRL_MAIN_SOURCE, ctrl_ns)
    cand_ns = {}
    exec(CAND_MAIN_SOURCE, cand_ns)

    # V4 selection contract helper
    def v4_legal_selection(obs, selected: List[int]) -> List[int]:
        sel = obs.select
        if not sel or not sel.option: return []
        opt_count = len(sel.option)
        min_c = max(0, int(sel.minCount or 0))
        max_c = max(min_c, min(opt_count, int(sel.maxCount or opt_count)))
        valid = [i for i in selected if isinstance(i, int) and 0 <= i < opt_count]
        if len(valid) < min_c:
            for i in range(opt_count):
                if i not in valid: valid.append(i)
                if len(valid) >= min_c: break
        return valid[:max_c]

    obs, start_data = battle_start(SOL_DECK, SOL_DECK)
    if not obs or not start_data:
        raise RuntimeError(f"Game {game_id}: battle_start failed")

    has_divergence = False
    first_div_step = None
    first_div_turn = None
    first_div_ctrl_action = "None"
    first_div_cand_action = "None"
    total_divergences = 0
    alak_at_div = 0
    kad_at_div = 0
    abra_at_div = 0
    hand_at_div = 0
    my_prizes_at_div = 0
    opp_prizes_at_div = 0
    my_active_at_div = "None"
    cand_search_div = False
    ctrl_search_div = False

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

        obs_cls = cand_ns["to_observation_class"](obs)
        sel = obs_cls.select
        my_p = obs_cls.current.players[player_idx]
        op_p = obs_cls.current.players[1 - player_idx]

        if player_idx == cand_seat:
            cand_ns["_stats"]["calls"] = 0
            raw_cand = cand_ns["agent"](obs)
            cand_action = v4_legal_selection(obs_cls, raw_cand)
            cand_searched = (cand_ns["_stats"]["calls"] > 0)

            # Evaluate control on exact same state
            ctrl_ns["_stats"]["calls"] = 0
            ctrl_action = ctrl_ns["agent"](obs)
            ctrl_searched = (ctrl_ns["_stats"]["calls"] > 0)

            if ctrl_action != cand_action:
                total_divergences += 1
                if not has_divergence:
                    has_divergence = True
                    first_div_step = step
                    first_div_turn = obs_cls.current.turn

                    ctrl_opt = sel.option[ctrl_action[0]] if ctrl_action and 0 <= ctrl_action[0] < len(sel.option) else None
                    cand_opt = sel.option[cand_action[0]] if cand_action and 0 <= cand_action[0] < len(sel.option) else None
                    first_div_ctrl_action = describe_opt(ctrl_ns, obs_cls, ctrl_opt)
                    first_div_cand_action = describe_opt(cand_ns, obs_cls, cand_opt)

                    alak_at_div = sum(1 for p in (my_p.active + my_p.bench) if p and p.id == cand_ns["Alakazam"])
                    kad_at_div = sum(1 for p in (my_p.active + my_p.bench) if p and p.id == cand_ns["Kadabra"])
                    abra_at_div = sum(1 for p in (my_p.active + my_p.bench) if p and p.id == cand_ns["Abra"])
                    hand_at_div = len(my_p.hand) if my_p.hand else my_p.handCount
                    my_prizes_at_div = len(my_p.prize)
                    opp_prizes_at_div = len(op_p.prize)

                    def desc_p(p):
                        if not p: return "None"
                        cd = cand_ns["card_table"].get(p.id)
                        return cd.name if cd else f"Card_{p.id}"
                    my_active_at_div = desc_p(my_p.active[0] if my_p.active else None)

                    cand_search_div = cand_searched
                    ctrl_search_div = ctrl_searched

            action = cand_action
        else:
            action = ctrl_ns["agent"](obs)

        obs = battle_select(action)

    battle_finish()
    final_res = obs.get("current", {}).get("result", -1)

    cand_won = (final_res == cand_seat)
    ctrl_won = (final_res == (1 - cand_seat))
    is_draw = not (cand_won or ctrl_won)

    outcome_str = "WIN" if cand_won else ("LOSS" if ctrl_won else "DRAW")

    return PairedMatchResult(
        game_id=game_id,
        starting_seat=cand_seat,
        has_divergence=has_divergence,
        first_div_step=first_div_step,
        first_div_turn=first_div_turn,
        first_div_ctrl_action=first_div_ctrl_action,
        first_div_cand_action=first_div_cand_action,
        total_divergences=total_divergences,
        alakazam_at_first_div=alak_at_div,
        kadabra_at_first_div=kad_at_div,
        abra_at_first_div=abra_at_div,
        hand_size_at_first_div=hand_at_div,
        my_prizes_at_first_div=my_prizes_at_div,
        opp_prizes_at_first_div=opp_prizes_at_div,
        my_active_at_first_div=my_active_at_div,
        cand_search_invoked_first_div=cand_search_div,
        ctrl_search_invoked_first_div=ctrl_search_div,
        game_outcome=outcome_str,
        cand_won=cand_won,
        ctrl_won=ctrl_won,
        is_draw=is_draw,
        game_length=step,
    )

def main():
    print("=" * 80)
    print("RUNNING PAIRED / MATCHED-STATE EFFECT ANALYSIS (200 GAMES)")
    print("=" * 80)

    tasks = [(g, 0 if g <= 100 else 1) for g in range(1, 201)]
    results: List[PairedMatchResult] = []

    start_t = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(run_paired_match, g, s): g for (g, s) in tasks}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == 200:
                print(f"  Progress: {completed:03d}/200 paired matches completed", flush=True)

    elapsed = time.time() - start_t
    results.sort(key=lambda x: x.game_id)

    # Convert to DataFrame
    records = []
    for r in results:
        records.append({
            "game_id": r.game_id,
            "starting_seat": r.starting_seat,
            "has_divergence": r.has_divergence,
            "first_div_step": r.first_div_step,
            "first_div_turn": r.first_div_turn,
            "first_div_ctrl_action": r.first_div_ctrl_action,
            "first_div_cand_action": r.first_div_cand_action,
            "total_divergences": r.total_divergences,
            "alakazam_at_first_div": r.alakazam_at_first_div,
            "kadabra_at_first_div": r.kadabra_at_first_div,
            "abra_at_first_div": r.abra_at_first_div,
            "hand_size_at_first_div": r.hand_size_at_first_div,
            "my_prizes_at_first_div": r.my_prizes_at_first_div,
            "opp_prizes_at_first_div": r.opp_prizes_at_first_div,
            "my_active_at_first_div": r.my_active_at_first_div,
            "cand_search_invoked": r.cand_search_invoked_first_div,
            "ctrl_search_invoked": r.ctrl_search_invoked_first_div,
            "game_outcome": r.game_outcome,
            "cand_won": r.cand_won,
            "ctrl_won": r.ctrl_won,
            "is_draw": r.is_draw,
            "game_length": r.game_length,
        })

    df = pd.DataFrame(records)
    out_csv = HERE / "hybrid_paired_state_results.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"\nWrote {out_csv} ({len(df)} records)")

    # Analysis
    div_df = df[df["has_divergence"] == True]
    non_div_df = df[df["has_divergence"] == False]

    dw = div_df["cand_won"].sum()
    dl = div_df["ctrl_won"].sum()
    dd = div_df["is_draw"].sum()
    d_dec = dw + dl
    d_wr = dw / d_dec * 100 if d_dec else 0.0

    ndw = non_div_df["cand_won"].sum()
    ndl = non_div_df["ctrl_won"].sum()
    ndd = non_div_df["is_draw"].sum()
    nd_dec = ndw + ndl
    nd_wr = ndw / nd_dec * 100 if nd_dec else 0.0

    print("\n" + "=" * 80)
    print("PAIRED / MATCHED-STATE EFFECT ANALYSIS RESULTS")
    print("=" * 80)
    print(f"Total Paired Matches:            200")
    print(f"Matches with Policy Divergence:  {len(div_df)} / 200 ({len(div_df)/200*100:.1f}%)")
    print(f"  --> Divergent Matches Record:  {dw}W - {dl}L - {dd}D (Decisive WR: {d_wr:.2f}%)")
    print(f"Matches with ZERO Divergence:    {len(non_div_df)} / 200 ({len(non_div_df)/200*100:.1f}%)")
    print(f"  --> Non-Divergent Record:      {ndw}W - {ndl}L - {ndd}D (Decisive WR: {nd_wr:.2f}%)")
    print(f"Net Match Record:                {dw+ndw}W - {dl+ndl}L - {dd+ndd}D")
    print(f"Elapsed Time:                    {elapsed:.2f}s")
    print("=" * 80)

    # First divergence breakdown
    first_pairs = div_df.groupby(["first_div_ctrl_action", "first_div_cand_action"]).agg(
        count=("game_id", "count"),
        wins=("cand_won", "sum"),
        losses=("ctrl_won", "sum"),
        draws=("is_draw", "sum"),
    ).reset_index()
    first_pairs["decisive_wr"] = first_pairs["wins"] / (first_pairs["wins"] + first_pairs["losses"]) * 100
    first_pairs = first_pairs.sort_values("count", ascending=False)

    print("\nFIRST DIVERGENCE ACTION PAIR BREAKDOWN:")
    for idx, row in first_pairs.iterrows():
        print(f"  {row['first_div_ctrl_action']:<32} -> {row['first_div_cand_action']:<32} | N={row['count']:>3} | {row['wins']}W-{row['losses']}L-{row['draws']}D (WR: {row['decisive_wr']:.1f}%)")

    # State condition breakdown for PLAY(Dawn) -> PLAY(Hilda)
    hilda_first = div_df[(div_df["first_div_ctrl_action"] == "PLAY(Dawn)") & (div_df["first_div_cand_action"] == "PLAY(Hilda)")]
    print(f"\nSTATE CONDITIONING AT FIRST DAWN->HILDA DIVERGENCE (N={len(hilda_first)} games):")
    for alak_c in [0, 1, 2]:
        if alak_c == 2:
            sub = hilda_first[hilda_first["alakazam_at_first_div"] >= 2]
            lbl = "Alakazam >= 2"
        else:
            sub = hilda_first[hilda_first["alakazam_at_first_div"] == alak_c]
            lbl = f"Alakazam == {alak_c}"
        sw = sub["cand_won"].sum()
        sl = sub["ctrl_won"].sum()
        sd = sub["is_draw"].sum()
        s_dec = sw + sl
        swr = sw / s_dec * 100 if s_dec else 0.0
        print(f"  {lbl:<15}: N={len(sub):>2} games | {sw}W-{sl}L-{sd}D | Decisive WR: {swr:.1f}%")

if __name__ == "__main__":
    main()
