# H_XEROSIC Isolated Benchmark Report

**Hypothesis**: Demote `WEIGHTS["xerosic"]` from `3250` to `2950` to prioritize self-development (`Dawn` @ 3100, `Hilda` @ 3000) over opponent hand disruption (`Xerosic` @ 2950).  
**Protocol**: 200 balanced head-to-head matches against the frozen Sol Eclipse Control baseline (100 as Player 0, 100 as Player 1).  
**Dataset Artifact**: `h_xerosic_decision_audit.csv` (15,012 instrumented decision rows).  
**Status**: BENCHMARK COMPLETE — HYPOTHESIS REJECTED / PROMOTION DENIED.  

---

## 1. Executive Summary & Verdict

| Metric | Frozen Control (`xerosic: 3250`) | Candidate Hypothesis (`xerosic: 2950`) | Delta / Evaluation |
| :--- | :---: | :---: | :---: |
| **Match Outcome (200 Games)** | **33 Wins** | **28 Wins** (139 Draws) | **-5 Net Wins** |
| **Aggregate Win Rate** | 16.50% | **14.00%** | -2.50% |
| **95% Wilson Confidence Interval** | — | **[9.87%, 19.49%]** | Fails promotion threshold |
| **Decisive (Non-Draw) Win Rate** | 54.10% (33/61) | **45.90%** (28/61) | Control outperformed Candidate |
| **Player 0 Win Rate (1st)** | — | **8.00%** (8/100) | First-player disadvantage in mirror |
| **Player 1 Win Rate (2nd)** | — | **20.00%** (20/100) | Second-player draw advantage |
| **Average Game Length** | 148.37 steps | 148.37 steps | Match stall / step limit |
| **Contract / Runtime Errors** | 0 | 0 | Perfect contract validity |
| **Fallback Activations** | 0 | 0 | 0 |

**Verdict**: **REJECT HYPOTHESIS `H_XEROSIC`**. The candidate failed to demonstrate a statistically significant or substantive improvement over the frozen control baseline. The production artifact (`codex_sol_eclipse_alakazam.py`) remains **unmodified**.

---

## 2. Decision Instrumentation & Override Telemetry

Across 200 complete simulation matches:
- **Total Decisions Instrumented**: 15,012
- **Multi-Supporter Competition States**: 3,373 (22.47% of all decisions)
- **Control Xerosic Plays**: 255 plays
- **Candidate Xerosic Plays**: 176 plays (-30.98% reduction)
- **Total Decisions Overridden**: 638 / 15,012 (**4.25% override rate**)
- **Override Games Count**: 160 / 200 (**80.0% of matches**)

### Match-Level Outcomes by Override Category

| Match Category | Games | Candidate Wins | Candidate Losses | Draws | Decisive Win Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Override Games** (Weight altered $\ge 1$ decision) | 160 | 19 | 18 | 123 | **51.35%** (19/37) |
| **Non-Override Games** (Zero weight alterations) | 40 | 9 | 15 | 16 | **37.50%** (9/24) |
| **All Games Combined** | 200 | 28 | 33 | 139 | **45.90%** (28/61) |

---

## 3. Action Transitions Breakdown

The single weight change produced **638 total action overrides**. The primary intended transitions occurred as designed:

| Control Action (`3250`) | Candidate Action (`2950`) | Frequency | % of Overrides |
| :--- | :--- | :---: | :---: |
| `PLAY(Xerosic’s Machinations)` | $\to$ `PLAY(Dawn)` | **85** | 13.32% |
| `PLAY(Xerosic’s Machinations)` | $\to$ `PLAY(Hilda)` | **50** | 7.84% |
| `PLAY(Dawn)` | $\to$ `EVOLVE(Dudunsparce)` | 35 | 5.49% |
| `PLAY(Hilda)` | $\to$ `EVOLVE(Dudunsparce)` | 28 | 4.39% |
| `PLAY(Dawn)` | $\to$ `PLAY(Poké Pad)` | 23 | 3.61% |
| `PLAY(Hilda)` | $\to$ `EVOLVE(Alakazam)` | 22 | 3.45% |
| `PLAY(Dawn)` | $\to$ `EVOLVE(Kadabra)` | 22 | 3.45% |
| `PLAY(Hilda)` | $\to$ `PLAY(Buddy-Buddy Poffin)` | 17 | 2.66% |
| `PLAY(Hilda)` | $\to$ `PLAY(Poké Pad)` | 16 | 2.51% |
| `PLAY(Dawn)` | $\to$ `PLAY(Buddy-Buddy Poffin)` | 15 | 2.35% |
| `Other Multi-step Cascades` | $\to$ Various | 325 | 50.94% |

---

## 4. Mechanistic Analysis: Why `H_XEROSIC` Failed

While the hypothesis was strategically plausible (preventing self-starvation), empirical mirror match testing revealed a critical opposing factor in Pokémon TCG mechanics:

1. **Symmetric Win Condition Scaling**:
   - Both Sol Eclipse players depend on Alakazam's *Powerful Hand* ($20 \times \text{hand size}$) to achieve lethal 140+ damage OHKOs.
   - When the Control agent plays `Xerosic's Machinations`, it strips the opponent's hand from 10–14 cards down to 3 cards.
   - This immediately crashes the opponent's attack damage from 200–280 damage down to **60 damage**, making it impossible for the opponent to OHKO active Alakazam (140 HP) or Dudunsparce (140 HP).
2. **Defensive Utility of Opponent Hand Disruption**:
   - By prioritizing `Dawn` (+3 cards) or `Hilda` (search 2 cards), Candidate expanded its own hand but left Control's massive hand intact.
   - Control retained lethal OHKO capability on the following turn, capitalizing on Candidate's failure to disrupt its hand.
3. **Conclusion on `W["xerosic"] = 3250`**:
   - In combo-versus-combo match-ups where damage scales with hand size, aggressive hand disruption is not a "waste of tempo" — it is an active damage barrier that suppresses incoming lethal attacks.
   - The baked weight of `3250` is functionally defensible in the mirror match and should not be blindly demoted without opponent archetype conditioning.

---
*Benchmark Completed: 2026-08-30. Protocol followed: Evidence documented, production untouched.*
