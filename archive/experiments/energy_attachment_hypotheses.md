
# Energy Attachment Hypotheses & Research Synthesis

This document synthesizes the empirical findings from [`energy_attachment_analysis.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/energy_attachment_analysis.md), [`energy_attachment_counterfactuals.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/energy_attachment_counterfactuals.csv), and [`energy_attachment_failure_clusters.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/energy_attachment_failure_clusters.md).

---

## 1. Quantitative Synthesis of Hypotheses

| Hypothesis Focus | State Target | Corpus Frequency | Legal Alternative Target Available? | Causal Feasibility | Verdict |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Bench Attachment at $\ge 3$E** | Active $= 3$ Energy | 46 states (0.71%) | 16 states had bench (8 were Mega ex needing 4th E) | **Low Scope (8 states)** | **REJECTED AS HIGH-FREQUENCY TARGET** |
| **Bench Attachment at $\ge 4$E** | Active $\ge 4$ Energy | 7 states (0.11%) | 3 states had bench | **Extremely Low Scope (3 states)** | **REJECTED AS HIGH-FREQUENCY TARGET** |

---

## 2. Definitive Research Finding

1. **Volume Reality**:
   - Out of **1,762 total energy attachment decisions** across 300 complete matches, **1,709 (97.0%)** occurred when the active Pokémon had $<3$ energy, where attaching to active is operationally mandatory.
   - Out of the remaining 53 attachments with $\ge 3$ energy, **42 occurred either on Mega Abomasnow ex needing its 4th energy or in zero-bench states** where no bench target existed.
   - Only **11 total decision states across 300 games (0.17% of decisions)** presented an actual over-saturation scenario where an alternative bench target was legally available.
2. **Why P10 Should NOT Target Energy Attachment**:
   - Modifying energy attachment behavior cannot produce a high-frequency strategic breakthrough because the actionable domain is $<0.2\%$ of states.
   - V4's active-first energy attachment policy is already **$99.8\%$ aligned with the deck's physical requirements**.
3. **Next Strategic Research Frontier**:
   - The research focus should shift to high-frequency decision domains with genuine multi-action trade-offs, specifically **Attack Selection (1,898 decisions / 29.3%)** and **Tactical Knockout Pivoting (559 decisions / 8.6%)**.

---

## 3. Invariants & Governance

- Production code ([`main.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/main.py)) and baseline notebooks remain **100% frozen**.
- No P10 model will be implemented targeting energy attachment without empirical justification.
