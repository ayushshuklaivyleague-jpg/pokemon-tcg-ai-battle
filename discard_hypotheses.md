
# `DISCARD_ENERGY` Strategic Hypotheses & Research Synthesis

This document formalizes the strategic hypotheses for optimizing discard resource management based on the findings in [`discard_energy_analysis.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/discard_energy_analysis.md) and [`discard_failure_clusters.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/discard_failure_clusters.md).

---

## 1. Candidate Research Hypotheses

### Hypothesis H_DISCARD_1: Surplus Energy Discard Prioritization (Targeting `DF-01` & `DF-02`)
- **Mechanism**:
  - In `DISCARD_ENERGY` (and discard prompts), assign **Basic Water Energy the highest discard priority** ($+20,000$).
  - Assign **Draw Supporters (`Waitress`, `Lillie`) the lowest discard priority / heavy protection penalty** ($-30,000$) whenever Basic Energy is also available in the discard prompt.
- **Expected Actionable Volume**:
  - Affects **182 multi-choice decision states** across 300 matches (**2.81% of all game decisions / 49.2% of all discard prompts**).
- **Expected Impact**:
  - Eliminates premature draw engine exhaustion, preserving Waitress and Lillie to draw fresh hands on subsequent turns.
  - Aligns discard behavior with the fact that 35 out of 60 cards in the deck are Basic Water Energies.

---

## 2. Invariants & Governance

- Production code ([`main.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/main.py)) and baseline notebooks remain **100% frozen**.
- No policy implementation will be committed without prior user approval and rigorous 200-game controlled testing against frozen V4.
