# `H_DISCARD` Experimental Benchmark Results & Statistical Report

**Benchmark Timestamp**: 2026-08-30  
**Target Hypothesis**: `H_DISCARD` (Resource-Preservation in `DISCARD_ENERGY` / Discard Prompts)  
**Control Baseline**: Frozen MIKE V4 Champion (`main.py` / P0 Control)  
**Evaluation Protocol**: 200 balanced head-to-head matches (100 as Player 0, 100 as Player 1) with 50/50 starting-order distribution.

---

## 1. Executive Summary

| Metric | Result | Evaluation vs Frozen V4 Control |
| :--- | :--- | :--- |
| **Match Record (W-L-D)** | **105W – 95L – 0D** | 200 balanced games completed |
| **Observed Win Rate** | **52.50%** | Stochastic variance around 50% baseline |
| **95% Wilson Confidence Interval** | **[45.60%, 59.31%]** | **Spans 50.0%** (No statistically significant delta) |
| **Starting-Order: Player 0 (1st)** | **47.00%** (47 / 100) | Normal 1st-turn tempo disadvantage in deck |
| **Starting-Order: Player 1 (2nd)** | **58.00%** (5

8 / 100) | Normal 2nd-turn attack advantage |
| **Total Decision Points Logged** | **3,346 decisions** | 100% audited in `h_discard_decision_audit.csv` |
| **Simultaneous Candidate Prompts** | **0 / 3,346 (0.00%)** | Basic Energy + Draw Supporter never co-occur |
| **H_DISCARD Overrides Triggered** | **0 / 3,346 (0.00%)** | Rule remained dormant (untriggered) |
| **Override Win Conversion** | **N/A** (0 overrides) | N/A |
| **Contract / Runtime Errors** | **0** (100% legal) | Zero engine contract violations |
| **Fallback Activations** | **0** (0.00%) | Zero unhandled exceptions |
| **Average Match Length** | **27.95 steps** | Identical to V4 baseline (27.95 steps) |
| **Official Determination** | **EXACT PARITY / INACTIVE HYPOTHESIS** | **Insufficient Evidence of Improvement** |

---

## 2. Hypothesis Definition & Rule Implementation

### The Hypothesis:
In `DISCARD_ENERGY` (and discard prompts), if **Basic Water Energy** and either **Waitress** or **Lillie's Determination** are simultaneously legal discard candidates, prefer discarding the Basic Water Energy.
*Constraint*: This rule applies **ONLY** when both resource categories are simultaneously legal candidates.

### Strict Isolation Invariants:
- `main.py` (MIKE V4 Champion) is **FROZEN** and untouched.
- `submission_notebook.ipynb` is **FROZEN** and untouched.
- No modifications were made to `MAIN` scoring, `TO_HAND` search, attack selection, retreat logic, KO logic, threat model, counterfactual logic, or energy attachment logic.

---

## 3. Structural Discovery & Root-Cause Audit

### Why `H_DISCARD` Remained Dormant (0 Overrides across 3,346 Decisions):

1. **Engine Selection Context Isolation**:
   - `DISCARD_ENERGY` is prompted exclusively when paying retreat costs or activating attack discard costs (e.g. Kyogre's retreat or attack).
   - In `DISCARD_ENERGY`, the engine only presents attached energy cards located on the Active or Bench Pokémon (`AreaType.ACTIVE` or `AreaType.BENCH`).
   - Non-energy cards (such as Draw Supporters `Waitress` or `Lillie's Determination`) reside exclusively in the player's Hand (`AreaType.HAND`) and are never attached as Energy to Pokémon.

2. **Resolution Artifact in Prior Offline Analysis**:
   - The prior offline analysis (`discard_energy_counterfactuals.csv`) reported 182 decisions where Waitress/Lillie appeared alongside Energy.
   - Investigation revealed this was an artifact of `v4_card_from_option` fallback logic: when an option had `area == AreaType.ACTIVE` (4) and `index == 0`, `v4_card_from_option` checked `player.hand[0]`, misidentifying the attached energy as the first card in hand (`Waitress` or `Lillie`).
   - In actual live gameplay, attached energies are 100% `Basic {W} Energy` (Card ID 3). Hand cards are never legal options in `DISCARD_ENERGY`.

3. **Absence of Hand-Discard Cards in Deck**:
   - The current deck archetype contains 35 Basic Water Energies, Snover, Abomasnow, Mega Abomasnow ex, Kyogre, Mega Signal, Cyrano, Waitress, and Lillie's Determination.
   - The deck contains no `Ultra Ball`, `Professor's Research`, or other hand-discard effects that discard cards from hand.

---

## 4. Statistical Discipline Assessment

- **Observed Win Rate**: 52.50% (105W - 95L).
- **Wilson 95% Confidence Interval**: $[45.60\%, 59.31\%]$.
- **Evaluation Criteria**:
  - Wilson $\text{CI}_{\text{lower}} = 45.60\% \le 50.0\%$.
  - Number of overrides = 0.
  - The observed $52.5\%$ win rate is entirely attributable to standard stochastic self-play variance (matching V4 vs V4 baseline distributions).
- **Verdict**: **No evidence of performance improvement over frozen V4 control**.
- **Recommendation**: Do not promote `H_DISCARD` to production. MIKE V4 Champion remains the uncontested production standard.
