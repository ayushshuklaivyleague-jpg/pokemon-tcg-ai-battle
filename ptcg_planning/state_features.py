"""
State Representation & Feature Extraction Module.
Extracts normalized board context, energy curves, HP pools, and prize state.
"""

from dataclasses import dataclass
from typing import Optional, List, Any
import main


@dataclass
class StateFeatures:
    my_active_hp: float
    my_active_max_hp: float
    my_active_hp_ratio: float
    my_active_energy: int
    my_bench_count: int
    my_bench_total_energy: int
    my_highest_bench_energy: int
    my_hand_count: int
    my_prize_remaining: int
    opp_active_hp: float
    opp_active_max_hp: float
    opp_active_hp_ratio: float
    opp_active_energy: int
    opp_bench_count: int
    opp_prize_remaining: int
    prize_differential: int
    supporter_played: bool


def extract_state_features(obs: Any) -> StateFeatures:
    """
    Extract structured state features from the current observation.
    Never throws an unhandled exception; returns default safe features on error.
    """
    try:
        my_idx = main.safe_get(obs.current, "yourIndex", 0)
        opp_idx = 1 - my_idx

        # My Board
        my_active = main.v4_active(obs, my_idx)
        my_hp = main.v4_hp(my_active)
        my_max_hp = max(1.0, main.v4_max_hp(my_active))
        my_hp_ratio = my_hp / my_max_hp if my_max_hp > 0 else 0.0
        my_act_energy = main.v4_energy_count(my_active)

        my_bench = main.v4_bench(obs, my_idx)
        my_bench_count = len(my_bench)
        my_bench_energies = [main.v4_energy_count(p) for p in my_bench if p is not None]
        my_bench_total_energy = sum(my_bench_energies)
        my_highest_bench_energy = max(my_bench_energies) if my_bench_energies else 0

        my_hand = main.v4_hand(obs)
        my_hand_count = len(my_hand)

        my_p = obs.current.players[my_idx]
        my_prizes = main.safe_list(main.safe_get(my_p, "prize", []))
        my_prize_remaining = len(my_prizes)

        # Opponent Board
        opp_active = main.v4_active(obs, opp_idx)
        opp_hp = main.v4_hp(opp_active)
        opp_max_hp = max(1.0, main.v4_max_hp(opp_active))
        opp_hp_ratio = opp_hp / opp_max_hp if opp_max_hp > 0 else 0.0
        opp_act_energy = main.v4_energy_count(opp_active)

        opp_bench = main.v4_bench(obs, opp_idx)
        opp_bench_count = len(opp_bench)

        opp_p = obs.current.players[opp_idx]
        opp_prizes = main.safe_list(main.safe_get(opp_p, "prize", []))
        opp_prize_remaining = len(opp_prizes)

        prize_diff = opp_prize_remaining - my_prize_remaining
        supporter_played = bool(main.safe_get(obs.current, "supporterPlayed", False))

        return StateFeatures(
            my_active_hp=my_hp,
            my_active_max_hp=my_max_hp,
            my_active_hp_ratio=my_hp_ratio,
            my_active_energy=my_act_energy,
            my_bench_count=my_bench_count,
            my_bench_total_energy=my_bench_total_energy,
            my_highest_bench_energy=my_highest_bench_energy,
            my_hand_count=my_hand_count,
            my_prize_remaining=my_prize_remaining,
            opp_active_hp=opp_hp,
            opp_active_max_hp=opp_max_hp,
            opp_active_hp_ratio=opp_hp_ratio,
            opp_active_energy=opp_act_energy,
            opp_bench_count=opp_bench_count,
            opp_prize_remaining=opp_prize_remaining,
            prize_differential=prize_diff,
            supporter_played=supporter_played,
        )

    except Exception:
        return StateFeatures(
            my_active_hp=50.0,
            my_active_max_hp=100.0,
            my_active_hp_ratio=0.5,
            my_active_energy=0,
            my_bench_count=0,
            my_bench_total_energy=0,
            my_highest_bench_energy=0,
            my_hand_count=5,
            my_prize_remaining=6,
            opp_active_hp=50.0,
            opp_active_max_hp=100.0,
            opp_active_hp_ratio=0.5,
            opp_active_energy=0,
            opp_bench_count=0,
            opp_prize_remaining=6,
            prize_differential=0,
            supporter_played=False,
        )
