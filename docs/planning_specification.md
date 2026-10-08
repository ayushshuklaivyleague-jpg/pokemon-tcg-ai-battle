# Pokémon TCG Modular Planning Layer — Technical Specification

This specification defines the architecture, interfaces, state schemas, threat metrics, and gating mathematics for the Next-Generation Pokémon TCG Modular Planning Layer ($P_1 \dots P_5$) built on top of the frozen $P_0$ (V4) baseline.

---

## 1. System Architecture & Invariants

```
                      ┌────────────────────────────────────────┐
                      │          Raw Observation (obs)         │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    Legality & Selection Contract       │
                      │  • minCount / maxCount extraction      │
                      │  • Option filtering & bounds check     │
                      └───────────────────┬────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
                     ▼                                         ▼
        ┌─────────────────────────┐             ┌─────────────────────────┐
        │   V4 Baseline Scorer    │             │  Modular Planning Layer │
        │   (Proven Tactical)     │             │  • State Representation │
        │                         │             │  • Threat Engine        │
        │   Score: S_v4(a_i)      │             │  • Probability Engine   │
        └────────────┬────────────┘             │  • Counterfactual Delta │
                     │                          │                         │
                     │                          │  Score: S_plan(a_i)     │
                     │                          └────────────┬────────────┘
                     │                                       │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │       Anti-Regression Gating (τ)       │
                      │                                        │
                      │  If (S_plan(a*) - S_v4(a_v4)) > τ:     │
                      │      Action = a*                       │
                      │  Else:                                 │
                      │      Action = a_v4 (Strict Fallback)   │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │     Validated Legal Selection Output   │
                      └────────────────────────────────────────┘
```

### Core Invariants
1. **Zero Legality Violation Invariant**: Every emitted action list must strictly satisfy:
   $$\min\text{Count} \le |\text{selection}| \le \min(\max\text{Count}, |\text{options}|)$$
   and contain unique, valid option indices from the current observation.
2. **Immutable Control Invariant**: The baseline $P_0$ policy remains byte-for-byte identical to the V4 champion.
3. **Graceful Fallback Invariant**: If any exception or numerical instability occurs during feature computation, planning, or counterfactual evaluation, the agent immediately defaults to the pure V4 selection.

---

## 2. Module Specifications

### Module 1: Structured State Representation (`state_features.py`)
Computes normalized board-level context vectors:
- **Active Combat Metrics**:
  - `active_hp_ratio` $= \text{HP}_{\text{active}} / \text{MaxHP}_{\text{active}} \in [0.0, 1.0]$
  - `active_energy_count`: Number of energy cards attached to active Pokémon.
  - `has_active_attacker`: Boolean indicator if active Pokémon possesses sufficient energy to execute at least one attack.
- **Bench Capacity & Energy Distribution**:
  - `bench_count` $\in [0, 5]$
  - `bench_total_energy`: Total energy cards across bench.
  - `highest_bench_energy`: Peak energy count on any single benched Pokémon.
- **Prize & Hand Pressure**:
  - `prize_differential` $= \text{OpponentPrizesRemaining} - \text{MyPrizesRemaining}$ (positive implies winning position).
  - `hand_size`: Number of playable cards in hand.
  - `supporter_played_this_turn`: Boolean flag preventing illegal supporter chaining.

---

### Module 2: Opponent Threat & KO Model (`threat_model.py`)
Evaluates immediate board dangers and lethal thresholds:
- **Opponent Damage Capacity**:
  - Estimates opponent active Pokémon's maximum theoretical damage output given current attached energies and known card attack profiles.
- **Lethal Threat Ratio ($L_{\text{threat}}$)**:
  $$L_{\text{threat}} = \frac{\text{OpponentEstimatedDamage}}{\max(1, \text{MyActiveHP})}$$
  - If $L_{\text{threat}} \ge 1.0$, our active Pokémon is in **Immediate 1-Hit Knockout (1HKO) Danger**.
  - Triggers elevated scores for tactical retreat, evolution HP boost, or defensive disruptions.
- **Opponent Bench Evolution Pressure**:
  - Detects basic Pokémon on opponent bench primed for stage-1/stage-2 evolution with attached energy.

---

### Module 3: Information-Boundary Probability Engine (`prob_info.py`)
Tracks strictly accessible game knowledge without leaking hidden variables:
- **Known Card Partition**:
  - Discard pile (public knowledge).
  - Active and bench cards (public knowledge).
  - Current hand cards (private to agent).
- **Deck Distribution Estimator**:
  - Computes remaining card frequencies:
    $$\text{CountRemaining}(c) = \text{DeckListCount}(c) - \text{KnownCount}(c)$$
  - Calculates probability of drawing specific card types (Basic Pokémon, Energy, Supporter) on next turn:
    $$P(\text{Draw Type } T) = \frac{\sum_{c \in T} \max(0, \text{CountRemaining}(c))}{\max(1, \text{EstimatedDeckSize})}$$
- **Search Item Valuation**:
  - Adjusts priority of search cards (Nest Ball, Ultra Ball, Poffin) based on whether desired targets still exist in the remaining deck.

---

### Module 4: Short-Horizon Counterfactual Evaluation (`counterfactual.py`)
Estimates the immediate resulting state value delta $\Delta V(a)$ for candidate legal actions:
$$\Delta V(a) = V(S'(a)) - V(S)$$
where $V(S)$ is the state evaluation function:
$$V(S) = w_{\text{prize}} \cdot (\text{PrizesTaken}) + w_{\text{hp}} \cdot (\text{MyHPNet}) + w_{\text{energy}} \cdot (\text{MyAttachedEnergy}) - w_{\text{threat}} \cdot (\text{OpponentThreatLevel})$$
- Evaluates actions such as:
  - **Attack Actions**: Prizes taken, opponent damage dealt, knockout confirmed.
  - **Energy Attachments**: Accelerating energy to active vs bench carry.
  - **Evolution**: Increasing max HP and unlocking stronger attack profiles.
  - **Retreat**: Swapping a critically wounded Pokémon for a healthy attacker.

---

### Module 5: Anti-Regression Gating & Hybrid Decision Engine (`planner.py`)
Combines V4 baseline scores with modular planning signals using a confidence threshold $\tau$:
1. Compute baseline V4 scores: $S_{\text{v4}}(a_i)$ for each legal option $a_i$.
2. Compute combined planning evaluation:
   $$S_{\text{plan}}(a_i) = S_{\text{v4}}(a_i) + \alpha_1 \cdot \text{StateBonus}(a_i) + \alpha_2 \cdot \text{ThreatBonus}(a_i) + \alpha_3 \cdot \text{ProbBonus}(a_i) + \alpha_4 \cdot \Delta V(a_i)$$
3. Let $a_{\text{v4}} = \arg\max_a S_{\text{v4}}(a)$ and $a^* = \arg\max_a S_{\text{plan}}(a)$.
4. Decision Rule:
   $$\text{SelectedAction} = \begin{cases} a^* & \text{if } (S_{\text{plan}}(a^*) - S_{\text{plan}}(a_{\text{v4}})) > \tau \\ a_{\text{v4}} & \text{otherwise} \end{cases}$$
5. Pass selected index through `legal_selection(obs, [SelectedAction])` to guarantee 100% contract adherence.

---

## 3. Configuration Hyperparameters

| Parameter | Symbol | Default Value | Description |
| :--- | :--- | :--- | :--- |
| **Gating Threshold** | $\tau$ | $150.0$ | Minimum required planning delta to override V4 default. |
| **Prize Weight** | $w_{\text{prize}}$ | $2500.0$ | Value per prize card taken or protected. |
| **Energy Weight** | $w_{\text{energy}}$ | $450.0$ | Value per attached usable energy. |
| **Threat Weight** | $w_{\text{threat}}$ | $600.0$ | Penalty for remaining in active 1HKO range. |
| **HP Ratio Weight**| $w_{\text{hp}}$ | $800.0$ | Value of health retention on active attacker. |
| **Draw Utility** | $w_{\text{prob}}$ | $300.0$ | Weight for optimizing draw/search probabilities. |
