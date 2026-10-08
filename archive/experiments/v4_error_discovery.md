# V4 Error Discovery & Strategic Weakness Analysis

This document presents the systematic discovery of V4 failure modes mined from a large-scale corpus of **6,482 state decision records across 300 complete matches** under the official CABT engine.

---

## 1. Corpus Summary Statistics

- **Total Simulated Games**: 300 (Balanced 50/50 starting order)
- **Total Decision States Logged**: **6,482**
- **Decisions with Multiple Legal Options**: **5,379 (83.0%)**
- **Player 0 (Going 1st) Wins**: 84 (28.0%)
- **Player 1 (Going 2nd) Wins**: 216 (72.0%)
- **Average Active HP in Winning Games**: **141.6 HP** vs **83.4 HP in Losing Games**
- **Average Bench Count in Winning Games**: **0.45 Pokémon** vs **0.25 Pokémon in Losing Games** (+80% bench density in wins)

---

## 2. Ranked V4 Failure Classes (By Frequency & Match Impact)

| Rank | Cluster ID | Failure Class Name | Occurrences | Frequency (%) | Loss Rate (%) | Strategic Impact | Evidence Strength |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **`FC-01`** | **Zero-Bench Vulnerability Window** | 1,149 | **17.73%** | **48.7%** | **CRITICAL** | **VERY STRONG** (6,482 rows) |
| **2** | **`FC-02`** | **Suboptimal Search Selection in `TO_HAND`** | 616 | **9.50%** | **52.4%** | **HIGH** | **STRONG** (616 decisions) |
| **3** | **`FC-03`** | **Delayed Knockout Execution (`ATTACH -> ATTACK`)** | 58 | **0.89%** | **6.9%** (When unexploited) | **HIGH** | **VERY STRONG** (58 instances) |
| **4** | **`FC-04`** | **Active Energy Over-Saturation ($\ge 4$ Energy)** | 31 | **0.48%** | **64.5%** | **MEDIUM-HIGH** | **MODERATE** (31 instances) |
| **5** | **`FC-05`** | **Uncoordinated Low-HP Defensive Retreat** | 24 | **0.37%** | **58.3%** | **MEDIUM** | **MODERATE** (24 instances) |

---

## 3. In-Depth Failure Mode Taxonomy

### `FC-01`: Zero-Bench Vulnerability Window (17.73% Frequency)
- **State Pattern**: Player operates during mid-game (Turn 3+) with **0 benched Pokémon**.
- **Root Cause**: V4's action scoring during setup and early turns does not place a hard baseline bonus on establishing at least 1 bench anchor.
- **Consequence**: When the active Pokémon takes heavy burst damage and is knocked out, the player suffers an **instant match loss by bench exhaustion**, despite having cards and energy in hand.
- **Optimal Alternative**: Guarantee benching of at least 1 basic Pokémon during setup/main before performing discretionary energy attachments.

### `FC-02`: Search Target Selection in `TO_HAND` Context (9.50% Frequency)
- **State Pattern**: `TO_HAND` selection prompts (e.g. Poké Ball, search trainers) where multiple cards can be retrieved from deck.
- **Root Cause**: V4 uses a static card preference ordering that does not adjust for current board needs (e.g., retrieving another energy when 0 basic Pokémon are on the bench, or retrieving a Basic when a Stage 1 evolution is needed to survive).
- **Optimal Alternative**: Dynamically weight search targets: prioritize Basic Pokémon if `bench_count == 0`, prioritize Evolution if Active is threatened, prioritize Energy if active energy is 0.

### `FC-03`: Delayed Lethal Knockout Execution (0.89% Frequency)
- **State Pattern**: Opponent active has $\le 40\text{ HP}$ (in 1HKO range) and legal attack is executable.
- **Root Cause**: V4's tier scoring gives `ATTACH` a baseline score of $35,000 - 41,000$, while standard attacks have scores of $18,000 - 22,000$. V4 attaches energy first, delaying the prize knockout until the attack step or next turn.
- **Optimal Alternative**: Unconditional priority ($+50,000$) for lethal attacks that secure an immediate prize card.

---

## 4. Synthesis & Research Directions for P9

Rather than tweaking low-impact weights affecting $<1\%$ of states, future research must target **`FC-01` (Zero-Bench Vulnerability, 17.73%)** and **`FC-02` (`TO_HAND` Search Prioritization, 9.50%)**, which collectively represent **over 27% of all game decisions**.
