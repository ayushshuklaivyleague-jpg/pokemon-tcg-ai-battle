"""
Sol Eclipse Telemetry and Audit Harness.
Executes games using the exact, unmodified Sol Eclipse Alakazam agent
and instruments every decision to capture full board state, heuristic scores,
weight usage, search invocations, overrides, and game outcomes.
"""

import sys
import os
import re
import csv
import time
import json
import random
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, List, Tuple, Optional

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cg.api as api
from cg.game import battle_start, battle_select, battle_finish
import main

# 1. Extract MAIN_SOURCE and DECK_SOURCE from codex_sol_eclipse_alakazam.py
source_file = HERE / "codex_sol_eclipse_alakazam.py"
raw_code = source_file.read_text(encoding="utf-8")

main_match = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)

if not main_match or not deck_match:
    raise RuntimeError("Failed to parse codex_sol_eclipse_alakazam.py")

main_source = main_match.group(1)
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]

# Compile and create module namespace for Sol Eclipse
sol_namespace = {"__file__": str(source_file)}
exec(main_source, sol_namespace)

sol_agent_func = sol_namespace["agent"]
sol_weights = sol_namespace["WEIGHTS"]
card_table = sol_namespace["card_table"]
to_obs = sol_namespace["to_observation_class"]
heuristic_scores_func = sol_namespace["heuristic_scores"]
search_decide_func = sol_namespace["_search_decide"]
courage_guard_func = sol_namespace["_courage_teleportation_guard"]

# Card name helper
def card_name(cid: int) -> str:
    c = card_table.get(cid)
    return c.name if c else f"Card_{cid}"

def context_name(ctx) -> str:
    if hasattr(ctx, "name"):
        return ctx.name
    try:
        return api.SelectContext(ctx).name
    except Exception:
        return str(ctx)

def option_type_name(opt_type) -> str:
    if hasattr(opt_type, "name"):
        return opt_type.name
    try:
        return api.OptionType(opt_type).name
    except Exception:
        return str(opt_type)

def describe_option(obs, opt) -> str:
    t_name = option_type_name(opt.type)
    if opt.type == api.OptionType.NUMBER:
        return f"NUMBER({opt.number})"
    elif opt.type == api.OptionType.YES:
        return "YES"
    elif opt.type == api.OptionType.NO:
        return "NO"
    elif opt.type == api.OptionType.END:
        return "END_TURN"
    elif opt.type == api.OptionType.CARD:
        c = sol_namespace["get_card"](obs, opt.area, opt.index, opt.playerIndex)
        return f"CARD({card_name(c.id) if c else 'None'} in {opt.area})"
    elif opt.type == api.OptionType.PLAY:
        c = sol_namespace["get_card"](obs, api.AreaType.HAND, opt.index, obs.current.yourIndex)
        return f"PLAY({card_name(c.id) if c else 'None'})"
    elif opt.type == api.OptionType.ATTACH:
        c = sol_namespace["get_card"](obs, api.AreaType.HAND, opt.index, obs.current.yourIndex)
        target = sol_namespace["get_card"](obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)
        return f"ATTACH({card_name(c.id) if c else 'None'} -> {card_name(target.id) if target else 'None'}@{opt.inPlayArea})"
    elif opt.type == api.OptionType.EVOLVE:
        c = sol_namespace["get_card"](obs, api.AreaType.HAND, opt.index, obs.current.yourIndex)
        target = sol_namespace["get_card"](obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)
        return f"EVOLVE({card_name(c.id) if c else 'None'} on {card_name(target.id) if target else 'None'})"
    elif opt.type == api.OptionType.ABILITY:
        c = sol_namespace["get_card"](obs, opt.area, opt.index, obs.current.yourIndex)
        return f"ABILITY({card_name(c.id) if c else 'None'})"
    elif opt.type == api.OptionType.RETREAT:
        return "RETREAT"
    elif opt.type == api.OptionType.ATTACK:
        atk_names = {1070: "Teleportation", 1071: "Super Psy Bolt", 1072: "Powerful Hand"}
        return f"ATTACK({atk_names.get(opt.attackId, opt.attackId)})"
    return f"{t_name}"

# Instrumented Telemetry Agent
class InstrumentedSolAgent:
    def __init__(self, name: str = "SolEclipse"):
        self.name = name
        self.records: List[Dict[str, Any]] = []
        self.current_game_id = 0
        self.current_step = 0
        self.player_idx = 0
        self.total_search_invocations = 0
        self.total_search_overrides = 0
        self.total_courage_overrides = 0

    def set_game(self, game_id: int, player_idx: int):
        self.current_game_id = game_id
        self.player_idx = player_idx
        self.current_step = 0

    def decide(self, obs_dict: Dict[str, Any]) -> List[int]:
        self.current_step += 1
        if obs_dict.get("select") is None:
            # Initialization
            return sol_agent_func(obs_dict)

        obs = to_obs(obs_dict)
        state = obs.current
        select = obs.select
        my_idx = state.yourIndex
        my_p = state.players[my_idx]
        op_p = state.players[1 - my_idx]

        # 1. Base heuristic evaluation
        scores = heuristic_scores_func(obs)
        n_opts = len(select.option)
        base_order = sorted(range(n_opts), key=lambda i: scores[i], reverse=True)
        heur_pick = base_order[0] if base_order else 0

        # Exact production fallback action (respecting maxCount)
        k_count = min(select.maxCount, n_opts)
        k_count = max(k_count, min(max(1, select.minCount), n_opts))
        heuristic_action = base_order[:k_count]

        # 2. Check search layer
        search_invoked = False
        search_pick = None
        is_search_override = False
        if select.context == api.SelectContext.MAIN and n_opts >= 3 and state.turn >= 2:
            search_invoked = True
            self.total_search_invocations += 1
            search_pick = search_decide_func(obs, base_order, scores)
            if search_pick is not None and search_pick != heur_pick:
                is_search_override = True
                self.total_search_overrides += 1

        pre_guard_action = [search_pick] if search_pick is not None else list(heuristic_action)

        # 3. Courage guard check
        final_action = courage_guard_func(obs_dict, pre_guard_action)
        is_courage_override = (final_action != pre_guard_action)
        if is_courage_override:
            self.total_courage_overrides += 1

        # Selected option description
        sel_idx = final_action[0] if final_action else 0
        sel_opt = select.option[sel_idx] if 0 <= sel_idx < n_opts else None
        heur_opt = select.option[heur_pick] if 0 <= heur_pick < n_opts else None

        # Extract features for record
        my_act = my_p.active[0] if my_p.active else None
        op_act = op_p.active[0] if op_p.active else None

        my_act_str = f"{card_name(my_act.id)} HP:{my_act.hp} En:{len(my_act.energies)}" if my_act else "None"
        op_act_str = f"{card_name(op_act.id)} HP:{op_act.hp} En:{len(op_act.energies)}" if op_act else "None"

        my_bench_str = "/".join([f"{card_name(b.id)} HP:{b.hp} En:{len(b.energies)}" for b in my_p.bench if b]) or "Empty"
        op_bench_str = "/".join([f"{card_name(b.id)} HP:{b.hp} En:{len(b.energies)}" for b in op_p.bench if b]) or "Empty"

        legal_options_desc = [describe_option(obs, o) for o in select.option]
        selected_desc = describe_option(obs, sel_opt) if sel_opt else "None"
        heur_desc = describe_option(obs, heur_opt) if heur_opt else "None"

        # Record decision
        rec = {
            "game_id": self.current_game_id,
            "step": self.current_step,
            "turn": state.turn,
            "player_idx": my_idx,
            "context": context_name(select.context),
            "num_options": n_opts,
            "legal_options": " | ".join(legal_options_desc),
            "selected_idx": sel_idx,
            "selected_action": str(final_action),
            "selected_desc": selected_desc,
            "heuristic_top_idx": heur_pick,
            "heuristic_top_desc": heur_desc,
            "heuristic_score": scores[heur_pick] if scores else 0,
            "all_scores": ",".join([str(round(s, 2)) for s in scores]),
            "search_invoked": search_invoked,
            "search_override": is_search_override,
            "courage_override": is_courage_override,
            "hand_size": len(my_p.hand) if my_p.hand else my_p.handCount,
            "deck_count": my_p.deckCount,
            "my_prizes": len(my_p.prize),
            "opp_prizes": len(op_p.prize),
            "my_active": my_act_str,
            "my_bench": my_bench_str,
            "opp_active": op_act_str,
            "opp_bench": op_bench_str,
            "game_outcome": "UNKNOWN"
        }
        self.records.append(rec)

        # Call the underlying post_pick if applicable
        if select.context == api.SelectContext.MAIN and final_action:
            sol_namespace["_post_pick"](obs, final_action[0])

        return final_action

print("Harness instrumented agent ready.")
