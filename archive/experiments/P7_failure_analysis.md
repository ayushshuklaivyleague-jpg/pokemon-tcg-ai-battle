# P7 Post-Hoc Failure Analysis & Losing Overrides Audit

This document isolates and audits all losing overrides produced by the P7 all-components integration.

## 1. Losing Override Cases

Total Losing Overrides in 200 Games: **10** (out of 27 total overrides, 63.0% win rate).

| Game | Step | Context | State (My HP / Opp HP / My Energy / Opp Energy) | V4 Action | P7 Action | Primary Driver | Component Deltas (KO / Retreat / Threat / CF) | Score Delta |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 53 | 18 | `MAIN` | 20HP / 150HP / 3E / 1E | `RETREAT` | `ATTACK` | `COUNTERFACTUAL` | 0 / 0 / 0 / 800 | 3904.3 |
| 64 | 15 | `MAIN` | 50HP / 60HP / 3E / 2E | `ATTACH` | `ATTACH` | `COUNTERFACTUAL` | 0 / 0 / 2000 / 3000 | 400.0 |
| 64 | 28 | `MAIN` | 50HP / 150HP / 3E / 0E | `ATTACH` | `ATTACH` | `COUNTERFACTUAL` | 0 / 0 / 2000 / 3000 | 400.0 |
| 68 | 28 | `MAIN` | 50HP / 350HP / 3E / 0E | `ATTACH` | `ATTACH` | `COUNTERFACTUAL` | 0 / 0 / 2000 / 3000 | 400.0 |
| 68 | 37 | `MAIN` | 50HP / 320HP / 3E / 1E | `ATTACH` | `ATTACH` | `COUNTERFACTUAL` | 0 / 0 / 2000 / 3000 | 1100.0 |
| 68 | 38 | `MAIN` | 50HP / 320HP / 3E / 1E | `ATTACK` | `RETREAT` | `SAFE_RETREAT` | 0 / 15000 / 0 / 5000 | 2095.5 |
| 72 | 30 | `MAIN` | 10HP / 30HP / 5E / 2E | `ATTACH` | `ATTACK` | `KO_GUARANTEE` | 50000 / 0 / 0 / 5000 | 28804.5 |
| 90 | 14 | `MAIN` | 90HP / 120HP / 3E / 2E | `ATTACH` | `ATTACH` | `COUNTERFACTUAL` | 0 / 0 / 2000 / 3000 | 400.0 |
| 169 | 19 | `MAIN` | 20HP / 150HP / 3E / 1E | `RETREAT` | `ATTACK` | `COUNTERFACTUAL` | 0 / 0 / 0 / 800 | 3904.3 |
| 175 | 21 | `MAIN` | 20HP / 150HP / 3E / 1E | `RETREAT` | `ATTACK` | `COUNTERFACTUAL` | 0 / 0 / 0 / 800 | 3904.3 |

---

## 2. Qualitative Root Cause Analysis

1. **Harmful Interactions**: When multiple heuristic components combine (e.g. Counterfactual + Threat), minor positive evaluation deltas can occasionally compound to shift priority away from stable baseline actions in marginal mid-game board states.
2. **Knockout Resilience**: The KO Guarantee component remains the single most reliable driver (high win conversion), while counterfactual short-horizon shifts carry higher variance.
3. **Recommendation**: Gating should be tightened on counterfactual heuristic signals to prevent non-decisive action swaps.
