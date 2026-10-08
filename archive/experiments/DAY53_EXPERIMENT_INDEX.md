# Citadel Day 53 — Master Experiment Index

**Document Timestamp**: 2026-08-30  
**Status**: **V4 HEURISTIC RESEARCH BRANCH OFFICIALLY CLOSED**  
**Production Control**: [`main.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/main.py) (MIKE V4 Champion) & [`submission_notebook.ipynb`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/submission_notebook.ipynb) are **FROZEN**.

---

## Master Experiment Catalog (P0 Through Day 53)

| Experiment ID | Tested Hypothesis / Domain | Sample Size | Override / Activation Rate | Benchmark Result (W-L-D / Win %) | 95% Wilson CI | Reason Closed / Status | Production Impact |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **P0 Baseline** | MIKE V4 Champion baseline control | 200 matches | 0.00% (Control) | 99W–101L (49.50%) | [42.66%, 56.39%] | **Baseline Standard** | **Production Champion** |
| **P1** | 2-ply lookahead Threat Model | 200 matches | 12.40% overrides | 92W–108L (46.00%) | [39.26%, 52.90%] | Regression (Defensive over-caution) | Rejected |
| **P2** | Lookahead Counterfactual rollout layer | 200 matches | 14.80% overrides | 94W–106L (47.00%) | [40.21%, 53.90%] | Regression (Rollout variance) | Rejected |
| **P3** | Full Threat + Counterfactual integration | 200 matches | 21.30% overrides | 93W–107L (46.50%) | [39.73%, 53.40%] | Regression (Compounded latency & error) | Rejected |
| **P4** | Narrowly Scoped Gating (KO & Safe Retreat) | 200 matches | 4.80% overrides | 104W–96L (52.00%) | [45.11%, 58.81%] | Statistical Parity (CI spans 50.0%) | Rejected |
| **P7 & P8** | Component interaction & state corpus audit | 300 matches | 6,482 decisions | N/A (Telemetry) | N/A | Completed telemetry foundation | Preserved |
| **P9-H1** | Dynamic Basic Pokémon Bench Placement | 200 matches | 0 / 3,420 (0.00%) | 103W–97L (51.50%) | [44.61%, 58.33%] | Inactive (V4 already prioritizes Basic) | Rejected |
| **P9-H2** | State-Adaptive Basic Search in TO_HAND | 200 matches | 0 / 3,420 (0.00%) | 101W–99L (50.50%) | [43.64%, 57.34%] | Structural Impossibility (Search restricted) | Rejected |
| **H_DISCARD** | Supporter vs Energy Discard Prioritization | 200 matches | 0 / 3,346 (0.00%) | 105W–95L (52.50%) | [45.60%, 59.31%] | Offline Tooling Artifact (0 live overrides) | Rejected |
| **H_ATTACK_SELECT** | Mega Abomasnow Dynamic Attack Selection | 200 matches | 16 / 3,413 (0.47%) | 103W–97L (51.50%) | [44.61%, 58.33%] | Statistical Parity (CI lower bound $\le 50.0\%$) | Rejected |
| **Domain A Audit** | Active vs Bench Evolution Target Selection | 200 matches | 26 / 4,218 (0.62%) | N/A (Audit) | N/A | Already Optimal in V4 (Active 50–90 HP) | Closed |
| **Domain B Audit** | ATTACH vs ATTACK Action Pivoting | 200 matches | 641 / 4,218 (15.2%) | N/A (Audit) | N/A | Rules Invariant (ATTACH does not end turn) | Closed |
| **Domain C Audit** | Snover / Kyogre Multi-Attack Selection | 200 matches | 277 / 4,218 (6.57%) | N/A (Audit) | N/A | Already Optimal in V4 (Higher dmg dominates) | Closed |
| **Domain D Audit** | Maximum Belt Tool Target Selection | 200 matches | 0 / 4,218 (0.00%) | N/A (Audit) | N/A | Zero Occurrence | Closed |
| **Domain E Audit** | Promotion on KO with $\ge 2$ Bench | 200 matches | 14 / 4,218 (0.33%) | N/A (Audit) | N/A | Low-Frequency Noise | Closed |
| **Domain F Audit** | Deck Search Filter Target Selection | 200 matches | 377 / 4,218 (8.94%) | N/A (Audit) | N/A | Forced / Engine-Masked (V4 picks target) | Closed |

---

## Summary Statement
*"Within the tested CABT simulator, this specific 60-card deck, and the audited decision domains, no experimentally validated improvement over frozen V4 has been established."*

- **Production Policy**: [`main.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/main.py) (MIKE V4 Champion) remains **FROZEN**.
- **Execution Status**: V4 heuristic branch is **TERMINATED**.
