# Pokémon TCG Model Lineage & Architecture Evolution

This document provides a comprehensive reverse-engineering and architectural audit of the Pokémon Trading Card Game (PTCG) competitive AI lineage from **V2** through **V3**, **V4 (Champion Control)**, and **V4F/Research**.

---

## 1. Executive Summary & Lineage Overview

```
                      ┌─────────────────────────────────┐
                      │    CITADEL PTCG V2 (Search)     │
                      │  • CABT Minimax Search (D2-D3)  │
                      │  • Branch deduplication         │
                      │  • High latency / brittle eval  │
                      └────────────────┬────────────────┘
                                       │
                                       ▼  (Paradigm shift: Tactical fast heuristic)
                      ┌─────────────────────────────────┐
                      │    CITADEL PTCG V3 (Tactical)   │
                      │  • Low-latency action priority  │
                      │  • Contextual attack weighting  │
                      │  • Evolve/attach/supporter tiers│
                      └────────────────┬────────────────┘
                                       │
                                       ▼  (Airtight legality & contract hardening)
                      ┌─────────────────────────────────┐
                      │  CITADEL PTCG V4 (Champion P0)  │
                      │  • Strict Selection Contract    │
                      │  • minCount/maxCount clamping   │
                      │  • deck.csv auto-fallback       │
                      │  • 14/20 Wins (70.0% Benchmark) │
                      └───────┬─────────────────┬───────┘
                              │                 │
                              │                 ▼ (Research branch)
                              │  ┌─────────────────────────────────┐
                              │  │    PTCG V4F / Research          │
                              │  │  • MultiPly Beam Search         │
                              │  │  • Stochastic deck sampling     │
                              │  │  • Vulnerable to timeouts/diverg│
                              │  └─────────────────────────────────┘
                              │
                              ▼ (Principled next-gen modular architecture)
              ┌─────────────────────────────────────────────────┐
              │          NEXT-GEN MODULAR PLANNING LAYER        │
              │  • P0: Frozen V4 Baseline Control               │
              │  • P1: Structured State Representation          │
              │  • P2: Opponent Threat & KO Modeling            │
              │  • P3: Strict Information Boundary Probability  │
              │  • P4: Short-Horizon Counterfactual Evaluation  │
              │  • P5: Validated Gated Ensemble (τ-Threshold)   │
              └─────────────────────────────────────────────────┘
```

---

## 2. Granular Lineage Breakdown

### V2 Architecture (`CITADEL_PTCG_V2` / `ptcg-v1-r.ipynb`)
- **Core Mechanism**: Recursive tree search over game states via CABT search APIs (`search_begin`, `search_step`), minimax lookahead of depth 2 to 3, and transposition/branch deduplication.
- **Components Introduced**:
  - Search state snapshotting and position feature evaluation.
  - Turn-aware tree expansions attempting to anticipate opponent counter-actions.
  - Multi-feature weighted state scoring (HP advantage, energy attachment progress, card acceleration).
- **Failure Modes & Empirical Flaws**:
  - **Excessive Latency**: Deep search trees frequently approached per-step time limits.
  - **Information Bleed / State Inaccuracy**: Simulating future turns required making arbitrary assumptions about hidden opponent hands and deck shuffles, leading to hallucinated tactical advantages that diverged from actual game trajectories.
  - **Brittleness**: Search failures or unhandled engine exceptions caused complete step timeouts.

### V3 Architecture (`citadel_ptcg_v3_main`)
- **Core Mechanism**: Direct, deterministic tactical priority scorer evaluating legal options in $O(1)$ time per option.
- **Components Introduced**:
  - Hierarchical action scoring with distinct tier bands:
    - Attack Context / Attack Options: $\sim 18,000 - 100,000+$
    - Evolution Plays: $\sim 70,000 + (\text{attached energy} \times 500)$
    - Supporter Cards: $\sim 42,000$ (with hand size thresholds)
    - Energy Attachment: $\sim 35,000 - 39,000$ (preferring active Pokémon)
    - Item Plays: Search/draw items (Nest Ball, Ultra Ball, Poffin) prioritized over utility items.
    - Bench Deployment & Retreat logic.
- **Empirical Findings**:
  - Dramatically faster execution ($< 1$ ms per decision).
  - Outperformed deep tree search because the tactical priorities aligned directly with Pokémon TCG tempo mechanics (attaching energy every turn, evolving immediately, using supporters for hand refresh, and attacking when eligible).

### V4 Production Champion (`main.py` / `ptcg-v4 (1).ipynb` — Frozen Baseline $P_0$)
- **Core Mechanism**: Hardened contract-enforcing wrapper around the V3 tactical core.
- **Components Introduced & Proven**:
  1. **Selection Contract Validator (`validate_selection`, `legal_selection`)**:
     - Guarantees selections strictly respect `minCount` $\le |\text{selection}| \le \text{maxCount}$.
     - Filters duplicates and out-of-bounds indices.
     - Never invents an option not present in `obs.select.option`.
  2. **Kaggle Simulation Protocol Support**:
     - Handles `select=None` initial deck-selection phase by returning the complete 60-card list from `deck.csv`.
  3. **Deterministic Tie-Breaking**:
     - Scored options use `(score, -original_index, original_index)` for strict reproducibility.
  4. **Multi-Area Card Resolution (`v4_card_from_option`)**:
     - Safely traverses `hand`, `active`, `bench`, `discard`, `prize`, and `deck`.
- **Benchmark Performance**: **14/20 wins (70.0% win rate)** against standard reference decks.

### V4F / Research (`probablity-v2.ipynb` / Beam Search)
- **Core Mechanism**: Hybridizing the heuristic policy with a 4-step beam search using stochastic opponent deck guessing.
- **Experimental Additions**:
  - `get_search_kwargs()`: Randomly samples unknown cards from remaining deck cards.
  - Multi-ply beam rollouts for `SelectContext.MAIN`.
- **Risk Analysis**:
  - Violates strict information boundaries by guessing unknown prize/opponent cards uniformly.
  - Multi-ply simulation can diverge or trigger engine errors if simulated state differs from actual runtime invariants.
  - **Verdict**: Unsafe for unconditional production deployment; valuable only if isolated in a bounded counterfactual module with strict fallback.

---

## 3. Proven vs. Experimental Component Taxonomy

| Component | Proven Status | Risk Level | Design Recommendation |
| :--- | :--- | :--- | :--- |
| **Legality Contract Enforcer** | **Proven (V4)** | Zero | **Freeze & Preserve 100%** across all versions. |
| **Card Data / Metadata Resolver** | **Proven (V4)** | Zero | **Freeze & Preserve 100%**. |
| **Tactical Action Tier Scoring** | **Proven (V3/V4)** | Low | Use as the primary reference fallback. |
| **Structured Board State Features** | **Validated** | Low | Integrate in $P_1$ as non-disruptive signal. |
| **Opponent Threat & 1HKO Engine** | **Validated** | Low-Med | Integrate in $P_2$ to adjust retreat & attack targets. |
| **Known/Unknown Probability Engine**| **Validated** | Low | Integrate in $P_3$ to guide search/draw card timing. |
| **Short-Horizon Counterfactuals** | **Experimental** | Medium | Integrate in $P_4$ with strict horizon $\le 1$ and timeout guards. |
| **Gated Hybrid Ensemble ($\tau$)** | **Experimental** | Low | Integrate in $P_5$; override V4 only when $\Delta_{\text{eval}} > \tau$. |

---

## 4. Lineage Conclusions

1. **Complexity Trap**: Complex multi-turn search trees in V2 degraded performance compared to direct tactical evaluation due to branching factor explosion and imperfect information.
2. **Robustness is Supreme**: V4's dominance stems from zero-fault legality handling and consistent execution of core TCG fundamentals.
3. **Next-Gen Objective**: The next-generation architecture must **never compromise V4's legality or defensive guarantees**. Any new planning layer must be purely additive, modular, and gated by statistical anti-regression criteria.
