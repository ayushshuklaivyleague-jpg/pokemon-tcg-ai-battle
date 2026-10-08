# P9 Hypothesis Validation & Next Experimental Roadmap

This document synthesizes the findings from `fc01_counterfactual_analysis.md`, `fc02_search_analysis.md`, and the 5,112-row dataset [`p9_legal_counterfactuals.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/p9_legal_counterfactuals.csv).

---

## 1. Synthesis of Causal Evidence

| Cluster | Hypothesis Description | Recorded Frequency | Legal Counterfactual Availability | Observed Causal Link | Validation Status |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **`FC-01`** | Zero-Bench Vulnerability | 4,496 states (69.4%) | 467 states had Basic in hand (10.4%) | 89.6% of zero-bench states lack Basic in hand; bench placement when available gives **+17.4% win delta**. | **SUPPORTED (Draw-Dependent)** |
| **`FC-02`** | `TO_HAND` Search Prioritization | 616 states (9.5%) | 100% of search prompts have choices | 63.8% of searches occur with an empty bench. Searching Basic directly fixes FC-01 deficit. | **STRONGLY SUPPORTED** |

---

## 2. Structured P9 Experimental Roadmap

In accordance with the experimental design protocol, candidate mechanisms will not be combined prematurely:

### Phase 1: Isolated Evaluation of Hypothesis H1 ($P_{9\text{-H1}}$)
- **Mechanism**: **Dynamic Bench Placement Priority (Targeting FC-01)**.
  - In `MAIN` context, whenever `my_bench_count == 0` and a legal Basic Pokémon is in hand, elevate bench placement score to ensure it is deployed before optional actions.
- **Protocol**: 200 balanced matches vs Frozen $P_0$ V4 Control.

### Phase 2: Isolated Evaluation of Hypothesis H2 ($P_{9\text{-H2}}$)
- **Mechanism**: **State-Adaptive Search Resolution (Targeting FC-02)**.
  - In `TO_HAND` search prompts:
    - If `my_bench_count == 0`: Elevate Basic Pokémon search score ($+20,000$).
    - If `my_active_hp <= 50` and Basic in play: Elevate Evolution search score ($+15,000$).
    - If `my_active_energy == 0`: Elevate Energy search score ($+10,000$).
- **Protocol**: 200 balanced matches vs Frozen $P_0$ V4 Control.

### Phase 3: Combined Evaluation of Hypothesis H3 ($P_{9\text{-H3}}$)
- **Condition**: Executed **only if** both $P_{9\text{-H1}}$ and $P_{9\text{-H2}}$ demonstrate positive empirical win deltas and zero regressions under isolated evaluation.

---

## 3. Invariant & Promotion Governance

- Production code ([`main.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/main.py)) and baseline notebooks remain **100% frozen**.
- Promotion threshold: $\text{CI}_{\text{lower}} > 50.0\%$ under 200+ balanced games with zero contract errors.
