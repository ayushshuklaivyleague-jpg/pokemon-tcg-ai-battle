"""
Pokémon TCG Modular Planning Layer Package.
Extends the frozen V4 control baseline with modular, contract-safe planning layers.
"""

from .state_features import extract_state_features, StateFeatures
from .threat_model import evaluate_opponent_threat, ThreatAssessment
from .prob_info import compute_probability_features, ProbabilityFeatures
from .counterfactual import evaluate_action_counterfactual, CounterfactualAssessment
from .planner import (
    ModularPlanner,
    score_with_planning,
    choose_planned_action,
    GatingConfig,
)
from .ablation_agents import (
    agent_p0_frozen_v4,
    agent_p1_state,
    agent_p2_threat,
    agent_p3_prob,
    agent_p4_counterfactual,
    agent_p5_ensemble,
    get_ablation_agent,
)

__all__ = [
    "extract_state_features",
    "StateFeatures",
    "evaluate_opponent_threat",
    "ThreatAssessment",
    "compute_probability_features",
    "ProbabilityFeatures",
    "evaluate_action_counterfactual",
    "CounterfactualAssessment",
    "ModularPlanner",
    "score_with_planning",
    "choose_planned_action",
    "GatingConfig",
    "agent_p0_frozen_v4",
    "agent_p1_state",
    "agent_p2_threat",
    "agent_p3_prob",
    "agent_p4_counterfactual",
    "agent_p5_ensemble",
    "get_ablation_agent",
]
