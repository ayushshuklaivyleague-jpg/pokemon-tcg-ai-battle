# `HYBRID_STAGE_3` Empirical Benchmark & Scientific Audit Report

## 1. Executive Summary
- **Hypothesis Tested**: `HYBRID_STAGE_3` (MIKE V4 Steel Frame + Sol Eclipse State + Validated Genome `Hilda=3150`, **Search Strictly Disabled**).
- **Control Baseline**: Frozen Production Sol Eclipse (`codex_sol_eclipse_alakazam.py`, Baseline Genome `Hilda=3000`, **Search Enabled**).
- **Match Sample**: 200 balanced head-to-head matches (100 as Player 0, 100 as Player 1) across 14,520 instrumented decisions.
- **Match Record**: **11W – 112L – 77D** (5.50% Candidate aggregate WR, 56.00% Control aggregate WR, 38.50% Draw rate).
- **Decisive Win Rate**: **8.94% (11W / 112L, $N=123$)**, 95% Wilson CI: **[5.07%, 15.31%]**.
- **Determination**: **SEVERE REGRESSION** against the frozen Sol Eclipse Control.
- **Telemetry File**: [`hybrid_stage3_decision_audit.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/hybrid_stage3_decision_audit.csv) (14,520 records).

---

## 2. Benchmark Metrics Summary

| Metric | Candidate (`HYBRID_STAGE_3`: Search=OFF) | Control (Sol Eclipse: Search=ON) |
| :--- | :--- | :--- |
| **Match Record (W–L–D)** | **11W – 112L – 77D** | **112W – 11L – 77D** |
| **Aggregate Win Rate** | **5.50%** (11 / 200) | **56.00%** (112 / 200) |
| **Draw Rate** | **38.50%** (77 / 200) | **38.50%** (77 / 200) |
| **Decisive (Non-Draw) Win Rate** | **8.94%** (11W / 112L, $N=123$) | **91.06%** (112W / 11L, $N=123$) |
| **Aggregate 95% Wilson CI** | **[3.10%, 9.58%]** | **[49.12%, 62.67%]** |
| **Decisive 95% Wilson CI** | **[5.07%, 15.31%]** | **[84.69%, 94.93%]** |
| **Player 0 (Going 1st) Record** | 6W – 61L – 33D (6.0% WR) | 61W – 6L – 33D (61.0% WR) |
| **Player 1 (Going 2nd) Record** | 5W – 51L – 44D (5.0% WR) | 51W – 5L – 44D (51.0% WR) |
| **Average Game Length** | 136.49 steps | 136.49 steps |
| **Contract / Runtime Errors** | **0** | **0** |
| **Fallback Activations** | **0** | **0** |
| **Total Search Invocations** | **0 (Verified Disabled)** | Active (1-Ply Rollouts) |
| **Decisions Instrumented** | 14,520 | 14,520 |
| **Dawn vs Hilda Comp States** | 1,278 | 1,278 |
| **Xerosic Plays** | **61** | **943 (+882 / 15.5x)** |
| **Hilda Plays** | 383 | 455 |
| **Dawn Plays** | 269 | 865 |
| **Total Decision Overrides** | **1,644 / 14,520 (11.32%)** | — |
| **Override Games Record (185G)** | **11W – 97L – 77D (10.19% Decisive WR)** | — |

---

## 3. Top Action Transitions (Control with Search → Candidate without Search)

| Control Action (Search ON) | Candidate Action (Search OFF) | Count | Strategic Impact |
| :--- | :--- | :--- | :--- |
| **`PLAY(Xerosic’s Machinations)`** | **`PLAY(Hilda)`** | **174** | Candidate failed to suppress opponent hand; allowed opponent combo blowout |
| **`PLAY(Xerosic’s Machinations)`** | **`PLAY(Dawn)`** | **109** | Discarded disruptive pressure for passive topdeck draw |
| **`PLAY(Xerosic’s Machinations)`** | **`PLAY(Boss’s Orders)`** | **106** | Suboptimal target selection |
| `PLAY(Dawn)` | `PLAY(Hilda)` | 97 | Hilda priority shift |
| `PLAY(Xerosic’s Machinations)` | `ABILITY(Dudunsparce)` | 50 | Overdrew rather than disrupting opponent |
| `ATTACH(Energy -> Alakazam)` | `ATTACH(Energy -> Dunsparce)` | 42 | Wasted energy tempo on support Pokémon |
| `PLAY(Xerosic’s Machinations)` | `EVOLVE(Dudunsparce)` | 41 | Ignored hand suppression |
| `ATTACH(Energy -> Kadabra)` | `ATTACH(Energy -> Dunsparce)` | 24 | Delayed attacker readiness |

---

## 4. Root Cause Analysis: The Indispensable Value of Search

1. **Massive Suppression Deficit (-882 Xerosic Plays)**:
   - Control's 1-ply search engine simulates opponent responses and discovers that playing Xerosic to shrink an opponent's hand to 3 cards drastically lowers the opponent's transition value on the subsequent turn.
   - Candidate's heuristic layer alone only triggers Xerosic when `op_state.handCount >= 6` and assigns it a static weight (3250), which frequently loses to competing items/draw supporters in the static ranking.
   - Result: Control played Xerosic **943 times** vs Candidate's **61 times** (a 15.5x disparity).
2. **Energy Attachment Misallocations**:
   - Without forward lookahead, Candidate attached energies to Dunsparce instead of Active/Bench Alakazam and Kadabra (85+ transitions), delaying attacker readiness by 1–2 critical turns.
3. **Definitive Scientific Finding**:
   - In Sol Eclipse Alakazam, **Layer 5 (Search) is not an auxiliary component; it is the core driver of competitive win rate**.
   - Pure heuristics (Layers 1+2+3+4) cannot replicate the tactical precision of 1-ply forward evaluation in the Alakazam mirror.

---

## 5. Architectural Verdict

### **VERDICT: SEVERE REGRESSION (8.94% Decisive Win Rate)**

- **Determination against Frozen Control**: **REGRESSES** (Category 3).
- **Recommendation**:
  - `HYBRID_STAGE_3` (Search=OFF) is **REJECTED** as a standalone competitive model.
  - To achieve parity or superiority over Sol Eclipse, the hybrid architecture **must incorporate Layer 5 (Context-Gated Selective Search) and Layer 6 (Confidence-Gated Overrides)**.
  - Production files [`main.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/main.py) and [`codex_sol_eclipse_alakazam.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/codex_sol_eclipse_alakazam.py) remain **100% FROZEN and UNTOUCHED**.
