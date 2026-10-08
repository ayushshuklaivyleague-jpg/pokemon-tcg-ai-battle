#!/usr/bin/env python3
"""
HYBRID_STAGE_4: Preserved Sol Eclipse Search Engine with MIKE V4 Egress Safety & Hilda=3150.

Architecture:
  - Full Sol Eclipse Search Layer (1-ply determinized rollouts with belief modeling) EXACTLY INTACT.
  - Full Sol Eclipse Rich State Representation & Heuristics EXACTLY INTACT.
  - Parameter Genome: WEIGHTS["hilda"] = 3150 (validated candidate), all other 68 weights identical.
  - Outer Egress: MIKE V4 selection_contract and legal_selection wrapper for absolute contract safety.
"""

import sys
import os
import re
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# Load base code from codex_sol_eclipse_alakazam.py
source_file = HERE / "codex_sol_eclipse_alakazam.py"
raw_code = source_file.read_text(encoding="utf-8")

main_match = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)

if not main_match or not deck_match:
    raise RuntimeError("Failed to parse codex_sol_eclipse_alakazam.py")

SOL_MAIN_SOURCE = main_match.group(1)
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]

# Apply validated Hilda=3150 genome update to candidate source
STAGE4_SOURCE = SOL_MAIN_SOURCE.replace('"hilda": 3000,', '"hilda": 3150,')

# Compile candidate environment
candidate_ns: Dict[str, Any] = {}
exec(STAGE4_SOURCE, candidate_ns)

# Extract core functions
_sol_agent = candidate_ns["agent"]
to_observation_class = candidate_ns["to_observation_class"]
SelectContext = candidate_ns["SelectContext"]
OptionType = candidate_ns["OptionType"]
AreaType = candidate_ns["AreaType"]
card_table = candidate_ns["card_table"]
WEIGHTS = candidate_ns["WEIGHTS"]


# ============================================================
# MIKE V4 OUTER SAFETY & SELECTION CONTRACT WRAPPER
# ============================================================

def safe_get(obj, name, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def safe_list(value):
    if value is None:
        return []
    try:
        return list(value)
    except Exception:
        return []


def selection_contract(obs):
    sel = safe_get(obs, "select", None)
    if sel is None:
        return {"option_count": 0, "min_count": 0, "max_count": 0, "context": None}

    options = safe_list(safe_get(sel, "option", []))
    opt_count = len(options)
    min_c = max(0, int(safe_get(sel, "minCount", 0) or 0))
    max_c = max(0, int(safe_get(sel, "maxCount", opt_count) or opt_count))

    max_c = min(max_c, opt_count)
    min_c = min(min_c, max_c)

    return {
        "option_count": opt_count,
        "min_count": min_c,
        "max_count": max_c,
        "context": safe_get(sel, "context", None),
    }


def legal_selection(obs, selected: List[int]) -> List[int]:
    contract = selection_contract(obs)
    opt_count = contract["option_count"]
    min_c = contract["min_count"]
    max_c = contract["max_count"]

    if opt_count == 0:
        return []

    valid = []
    seen = set()
    if isinstance(selected, list):
        for idx in selected:
            if isinstance(idx, int) and 0 <= idx < opt_count and idx not in seen:
                valid.append(idx)
                seen.add(idx)

    # Pad if below minimum constraint
    if len(valid) < min_c:
        for idx in range(opt_count):
            if idx not in seen:
                valid.append(idx)
                seen.add(idx)
                if len(valid) >= min_c:
                    break

    # Truncate if above maximum constraint
    if len(valid) > max_c:
        valid = valid[:max_c]

    return valid


def hybrid_stage4_agent(obs_dict, configuration=None) -> List[int]:
    """
    HYBRID_STAGE_4 Entrypoint:
    Executes full Sol Eclipse decision engine (Heuristics + Search) with V4 Egress Safety.
    """
    if not isinstance(obs_dict, dict):
        return []

    if "select" not in obs_dict or obs_dict.get("select") is None:
        return list(SOL_DECK)

    try:
        # Full Sol Eclipse decision engine (Heuristic + 1-Ply Search)
        action = _sol_agent(obs_dict)

        # V4 Outer Safety Contract
        obs = to_observation_class(obs_dict)
        return legal_selection(obs, action)

    except Exception:
        # V4 Fallback Cascade
        try:
            sel = obs_dict.get("select") or {}
            opts = sel.get("option", [])
            min_c = max(1, int(sel.get("minCount", 1) or 1))
            k = min(min_c, len(opts)) if opts else 0
            return list(range(k))
        except Exception:
            return [0]

agent = hybrid_stage4_agent
