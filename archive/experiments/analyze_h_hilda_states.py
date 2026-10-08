#!/usr/bin/env python3
"""
H_HILDA State-Conditioned Outcome Analysis.

Isolates all 442 Dawn → Hilda inversions from pooled 400-game telemetry,
extracts board-state features at the moment of each inversion, clusters
by outcome, and identifies state variables that explain differential
conversion rates.

Outputs:
  - h_hilda_inversion_outcomes.csv   (per-inversion feature table)
  - h_hilda_state_clusters.csv       (cluster summary)
  - Console analysis for H_HILDA_STATE_ANALYSIS.md
"""

import sys, os, re, csv, math
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent

import pandas as pd
import numpy as np

# ------------------------------------------------------------------ #
# 1.  Load and merge both telemetry CSVs
# ------------------------------------------------------------------ #
print("=" * 80)
print("H_HILDA STATE-CONDITIONED OUTCOME ANALYSIS")
print("=" * 80)

df1 = pd.read_csv(HERE / "h_hilda_decision_audit.csv", encoding="utf-8")
if "batch" not in df1.columns:
    df1.insert(0, "batch", "INITIAL_SET")

df2 = pd.read_csv(HERE / "h_hilda_confirmation_decision_audit.csv", encoding="utf-8")

df = pd.concat([df1, df2], ignore_index=True)
print(f"Pooled telemetry loaded: {len(df)} total decision records across {df['game_id'].nunique()} games.")

# ------------------------------------------------------------------ #
# 2.  Isolate Dawn → Hilda inversions
# ------------------------------------------------------------------ #
# An inversion is: control chose Dawn, candidate chose Hilda
inversions = df[
    (df["is_override"] == True) &
    (df["control_desc"].str.contains("Dawn", na=False)) &
    (df["candidate_desc"].str.contains("Hilda", na=False))
].copy()

print(f"Dawn → Hilda inversions isolated: {len(inversions)}")

# ------------------------------------------------------------------ #
# 3.  Extract board-state features from each inversion row
# ------------------------------------------------------------------ #

def count_pokemon_in_field(bench_str: str, active_str: str, name: str) -> int:
    """Count occurrences of a Pokémon name across active + bench."""
    count = 0
    for s in [str(bench_str), str(active_str)]:
        count += s.count(name)
    return count

def parse_bench_count(bench_str: str) -> int:
    """Count number of Pokémon on bench from description string."""
    s = str(bench_str)
    if s in ("Empty", "nan", "None", ""):
        return 0
    return len(s.split(","))

def has_pokemon(field_str: str, name: str) -> bool:
    return name in str(field_str)

def extract_energy_count(active_str: str) -> int:
    """Extract energy count from active Pokemon description (e.g. 'Alakazam(2E)')."""
    m = re.findall(r"\((\d+)E\)", str(active_str))
    return sum(int(x) for x in m) if m else 0

def check_xerosic_legal(legal_options: str) -> bool:
    return "Xerosic" in str(legal_options)

def check_card_in_legal(legal_options: str, card_name: str) -> bool:
    return card_name in str(legal_options)

# Feature extraction
records = []
for idx, row in inversions.iterrows():
    game_id = row["game_id"]
    batch = row.get("batch", "INITIAL_SET")
    step = row["step"]
    turn = row["turn"]
    hand_size = int(row["hand_size"]) if pd.notna(row["hand_size"]) else 0
    deck_count = int(row["deck_count"]) if pd.notna(row["deck_count"]) else 0
    my_prizes = int(row["my_prizes"]) if pd.notna(row["my_prizes"]) else 0
    opp_prizes = int(row["opp_prizes"]) if pd.notna(row["opp_prizes"]) else 0
    my_active = str(row["my_active"])
    my_bench = str(row["my_bench"])
    opp_active = str(row["opp_active"])
    opp_bench = str(row["opp_bench"])
    legal_opts = str(row["legal_options"])
    game_outcome = str(row["game_outcome"])

    # Pokémon counts
    abra_count = count_pokemon_in_field(my_bench, my_active, "Abra")
    kadabra_count = count_pokemon_in_field(my_bench, my_active, "Kadabra")
    alakazam_count = count_pokemon_in_field(my_bench, my_active, "Alakazam")
    dunsparce_count = count_pokemon_in_field(my_bench, my_active, "Dunsparce")
    dudunsparce_count = count_pokemon_in_field(my_bench, my_active, "Dudunsparce")
    total_evo_line = abra_count + kadabra_count + alakazam_count

    # Bench occupancy
    bench_count = parse_bench_count(my_bench)
    opp_bench_count = parse_bench_count(opp_bench)

    # Active energy
    active_energy = extract_energy_count(my_active)

    # Xerosic legal
    xerosic_legal = check_xerosic_legal(legal_opts)

    # Other supporters legal
    dawn_legal = check_card_in_legal(legal_opts, "Dawn")
    rare_candy_legal = check_card_in_legal(legal_opts, "Rare Candy")
    poffin_legal = check_card_in_legal(legal_opts, "Poffin")
    night_stretcher_legal = check_card_in_legal(legal_opts, "Night Stretcher")

    # Evolution stage (how far along is the Alakazam line?)
    has_alakazam = alakazam_count > 0
    has_kadabra_no_alak = kadabra_count > 0 and alakazam_count == 0
    has_only_abra = abra_count > 0 and kadabra_count == 0 and alakazam_count == 0
    evo_stage = "ALAKAZAM_UP" if has_alakazam else ("KADABRA_STAGE" if has_kadabra_no_alak else ("ABRA_ONLY" if has_only_abra else "NO_LINE"))

    # Active Pokémon type
    active_is_alakazam = "Alakazam" in my_active
    active_is_kadabra = "Kadabra" in my_active and "Alakazam" not in my_active
    active_is_abra = "Abra" in my_active and "Kadabra" not in my_active and "Alakazam" not in my_active

    # Prize differential
    prize_diff = my_prizes - opp_prizes  # positive = we're behind

    # Game phase heuristic
    if turn <= 3:
        game_phase = "EARLY"
    elif turn <= 7:
        game_phase = "MID"
    else:
        game_phase = "LATE"

    # Outcome mapping
    if game_outcome == "WIN":
        outcome_val = 1
    elif game_outcome == "LOSS":
        outcome_val = 0
    elif game_outcome == "DRAW":
        outcome_val = 0.5
    else:
        outcome_val = 0.5

    rec = {
        "batch": batch,
        "game_id": game_id,
        "step": step,
        "turn": turn,
        "hand_size": hand_size,
        "deck_count": deck_count,
        "my_prizes": my_prizes,
        "opp_prizes": opp_prizes,
        "prize_diff": prize_diff,
        "abra_count": abra_count,
        "kadabra_count": kadabra_count,
        "alakazam_count": alakazam_count,
        "total_evo_line": total_evo_line,
        "dunsparce_count": dunsparce_count,
        "dudunsparce_count": dudunsparce_count,
        "bench_count": bench_count,
        "opp_bench_count": opp_bench_count,
        "active_energy": active_energy,
        "my_active": my_active,
        "opp_active": opp_active,
        "evo_stage": evo_stage,
        "active_is_alakazam": active_is_alakazam,
        "game_phase": game_phase,
        "xerosic_legal": xerosic_legal,
        "rare_candy_legal": rare_candy_legal,
        "poffin_legal": poffin_legal,
        "night_stretcher_legal": night_stretcher_legal,
        "game_outcome": game_outcome,
        "outcome_val": outcome_val,
    }
    records.append(rec)

inv_df = pd.DataFrame(records)
print(f"Feature extraction complete: {len(inv_df)} inversion records with {len(inv_df.columns)} features.")

# Save per-inversion outcomes
inv_df.to_csv(HERE / "h_hilda_inversion_outcomes.csv", index=False, encoding="utf-8")
print(f"Wrote h_hilda_inversion_outcomes.csv")

# ------------------------------------------------------------------ #
# 4.  Game-level outcome aggregation per inversion game
# ------------------------------------------------------------------ #
# Multiple inversions can occur in the same game. Aggregate at game level.
game_outcomes = inv_df.groupby("game_id").agg(
    inversions_in_game=("step", "count"),
    game_outcome=("game_outcome", "first"),
    outcome_val=("outcome_val", "first"),
    avg_turn=("turn", "mean"),
    avg_hand_size=("hand_size", "mean"),
    avg_deck_count=("deck_count", "mean"),
    any_xerosic_legal=("xerosic_legal", "any"),
    any_alakazam_up=("active_is_alakazam", "any"),
    max_alakazam=("alakazam_count", "max"),
    max_kadabra=("kadabra_count", "max"),
    min_evo_stage=("evo_stage", "first"),
).reset_index()

total_inv_games = len(game_outcomes)
wins = (game_outcomes["game_outcome"] == "WIN").sum()
losses = (game_outcomes["game_outcome"] == "LOSS").sum()
draws = (game_outcomes["game_outcome"] == "DRAW").sum()
decisive_wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0

print(f"\n--- GAME-LEVEL OVERVIEW (Inversion Games Only) ---")
print(f"Total games with Dawn→Hilda inversions: {total_inv_games}")
print(f"Record: {wins}W - {losses}L - {draws}D")
print(f"Decisive WR: {decisive_wr:.1f}%")

# ------------------------------------------------------------------ #
# 5.  State variable distribution analysis
# ------------------------------------------------------------------ #
print("\n" + "=" * 80)
print("STATE VARIABLE DISTRIBUTIONS ACROSS INVERSIONS")
print("=" * 80)

# Turn distribution
print("\n--- Turn Distribution ---")
turn_dist = inv_df["turn"].value_counts().sort_index()
for t, c in turn_dist.items():
    print(f"  Turn {t}: {c} inversions ({c/len(inv_df)*100:.1f}%)")

# Evo stage distribution
print("\n--- Evolution Stage at Inversion ---")
evo_dist = inv_df["evo_stage"].value_counts()
for stage, c in evo_dist.items():
    print(f"  {stage}: {c} inversions ({c/len(inv_df)*100:.1f}%)")

# Hand size distribution
print("\n--- Hand Size Distribution ---")
hs_stats = inv_df["hand_size"].describe()
print(f"  Mean: {hs_stats['mean']:.1f}, Median: {hs_stats['50%']:.1f}, Std: {hs_stats['std']:.1f}")
print(f"  Min: {hs_stats['min']:.0f}, Max: {hs_stats['max']:.0f}")

# Xerosic co-legality
print("\n--- Xerosic Co-Legality ---")
xero_legal_count = inv_df["xerosic_legal"].sum()
print(f"  Xerosic also legal: {xero_legal_count} / {len(inv_df)} ({xero_legal_count/len(inv_df)*100:.1f}%)")

# ------------------------------------------------------------------ #
# 6.  Outcome analysis by state variable
# ------------------------------------------------------------------ #
print("\n" + "=" * 80)
print("OUTCOME ANALYSIS BY STATE VARIABLE")
print("=" * 80)

def wilson_ci(k, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    spread = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / denom
    return p, max(0, center - spread), min(1, center + spread)

def analyze_by_var(df_inv, var_name, var_label, bins=None):
    """Analyze game outcomes partitioned by a state variable."""
    print(f"\n--- Outcome by {var_label} ---")

    if bins is not None:
        df_inv = df_inv.copy()
        df_inv[f"{var_name}_bin"] = pd.cut(df_inv[var_name], bins=bins)
        group_col = f"{var_name}_bin"
    else:
        group_col = var_name

    # Aggregate at game level per group
    # For each inversion, take its game_id and outcome
    grouped = df_inv.groupby([group_col, "game_id"]).agg(
        game_outcome=("game_outcome", "first"),
    ).reset_index()

    summary_rows = []
    for grp, gdf in grouped.groupby(group_col):
        n_games = len(gdf)
        w = (gdf["game_outcome"] == "WIN").sum()
        l = (gdf["game_outcome"] == "LOSS").sum()
        d = (gdf["game_outcome"] == "DRAW").sum()
        decisive = w + l
        dwr = w / decisive * 100 if decisive > 0 else float("nan")
        p, lo, hi = wilson_ci(w, decisive) if decisive > 0 else (0, 0, 0)
        print(f"  {grp}: {n_games} games, {w}W-{l}L-{d}D, Decisive WR: {dwr:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]")
        summary_rows.append({
            "variable": var_label,
            "group": str(grp),
            "games": n_games,
            "wins": w,
            "losses": l,
            "draws": d,
            "decisive_wr": round(dwr, 2),
            "ci_lo": round(lo * 100, 2),
            "ci_hi": round(hi * 100, 2),
        })
    return summary_rows

all_cluster_rows = []

# 6a. Evolution Stage
all_cluster_rows += analyze_by_var(inv_df, "evo_stage", "Evolution Stage")

# 6b. Game Phase
all_cluster_rows += analyze_by_var(inv_df, "game_phase", "Game Phase")

# 6c. Hand Size
hs_median = inv_df["hand_size"].median()
inv_df["hand_size_group"] = inv_df["hand_size"].apply(
    lambda x: f"Low (≤{int(hs_median)})" if x <= hs_median else f"High (>{int(hs_median)})"
)
all_cluster_rows += analyze_by_var(inv_df, "hand_size_group", "Hand Size Group")

# 6d. Bench count
inv_df["bench_group"] = inv_df["bench_count"].apply(
    lambda x: "0-2 Bench" if x <= 2 else "3-4 Bench" if x <= 4 else "5 Bench"
)
all_cluster_rows += analyze_by_var(inv_df, "bench_group", "Bench Occupancy")

# 6e. Xerosic co-legality
inv_df["xerosic_group"] = inv_df["xerosic_legal"].apply(
    lambda x: "Xerosic Legal" if x else "Xerosic NOT Legal"
)
all_cluster_rows += analyze_by_var(inv_df, "xerosic_group", "Xerosic Co-Legality")

# 6f. Alakazam count on field
inv_df["alak_group"] = inv_df["alakazam_count"].apply(
    lambda x: "0 Alakazam" if x == 0 else "1 Alakazam" if x == 1 else "2+ Alakazam"
)
all_cluster_rows += analyze_by_var(inv_df, "alak_group", "Alakazam Count on Field")

# 6g. Kadabra on field (needing evolution)
inv_df["kadabra_group"] = inv_df["kadabra_count"].apply(
    lambda x: "0 Kadabra" if x == 0 else "1+ Kadabra"
)
all_cluster_rows += analyze_by_var(inv_df, "kadabra_group", "Kadabra on Field")

# 6h. Prize differential
inv_df["prize_group"] = inv_df["prize_diff"].apply(
    lambda x: "Ahead (prize_diff<0)" if x < 0 else "Even (prize_diff=0)" if x == 0 else "Behind (prize_diff>0)"
)
all_cluster_rows += analyze_by_var(inv_df, "prize_group", "Prize Differential")

# 6i. Deck count bins
deck_median = inv_df["deck_count"].median()
inv_df["deck_group"] = inv_df["deck_count"].apply(
    lambda x: f"Low Deck (≤{int(deck_median)})" if x <= deck_median else f"High Deck (>{int(deck_median)})"
)
all_cluster_rows += analyze_by_var(inv_df, "deck_group", "Deck Count")

# 6j. Dudunsparce status
inv_df["dudun_group"] = inv_df["dudunsparce_count"].apply(
    lambda x: "No Dudunsparce" if x == 0 else "Has Dudunsparce"
)
all_cluster_rows += analyze_by_var(inv_df, "dudun_group", "Dudunsparce Status")

# ------------------------------------------------------------------ #
# 7.  Interaction analysis: Multi-variable clusters
# ------------------------------------------------------------------ #
print("\n" + "=" * 80)
print("MULTI-VARIABLE INTERACTION CLUSTERS")
print("=" * 80)

# Key interaction: Evo Stage × Xerosic Legality
print("\n--- Evo Stage × Xerosic Co-Legality ---")
for evo in ["ABRA_ONLY", "KADABRA_STAGE", "ALAKAZAM_UP", "NO_LINE"]:
    for xero in [True, False]:
        mask = (inv_df["evo_stage"] == evo) & (inv_df["xerosic_legal"] == xero)
        sub = inv_df[mask]
        if len(sub) == 0:
            continue
        game_agg = sub.groupby("game_id").agg(outcome=("game_outcome", "first")).reset_index()
        w = (game_agg["outcome"] == "WIN").sum()
        l = (game_agg["outcome"] == "LOSS").sum()
        d = (game_agg["outcome"] == "DRAW").sum()
        decisive = w + l
        dwr = w / decisive * 100 if decisive > 0 else float("nan")
        p, lo, hi = wilson_ci(w, decisive) if decisive > 0 else (0, 0, 0)
        xero_str = "Xerosic Legal" if xero else "Xerosic NOT Legal"
        label = f"{evo} + {xero_str}"
        print(f"  {label}: {len(game_agg)}g, {w}W-{l}L-{d}D, DWR: {dwr:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]")
        all_cluster_rows.append({
            "variable": "EvoStage×Xerosic",
            "group": label,
            "games": len(game_agg),
            "wins": w, "losses": l, "draws": d,
            "decisive_wr": round(dwr, 2),
            "ci_lo": round(lo * 100, 2),
            "ci_hi": round(hi * 100, 2),
        })

# Key interaction: Evo Stage × Game Phase
print("\n--- Evo Stage × Game Phase ---")
for evo in ["ABRA_ONLY", "KADABRA_STAGE", "ALAKAZAM_UP", "NO_LINE"]:
    for phase in ["EARLY", "MID", "LATE"]:
        mask = (inv_df["evo_stage"] == evo) & (inv_df["game_phase"] == phase)
        sub = inv_df[mask]
        if len(sub) == 0:
            continue
        game_agg = sub.groupby("game_id").agg(outcome=("game_outcome", "first")).reset_index()
        w = (game_agg["outcome"] == "WIN").sum()
        l = (game_agg["outcome"] == "LOSS").sum()
        d = (game_agg["outcome"] == "DRAW").sum()
        decisive = w + l
        dwr = w / decisive * 100 if decisive > 0 else float("nan")
        p, lo, hi = wilson_ci(w, decisive) if decisive > 0 else (0, 0, 0)
        label = f"{evo} + {phase}"
        print(f"  {label}: {len(game_agg)}g, {w}W-{l}L-{d}D, DWR: {dwr:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]")
        all_cluster_rows.append({
            "variable": "EvoStage×Phase",
            "group": label,
            "games": len(game_agg),
            "wins": w, "losses": l, "draws": d,
            "decisive_wr": round(dwr, 2),
            "ci_lo": round(lo * 100, 2),
            "ci_hi": round(hi * 100, 2),
        })

# Key interaction: Kadabra on field × Rare Candy legal
print("\n--- Kadabra Present × Rare Candy Legal ---")
for kad in [True, False]:
    for rc in [True, False]:
        mask = (inv_df["kadabra_count"] > 0) == kad
        mask &= inv_df["rare_candy_legal"] == rc
        sub = inv_df[mask]
        if len(sub) == 0:
            continue
        game_agg = sub.groupby("game_id").agg(outcome=("game_outcome", "first")).reset_index()
        w = (game_agg["outcome"] == "WIN").sum()
        l = (game_agg["outcome"] == "LOSS").sum()
        d = (game_agg["outcome"] == "DRAW").sum()
        decisive = w + l
        dwr = w / decisive * 100 if decisive > 0 else float("nan")
        p, lo, hi = wilson_ci(w, decisive) if decisive > 0 else (0, 0, 0)
        kad_str = "Kadabra Present" if kad else "No Kadabra"
        rc_str = "RC Legal" if rc else "RC NOT Legal"
        label = f"{kad_str} + {rc_str}"
        print(f"  {label}: {len(game_agg)}g, {w}W-{l}L-{d}D, DWR: {dwr:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]")
        all_cluster_rows.append({
            "variable": "Kadabra×RareCandy",
            "group": label,
            "games": len(game_agg),
            "wins": w, "losses": l, "draws": d,
            "decisive_wr": round(dwr, 2),
            "ci_lo": round(lo * 100, 2),
            "ci_hi": round(hi * 100, 2),
        })

# ------------------------------------------------------------------ #
# 8.  Identify strongest / weakest state clusters
# ------------------------------------------------------------------ #
print("\n" + "=" * 80)
print("TOP POSITIVE & NEGATIVE STATE CLUSTERS (by Decisive WR)")
print("=" * 80)

cluster_df = pd.DataFrame(all_cluster_rows)
# Filter clusters with at least 3 decisive games
sig_clusters = cluster_df[(cluster_df["wins"] + cluster_df["losses"]) >= 3].copy()
sig_clusters = sig_clusters.sort_values("decisive_wr", ascending=False)

print("\n--- TOP 10 POSITIVE CLUSTERS (Hilda advantage) ---")
top_pos = sig_clusters.head(10)
for _, r in top_pos.iterrows():
    print(f"  {r['variable']}: {r['group']} -> {r['wins']}W-{r['losses']}L-{r['draws']}D, DWR: {r['decisive_wr']}% [{r['ci_lo']}%, {r['ci_hi']}%] ({r['games']}g)")

print("\n--- TOP 10 NEGATIVE CLUSTERS (Dawn was better) ---")
top_neg = sig_clusters.tail(10).sort_values("decisive_wr")
for _, r in top_neg.iterrows():
    print(f"  {r['variable']}: {r['group']} -> {r['wins']}W-{r['losses']}L-{r['draws']}D, DWR: {r['decisive_wr']}% [{r['ci_lo']}%, {r['ci_hi']}%] ({r['games']}g)")

# Save cluster summary
cluster_df.to_csv(HERE / "h_hilda_state_clusters.csv", index=False, encoding="utf-8")
print(f"\nWrote h_hilda_state_clusters.csv ({len(cluster_df)} rows)")

# ------------------------------------------------------------------ #
# 9.  Coverage analysis: What fraction of inversions fall in top clusters?
# ------------------------------------------------------------------ #
print("\n" + "=" * 80)
print("COVERAGE & CONDITIONAL POLICY ANALYSIS")
print("=" * 80)

# Analyze: If we restricted Hilda > Dawn to only evo_stage != ALAKAZAM_UP,
# how many inversions and what outcome?
for evo_filter in ["ABRA_ONLY", "KADABRA_STAGE", "ALAKAZAM_UP"]:
    mask = inv_df["evo_stage"] == evo_filter
    sub = inv_df[mask]
    game_agg = sub.groupby("game_id").agg(outcome=("game_outcome", "first")).reset_index()
    w = (game_agg["outcome"] == "WIN").sum()
    l = (game_agg["outcome"] == "LOSS").sum()
    d = (game_agg["outcome"] == "DRAW").sum()
    decisive = w + l
    dwr = w / decisive * 100 if decisive > 0 else float("nan")
    pct = len(sub) / len(inv_df) * 100
    print(f"  If Hilda only when {evo_filter}: {len(sub)} inversions ({pct:.1f}%), {len(game_agg)}g, {w}W-{l}L-{d}D, DWR: {dwr:.1f}%")

# Composite condition: pre-Alakazam AND no Xerosic
print("\n--- Composite: Pre-Alakazam + No Xerosic Legal ---")
mask_composite = (inv_df["evo_stage"].isin(["ABRA_ONLY", "KADABRA_STAGE"])) & (~inv_df["xerosic_legal"])
sub = inv_df[mask_composite]
game_agg = sub.groupby("game_id").agg(outcome=("game_outcome", "first")).reset_index()
w = (game_agg["outcome"] == "WIN").sum()
l = (game_agg["outcome"] == "LOSS").sum()
d = (game_agg["outcome"] == "DRAW").sum()
decisive = w + l
dwr = w / decisive * 100 if decisive > 0 else float("nan")
p, lo, hi = wilson_ci(w, decisive) if decisive > 0 else (0, 0, 0)
pct = len(sub) / len(inv_df) * 100
print(f"  Inversions: {len(sub)} ({pct:.1f}%), Games: {len(game_agg)}, {w}W-{l}L-{d}D, DWR: {dwr:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]")

# Composite: Pre-Alakazam (with or without Xerosic)
print("\n--- Composite: Pre-Alakazam (any Xerosic) ---")
mask_pre = inv_df["evo_stage"].isin(["ABRA_ONLY", "KADABRA_STAGE"])
sub = inv_df[mask_pre]
game_agg = sub.groupby("game_id").agg(outcome=("game_outcome", "first")).reset_index()
w = (game_agg["outcome"] == "WIN").sum()
l = (game_agg["outcome"] == "LOSS").sum()
d = (game_agg["outcome"] == "DRAW").sum()
decisive = w + l
dwr = w / decisive * 100 if decisive > 0 else float("nan")
p, lo, hi = wilson_ci(w, decisive) if decisive > 0 else (0, 0, 0)
pct = len(sub) / len(inv_df) * 100
print(f"  Inversions: {len(sub)} ({pct:.1f}%), Games: {len(game_agg)}, {w}W-{l}L-{d}D, DWR: {dwr:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]")

# Composite: Alakazam already up
print("\n--- Composite: Alakazam Already Up ---")
mask_alak = inv_df["evo_stage"] == "ALAKAZAM_UP"
sub = inv_df[mask_alak]
game_agg = sub.groupby("game_id").agg(outcome=("game_outcome", "first")).reset_index()
w = (game_agg["outcome"] == "WIN").sum()
l = (game_agg["outcome"] == "LOSS").sum()
d = (game_agg["outcome"] == "DRAW").sum()
decisive = w + l
dwr = w / decisive * 100 if decisive > 0 else float("nan")
p, lo, hi = wilson_ci(w, decisive) if decisive > 0 else (0, 0, 0)
pct = len(sub) / len(inv_df) * 100
print(f"  Inversions: {len(sub)} ({pct:.1f}%), Games: {len(game_agg)}, {w}W-{l}L-{d}D, DWR: {dwr:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]")

# ------------------------------------------------------------------ #
# 10.  Summary statistics for report
# ------------------------------------------------------------------ #
print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
print(f"Total inversions analyzed: {len(inv_df)}")
print(f"Unique games with inversions: {inv_df['game_id'].nunique()}")
print(f"Output files:")
print(f"  - h_hilda_inversion_outcomes.csv ({len(inv_df)} rows)")
print(f"  - h_hilda_state_clusters.csv ({len(cluster_df)} rows)")
