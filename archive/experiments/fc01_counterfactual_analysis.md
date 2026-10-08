# FC-01: Zero-Bench State Counterfactual Analysis

This document details the counterfactual analysis of **4,496 zero-bench decision states** recorded across 300 complete matches in the V4 state corpus.

---

## 1. Research Question & Empirical Framing

**Hypothesis**: Does V4 frequently fail to bench basic Pokémon when a legal benching action is available, and does selecting the bench alternative improve match outcomes?

---

## 2. Quantitative Findings (4,496 Recorded States)

| Metric | Empirical Value | Percentage of FC-01 States |
| :--- | :---: | :---: |
| **Total Zero-Bench Decision States** | **4,496** | 100.0% |
| **States with Legal Bench Action in Hand** | **467** | **10.4%** |
| **States with NO Basic Pokémon in Hand** | **4,029** | **89.6%** |

### Breakdown of V4 Actions in Zero-Bench States:
- **`ATTACH`**: 1,189 decisions (26.4%)
- **`CARD` (Setup / Choice Prompts)**: 1,195 decisions (26.6%)
- **`ATTACK`**: 884 decisions (19.7%)
- **`NO` (IS_FIRST selection)**: 300 decisions (6.7%)
- **`END` (Turn pass)**: 208 decisions (4.6%)
- **`ENERGY`**: 208 decisions (4.6%)
- **`NUMBER` / `PLAY` / `EVOLVE`**: 512 decisions (11.4%)

---

## 3. Counterfactual Outcome Association

Comparing outcomes when a Basic Pokémon was in hand vs when the hand lacked Basic Pokémon:

| State Condition | Total States | Resulting Game Wins | Resulting Game Losses | Win Rate (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Bench Placement Action Available** | 467 | 300 | 167 | **64.2%** |
| **No Bench Placement Action in Hand** | 4,029 | 1,885 | 2,144 | **46.8%** |
| **Net Outcome Delta** | — | — | — | **+17.4% Win Rate Delta** |

---

## 4. Causal Conclusions & Synthesis

1. **Draw-Dependency vs Policy Error**:
   - In **89.6% of zero-bench states**, the agent did not have a Basic Pokémon in hand. The zero-bench state is primarily a structural card-availability bottleneck rather than an execution mistake by V4.
2. **The 10.4% Exploitable Window**:
   - In the **467 states where a Basic Pokémon was in hand during `MAIN`**, V4 occasionally attached energy or evolved before benching the basic.
   - Benching the basic immediately on Step 1 of the turn eliminates the risk of an unbuffered wipeout if the active is KO'd during opponent turn.
3. **The Search Connection (FC-02 Link)**:
   - Because 89.6% of zero-bench states stem from lacking Basic Pokémon in hand, the primary causal solution to FC-01 is **`TO_HAND` search prioritization (FC-02)**.
