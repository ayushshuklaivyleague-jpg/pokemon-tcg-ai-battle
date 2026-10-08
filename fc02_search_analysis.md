# FC-02: `TO_HAND` Search Resolution & Board Deficit Analysis

This document details the analysis of **616 `TO_HAND` search prompts** recorded across 300 complete matches in the V4 state corpus.

---

## 1. Research Question & Empirical Framing

**Hypothesis**: When resolving `TO_HAND` deck search prompts (e.g., Poké Ball, search item cards), does V4's static card selection conflict with immediate board deficits (empty bench, threatened active, energy deficit)?

---

## 2. Board Deficit Distribution at Search Prompts (616 Decisions)

Every `TO_HAND` decision state in the corpus was classified by the active player's immediate board deficit at the moment of search:

| Board Deficit Classification | Occurrences | Share of Search Prompts (%) | Resulting Wins | Resulting Losses | Win Rate (%) | Strategic Requirement |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`EMPTY_BENCH`** | **393** | **63.8%** | 330 | 63 | **84.0%** | Retrieve **Basic Pokémon** to anchor bench |
| **`NONE` (Board Healthy / Stabilized)** | **156** | **25.3%** | 147 | 9 | **94.2%** | Retrieve highest-value offensive card |
| **`EVOLUTION_OPPORTUNITY`** | **45** | **7.3%** | 44 | 1 | **97.8%** | Retrieve **Stage 1/2 Evolution** to scale active |
| **`THREATENED_ACTIVE`** | **13** | **2.1%** | 13 | 0 | **100.0%** | Retrieve **Evolution** (HP boost) or **Basic** |
| **`ENERGY_DEFICIT`** | **9** | **1.5%** | 7 | 2 | **77.8%** | Retrieve **Energy Card** to power attack |
| **Total** | **616** | **100.0%** | **541** | **75** | **87.8%** | — |

---

## 3. Key Findings & Cross-Cluster Causal Link

1. **The Primary Driver of Bench Shortages**:
   - In **63.8% of all deck search opportunities**, the player's bench is completely empty (`my_bench_count == 0`).
   - Resolving these 393 search opportunities with a Basic Pokémon directly eliminates the vulnerability identified in FC-01.
2. **Context-Blind Static Ranking in V4**:
   - V4 currently scores card retrieval in `TO_HAND` based on static card value without checking whether `my_bench_count == 0`.
   - When a Basic Pokémon and an Energy card are both present in the search options, static preference may select Energy even when the bench is completely vacant.
3. **Causal Impact**:
   - Dynamic search resolution (prioritizing Basic Pokémon whenever `my_bench_count == 0`) provides a high-leverage causal mechanism directly impacting **over 6% of all match decisions** (393 / 6,482 states).
