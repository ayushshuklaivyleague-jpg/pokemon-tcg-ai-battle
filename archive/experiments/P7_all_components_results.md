# P7 All-Components Integration Benchmark Results

This document details the performance of **P7 (All-Components Integration)** evaluated against the frozen **P0 (MIKE V4 Control Baseline)** over 200 balanced matches.

## 1. Executive Summary

| Experiment ID | Architecture Configuration | Games Evaluated | Record (W-L-D) | Win Rate (%) | 95% Wilson CI | Overrides (Rate %) | Override Win % | Promotion Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **P0** | Frozen V4 Control Baseline | 200 | 99-101-0 | **49.50%** | [42.65%, 56.37%] | 0 (0.0%) | N/A | **PROVEN PRODUCTION CONTROL** |
| **P7** | All-Components (Threat + CF + KO + Safe Retreat) | 200 | 96-104-0 | **48.00%** | [41.18%, 54.90%] | 27 (1.36%) | 63.0% | **REJECTED (CI CROSSES PARITY)** |

---

## 2. Match Performance & Starting Order Breakdown

- **Total Games**: 200
- **Overall Win Rate**: **48.00%**
- **95% Wilson Confidence Interval**: **[41.18%, 54.90%]**
- **Win Rate as Player 0 (1st turn)**: **28.0%**
- **Win Rate as Player 1 (2nd turn)**: **68.0%**
- **Average Match Length**: **20.44 steps**
- **Contract Errors**: **0**

---

## 3. Component Interaction & Override Attribution

### Override Breakdown by Primary Driving Component:

| Primary Driver | Overrides Count | Resulting Wins | Resulting Losses | Win Conversion (%) |
| :--- | :---: | :---: | :---: | :---: |
| **`COUNTERFACTUAL`** | 15 | 7 | 8 | **46.7%** |
| **`KO_GUARANTEE`** | 11 | 10 | 1 | **90.9%** |
| **`SAFE_RETREAT`** | 1 | 0 | 1 | **0.0%** |

### Override Breakdown by Action Category:

| V4 Default Action | P7 Override Action | Count | Wins | Losses | Win Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `ATTACH` | `ATTACK` | 11 | 10 | 1 | **90.9%** |
| `ATTACH` | `ATTACH` | 10 | 5 | 5 | **50.0%** |
| `RETREAT` | `ATTACK` | 5 | 2 | 3 | **40.0%** |
| `ATTACK` | `RETREAT` | 1 | 0 | 1 | **0.0%** |
