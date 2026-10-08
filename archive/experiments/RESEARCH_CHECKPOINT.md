# PTCG AI Research Checkpoint & Session Resumption Guide

**Checkpoint Timestamp**: 2026-08-30 (End of Session)  
**Production Status**: **FROZEN** (`main.py` and `submission_notebook.ipynb` are 100% untouched and preserved as the production control).

---

## 1. Absolute Preservation State

All files and artifacts are fully preserved and validated:
- ✅ **Production Control Baseline**: [`main.py`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/main.py) (MIKE V4 Champion, 14/20 = 70% benchmark, 49.50% self-play baseline).
- ✅ **Production Notebook**: [`submission_notebook.ipynb`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/submission_notebook.ipynb) (Frozen, no changes or submissions made).
- ✅ **P0–P6 Evaluation Suite**: [`ptcg_head_to_head_results.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/ptcg_head_to_head_results.md), [`ptcg_ablation_results.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/ptcg_ablation_results.md).
- ✅ **P7 & P8 Telemetry**: [`P7_all_components_results.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/P7_all_components_results.md), [`P7_component_interactions.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/P7_component_interactions.csv).
- ✅ **V4 6,482-Decision State Corpus**: [`v4_state_corpus.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/v4_state_corpus.csv), [`v4_error_discovery.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/v4_error_discovery.md).
- ✅ **P9 Findings (H1 & H2 Inactive)**: [`p9_h1_results.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/p9_h1_results.md), [`p9_h2_results.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/p9_h2_results.md), [`p9_hypothesis_validation.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/p9_hypothesis_validation.md).
  - *Structural Finding*: V4 already assigns playing Basic Pokémon Tier 2 ($50,000$). The deck search cards (`Mega Signal` & `Cyrano`) are legally restricted to Mega Abomasnow ex, making basic search physically impossible via `TO_HAND`.
- ✅ **Energy Attachment Audit**: [`energy_attachment_analysis.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/energy_attachment_analysis.md), [`energy_attachment_counterfactuals.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/energy_attachment_counterfactuals.csv), [`energy_attachment_hypotheses.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/energy_attachment_hypotheses.md).
  - *Finding*: 97.0% of attachments are Active $<3\text{E}$ (mandatory ramp); true over-saturation is $<0.17\%$ of states (rejected as a high-frequency target).
- ✅ **Discard Resource Audit**: [`discard_energy_analysis.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/discard_energy_analysis.md), [`discard_energy_counterfactuals.csv`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/discard_energy_counterfactuals.csv), [`discard_failure_clusters.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/discard_failure_clusters.md), [`discard_hypotheses.md`](file:///c:/Users/ayush/OneDrive/Desktop/POKEMON/discard_hypotheses.md).

---

## 2. Next Experiment to Resume From: `H_DISCARD` (Resource-Preservation)

### Empirical Grounding:
1. **370 `DISCARD_ENERGY` decisions** analyzed across 300 complete matches.
2. **350 decisions (94.6%)** presented multiple distinct legal discard cards.
3. In **182 states (49.2% of all discard prompts / 2.81% of all match decisions)**, both **Basic Water Energy** and a scarce **Draw Supporter (`Waitress` or `Lillie's Determination`)** were simultaneously legal discard options.
4. **V4 Flaw**: V4 currently scores `ENERGY` at $30,000$ and `CARD` (Supporters) at $5,000$. Because V4 picks highest-scored options, it preferentially throws away its scarce 4-of Draw Supporters to "save" an abundant Basic Water Energy (35 copies in deck).
5. **Observational Impact**: Discarding Supporters yielded **53.3% - 62.7% win rate**, while discarding surplus Energy yielded **79.7% win rate (+26.4% delta)**.

### Exact Planned Intervention for Next Session:
- **Scope**: In `DISCARD_ENERGY` context only.
- **Rule**: If **Basic Water Energy** AND **`Waitress` or `Lillie's Determination`** are simultaneously legal discard candidates, prefer discarding **Basic Water Energy**.
- **Isolation Constraint**: **No other behavior may change** (no changes to `MAIN`, `ATTACK`, `TO_HAND`, KO logic, threat logic, or retreat logic).
- **Instrumentation**: Log for each decision:
  - `V4 selected discard`
  - `H_DISCARD selected discard`
  - `all legal discard candidates`
  - `hand / resource state`
  - `prompt / context`
  - `eventual game outcome`

### Resumption Execution Protocol:
1. Implement `H_DISCARD` in strict isolation inside a test harness (e.g. `test_h_discard_regression.py`).
2. Run the established **200-game balanced head-to-head benchmark** (100 as Player 0, 100 as Player 1) against the frozen V4 control.
3. Record: W-L-D, Win Rate, 95% Wilson CI, Override Count, Override Win Conversion, Starting-Order Split, Contract Errors (must be 0), Average Game Length.
4. **Promotion Threshold**: Wilson $\text{CI}_{\text{lower}} > 50.0\%$ under 200+ balanced games with 0 contract errors.
5. Do not combine `H_DISCARD` with any other component until its isolated benchmark is complete.
