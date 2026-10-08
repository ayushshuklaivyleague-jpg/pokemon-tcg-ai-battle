"""
Opponent Threat & Lethal Knockout Modeling.
Assesses opponent damage potential, active 1HKO danger, and evolution pressure.
"""

from dataclasses import dataclass
from typing import Any, Optional
import main
from .state_features import extract_state_features, StateFeatures


@dataclass
class ThreatAssessment:
    estimated_opp_damage: float
    lethal_threat_ratio: float
    is_active_lethal_danger: bool
    bench_evolution_threat: bool
    recommended_defensive_action: bool
    threat_score_penalty: float


def estimate_pokemon_damage_potential(pokemon: Any, energy_count: int) -> float:
    if pokemon is None:
        return 0.0

    card_data = main.v4_card_data(pokemon)
    if card_data is not None:
        attacks = main.safe_list(main.safe_get(card_data, "attacks", []))
        max_dmg = 0.0
        for atk in attacks:
            cost = len(main.safe_list(main.safe_get(atk, "cost", [])))
            dmg = float(main.safe_get(atk, "damage", 0) or 0)
            if energy_count >= cost:
                max_dmg = max(max_dmg, dmg)
        if max_dmg > 0:
            return max_dmg

    # Scaled damage estimate based on attached energies
    return float(energy_count * 40.0 + 30.0) if energy_count > 0 else 20.0


def evaluate_opponent_threat(obs: Any, state: Optional[StateFeatures] = None) -> ThreatAssessment:
    try:
        if state is None:
            state = extract_state_features(obs)

        my_idx = main.safe_get(obs.current, "yourIndex", 0)
        opp_idx = 1 - my_idx

        opp_active = main.v4_active(obs, opp_idx)
        opp_energy = state.opp_active_energy

        est_damage = estimate_pokemon_damage_potential(opp_active, opp_energy)

        # Lethal threat ratio: estimated damage / my active HP
        my_hp = max(1.0, state.my_active_hp)
        lethal_ratio = est_damage / my_hp
        is_lethal = lethal_ratio >= 1.0

        # Opponent bench threat
        opp_bench = main.v4_bench(obs, opp_idx)
        bench_threat = any(main.v4_energy_count(p) >= 2 for p in opp_bench if p is not None)

        threat_penalty = 500.0 if is_lethal else (200.0 if lethal_ratio > 0.6 else 0.0)

        return ThreatAssessment(
            estimated_opp_damage=est_damage,
            lethal_threat_ratio=lethal_ratio,
            is_active_lethal_danger=is_lethal,
            bench_evolution_threat=bench_threat,
            recommended_defensive_action=is_lethal and state.my_bench_count > 0,
            threat_score_penalty=threat_penalty,
        )

    except Exception:
        return ThreatAssessment(
            estimated_opp_damage=30.0,
            lethal_threat_ratio=0.3,
            is_active_lethal_danger=False,
            bench_evolution_threat=False,
            recommended_defensive_action=False,
            threat_score_penalty=0.0,
        )
