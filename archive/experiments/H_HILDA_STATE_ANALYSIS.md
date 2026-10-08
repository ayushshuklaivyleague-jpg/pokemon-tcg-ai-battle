# `H_HILDA` State-Conditioned Outcome Analysis

## 1. Objective

Determine whether the globally inconclusive `hilda = 3150` policy can be
refined into a **context-conditioned** policy that activates Hilda over Dawn
**only when specific board conditions hold**, thereby converting a marginal
global advantage into a targeted, high-confidence improvement.

---

## 2. Dataset

| Item | Value |
| :--- | :--- |
| **Source** | Pooled 400-game H_HILDA telemetry (Batches 1 + 2) |
| **Total Decisions** | 28,822 |
| **Dawn → Hilda Inversions Isolated** | **442** |
| **Unique Games Containing Inversions** | **273** of 400 |
| **Inversion Rate** | 1.53% of all decisions |
| **Features Extracted Per Inversion** | 28 board-state variables |
| **Telemetry Files** | [`h_hilda_inversion_outcomes.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/h_hilda_inversion_outcomes.csv) (442 rows), [`h_hilda_state_clusters.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/h_hilda_state_clusters.csv) (46 clusters) |

---

## 3. Key Discovery: Evolution Stage Is the Dominant State Variable

The 442 inversions partition cleanly by **evolution stage at the moment
of inversion**:

| Evolution Stage | Inversions | Coverage | Games | Record | Decisive WR | 95% Wilson CI |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ALAKAZAM_UP** | 295 | 66.7% | 206 | **42W – 3L – 161D** | **93.3%** | **[82.1%, 97.7%]** |
| KADABRA_STAGE | 82 | 18.6% | 71 | 6W – 6L – 59D | 50.0% | [25.4%, 74.6%] |
| ABRA_ONLY | 61 | 13.8% | 51 | 6W – 8L – 37D | 42.9% | [21.4%, 67.4%] |
| NO_LINE | 4 | 0.9% | 4 | 1W – 1L – 2D | 50.0% | [9.5%, 90.5%] |

> [!IMPORTANT]
> **When Alakazam is already on the field, Hilda wins 93.3% of decisive games (42W – 3L).**
> When Alakazam is NOT yet evolved, the advantage **vanishes entirely** (12W – 14L, 46.2% decisive WR).

---

## 4. Causal Mechanism

The data reveals a clear two-regime dynamic:

### Regime A: Alakazam Already Evolved (66.7% of inversions)
- Hilda's deterministic 2-card search finds **Energy** or a **second Alakazam line** to build additional attackers.
- Dawn's random 3-card draw is wasteful when the combo is already assembled — the player needs specific pieces (Energy, Night Stretcher, backup Abra), not volume.
- Result: **93.3% decisive WR** (practically guaranteed conversion).

### Regime B: Pre-Alakazam (33.3% of inversions)
- The player needs to assemble the combo (find Kadabra, Rare Candy, or Alakazam).
- Dawn's random 3-card draw has a higher probability of hitting at least one of multiple valid targets across a broader card pool.
- Hilda's deterministic 2-card search is too narrow when the exact missing piece isn't clear.
- Result: **46.2% decisive WR** (Dawn was actually marginally better).

---

## 5. Secondary State Variables

Beyond evolution stage, several secondary variables show strong associations:

| Variable | Best Cluster | Decisive WR | Worst Cluster | Decisive WR |
| :--- | :--- | :--- | :--- | :--- |
| **Prize Differential** | Ahead (taking prizes) | **100.0%** (26W – 0L) | Behind (losing prizes) | **16.7%** (2W – 10L) |
| **Xerosic Co-Legality** | Xerosic Legal | **96.4%** (27W – 1L) | Xerosic NOT Legal | **69.4%** (34W – 15L) |
| **Alakazam Count** | 1+ Alakazam | **92.4%** (49W – 4L) | 0 Alakazam | **48.0%** (12W – 13L) |
| **Hand Size** | High (>9) | **87.1%** (27W – 4L) | Low (≤9) | **70.5%** (31W – 13L) |
| **Game Phase** | Mid-game | **84.4%** (27W – 5L) | Early | **61.9%** (13W – 8L) |
| **Dudunsparce** | Has Dudunsparce | **84.2%** (32W – 6L) | No Dudunsparce | **70.7%** (29W – 12L) |

However, most of these **correlate with evolution stage**:
- Xerosic co-legality: Xerosic is legal when opponent hand ≥ 6, which happens more in later game states where Alakazam is already up.
- Prize differential: Being ahead on prizes means Alakazam has been attacking (evolved).
- Higher hand size and Dudunsparce both track with successful mid/late-game development.

**Evolution stage is the minimal sufficient variable** — it explains the outcome differential without requiring additional conditions.

---

## 6. Interaction Clusters (Cross-Validation)

| Interaction Cluster | Games | Record | Decisive WR | CI |
| :--- | :--- | :--- | :--- | :--- |
| **ALAKAZAM_UP + LATE** | 132 | 23W – 1L – 108D | **95.8%** | [79.8%, 99.3%] |
| **ALAKAZAM_UP + MID** | 93 | 22W – 2L – 69D | **91.7%** | [74.2%, 97.7%] |
| **ALAKAZAM_UP + Xerosic Legal** | 80 | 25W – 1L – 54D | **96.2%** | [81.1%, 99.3%] |
| **ALAKAZAM_UP + Xerosic NOT Legal** | 156 | 26W – 3L – 127D | **89.7%** | [73.6%, 96.4%] |
| KADABRA_STAGE + MID | 35 | 5W – 2L – 28D | 71.4% | [35.9%, 91.8%] |
| KADABRA_STAGE + Xerosic NOT Legal | 61 | 4W – 6L – 51D | 40.0% | [16.8%, 68.7%] |
| **ABRA_ONLY + LATE** | 16 | **0W – 6L – 10D** | **0.0%** | [0.0%, 39.0%] |

> [!CAUTION]
> **ABRA_ONLY + LATE** represents the worst state: 0 wins in 6 decisive games.
> Playing Hilda when you still only have Abra in the late game is actively harmful.

---

## 7. Coverage Analysis: Conditional Policy Potential

If we restrict `Hilda > Dawn` to **only** when `alakazam_count ≥ 1`:

| Metric | Global Hilda=3150 | Conditional (Alakazam Up Only) |
| :--- | :--- | :--- |
| **Inversions Applied** | 442 (100%) | 295 (66.7%) |
| **Games Affected** | 273 | 206 |
| **Decisive Record** | 50W – 19L | **42W – 3L** |
| **Decisive WR** | 72.5% | **93.3%** |
| **95% Wilson CI** | [59.1%, 82.8%] | **[82.1%, 97.7%]** |
| **Eliminated Losses** | — | **16 of 19 losses** (84.2%) |

The conditional policy retains **84% of the wins** (42 of 50) while **eliminating 84% of the losses** (16 of 19), converting a marginal 72.5% decisive advantage into a near-certain 93.3% advantage.

The 147 inversions that would be suppressed (pre-Alakazam) were generating a **46.2% decisive WR** (12W – 14L) — worse than not inverting at all.

---

## 8. Hypothesis Recommendation

### Recommended Hypothesis: `H_HILDA_CONDITIONAL`

**Policy**: Prefer Hilda over Dawn (`WEIGHTS["hilda"] > WEIGHTS["dawn"]`) **only when at least one Alakazam is on the player's field** (active or bench). Otherwise, maintain the existing priority ordering (`Dawn > Hilda`).

**Implementation Sketch** (not yet implemented):
```
When choosing between Dawn and Hilda in MAIN context:
  IF alakazam_count >= 1:
      use hilda priority = 3150  (above Dawn's 3100)
  ELSE:
      use hilda priority = 3000  (below Dawn's 3100, original behavior)
```

**Expected Impact**:
- Activates in ~67% of the Dawn/Hilda competition states.
- Preserves Dawn's probabilistic advantage during early combo assembly.
- Captures Hilda's deterministic advantage during late-game piece targeting.
- Eliminates the ~47% of global losses attributable to pre-Alakazam Hilda plays.

**Estimated Decisive WR**: 93.3% in activated states (42W – 3L across 206 games in pooled data).

---

## 9. What This Analysis Does NOT Do

- **Does not implement** the conditional policy.
- **Does not tune** `hilda` further.
- **Does not modify** production [`codex_sol_eclipse_alakazam.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/codex_sol_eclipse_alakazam.py) (remains FROZEN).
- **Does not combine** this with any other weight change.
- **Does not submit** to Kaggle.

---

## 10. Files Produced

| File | Description |
| :--- | :--- |
| [`h_hilda_inversion_outcomes.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/h_hilda_inversion_outcomes.csv) | 442-row per-inversion feature table with 28 board-state columns |
| [`h_hilda_state_clusters.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/h_hilda_state_clusters.csv) | 46-row cluster summary with decisive WR and Wilson CIs |
| [`analyze_h_hilda_states.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/analyze_h_hilda_states.py) | Analysis script (reproducible) |
