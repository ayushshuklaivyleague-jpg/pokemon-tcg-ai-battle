# HYBRID_STAGE_3 Pre-Benchmark Diff Report

## 1. Executive Summary
- **Candidate Module**: `hybrid_v4_sol_stage3.py`
- **Control Baseline**: Frozen `codex_sol_eclipse_alakazam.py` (Hilda = 3000)
- **Deck Invariance**: 100% Byte-for-Byte Identical (60 cards)
- **Genome Invariance**: 68 / 69 parameters identical; 1 parameter modified (`hilda: 3000 → 3150`)
- **Search Status**: Strictly DISABLED (`ENABLE_SEARCH = False`, 0 search invocations)
- **Overrides Status**: Strictly DISABLED (`ENABLE_ADVANCED_OVERRIDES = False`)
- **Layer 1 Safety**: MIKE V4 `selection_contract` + `legal_selection` active.

---

## 2. Parameter Comparison Table

| Parameter | Control Baseline (`codex_sol_eclipse_alakazam.py`) | Candidate (`hybrid_v4_sol_stage3.py`) | Status |
| :--- | :--- | :--- | :--- |
| **`hilda`** | **3000** | **3150** | **MODIFIED (Validated)** |
| **`xerosic`** | **3250** | **3250** | **IDENTICAL (Preserved)** |
| **`dawn`** | **3100** | **3100** | **IDENTICAL (Preserved)** |
| **All Other 66 Weights** | Standard Sol Baked Genome | Standard Sol Baked Genome | **IDENTICAL (Preserved)** |

---

## 3. Layer Status Checklist

- [x] **Layer 1 (Contract & Safety)**: Active (`selection_contract`, `legal_selection`, `safe_get`, `safe_list`).
- [x] **Layer 2 (State Representation)**: Active (`field_counts`, `hand_counts`, `discard_counts`, `op_has_ex`, `safe_draws`).
- [x] **Layer 3 (Deterministic Heuristics)**: Active (`heuristic_scores`, `_post_pick`, `_courage_teleportation_guard`).
- [x] **Layer 4 (Validated Genome)**: Active (`hilda = 3150`, `xerosic = 3250`, `dawn = 3100`).
- [x] **Layer 5 (Search Layer)**: **STRICTLY DISABLED** (`ENABLE_SEARCH = False`).
- [x] **Layer 6 (Advanced Overrides)**: **STRICTLY DISABLED** (`ENABLE_ADVANCED_OVERRIDES = False`).
