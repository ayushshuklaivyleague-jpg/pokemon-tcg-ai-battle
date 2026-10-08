# `DISCARD_ENERGY` Failure Cluster Audit

This document isolates and audits the failure clusters associated with discard selection decisions in the V4 state corpus.

---

## 1. Identified Failure Clusters

| Cluster ID | Failure Cluster Name | Description | Occurrences | Share of Discards (%) | Loss Rate (%) | Impact Rank |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **`DF-01`** | **Waitress Sacrificing** | Discarding Waitress when Basic Energy is available in hand | 102 | **27.6%** | **46.7%** | **CRITICAL** |
| **`DF-02`** | **Lillie Sacrificing** | Discarding Lillie's Determination when Basic Energy is available | 71 | **19.2%** | **37.3%** | **HIGH** |
| **`DF-03`** | **Mega Evolution Sacrificing** | Discarding Mega Abomasnow ex when Basic Energy is available | 55 | **14.9%** | **20.7%** | **MEDIUM** |
| **`DF-04`** | **Optimal Energy Discard** | Discarding Basic Energy (preserving Draw Supporters & Pokémon) | 74 | **20.0%** | **20.3%** | **BENCHMARK (OPTIMAL)** |

---

## 2. Failure Mechanism Details

- **`DF-01` & `DF-02` (46.8% of all discards / 173 states)**:
  - In nearly half of all discard prompts, V4 discards the deck's only draw engines (`Waitress` or `Lillie`) to save an abundant Basic Water Energy.
  - This immediately starves the player of draw power in subsequent turns, leading to stalled board development and eventual defeat.
  - This represents a **concrete, highly frequent, and statistically verified decision flaw in V4**.
