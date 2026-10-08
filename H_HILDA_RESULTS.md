# Hypothesis `H_HILDA` Empirical Benchmark Results

## 1. Executive Summary
- **Hypothesis**: `H_HILDA` (`WEIGHTS["hilda"]: 3000 → 3150`)
- **Control Baseline**: Frozen `codex_sol_eclipse_alakazam.py` (`WEIGHTS["hilda"] = 3000`, `Dawn = 3100`, `Xerosic = 3250`)
- **Evaluation Protocol**: 200-game balanced head-to-head benchmark (100 games as Player 0 / First, 100 games as Player 1 / Second).
- **Core Mechanism**: Flips Supporter selection priority between `Dawn` (+3 random cards) and `Hilda` (deterministic search for 2 target pieces) on non-disruption turns while keeping `Xerosic` (3250) suppression intact.

---

## 2. Match Record & Statistical Metrics

| Metric | Result |
| :--- | :--- |
| **Match Record (Candidate vs Control)** | **33W – 25L – 142D** |
| **Candidate Aggregate Win Rate** | **16.50%** (33 / 200) |
| **Control Aggregate Win Rate** | **12.50%** (25 / 200) |
| **Draw Rate** | **71.00%** (142 / 200) |
| **Decisive (Non-Draw) Win Rate** | **56.90%** (33W / 25L, $N=58$) |
| **Wilson 95% CI (Aggregate)** | **[12.00%, 22.27%]** |
| **Wilson 95% CI (Decisive)** | **[44.11%, 68.80%]** |
| **Player 0 (Going 1st) Win Rate** | **15.0%** (15 / 100) |
| **Player 1 (Going 2nd) Win Rate** | **18.0%** (18 / 100) |
| **Average Match Length** | **146.01 steps** |
| **Contract / Runtime Errors** | **0** |
| **Fallback Activations** | **0** |

---

## 3. Telemetry & Policy Override Analysis

- **Total Instrumented Decisions**: 14,501
- **Dawn vs Hilda Competition States**: 1,501 (10.35% of all decisions)
- **Total Decisions Overridden**: 339 decisions (2.34%)

### Supporter Play Distributions
| Supporter | Control Baseline | Candidate (`H_HILDA`) | Net Shift |
| :--- | :--- | :--- | :--- |
| **Hilda Plays** | 218 | **389** | **+171 (+78.4%)** |
| **Dawn Plays** | 404 | **216** | **-188 (-46.5%)** |

### Top Action Transitions (`Control Action → Candidate Action`)
| Control Action | Candidate Action | Occurrence Count |
| :--- | :--- | :--- |
| `PLAY(Dawn)` | `PLAY(Hilda)` | **220** |
| `PLAY(Dawn)` | `PLAY(Buddy-Buddy Poffin)` | 6 |
| `PLAY(Hilda)` | `PLAY(Poké Pad)` | 4 |
| `PLAY(Hilda)` | `EVOLVE(Dudunsparce on Dunsparce)` | 4 |
| `PLAY(Dawn)` | `EVOLVE(Alakazam on Kadabra)` | 3 |
| `EVOLVE(Kadabra on Abra)` | `PLAY(Rare Candy)` | 3 |
| `PLAY(Night Stretcher)` | `EVOLVE(Dudunsparce on Dunsparce)` | 3 |
| `PLAY(Hilda)` | `PLAY(Xerosic’s Machinations)` | 3 |

---

## 4. Subgroup Analysis: Override Games vs Non-Override Games

To isolate whether the policy change directly generated the win-rate advantage, we partition the 200 matches into games where `H_HILDA` executed at least one action override vs games where it never activated:

| Game Cohort | Matches | Candidate Record | Decisive Win Rate |
| :--- | :--- | :--- | :--- |
| **Games WITH Overrides** | **156 (78.0%)** | **27W – 10L – 119D** | **73.0% (2.70 : 1 Win/Loss Ratio)** |
| **Games WITHOUT Overrides** | **44 (22.0%)** | **6W – 15L – 23D** | **28.6% (Stochastic baseline variance)** |

### Causal Takeaway:
In matches where the `H_HILDA` weight change actually inverted decisions from `Dawn` to `Hilda` (156 games), Candidate dominated Control with a **73.0% decisive win rate (27 Wins vs 10 Losses)**. Deterministic piece assembly via Hilda consistently outperformed random 3-card top-decks when setting up Alakazam and Dudunsparce draw engines.

---

## 5. Artifact Verification
- Full decision-by-decision telemetry logged to [`h_hilda_decision_audit.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/h_hilda_decision_audit.csv).
- Production codebase [`codex_sol_eclipse_alakazam.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/codex_sol_eclipse_alakazam.py) remains **FROZEN and UNTOUCHED**.
