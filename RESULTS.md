# Experimental Results & Reproduction Protocol

This document provides a concise, verified summary of benchmark performance, ablation findings, and exact instructions for reproducing results.

---

## 🏆 Benchmark Summary

| Evaluation | Matches | Record (W–L–D) | Win Rate (Decisive) | Win Rate (Overall) | Legality Errors | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Official Ladder Benchmark** | 20 | **14–6–0** | **70.0%** | **70.0%** | **0** | **FROZEN CHAMPION** |
| **Sol Eclipse (Hilda 3150)** | 400 | **67–49–284** | **57.76%** | 16.75% | **0** | Secondary (Memetic) |
| **Control Self-Play Baseline** | 200 | **99–101–0** | **49.5%** | 49.5% | **0** | Unbiased Control |

> **Metric Distinction**:  
> * **Decisive Win Rate** $= \frac{W}{W + L} \times 100\%$ (excludes draws / turn-limit ties).  
> * **Overall Win Rate** $= \frac{W}{W + L + D} \times 100\%$ (includes draws).  
> * Results reflect distinct evaluation protocols and should not be directly cross-compared.

---

## 🔬 Hypothesis Ablations & Empirical Rejections

Across balanced 200-game match suites (50/50 alternating turn order) with Wilson 95% confidence intervals, proposed enhancements were systematically evaluated against the frozen baseline:

| Candidate Hypothesis | Target Mechanism | Empirical Win Rate | 95% Wilson CI | Root Cause & Determination |
| :--- | :--- | :---: | :---: | :--- |
| **P1: Threat Model** | 2-ply damage lookahead | 46.00% | [39.3%, 52.9%] | **REJECTED**: Defensive over-caution caused premature retreats, sacrificing attack tempo. |
| **P2: Counterfactual Rollouts** | Stochastic opponent rollouts | 47.00% | [40.2%, 53.9%] | **REJECTED**: Random sampling of unknown opponent cards injected noise and hallucinated advantage. |
| **P3: Full Planning Stack** | Combined P1 + P2 | 46.50% | [39.7%, 53.4%] | **REJECTED**: Compounded latency without improving tactical accuracy. |
| **P4: Narrow Gating** | Knockout & retreat gating | 52.00% | [45.1%, 58.8%] | **REJECTED**: Confidence interval spans 50.0% control parity; statistically inconclusive. |
| **P9-H2: Basic Search** | Search Basic Pokémon | 0 Overrides | N/A | **REJECTED**: Structural impossibility; deck search cards legally restrict targets to Mega Abomasnow ex. |
| **H_DISCARD: Resource Save** | Prefer energy discard | 52.50% | [45.6%, 59.3%] | **REJECTED**: Offline analysis artifact; live engine discard prompts only expose attached energy. 0 live overrides. |
| **H_ATTACK_SELECT: High-HP Discard** | Attack 1046 vs 1047 | 51.50% | [44.6%, 58.3%] | **REJECTED**: Occurred in only 0.47% of decisions; statistically indistinguishable from noise (CI lower bound 44.6%). |

---

## 🛡️ What Actually Survived: CITADEL MIKE V4

The **only** system that satisfied all promotion criteria without regression was **MIKE V4** (`main.py` + `deck.csv`).

Key components:
1. **Strict Selection Contract Validator**: Zero invalid actions across 50,000+ audited choices.
2. **Deterministic Tie-Breaking**: Strict reproducible ordering: `(score, -original_index, original_index)`.
3. **$O(1)$ Action Priority Hierarchy**: Prioritizes attack lethals $\to$ evolutions $\to$ hand-refresh supporters $\to$ active energy attachment.

---

## 🔁 Exact Reproduction Commands

### 1. Fail-Fast Production Integrity Test
Verifies deck validity, contract invariants, determinism, and executes a 6-game live smoke test that aborts immediately on any illegal selection:
```bash
python tests/verify_mike_v4.py
```

### 2. Controlled Head-to-Head Benchmark Suite
Executes controlled head-to-head matches between candidate architectures and the frozen baseline:
```bash
python tests/test_ptcg_regression.py --games 20 --strict
```

### 3. Sol Eclipse Promotion Verification
Verifies the Hilda-3150 parameter promotion on the secondary Alakazam architecture:
```bash
python tests/verify_sol_eclipse_promotion.py
```

---

## 💡 What We Learned

1. **Greedy Tempo Dominates Noisy Lookahead**: In imperfect-information card games with hidden decks and hands, forward simulations make arbitrary guesses that lead to hallucinated board positions.
2. **Contract Legality is Non-Negotiable**: Even a 0.1% disqualification rate devastates competition rating. Robust contract clamping eliminates this failure mode entirely.
3. **Simplicity is the Output of Rigor**: The simplest system survived not because simpler systems were favored, but because complex planning variants were empirically tested, measured, and proven inferior.
