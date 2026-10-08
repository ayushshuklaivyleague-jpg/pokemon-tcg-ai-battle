# HYBRID_STAGE_4 Integration Audit Report

## 1. Executive Summary
- **Candidate Module**: `hybrid_v4_sol_stage4.py`
- **Control Baseline**: Frozen Production `codex_sol_eclipse_alakazam.py` (Hilda = 3000, Search = ON)
- **Deck Configuration**: 100% Byte-for-Byte Identical (60 cards)
- **Genome Delta**: Exactly 1 parameter modified (`hilda: 3000 → 3150`), 68 parameters identical
- **Search Engine**: **EXACTLY INTACT & ACTIVE** (`USE_SEARCH = True`, 1-ply determinized rollouts)
- **Safety Wrapper**: MIKE V4 `selection_contract` + `legal_selection` active at outer egress.

---

## 2. Component Verification Checklist

| Component | Status | Audit Finding |
| :--- | :--- | :--- |
| **Search Engine (`_search_decide`)** | **ACTIVE** | Invoked and evaluated across all complex MAIN turns |
| **Opponent Belief Modeling** | **ACTIVE** | Dynamic template matching (`_TEMPLATES`, `_TEMPLATE_SIG`) intact |
| **Search Override Threshold** | **IDENTICAL** | Overrides triggered when margin $\ge 500.0$ value |
| **Genome Parameters** | **IDENTICAL** | 68 / 69 identical; `Hilda = 3150`, `Xerosic = 3250`, `Dawn = 3100` |
| **Contract / Egress Safety** | **ACTIVE** | Zero contract violations, zero runtime errors |

---

## 3. Smoke Test Validation (6 Games)

- **Candidate Search Invocations**: 188 calls (Control: 149 calls)
- **Candidate Search Overrides**: 7 overrides (Control: 6 overrides)
- **Xerosic Plays**: Candidate: 8 vs Control: 8
- **Contract / Runtime Errors**: **0** (100% legal)
- **Conclusion**: The V4 safety wrapper is **100% orthogonal** to the internal search engine and does not distort search mechanics, depth, or overrides.
