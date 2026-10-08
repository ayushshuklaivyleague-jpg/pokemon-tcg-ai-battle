# Pokémon TCG Ablation Results & Component Impact

This document records the systematic component ablation breakdown ($P_0 \dots P_6$) evaluated against the frozen **P0 Control Baseline (MIKE V4 Champion)**.

---

## 1. Complete Component Impact Breakdown

| Model | Mechanism Description | Games Evaluated | Win Rate vs V4 (%) | 95% Wilson CI | Overrides (Rate %) | Override Conversion | Formal Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **$P_0$** | **Frozen V4 Control Baseline** | 200 | **49.50%** | [42.65%, 56.37%] | 0 (0.0%) | N/A | **PROVEN PRODUCTION CONTROL** |
| **$P_1$** | **V4 + Threat Model** | 50 | **56.00%** | [42.31%, 68.84%] | 0 (0.0%) | N/A | **REJECTED** |
| **$P_2$** | **V4 + Counterfactual Layer** | 50 | **52.00%** | [38.51%, 65.24%] | 0 (0.0%) | N/A | **REJECTED** |
| **$P_3$** | **V4 + Threat + Counterfactual** | 50 | **52.00%** | [38.51%, 65.24%] | 1 (0.2%) | 100.0% (1/1) | **REJECTED** |
| **$P_4$** | **V4 + Combined Gating (KO + Retreat)** | 200 | **54.00%** | [47.08%, 60.77%] | 24 (1.14%) | 79.2% (19/24) | **REJECTED (CI INCLUDES PARITY)** |
| **$P_5$** | **V4 + KO Guarantee Only** | 200 | **51.00%** | [44.12%, 57.84%] | 11 (0.51%) | 90.9% (10/11) | **REJECTED (CI INCLUDES PARITY)** |
| **$P_6$** | **V4 + Safe Retreat Guard Only** | 200 | **50.50%** | [43.63%, 57.35%] | 7 (0.35%) | 42.9% (3/7) | **REJECTED (CI INCLUDES PARITY)** |

---

## 2. Granular Mechanism Isolation Findings

### P5: KO Guarantee Only (200 Games)
- **Hypothesis**: Absolute priority for attacks that deal lethal damage to opponent active ($\ge \text{opp\_active\_hp}$).
- **Record**: 102W - 98L - 0D (**51.00% Win Rate**, 95% CI: `[44.12%, 57.84%]`).
- **Starting Order**:
  - Player 0 (1st): 33.0% (33/100)
  - Player 1 (2nd): 69.0% (69/100)
- **Overrides**: 11 `ATTACH -> ATTACK` (10 Wins, 1 Loss = **90.9% conversion**).
- **Takeaway**: Highly accurate local overrides, but low overall frequency (0.51%) limits aggregate match impact.

### P6: Safe Retreat Guard Only (200 Games)
- **Hypothesis**: Suppress premature retreats unless active is doomed AND bench has an energized replacement ($\ge 2$ energy).
- **Record**: 101W - 99L - 0D (**50.50% Win Rate**, 95% CI: `[43.63%, 57.35%]`).
- **Starting Order**:
  - Player 0 (1st): 31.0% (31/100)
  - Player 1 (2nd): 70.0% (70/100)
- **Overrides**: 7 `RETREAT -> ATTACK` (3 Wins, 4 Losses = **42.9% conversion**).
- **Takeaway**: Suppressing retreat in isolation without active KO acceleration produces parity with control.

---

## 3. Anti-Regression Promotion Verdict

1. **Statistical Criterion**: Predefined threshold requires $\text{CI}_{\text{lower}} > 50.0\%$.
2. **Outcome**: All candidate models ($P_1 \dots P_6$) have 95% confidence intervals that cross the 50.0% baseline threshold.
3. **Verdict**: **Preserve Frozen MIKE V4 (`main.py`) as the champion production agent.**
