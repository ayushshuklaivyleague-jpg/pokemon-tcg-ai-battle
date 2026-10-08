# Energy Attachment Failure Cluster Audit

This document isolates and audits the failure clusters associated with energy attachment decisions in the V4 state corpus.

---

## 1. Identified Energy Attachment Clusters

| Cluster ID | Cluster Name | Definition | Total Occurrences | Frequency in Corpus (%) | Loss Rate (%) | Actionable Volume |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **`EA-01`** | **Essential Active Ramp** | Active $< 3$ Energy (building basic attack readiness) | 1,709 | **26.37%** | 44.1% | **Non-Actionable (Optimal)** |
| **`EA-02`** | **Mega Carry 4th Energy Charging** | Active is Mega Abomasnow at 3E, attaching 4th for Frost Barrier | 8 | **0.12%** | 25.0% | **Non-Actionable (Optimal)** |
| **`EA-03`** | **Snover/Kyogre 4th Energy Over-Attach** | Active is Snover/Kyogre at 3E, bench present, attaching 4th | 8 | **0.12%** | 37.5% | **Minor Actionable (8 states)** |
| **`EA-04`** | **Active 5th+ Energy Over-Saturation** | Active $\ge 4$ Energy, bench present, attaching 5th+ | 3 | **0.05%** | 66.7% | **Minor Actionable (3 states)** |
| **`EA-05`** | **Forced Active Stacking (Zero Bench)** | Active $\ge 4$ Energy, bench empty (no alternative target) | 4 | **0.06%** | 75.0% | **Non-Actionable (Zero Bench)** |

---

## 2. Failure Cluster Synthesis

- **`EA-01` & `EA-02` (99.37% of all attachments)**: Attaching energy to the active is strictly required to power up attacks. Diverting energy to the bench in these states directly harms tempo.
- **`EA-03` & `EA-04` (0.63% of attachments / 11 states total)**: Represent the only true over-saturation instances where an active Pokémon with sufficient energy receives additional attachments while a bench Pokémon is available.
- **Why EA-03/04 are so rare**: Matches with this deck end quickly once Mega Abomasnow ex (350 HP, 200 dmg) enters play, terminating before surplus energies accumulate.
