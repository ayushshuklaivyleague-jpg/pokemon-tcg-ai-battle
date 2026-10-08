# P9 Post-Mortem & New High-Leverage Multi-Choice Research Framework

This document formalizes the closure of the P9 hypothesis branch and establishes the new empirical research framework focused exclusively on states with **materially different legal alternatives**.

---

## 1. Formal Closure of the P9 Hypothesis Branch

| Hypothesis ID | Mechanism Focus | Empirical Benchmark Result (200 Games) | Activations / Overrides | Status | Structural Finding |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **$P_{9\text{-H1}}$** | Priority Benching in `MAIN` | **52.50%** (CI: [45.60%, 59.31%]) | **0 / 2,063 (0.00%)** | **CLOSED (INACTIVE)** | V4 already assigns playing Basic Pokémon Tier 2 score ($50,000$). |
| **$P_{9\text{-H2}}$** | Basic Search in `TO_HAND` | **50.00%** (CI: [43.14%, 56.86%]) | **0 / 2,093 (0.00%)** | **CLOSED (INACTIVE)** | Deck contains zero Basic-search cards (`Mega Signal` & `Cyrano` only target Mega ex). |
| **$P_{9\text{-H3}}$** | Combined Compound ($P_{9\text{-H1}} + P_{9\text{-H2}}$) | — | — | **CANCELLED** | Prerequisite mechanisms demonstrated zero active effect. |

### Structural Finding:
> **V4 already makes the maximally optimal legal bench and search decisions available under the physical deck list and simulator constraints.**
> The zero-bench states (`FC-01`) and search restrictions (`FC-02`) are physical card-availability bottlenecks of the 60-card champion deck list, not policy execution errors.

---

## 2. New Research Framing: Multi-Choice Materially Different Decisions

Rather than attempting to solve unavailable-card states, the new research phase investigates states where **multiple materially different legal actions exist** in the 6,482-state corpus:

### Quantitative Distribution of Multi-Choice Decision States:
| Decision Category | Corpus States | Share of Corpus (%) | Baseline V4 Policy Behavior |
| :--- | :---: | :---: | :--- |
| **1. Energy Attachment Target Selection** | **2,029** | **31.3%** | **100.0% to Active** (V4 adds $+4,000$ to active, never attaches to bench) |
| **2. Multi-Attack Choice** | **1,898** | **29.3%** | **Highest `attackId`** (V4 selects higher ID by formula $18\text{k} + \text{id}\times 0.1$) |
| **3. Energy Discard Selection (`DISCARD_ENERGY`)** | **350** | **5.4%** | Discards highest-score cards |
| **4. Evolution Target Choice** | **245** | **3.8%** | Evolve Active (score 60,000) vs Bench Basic (score 50,000) |
| **5. Action Category Pivot (`ATTACH` vs `ATTACK`)** | **559** | **8.6%** | `ATTACH` ($35\text{k}-41.8\text{k}$) prioritized over `ATTACK` ($18\text{k}-22\text{k}$) |
| **6. Retreat vs Attack (`RETREAT` vs `ATTACK`)** | **88** | **1.4%** | Retreat at $<45\%$ max HP |

---

## 3. High-Priority Research Targets for Next Phase

1. **Target A: Active Over-Saturation vs Bench Charging (31.3% of decisions)**:
   - V4 attaches energy to the Active Pokémon 100% of the time. When the Active already has $\ge 3$ or $\ge 4$ energy (sufficient for its maximum attack), continuing to attach to Active leaves benched Basic/Mega Pokémon completely unpowered.
2. **Target B: Discard Resource Management (5.4% of decisions)**:
   - In `DISCARD_ENERGY` prompts, analyzing which card types are safely discarded without forfeiting draw support (Waitress vs Lillie vs Water Energy).
3. **Target C: Tactical Knockout Sequencing (8.6% of decisions)**:
   - Distinguishing states where an immediate attack closes out the match vs when building up energy is required.

---

## 4. Governance & Anti-Regression Rules

- Production code ([`main.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/main.py)) and baseline notebooks remain **strictly frozen**.
- No heuristic scoring changes will be introduced until a concrete, statistically verified decision failure is proven.
