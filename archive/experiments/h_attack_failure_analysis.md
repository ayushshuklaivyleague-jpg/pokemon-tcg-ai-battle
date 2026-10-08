# `H_ATTACK_SELECT` Failure Analysis & Statistical Post-Mortem

**Document Timestamp**: 2026-08-30  
**Target Investigation**: Root-cause analysis of why `H_ATTACK_SELECT` failed to exceed the $50.0\%$ Wilson confidence lower bound in 200 balanced matches.

---

## 1. Executive Summary

`H_ATTACK_SELECT` successfully eliminated an arbitrary ID-ordering tiebreaker in V4 (`1047 > 1046`) and correctly selected the high-damage RNG discard attack (`1046`) against $350$ HP targets in 16 decisions across 8 games.

However, the 200-game benchmark produced:
- **Win Rate**: $51.50\%$ (103W – 97L – 0D)
- **95% Wilson Confidence Interval**: $[44.61\%, 58.33\%]$
- **Promotion Threshold**: Wilson $\text{CI}_{\text{lower}} > 50.0\%$ $\to$ **FAILED (44.61% $\le$ 50.0%)**.

---

## 2. In-Depth Root Cause Analysis

### Factor 1: Low Global Trigger Density (Dilution Effect)
- In a 200-game match suite (3,413 total decisions), Mega Abomasnow ex achieved $\ge 3$ attached energy with both attacks legal in **89 decisions (2.61% of all decisions)**.
- Of those 89 decisions, the opponent was a $>200$ HP target in only **16 decisions (0.47% of all decisions / 8 out of 200 games = 4.0% of matches)**.
- In 96.0% of matches (192 / 200 games), the rule never triggered because matches were decided by Snover/Kyogre early tempo before a 3-energy Mega Abomasnow mirror match occurred.
- Consequently, even a strong tactical advantage in 4% of games is statistically diluted across the 200-game sample size.

### Factor 2: Variance in the RNG Discard Attack (Attack 1046)
- Attack 1046 discards the top 6 cards of the deck and deals $50\times$ Water Energies discarded.
- While the expected value is $3.5 \times 50 = 175$ damage (and up to $350$ damage), its discrete probability distribution has inherent variance:
  - Discarding 7 Water Energies: Impossible (max 6 cards).
  - Discarding 6 Water Energies: Deals $300$ damage ($50$ damage short of a 1-hit KO on $350$ HP without Belt).
  - Discarding 7 Water Energies (with Belt): Deals $350$ damage ($1$-hit KO).
  - Discarding $\le 4$ Water Energies: Deals $\le 200$ damage (same or worse than Attack 1047's guaranteed $200$ flat damage, but costs 6 cards from the deck).
- In several override matches (e.g. Games 011, 039, 169), Attack 1046 failed to roll the required 7-energy threshold for a pure 1-shot KO, resulting in opponent survival while depleting the player's deck.

---

## 3. Methodological & Strategic Insights

1. **V4's Flat Damage is a Robust Baseline**:
   - Attack 1047's flat 200 damage is deterministic, reliable, and carries zero deck attrition risk.
   - Forcing Attack 1046 provides a ceiling of 300–350 damage, but introduces variance and accelerates deck exhaustion.
2. **Strict Statistical Discipline Verified**:
   - Despite an observed win rate $>50\%$ ($51.50\%$) and a favorable decision win conversion ($56.25\%$), the Wilson confidence interval ($[44.61\%, 58.33\%]$) demonstrates that the difference from control is statistically insignificant.
   - Without $\text{CI}_{\text{lower}} > 50.0\%$, modifying production code would violate sound engineering standards.

---

## 4. Final Verdict & Invariant Preservation

- **Promotion Decision**: **REJECTED**.
- **Production State**: `main.py` (MIKE V4 Champion) remains **FROZEN**.
- **Notebook State**: `submission_notebook.ipynb` remains **FROZEN**.
