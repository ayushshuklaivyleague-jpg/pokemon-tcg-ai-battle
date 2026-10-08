# `H_ATTACK_SELECT` Experimental Benchmark Results & Statistical Report

**Benchmark Timestamp**: 2026-08-30  
**Target Hypothesis**: `H_ATTACK_SELECT` (Dynamic High-HP Attack Selection on Mega Abomasnow ex)  
**Control Baseline**: Frozen MIKE V4 Champion (`main.py` / P0 Control)  
**Evaluation Protocol**: 200 balanced head-to-head matches (100 as Player 0, 100 as Player 1) with 50/50 starting-order distribution.

---

## 1. Executive Summary

| Metric | Result | Evaluation vs Frozen V4 Control |
| :--- | :--- | :--- |
| **Match Record (W-L-D)** | **103W – 97L – 0D** | 200 balanced games completed |
| **Observed Win Rate** | **51.50%** | Stochastic variance around 50% baseline |
| **95% Wilson Confidence Interval** | **[44.61%, 58.33%]** | **Spans 50.0%** (No statistically significant delta) |
| **Starting-Order: Player 0 (1st)** | **51.00%** (51 / 100) | Balanced |
| **Starting-Order: Player 1 (2nd)** | **52.00%** (52 / 100) | Balanced |
| **Total Decision Points Logged** | **3,413 decisions** | 100% audited in `h_attack_decision_audit.csv` |
| **Multi-Attack Abomasnow States** | **89 / 3,413 (2.61%)** | Both 1046 & 1047 simultaneously legal |
| **H_ATTACK Overrides Triggered** | **16 / 3,413 (0.47%)** | Overrides executed in 8 distinct games |
| **Override Win Conversion** | **56.25%** (9 Wins / 7 Losses) | Favorable decision-level conversion |
| **Contract / Runtime Errors** | **0** (100% legal) | Zero engine contract violations |
| **Fallback Activations** | **0** (0.00%) | Zero unhandled exceptions |
| **Average Match Length** | **28.57 steps** | Comparable to V4 baseline (27.95 steps) |
| **Official Determination** | **INSUFFICIENT EVIDENCE / STATISTICAL PARITY** | **Does Not Meet Promotion Threshold** |

---

## 2. Hypothesis Definition & Rule Specification

### The Hypothesis:
In `MAIN` / `ATTACK` contexts, when Active Pokémon is `Mega Abomasnow ex` and both Attack `1046` (RNG discard attack, 2 Energy, up to 350 damage) and Attack `1047` (Flat 200 dmg, 3 Energy) are legal:
1. **If Opponent Active HP $> 200$ AND Player Deck Count $> 6$**:
   - Prefer Attack `1046` ($+10,000$ priority bonus) to pursue the 1-Hit Knockout against high-HP targets (such as opponent Mega Abomasnow ex).
2. **If Opponent Active HP $\le 200$ OR Player Deck Count $\le 6$**:
   - Prefer Attack `1047` ($+10,000$ priority bonus) to preserve deck integrity and secure guaranteed lethal damage.

### Strict Isolation Invariants:
- `main.py` (MIKE V4 Champion) remains **100% FROZEN**.
- `submission_notebook.ipynb` remains **100% FROZEN**.
- Zero changes to other action types (`ATTACH`, `PLAY`, `EVOLVE`, `RETREAT`).
- Zero changes to other Pokémon attacks (`Kyogre`, `Snover`).
- Zero threat modeling, counterfactuals, or bench anchors.

---

## 3. Action Transition & Override Breakdown

Every single override transitioned from V4's default Attack 1047 to H_ATTACK's Attack 1046 when confronting $>200$ HP targets:

| Original V4 Action | H_ATTACK Override Action | Trigger Condition | Override Count | Decision Wins | Decision Losses | Conversion Rate (%) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `ATTACK_1047` (Flat 200 Dmg) | `ATTACK_1046` (RNG up to 350 Dmg) | Opponent HP $> 200$ & Deck $> 6$ | **16** | 9 | 7 | **56.25%** |

### Breakdown by Match:
- **Game 011**: 1 override $\to$ Loss
- **Game 039**: 2 overrides $\to$ Loss
- **Game 054**: 1 override $\to$ Loss
- **Game 140**: 5 overrides $\to$ **Win**
- **Game 150**: 2 overrides $\to$ **Win**
- **Game 169**: 2 overrides $\to$ Loss
- **Game 181**: 2 overrides $\to$ **Win**
- **Game 200**: 1 override $\to$ Loss
- **Match-Level Record in Override Games**: 3 Wins / 5 Losses (37.50%).

---

## 4. Statistical Discipline Assessment

- **Observed Win Rate**: 51.50% (103W – 97L – 0D).
- **Wilson 95% Confidence Interval**: $[44.61\%, 58.33\%]$.
- **Promotion Evaluation**:
  - The threshold for promotion is Wilson $\text{CI}_{\text{lower}} > 50.0\%$.
  - With $\text{CI}_{\text{lower}} = 44.61\% \le 50.0\%$, there is **no statistically significant proof of superiority** over the frozen V4 champion.
  - The observed $51.50\%$ win rate reflects normal stochastic self-play variance.
- **Verdict**: **REJECT PROMOTION**. Keep production `main.py` frozen.
