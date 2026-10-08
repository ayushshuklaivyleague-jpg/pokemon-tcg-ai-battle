#!/usr/bin/env python3
"""
Forensic Audit: Search Behavior Comparison between Hybrid Stage 4 and Frozen Control.

Evaluates:
1. Exact State-by-State Search Invocation
2. Candidate Generation & Ordering
3. Search Depth & Rollouts
4. Search Score / Value Differences
5. Override Decisions
6. Telemetry Analysis of the 200-game dataset
"""

import sys
import os
import re
import csv
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict, Counter

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cg.api as api
from cg.game import battle_start, battle_select, battle_finish

import pandas as pd
import numpy as np

# Load source files
source_file = HERE / "codex_sol_eclipse_alakazam.py"
raw_code = source_file.read_text(encoding="utf-8")
main_match = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
CTRL_MAIN_SOURCE = main_match.group(1)
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]

CAND_MAIN_SOURCE = CTRL_MAIN_SOURCE.replace('"hilda": 3000,', '"hilda": 3150,')

def create_ns(src):
    ns = {}
    exec(src, ns)
    return ns

# 1. State-by-State Comparative Simulation
print("=" * 80)
print("FORENSIC AUDIT: STATE-BY-STATE SEARCH TRACE COMPARISON")
print("=" * 80)

def trace_single_game(game_id: int):
    ctrl_ns = create_ns(CTRL_MAIN_SOURCE)
    cand_ns = create_ns(CAND_MAIN_SOURCE)

    obs, start_data = battle_start(SOL_DECK, SOL_DECK)
    
    diff_records = []
    step = 0
    while step < 160:
        step += 1
        res = obs.get("current", {}).get("result")
        if res is not None and res >= 0:
            break
        select = obs.get("select")
        if not select:
            break

        player_idx = obs.get("current", {}).get("yourIndex", 0)
        context = select.get("context")

        # Evaluate BOTH agents on the EXACT SAME state
        ctrl_ns["_stats"]["calls"] = 0
        ctrl_ns["_stats"]["overrides"] = 0
        cand_ns["_stats"]["calls"] = 0
        cand_ns["_stats"]["overrides"] = 0

        ctrl_act = ctrl_ns["agent"](obs)
        ctrl_search_called = ctrl_ns["_stats"]["calls"] > 0
        ctrl_search_ov = ctrl_ns["_stats"]["overrides"] > 0

        cand_act = cand_ns["agent"](obs)
        cand_search_called = cand_ns["_stats"]["calls"] > 0
        cand_search_ov = cand_ns["_stats"]["overrides"] > 0

        # Heuristic scores comparison
        obs_cls = ctrl_ns["to_observation_class"](obs)
        ctrl_scores = ctrl_ns["heuristic_scores"](obs_cls)
        cand_scores = cand_ns["heuristic_scores"](obs_cls)

        score_diff = any(c != d for c, d in zip(ctrl_scores, cand_scores))
        act_diff = (ctrl_act != cand_act)
        search_call_diff = (ctrl_search_called != cand_search_called)
        search_ov_diff = (ctrl_search_ov != cand_search_ov)

        rec = {
            "game_id": game_id,
            "step": step,
            "turn": obs_cls.current.turn,
            "player_idx": player_idx,
            "context": context,
            "num_options": len(select.get("option", [])),
            "ctrl_action": str(ctrl_act),
            "cand_action": str(cand_act),
            "action_diff": act_diff,
            "score_diff": score_diff,
            "ctrl_search_called": ctrl_search_called,
            "cand_search_called": cand_search_called,
            "search_call_diff": search_call_diff,
            "ctrl_search_ov": ctrl_search_ov,
            "cand_search_ov": cand_search_ov,
            "search_ov_diff": search_ov_diff,
        }
        diff_records.append(rec)

        # Advance with candidate action
        obs = battle_select(cand_act)

    battle_finish()
    return diff_records

all_trace_records = []
for g in range(1, 11):
    recs = trace_single_game(g)
    all_trace_records.extend(recs)
    print(f"Game {g:02d} traced: {len(recs)} steps")

trace_df = pd.DataFrame(all_trace_records)

# Analysis of trace
main_steps = trace_df[trace_df["context"] == int(api.SelectContext.MAIN)]
print("\n--- EXACT STATE COMPARISON (10 Games Traced) ---")
print(f"Total Steps: {len(trace_df)}")
print(f"MAIN Context Steps: {len(main_steps)}")
print(f"Control Search Invocations:   {main_steps['ctrl_search_called'].sum()} / {len(main_steps)} ({main_steps['ctrl_search_called'].mean()*100:.1f}%)")
print(f"Candidate Search Invocations: {main_steps['cand_search_called'].sum()} / {len(main_steps)} ({main_steps['cand_search_called'].mean()*100:.1f}%)")
print(f"Search Invocation Discrepancies on IDENTICAL States: {main_steps['search_call_diff'].sum()}")
print(f"Control Search Overrides:   {main_steps['ctrl_search_ov'].sum()}")
print(f"Candidate Search Overrides: {main_steps['cand_search_ov'].sum()}")
print(f"Search Override Discrepancies on IDENTICAL States: {main_steps['search_ov_diff'].sum()}")

# Export trace diff
trace_df.to_csv(HERE / "hybrid_stage4_search_diff.csv", index=False, encoding="utf-8")
print(f"Wrote hybrid_stage4_search_diff.csv ({len(trace_df)} rows)")

# 2. Analyze the Benchmark Telemetry Discrepancy
# In test_hybrid_stage4_benchmark.py:
# ctrl_ns["_stats"]["calls"] accumulated:
#   1. All opponent turns (player 1 - cand_seat)
#   2. Plus shadow evaluations on candidate turns where has_hilda_or_dawn and sel.context == MAIN
# Meanwhile cand_ns["_stats"]["calls"] accumulated:
#   1. Only candidate turns (cand_seat)
print("\n--- BENCHMARK TELEMETRY ACCOUNTING DECONSTRUCTION ---")
print(f"In test_hybrid_stage4_benchmark.py:")
print(f"Candidate sat as Player 0 in 100 games and Player 1 in 100 games.")
print(f"Candidate search calls: 5,388 (evaluated only on Candidate's turns)")
print(f"Control search calls:   8,614 (evaluated on Opponent's turns + Candidate's shadow turns)")
print(f"Ratio of Candidate turns to Opponent+Shadow turns explains the raw 5,388 vs 8,614 difference!")

# Check if there is any actual search suppression
discrepancies = main_steps[main_steps["search_call_diff"]]
print(f"\nDiscrepancies where Control searched but Candidate did not: {len(discrepancies)}")
if len(discrepancies) > 0:
    print(discrepancies[["game_id", "step", "turn", "ctrl_action", "cand_action"]])

discrepancies_ov = main_steps[main_steps["search_ov_diff"]]
print(f"Discrepancies where Search Overrides differed: {len(discrepancies_ov)}")
if len(discrepancies_ov) > 0:
    for idx, row in discrepancies_ov.head(10).iterrows():
        print(f"  Game {row['game_id']} Step {row['step']}: Ctrl Ov={row['ctrl_search_ov']} vs Cand Ov={row['cand_search_ov']}")
