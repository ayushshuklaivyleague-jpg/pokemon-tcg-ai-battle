# Pokémon TCG Head-to-Head Benchmark & Promotion Audit

This document provides the definitive empirical evaluation comparing candidate planning models (**P1 through P6**) against the frozen **P0 Control Baseline (MIKE V4 Champion)** under large-sample balanced evaluation.

---

## 1. Executive Summary & Complete Promotion Matrix

Under the predefined anti-regression criteria, a candidate model enters production **only if it achieves reproducible, statistically significant superiority over the frozen V4 control baseline ($p < 0.05$) with zero contract errors**.

| Model ID | Architecture Configuration | Games Evaluated | Match Record (W-L-D) | Win Rate vs P0 (%) | 95% Wilson CI | Contract Errors | Overrides | Override Conversion | Formal Promotion Ruling |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **$P_0$** | **Frozen V4 Control Baseline** | 200 | 99 - 101 - 0 | **49.50%** | [42.65%, 56.37%] | **0** | 0 (0.0%) | N/A | **PROVEN PRODUCTION CONTROL** |
| **$P_1$** | **V4 + Threat Model** | 50 | 28 - 22 - 0 | **56.00%** | [42.31%, 68.84%] | **0** | 0 (0.0%) | N/A | **REJECTED** |
| **$P_2$** | **V4 + Counterfactual Layer** | 50 | 26 - 24 - 0 | **52.00%** | [38.51%, 65.24%] | **0** | 0 (0.0%) | N/A | **REJECTED** |
| **$P_3$** | **V4 + Threat + Counterfactual** | 50 | 26 - 24 - 0 | **52.00%** | [38.51%, 65.24%] | **0** | 1 (0.2%) | 100.0% (1/1) | **REJECTED** |
| **$P_4$** | **V4 + Combined Gating (KO + Retreat)** | 200 | 108 - 92 - 0 | **54.00%** | [47.08%, 60.77%] | **0** | 24 (1.14%) | 79.2% (19/24) | **REJECTED (CI INCLUDES PARITY)** |
| **$P_5$** | **V4 + KO Guarantee Only** | 200 | 102 - 98 - 0 | **51.00%** | [44.12%, 57.84%] | **0** | 11 (0.51%) | 90.9% (10/11) | **REJECTED (CI INCLUDES PARITY)** |
| **$P_6$** | **V4 + Safe Retreat Guard Only** | 200 | 101 - 99 - 0 | **50.50%** | [43.63%, 57.35%] | **0** | 7 (0.35%) | 42.9% (3/7) | **REJECTED (CI INCLUDES PARITY)** |

---

## 2. Granular Mechanism Isolation Analysis (P5 vs P6)

### Mechanism 1: KO Guarantee Only ($P_5$)
- **Intervention**: If an available legal attack deals lethal damage to the opponent's active Pokémon ($\ge \text{opp\_active\_hp}$), it receives absolute priority ($+50,000$).
- **Overall 200-Game Win Rate**: **51.00%** (102W - 98L - 0D)
- **95% Wilson CI**: **[44.12%, 57.84%]**
- **Win Rate by Starting Order**:
  - As Player 0 (Going 1st): **33.0%** (33/100)
  - As Player 1 (Going 2nd): **69.0%** (69/100)
- **Average Game Length**: 21.46 steps
- **Override Profile**: `ATTACH -> ATTACK` (11 overrides: 10 Wins, 1 Loss = **90.9% win correlation**).
- **Finding**: While tactical knockout execution is positive when triggered (90.9% conversion), its activation frequency (0.51% of decisions) is insufficient to move the global win rate beyond statistical parity over 200 games.

### Mechanism 2: Safe Retreat Guard Only ($P_6$)
- **Intervention**: Restricts tactical retreat to instances where active is under 1HKO danger AND bench has an energized replacement ($\ge 2$ energy).
- **Overall 200-Game Win Rate**: **50.50%** (101W - 99L - 0D)
- **95% Wilson CI**: **[43.63%, 57.35%]**
- **Win Rate by Starting Order**:
  - As Player 0 (Going 1st): **31.0%** (31/100)
  - As Player 1 (Going 2nd): **70.0%** (70/100)
- **Average Game Length**: 20.59 steps
- **Override Profile**: `RETREAT -> ATTACK` (7 overrides: 3 Wins, 4 Losses = **42.9% win correlation**).
- **Finding**: Suppressing retreat in isolation without offensive KO acceleration did not produce positive conversion (42.9% win correlation) and yielded exact parity with baseline (50.50%).

---

## 3. Controlled Evaluation Protocol Invariants

- **Simulator**: Official CABT Engine (`cg.dll` / `libcg.so`).
- **Deck Invariant**: Identical 60-card champion deck (`deck.csv`) for both players across all 1,000+ simulated matches.
- **Starting Parity**: Strict 50/50 alternating first-player allocation.
- **Opponent Invariant**: 100% of candidate games played against the frozen P0 V4 champion.
- **Legality Compliance**: 100% runtime validation of selection bounds, duplicate rejection, and bounds checks (zero tolerance for contract errors).

---

## 4. Final Promotion Ruling & Production Decision

1. **Predefined Statistical Threshold**: For a candidate model to be promoted over V4, its lower 95% Wilson confidence bound must strictly exceed 50.0% ($\text{CI}_{\text{lower}} > 50.0\%$).
2. **Evaluation Outcome**:
   - $P_5$: $\text{CI} = [44.12\%, 57.84\%]$ (Spans across parity).
   - $P_6$: $\text{CI} = [43.63\%, 57.35\%]$ (Spans across parity).
3. **Conclusion**: Neither isolated mechanism provides statistically significant improvement over the control.
4. **Final Ruling**: **Preserve Frozen MIKE V4 (`main.py`) as the champion production agent.**
