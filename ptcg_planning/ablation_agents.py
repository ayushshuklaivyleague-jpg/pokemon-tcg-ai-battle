"""
Ablation Matrix Agents ($P_0$ through $P_5$).
Provides unified agent entry points for each experimental configuration.
"""

from typing import Any, Dict, List, Optional
import main
from .planner import GatingConfig, choose_planned_action


def agent_p0_frozen_v4(obs_dict: Dict[str, Any], configuration: Optional[Any] = None) -> List[int]:
    """P0: Frozen V4 Control Baseline (Champion)."""
    return main.agent(obs_dict, configuration)


def agent_p1_state(obs_dict: Dict[str, Any], configuration: Optional[Any] = None) -> List[int]:
    """P1: V4 + Structured State Representation."""
    if not isinstance(obs_dict, dict):
        return []
    if "select" not in obs_dict or obs_dict.get("select") is None:
        return list(main.DECK)
    try:
        obs = main.to_observation_class(obs_dict)
        cfg = GatingConfig(enable_state=True, gating_threshold=100.0)
        return choose_planned_action(obs, cfg)
    except Exception:
        return main.agent(obs_dict, configuration)


def agent_p2_threat(obs_dict: Dict[str, Any], configuration: Optional[Any] = None) -> List[int]:
    """P2: V4 + Opponent Threat & KO Model."""
    if not isinstance(obs_dict, dict):
        return []
    if "select" not in obs_dict or obs_dict.get("select") is None:
        return list(main.DECK)
    try:
        obs = main.to_observation_class(obs_dict)
        cfg = GatingConfig(enable_threat=True, gating_threshold=100.0)
        return choose_planned_action(obs, cfg)
    except Exception:
        return main.agent(obs_dict, configuration)


def agent_p3_prob(obs_dict: Dict[str, Any], configuration: Optional[Any] = None) -> List[int]:
    """P3: V4 + Information-Boundary Probability Features."""
    if not isinstance(obs_dict, dict):
        return []
    if "select" not in obs_dict or obs_dict.get("select") is None:
        return list(main.DECK)
    try:
        obs = main.to_observation_class(obs_dict)
        cfg = GatingConfig(enable_prob=True, gating_threshold=100.0)
        return choose_planned_action(obs, cfg)
    except Exception:
        return main.agent(obs_dict, configuration)


def agent_p4_counterfactual(obs_dict: Dict[str, Any], configuration: Optional[Any] = None) -> List[int]:
    """P4: V4 + Short-Horizon Counterfactual Evaluation."""
    if not isinstance(obs_dict, dict):
        return []
    if "select" not in obs_dict or obs_dict.get("select") is None:
        return list(main.DECK)
    try:
        obs = main.to_observation_class(obs_dict)
        cfg = GatingConfig(enable_counterfactual=True, gating_threshold=150.0)
        return choose_planned_action(obs, cfg)
    except Exception:
        return main.agent(obs_dict, configuration)


def agent_p5_ensemble(obs_dict: Dict[str, Any], configuration: Optional[Any] = None) -> List[int]:
    """P5: V4 + Validated Ensemble (State + Threat + Counterfactuals with Calibrated Gating)."""
    if not isinstance(obs_dict, dict):
        return []
    if "select" not in obs_dict or obs_dict.get("select") is None:
        return list(main.DECK)
    try:
        obs = main.to_observation_class(obs_dict)
        cfg = GatingConfig(
            enable_state=True,
            enable_threat=True,
            enable_prob=False,  # Exclude noisy uncalibrated probability signals
            enable_counterfactual=True,
            gating_threshold=200.0,
        )
        return choose_planned_action(obs, cfg)
    except Exception:
        return main.agent(obs_dict, configuration)


ABLATION_MAP = {
    "P0": ("Frozen V4 Baseline", agent_p0_frozen_v4),
    "P1": ("V4 + State Representation", agent_p1_state),
    "P2": ("V4 + Threat Model", agent_p2_threat),
    "P3": ("V4 + Probability Features", agent_p3_prob),
    "P4": ("V4 + Counterfactuals", agent_p4_counterfactual),
    "P5": ("V4 + All Validated (Ensemble)", agent_p5_ensemble),
}


def get_ablation_agent(model_id: str):
    if model_id not in ABLATION_MAP:
        raise ValueError(f"Unknown ablation model ID: {model_id}. Valid choices: {list(ABLATION_MAP.keys())}")
    return ABLATION_MAP[model_id]
