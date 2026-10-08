# Next Sol Eclipse Weakness Audit & Candidate Ranking

**Research Branch**: Post-`H_XEROSIC` Isolation & Genome Mining  
**Dataset Corpus**: 18,654 total decisions across `h_xerosic_decision_audit.csv` (15,012) and `sol_eclipse_decision_audit.csv` (3,642).  
**Multi-Choice Decisions**: 17,225 (92.34% of corpus).  
**Production Status**: FROZEN (`codex_sol_eclipse_alakazam.py` unmodified).  

---

## 1. Key Lessons from `H_XEROSIC`

The rejection of `H_XEROSIC` provided critical empirical insight into the Sol Eclipse Alakazam architecture:
1. **Opponent Hand Suppression is Defensive**: Alakazam deals damage scaling directly with hand size ($20 \times \text{hand size}$). `Xerosic's Machinations` reduces the opponent's hand to 3 cards, dropping incoming attack damage from 240+ down to 60. Demoting Xerosic left opponents with lethal OHKO capabilities on return turns.
2. **True In-Archetype Weakness Must Focus on Self-Consistency**: In combo-centric archetypes, self-development bottlenecks (deterministic search vs random top-decking, resource preservation, evolution timing) determine whether the player can establish the Alakazam + Dudunsparce engine smoothly without bricking.

---

## 2. Comprehensive Candidate Ranking

Across the 18,654-decision corpus, all multi-choice competitions between legal actions were extracted and audited against five strict criteria:
- **Legal alternative**: Both actions were genuinely legal and available in `MAIN` context.
- **Heuristic selection**: Choice was directly determined by `WEIGHTS` score differential.
- **Material difference**: Actions represent qualitatively distinct game actions (e.g. search vs blind draw).
- **Causal plausibility**: Clear mechanical reason why the alternative produces better board states.
- **Statistical frequency**: Occurs frequently enough to produce high-powered experimental signals.

| Rank | Candidate ID | Action Competition | Weight Parameter Affected | Current Scores (Margin) | Corpus Frequency | Decisive WR | Est. Match Activation |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **1** | **`CAND_HILDA_OVER_DAWN`** | **`Hilda` (Targeted Search) vs `Dawn` (Blind Draw)** | **`WEIGHTS["hilda"]` vs `WEIGHTS["dawn"]`** | **3000 vs 3100 (100 pts)** | **401 (2.15%)** | **90.3%** | **45.0%** |
| **2** | **`CAND_RARE_CANDY_PRESERVE`** | `Kadabra Manual` vs `Rare Candy` | `WEIGHTS["rare_candy"]` | 6051 vs 16000 (9,949 pts) | 51 (0.27%) | 96.3% | 22.0% |
| **3** | **`CAND_NIGHT_STRETCHER_OVER_ASH`** | `Night Stretcher` (to Hand) vs `Sacred Ash` (to Deck) | `WEIGHTS["sacred_ash_hi"]` | 13000 vs 13500 (500 pts) | 43 (0.23%) | 90.3% | 18.0% |
| **4** | **`CAND_DUDUN_EVO`** | `Dudunsparce Evo` vs `Kadabra Evo` | Hardcoded bonus (+80 vs +100) | 6031 vs 6051 (20 pts) | 139 (0.75%) | 96.6% | 35.0% |

---

## 3. Deep Dive: The Strongest Surviving Weakness (`H_HILDA`)

### A. The Structural Bottleneck
In `codex_sol_eclipse_alakazam.py`:
- `WEIGHTS["dawn"] = 3100`
- `WEIGHTS["hilda"] = 3000`

Whenever both `Dawn` and `Hilda` are in hand (and `Xerosic` is not triggered):
- `Dawn` is scored at **3100**.
- `Hilda` is scored at **3000**.
- `Dawn` is selected **100% of the time** over `Hilda` due to the 100-point heuristic preference.

### B. Why Prioritizing `Dawn` over `Hilda` is Strategically Flawed
1. **Blind Top-Deck Draw vs Targeted Piece Assembly**:
   - `Dawn` draws the top 3 cards from the deck blindly. In mid-game states, drawing 3 random cards frequently pulls basic energy, redundant basic Pokémon, or unplayable items, failing to solve the immediate board need.
   - `Hilda` searches the deck for **2 specific cards** (Pokémon/Energy/Supporters via Hilda's selection protocol). It deterministically finds the exact missing evolution piece (e.g. Alakazam to evolve Kadabra, Dudunsparce to cycle, or Telepath Energy to power an attack).
2. **Combo Deck Precision**:
   - Sol Eclipse requires specific multi-card synergies (Abra $\to$ Kadabra $\to$ Alakazam + Energy + Dudunsparce draw engine). Deterministic search is mathematically superior to blind 3-card draw when 1 or 2 specific pieces are required to unlock lethal damage.
3. **No Compromise of Opponent Hand Control**:
   - Unlike `H_XEROSIC`, promoting `Hilda` over `Dawn` does not alter `Xerosic's Machinations` (3250). When the opponent has $\ge 6$ cards, `Xerosic` will still execute its critical defensive hand suppression.

### C. Confound & Activation Analysis
- **Decision Count**: 401 decisions across the 18,654 corpus (2.33% of all multi-choice decisions).
- **Match-Level Occurrence**: In 45.0% of all games, the player holds both Dawn and Hilda simultaneously.
- **Score Margin**: Exactly 100 points ($3100 - 3000 = 100$). A single isolated weight increase on `WEIGHTS["hilda"]` cleanly flips the preference without touching any other tier in the genome.

---

## 4. Isolated Candidate Specification

- **Candidate Name**: `H_HILDA`
- **Target Genome Key**: `WEIGHTS["hilda"]`
- **Current Baseline Value**: `3000`
- **Proposed Experimental Value**: `3150` (Placing Hilda strictly above Dawn at 3100 and Eri at 3150, but safely below Xerosic at 3250, Lana at 4249, and Lillie at 3400).
- **Expected Override Rate**: ~2.5% to 3.0% of total game decisions.
- **Expected Match Activation Rate**: ~40% to 45% of matches.

---

## 5. Benchmarking Protocol (Ready Upon Approval)

1. **Environment**: Separate experimental script (`test_h_hilda_parallel.py`). Production file remains frozen and untouched.
2. **Single Parameter Isolation**: Only `WEIGHTS["hilda"]: 3000 → 3150`. All other 68 parameters, search settings, decks, and contracts identical.
3. **Sample Size**: 200 head-to-head balanced matches against frozen Control (100 as Player 0, 100 as Player 1).
4. **Instrumentation**: Full logging of decisions, Dawn vs Hilda choices, action overrides, match outcomes, and 95% Wilson confidence intervals.
5. **Promotion Standard**: Statistically significant positive win rate improvement over frozen baseline under Wilson 95% CI.
