"""
Modular Planner & Anti-Regression Hybrid Decision Engine.
Integrates feature representation, threat analysis, probability estimation,
and counterfactual scoring with confidence-threshold gating over the V4 control baseline.
"""

from dataclasses import dataclass
from typing import Any, List, Optional
import main
from .state_features import extract_state_features, StateFeatures
from .threat_model import evaluate_opponent_threat, ThreatAssessment
from .prob_info import compute_probability_features, ProbabilityFeatures
from .counterfactual import evaluate_action_counterfactual, CounterfactualAssessment


@dataclass
class GatingConfig:
    enable_state: bool = False
    enable_threat: bool = False
    enable_prob: bool = False
    enable_counterfactual: bool = False
    gating_threshold: float = 150.0  # tau: minimum planning advantage to override V4 default


class ModularPlanner:
    def __init__(self, config: Optional[GatingConfig] = None):
        self.config = config or GatingConfig()

    def score_option(
        self,
        obs: Any,
        option: Any,
        context: Optional[str] = None,
        state: Optional[StateFeatures] = None,
        threat: Optional[ThreatAssessment] = None,
        prob: Optional[ProbabilityFeatures] = None,
    ) -> float:
        # 1. Base V4 Tactical Score
        base_score = float(main.v4_score_action(obs, option, context))

        if not (
            self.config.enable_state
            or self.config.enable_threat
            or self.config.enable_prob
            or self.config.enable_counterfactual
        ):
            return base_score

        bonus = 0.0
        typ_name = main.option_type_name(option)

        # 2. Threat Model Bonus
        if self.config.enable_threat and threat is not None:
            if typ_name == "RETREAT" and threat.is_active_lethal_danger:
                bonus += 16000.0  # Moves retreat (30k) to 46k, above attach (35k-39k)
            elif typ_name == "EVOLVE" and threat.is_active_lethal_danger:
                bonus += 5000.0   # Moves evolve from 70k to 75k to escape 1HKO range
            elif typ_name == "ATTACH" and threat.is_active_lethal_danger:
                area = main.safe_get(option, "inPlayArea", None)
                if area == main.AreaType.ACTIVE:
                    bonus -= 4000.0  # Penalize attaching to a doomed active

        # 3. Counterfactual Value Delta
        if self.config.enable_counterfactual:
            cf = evaluate_action_counterfactual(obs, option, state, threat)
            bonus += cf.immediate_value_delta

        # 4. State Features Bonus
        if self.config.enable_state and state is not None:
            if typ_name == "ATTACH":
                area = main.safe_get(option, "inPlayArea", None)
                if area == main.AreaType.ACTIVE and state.my_active_energy < 2:
                    bonus += 1200.0
            elif typ_name == "PLAY" and state.my_bench_count < 2:
                card = main.v4_card_from_option(obs, option)
                if card is not None and main.v4_is_pokemon(card):
                    bonus += 1800.0

        # 5. Probability Engine Bonus
        if self.config.enable_prob and prob is not None:
            if typ_name == "PLAY":
                card = main.v4_card_from_option(obs, option)
                if card is not None:
                    cname = str(main.safe_get(main.v4_card_data(card), "name", "")).lower()
                    if "nest ball" in cname or "poffin" in cname:
                        bonus += 1500.0 * prob.search_item_utility

        return base_score + bonus


def score_with_planning(
    obs: Any,
    option: Any,
    context: Optional[str] = None,
    config: Optional[GatingConfig] = None,
) -> float:
    planner = ModularPlanner(config)
    state = extract_state_features(obs) if config and config.enable_state else None
    threat = evaluate_opponent_threat(obs, state) if config and config.enable_threat else None
    prob = compute_probability_features(obs) if config and config.enable_prob else None
    return planner.score_option(obs, option, context, state, threat, prob)


def choose_planned_action(obs: Any, config: Optional[GatingConfig] = None) -> List[int]:
    if obs.select is None or not obs.select.option:
        return []

    options = list(obs.select.option)
    try:
        context = main.SelectContext(obs.select.context).name
    except Exception:
        context = None

    cfg = config or GatingConfig()
    planner = ModularPlanner(cfg)

    state = extract_state_features(obs)
    threat = evaluate_opponent_threat(obs, state)
    prob = compute_probability_features(obs)

    v4_scored = []
    planned_scored = []

    for i, option in enumerate(options):
        try:
            v4_score = main.v4_score_action(obs, option, context)
        except Exception:
            v4_score = -10**8
        v4_scored.append((v4_score, -i, i))

        try:
            plan_score = planner.score_option(obs, option, context, state, threat, prob)
        except Exception:
            plan_score = v4_score
        planned_scored.append((plan_score, -i, i))

    v4_scored.sort(reverse=True)
    planned_scored.sort(reverse=True)

    v4_best_idx = v4_scored[0][2]
    planned_best_idx = planned_scored[0][2]

    planned_dict = {entry[2]: entry[0] for entry in planned_scored}
    plan_score_for_best = planned_dict.get(planned_best_idx, -10**8)
    plan_score_for_v4 = planned_dict.get(v4_best_idx, -10**8)
    planning_delta = plan_score_for_best - plan_score_for_v4

    # Anti-Regression Rule: override V4 ONLY if planning delta exceeds threshold tau
    if planned_best_idx != v4_best_idx and planning_delta > cfg.gating_threshold:
        primary_choice = planned_best_idx
        primary_scored = planned_scored
    else:
        primary_choice = v4_best_idx
        primary_scored = v4_scored

    max_count = getattr(obs.select, "maxCount", 1) or 1
    min_count = getattr(obs.select, "minCount", 1) or 1
    max_count = max(min_count, min(int(max_count), len(options)))

    selected = [primary_choice]
    if max_count > 1:
        for _, _, index in primary_scored:
            if index != primary_choice:
                selected.append(index)
            if len(selected) >= max_count:
                break

    return main.legal_selection(obs, selected)
