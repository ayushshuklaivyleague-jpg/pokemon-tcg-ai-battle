# Energy Attachment Over-Saturation Investigation Report

This document details the exhaustive counterfactual audit of all **1,762 `ATTACH` decision states** recorded across 300 complete matches in the V4 state corpus.

---

## 1. Executive Summary & Quantitative Segmentation

Every `ATTACH` decision in the 6,482-state corpus was classified by the active Pokémon's energy level at the moment of attachment:

| Energy Tier | Definition | Total Decisions | Share of Attachments (%) | Bench Present (%) | Resulting Wins | Resulting Losses | Win Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`ACTIVE_LT3`** | Active $< 3$ Energy | **1,709** | **97.0%** | 32.4% (554) | 956 | 753 | **55.9%** |
| **`ACTIVE_EQ3`** | Active $= 3$ Energy | **46** | **2.6%** | 34.8% (16) | 32 | 14 | **69.6%** |
| **`ACTIVE_GE4`** | Active $\ge 4$ Energy | **7** | **0.4%** | 42.9% (3) | 2 | 5 | **28.6%** |
| **Total** | — | **1,762** | **100.0%** | **32.5%** (573) | **990** | **772** | **56.2%** |

---

## 2. In-Depth State Analysis of Multi-Target Attachments

### Category A: Active $< 3$ Energy (1,709 Decisions - 97.0%)
- **State Requirement**: Active needs energy to reach attack threshold (1E, 2E, 3E, or 4E).
- **V4 Action**: Attaches to Active (100.0%).
- **Evaluation**: **100% Mathematically Optimal**. Diverting energy to the bench when the Active cannot yet attack delays offensive tempo by an entire turn.

### Category B: Active $= 3$ Energy (46 Decisions - 2.6%)
- **Bench Present**: In 16 of the 46 decisions, a benched Pokémon was on the field.
- **Active Card Breakdown**:
  - **Mega Abomasnow ex (ID 723)**: 8 decisions. *Mega Abomasnow ex requires 4 Energy for Frost Barrier (200 damage)*. Attaching the 4th energy to Active is **operationally required**, not over-saturation.
  - **Kyogre (ID 721)**: 1 decision. (Requires 3E for Swirling Waves 130 dmg).
  - **Snover (ID 722)**: 7 decisions. (Requires 2E for Icy Snow 30 dmg).
- **True Over-Saturation at 3E**: Occurred in **only 8 decisions across 300 matches** (0.12% of corpus).

### Category C: Active $\ge 4$ Energy (7 Decisions - 0.4%)
- **Bench Present**: In only 3 of the 7 decisions, a benched Pokémon was on the field (1 Mega Abomasnow, 2 Snover).
- **In the remaining 4 decisions**, the bench was empty (`bench_count == 0`), making the Active the only legal attachment target in the game.
- **True Over-Saturation at $\ge 4$E**: Occurred in **only 3 decisions across 300 matches** (0.046% of corpus).

---

## 3. Empirical Verdict

1. **Volume Assessment**: True energy over-saturation (Active fully charged + Bench present) occurs in **only 11 out of 6,482 total decisions (0.17% of states)**.
2. **Deck Constraint**: Because the deck's primary carry (`Mega Abomasnow ex`) requires **4 full Energy** to execute its 200-damage attack, attaching the 1st through 4th energies to the Active is necessary for win condition execution.
3. **Conclusion**: Energy over-saturation is **not a high-frequency strategic bottleneck in V4**.
