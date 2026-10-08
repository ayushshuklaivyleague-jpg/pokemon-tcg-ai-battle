"""
Short-Horizon Counterfactual Evaluation Module.
Evaluates the immediate state consequences and tactical value deltas of candidate actions.
"""

from dataclasses import dataclass
from typing import Any, Optional
import main
from .state_features import StateFeatures, extract_state_features
from .threat_model import ThreatAssessment, evaluate_opponent_threat


@dataclass
class CounterfactualAssessment:
    action_type: str
    immediate_value_delta: float
    is_knockout_line: bool
    is_tempo_positive: bool


def evaluate_action_counterfactual(
    obs: Any,
    option: Any,
    state: Optional[StateFeatures] = None,
    threat: Optional[ThreatAssessment] = None,
) -> CounterfactualAssessment:
    try:
        if state is None:
            state = extract_state_features(obs)
        if threat is None:
            threat = evaluate_opponent_threat(obs, state)

        typ_name = main.option_type_name(option)
        card = main.v4_card_from_option(obs, option)
        delta_val = 0.0
        is_ko = False
        tempo_pos = False

        # 1. ATTACK EVALUATION
        if typ_name == "ATTACK":
            tempo_pos = True
            atk_dmg = 40.0
            card_data = main.v4_card_data(card) if card is not None else None
            if card_data is not None:
                atk_id = main.safe_get(option, "attackId", 0) or 0
                attacks = main.safe_list(main.safe_get(card_data, "attacks", []))
                for a in attacks:
                    if main.safe_get(a, "id", 0) == atk_id:
                        atk_dmg = float(main.safe_get(a, "damage", 40) or 40)
                        break

            # If this attack knocks out the opponent active, give significant priority
            if atk_dmg >= state.opp_active_hp and state.opp_active_hp > 0:
                is_ko = True
                delta_val += 5000.0
            else:
                delta_val += atk_dmg * 20.0

        # 2. EVOLVE EVALUATION
        elif typ_name == "EVOLVE":
            tempo_pos = True
            delta_val += 2000.0

        # 3. ATTACH ENERGY EVALUATION
        elif typ_name == "ATTACH":
            area = main.safe_get(option, "inPlayArea", None)
            if area == main.AreaType.ACTIVE:
                # If active already has enough energy (>= 3), attaching to bench is better
                if state.my_active_energy >= 3 and state.my_bench_count > 0:
                    delta_val -= 1500.0
                else:
                    delta_val += 2500.0
                    tempo_pos = True
            else:
                # Attaching to bench when active is fully charged
                if state.my_active_energy >= 3:
                    delta_val += 3000.0
                    tempo_pos = True
                else:
                    delta_val += 1000.0

        # 4. RETREAT EVALUATION
        elif typ_name == "RETREAT":
            if threat.is_active_lethal_danger and state.my_bench_count > 0:
                delta_val += 15000.0  # Elevate retreat above attach when active is doomed
                tempo_pos = True
            else:
                delta_val -= 5000.0

        # 5. PLAY CARD (TRAINER / POKEMON)
        elif typ_name == "PLAY":
            if card is not None:
                cname = str(main.safe_get(main.v4_card_data(card), "name", "")).lower()
                if main.v4_is_pokemon(card):
                    if state.my_bench_count < 3:
                        delta_val += 2500.0
                        tempo_pos = True
                elif main.v4_is_supporter(card):
                    if state.my_hand_count <= 4:
                        delta_val += 3000.0
                        tempo_pos = True
                elif "nest ball" in cname or "poffin" in cname or "ultra ball" in cname:
                    if state.my_bench_count < 4:
                        delta_val += 3500.0
                        tempo_pos = True
                elif "boss" in cname and state.opp_bench_count > 0:
                    delta_val += 4000.0
                    tempo_pos = True

        return CounterfactualAssessment(
            action_type=typ_name,
            immediate_value_delta=delta_val,
            is_knockout_line=is_ko,
            is_tempo_positive=tempo_pos,
        )

    except Exception:
        return CounterfactualAssessment(
            action_type="UNKNOWN",
            immediate_value_delta=0.0,
            is_knockout_line=False,
            is_tempo_positive=False,
        )
