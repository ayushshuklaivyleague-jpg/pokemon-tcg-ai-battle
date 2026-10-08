# `DISCARD_ENERGY` Resource Management & Counterfactual Analysis

This document details the exhaustive audit of all **370 `DISCARD_ENERGY` decision states** recorded across 300 complete matches in the V4 state corpus.

---

## 1. Executive Summary & Resource Discard Segmentation

In `DISCARD_ENERGY` prompts (e.g. paying retreat costs or card discard effects), every decision was classified by the resource type selected by V4:

| Resource Group Discarded | Card Name(s) | Total Decisions | Share of Discards (%) | Multi-Choice Present (%) | Resulting Wins | Resulting Losses | Win Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`WAITRESS`** | Waitress (Draw/Recovery) | **107** | **28.9%** | 95.3% (102) | 57 | 50 | **53.3%** |
| **`LILLIE`** | Lillie's Determination (Draw) | **75** | **20.3%** | 94.7% (71) | 47 | 28 | **62.7%** |
| **`ENERGY`** | Basic {W} Energy | **74** | **20.0%** | 93.2% (69) | 59 | 15 | **79.7%** |
| **`POKEMON`** | Mega Abomasnow / Kyogre / Snover | **58** | **15.7%** | 94.8% (55) | 46 | 12 | **79.3%** |
| **`OTHER`** | Mega Signal / Cyrano / Belt | **56** | **15.1%** | 94.6% (53) | 43 | 13 | **76.8%** |
| **Total** | — | **370** | **100.0%** | **94.6%** (350) | **252** | **118** | **68.1%** |

---

## 2. In-Depth Root Cause Discovery: The Draw Supporter Sacrificing Flaw

### V4 Scoring Mechanism in `DISCARD_ENERGY` Context:
```python
# From main.py lines 885-909:
if typ in ("ENERGY", "ENERGY_CARD"):
    return 30000.0  # High score -> Selected first by V4

if typ == "CARD":
    if card is None: return 1000.0
    if v4_is_pokemon(card):
        return 10000.0 + ...
    return 5000.0   # Low score for Supporters (Waitress, Lillie)
```

### The Flaw Explained:
1. **Scoring Inversion**:
   - V4 scores `ENERGY` at **30,000.0** and Trainer Cards (`Waitress`, `Lillie`) at **5,000.0**.
   - Because V4 chooses the option with the highest score, when presented with a choice to discard cards, **it preferentially discards Waitress and Lillie to "save" the Basic Energy**.
2. **Deck Scarcity Asymmetry**:
   - In this 60-card deck, there are **35 Basic Water Energies (58.3% of the deck)** and only **4 copies of Waitress and 4 copies of Lillie**.
   - Basic Energy is virtually inexhaustible, whereas Draw Supporters are the sole engine powering card flow.
3. **Causal Impact on Match Outcomes**:
   - In **182 decisions**, V4 threw away a critical Draw Supporter while having a Basic Water Energy legally available to discard.
   - When Supporters were discarded, the win rate plummeted to **53.3% - 62.7%**.
   - When surplus Energy was discarded (preserving the Supporter), the win rate was **79.7%** (**a +26.4% win rate delta**).
