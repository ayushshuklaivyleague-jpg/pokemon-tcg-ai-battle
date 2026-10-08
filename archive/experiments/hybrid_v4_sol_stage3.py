#!/usr/bin/env python3
"""
HYBRID_STAGE_3: MIKE V4 x Sol Eclipse Alakazam.
Combines:
  Layer 1: MIKE V4 Strict Selection Contract & Safe Fallback Framework
  Layer 2: Sol Eclipse Rich Multi-Zone State & Opponent Modeling
  Layer 3: Deterministic Baseline Heuristic Policy
  Layer 4: Validated Parameterized Genome (Hilda=3150, Xerosic=3250, Dawn=3100)

Disabled:
  Layer 5: Search (ENABLE_SEARCH = False)
  Layer 6: Advanced Overrides (ENABLE_ADVANCED_OVERRIDES = False)
"""

import sys
import os
import re
import csv
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cg.api as api
from cg.api import (
    to_observation_class,
    SelectContext,
    OptionType,
    AreaType,
    CardType,
    all_card_data,
)

# Load Deck
source_file = HERE / "codex_sol_eclipse_alakazam.py"
raw_code = source_file.read_text(encoding="utf-8")
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
if not deck_match:
    raise RuntimeError("Failed to parse DECK_SOURCE from codex_sol_eclipse_alakazam.py")
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]

# Card Database
try:
    all_cards = all_card_data()
    card_table = {c.cardId: c for c in all_cards}
except Exception:
    card_table = {}

# Card IDs
Abra = 741
Kadabra = 742
Alakazam = 743
Dunsparce65 = 65
Dunsparce305 = 305
Dudunsparce = 66
Fezandipiti_ex = 140
Genesect = 142
Shaymin = 343
Psyduck = 858
Fan_Rotom = 174
Rare_Candy = 1079
Enhanced_Hammer = 1081
Buddy_Buddy_Poffin = 1086
Night_Stretcher = 1097
Meddling_Memo = 1103
Sacred_Ash = 1129
Wondrous_Patch = 1146
Poke_Pad = 1152
Switch = 1123
Lucky_Helmet = 1156
Hero_Cape = 1159
Air_Balloon = 1184
Fan_Rotom_Tool = 1197
Dawn = 1231
Lillie_Det = 1227
Hilda = 1225
Lanas_Aid = 1182
Boss_Orders = 1137
Xerosic = 1247
Eri = 1219
Neutralization_Zone = 1147
Battle_Cage = 1204
Nighttime_Mine = 1185
Jamming_Tower = 1122
Mist_Energy = 11
Rock_Fighting_Energy = 14
Enriching_Energy = 16
Basic_Psychic_Energy = 5
Telepath_Psychic_Energy = 19
TEAM_ROCKET_ENERGY = 15

Dreepy = 654
Drakloak = 655
Dragapult_ex = 656
Impidimp_G = 646
Morgrem_G = 647
Grimmsnarl_ex = 648
Munkidori = 104
Duskull = 54
Slowpoke_IDs = (85, 86)
Froakie_IDs = (109, 110)
Wellspring_Mask_Ogerpon_ex = 107
N_Darumaka = 724

ATTACK_POWERFUL_HAND = 1072
ATTACK_SUPER_PSY_BOLT = 1071
ATTACK_TELEPORTATION = 1070

ABRA_LINE = (Abra, Kadabra, Alakazam)
DUNSPARCE_IDS = (Dunsparce65, Dunsparce305)
PSYCHIC_ENERGY_IDS = (Basic_Psychic_Energy, Telepath_Psychic_Energy)
OUR_STADIUMS = (Neutralization_Zone, Battle_Cage, Nighttime_Mine, Jamming_Tower)

# ============================================================
# LAYER 4: PARAMETERIZED GENOME (Validated Weights)
# ============================================================
WEIGHTS = {
    # PLAY: Pokémon
    "play_pokemon_base": 20000,
    "play_abra_early": 604, "play_abra_need": 200, "play_abra_extra": 50,
    "play_dun_first_early": 178, "play_dun_first_late": 70, "play_dun_second": 50, "play_dun_ex": 59,
    "play_fez": 20080, "play_genesect": 20100, "play_psyduck": 20300, "play_shaymin": 19807, "play_fanrotom": 20250,
    "play_bench_penalty": 3923,
    # PLAY: Trainers
    "poffin_early": 18000, "poffin_fallback": 4083, "poffin_late": 15000,
    "pokepad_early": 17000, "pokepad_need": 14000, "pokepad_ok": 12000,
    "rare_candy": 16000,
    "night_stretcher_mon": 13000, "night_stretcher_energy": 11000,
    "sacred_ash_hi": 13500, "sacred_ash_lo": 11000,
    "hammer_target": 6500, "hammer_any": 6993,
    "wondrous_patch": 8500, "meddling_memo": 6000,
    "boss_kill": 2262,
    # Validated Supporter Genome:
    "hilda": 3150,           # VALIDATED PROMOTION PARAMETER
    "dawn_emergency": 16500,
    "dawn": 3100,            # Baseline draw supporter
    "lillie": 3400, "lana": 4249,
    "xerosic": 3250,         # Validated hand suppression (>= 6 cards)
    "eri": 3150,
    "nz_ex": 19500, "nz_counter": 7500,
    "cage_counter": 19000, "cage_snipe": 18500,
    "mine_counter": 18495, "jamming_tools": 18900, "jamming_counter": 18700,
    # ATTACH
    "helmet": 7000, "fan_abra": 4301, "fan_genesect": 5611, "balloon": 7300,
    "cape_alak": 9800, "cape_kadabra": 9600, "cape_abra": 7500,
    "energy_retreat": 9500, "energy_abra": 8000,
    "enriching_2nd": 6249, "enriching_1st": 2000,
    "mist_2nd": 4200, "mist_retreat": 9400,
    # EVOLVE / ABILITY / RETREAT / ATTACK
    "evolve_base": 5951,
    "ability_dudun": 30000, "ability_fez": 38066, "ability_fanrotom": 29500, "ability_default": 38085,
    "retreat_kadabra": 2500, "retreat_promote": 2000,
    "attack_base": 1000, "attack_powerful": 655, "attack_psybolt_kill": 600, "attack_psybolt": 127, "attack_teleport": 67,
}
W = WEIGHTS

# Global runtime flags
ENABLE_BASE_POLICY = True
ENABLE_STATE_LAYER = True
ENABLE_HILDA_PRIORITY = True
ENABLE_SEARCH = False                  # STRICTLY DISABLED IN STAGE 3
ENABLE_ADVANCED_OVERRIDES = False      # STRICTLY DISABLED IN STAGE 3

pre_turn = -1
ability_used_dudunsparce = False
ability_used_fezandipiti = False


# ============================================================
# LAYER 1: MIKE V4 SELECTION CONTRACT & SAFE ACCESSORS
# ============================================================

def safe_get(obj, name, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def safe_list(value):
    if value is None:
        return []
    try:
        return list(value)
    except Exception:
        return []


def selection_contract(obs):
    """
    MIKE V4 Exact selection constraint validator.
    """
    sel = safe_get(obs, "select", None)
    if sel is None:
        return {"option_count": 0, "min_count": 0, "max_count": 0, "context": None}

    options = safe_list(safe_get(sel, "option", []))
    opt_count = len(options)
    min_c = max(0, int(safe_get(sel, "minCount", 0) or 0))
    max_c = max(0, int(safe_get(sel, "maxCount", opt_count) or opt_count))

    max_c = min(max_c, opt_count)
    min_c = min(min_c, max_c)

    return {
        "option_count": opt_count,
        "min_count": min_c,
        "max_count": max_c,
        "context": safe_get(sel, "context", None),
    }


def legal_selection(obs, selected: List[int]) -> List[int]:
    """
    MIKE V4 Egress clamp enforcing engine bounds.
    """
    contract = selection_contract(obs)
    opt_count = contract["option_count"]
    min_c = contract["min_count"]
    max_c = contract["max_count"]

    if opt_count == 0:
        return []

    # Filter out of bounds and duplicates
    valid = []
    seen = set()
    for idx in selected:
        if isinstance(idx, int) and 0 <= idx < opt_count and idx not in seen:
            valid.append(idx)
            seen.add(idx)

    # Pad if below minimum
    if len(valid) < min_c:
        for idx in range(opt_count):
            if idx not in seen:
                valid.append(idx)
                seen.add(idx)
                if len(valid) >= min_c:
                    break

    # Truncate if above maximum
    if len(valid) > max_c:
        valid = valid[:max_c]

    return valid


def get_card(obs, area, index, player_index):
    try:
        p = obs.current.players[player_index]
        if area == AreaType.HAND: return p.hand[index]
        if area == AreaType.ACTIVE: return p.active[index]
        if area == AreaType.BENCH: return p.bench[index]
        if area == AreaType.DISCARD: return p.discard[index]
    except Exception:
        pass
    return None


def count_special_defense_energies(pokemon):
    if not pokemon: return 0
    return sum(1 for ec in pokemon.energyCards if ec.id in (Mist_Energy, Rock_Fighting_Energy))


# ============================================================
# LAYER 2 & 3: RICH STATE REPRESENTATION & HEURISTIC ENGINE
# ============================================================

def heuristic_scores(obs) -> List[float]:
    state = obs.current
    select = obs.select
    context = select.context
    my_index = state.yourIndex
    my_state = state.players[my_index]
    op_state = state.players[1 - my_index]
    my_prize_count = len(my_state.prize)

    global pre_turn, ability_used_dudunsparce, ability_used_fezandipiti
    if pre_turn != state.turn:
        pre_turn = state.turn
        ability_used_dudunsparce = False
        ability_used_fezandipiti = False

    # Layer 2: Rich State Counters
    field_counts = defaultdict(int)
    hand_counts = defaultdict(int)
    discard_counts = defaultdict(int)

    my_field = []
    for card in my_state.active:
        if card is not None:
            field_counts[card.id] += 1
            my_field.append((0, card))
    for idx, card in enumerate(my_state.bench):
        if card is not None:
            field_counts[card.id] += 1
            my_field.append((idx + 1, card))
    for card in my_state.hand:
        hand_counts[card.id] += 1
    for card in my_state.discard:
        discard_counts[card.id] += 1

    abra_line_on_field = sum(field_counts[x] for x in ABRA_LINE)
    dunsparce_on_field = sum(field_counts[x] for x in DUNSPARCE_IDS)
    dunsparce_line_on_field = dunsparce_on_field + field_counts[Dudunsparce]

    # Opponent Modeling
    op_all_pokemon = [p for p in (op_state.active + op_state.bench) if p is not None]
    op_has_dragapult_line = any(p.id in (Dreepy, Drakloak, Dragapult_ex) for p in op_all_pokemon)
    op_has_grimmsnarl = any(p.id in (Impidimp_G, Morgrem_G, Grimmsnarl_ex, Munkidori) for p in op_all_pokemon)
    op_has_ex = any((cd := card_table.get(p.id)) and (cd.ex or cd.megaEx) for p in op_all_pokemon)
    op_has_duskull = any(p.id == Duskull for p in op_all_pokemon)
    op_has_water_threat = any(
        p.id in Slowpoke_IDs or p.id in Froakie_IDs
        or p.id == Wellspring_Mask_Ogerpon_ex or p.id == N_Darumaka
        for p in op_all_pokemon
    )
    op_has_tools = any(len(p.tools) > 0 for p in op_all_pokemon)

    stadium_id = state.stadium[0].id if state.stadium else 0
    our_stadium_up = stadium_id in OUR_STADIUMS

    bench_count = len([b for b in my_state.bench if b])
    bench_max = my_state.benchMax
    bench_free = bench_max - bench_count

    active_pokemon = my_state.active[0] if my_state.active else None
    active_id = active_pokemon.id if active_pokemon else -1
    active_has_psychic = active_pokemon and any(ec.id in PSYCHIC_ENERGY_IDS for ec in active_pokemon.energyCards)

    op_active = op_state.active[0] if op_state.active else None
    op_active_hp = op_active.hp if op_active else 9999

    hand_size = len(my_state.hand) if my_state.hand else my_state.handCount

    # Safe Draws & Fatigue Estimation
    deck_count = my_state.deckCount
    safe_draws = deck_count - (my_prize_count + 1)
    overdraw = safe_draws < 0

    scores = []
    for o in select.option:
        score = 0.0

        if o.type == OptionType.PLAY:
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            if card is None:
                scores.append(0.0)
                continue
            cid = card.id

            if cid == Abra:
                if bench_free <= 0: score = -1
                elif abra_line_on_field == 0: score = W["play_pokemon_base"] + W["play_abra_early"]
                elif abra_line_on_field == 1 and hand_counts[Abra] >= 1: score = W["play_pokemon_base"] + W["play_abra_need"]
                elif abra_line_on_field < 3: score = W["play_pokemon_base"] + W["play_abra_extra"]
                else: score = W["play_pokemon_base"] - W["play_bench_penalty"]

            elif cid in DUNSPARCE_IDS:
                if bench_free <= 0: score = -1
                elif dunsparce_line_on_field == 0:
                    score = W["play_pokemon_base"] + (W["play_dun_first_early"] if state.turn <= 2 else W["play_dun_first_late"])
                elif dunsparce_line_on_field == 1: score = W["play_pokemon_base"] + W["play_dun_second"]
                elif op_has_ex and dunsparce_line_on_field < 3: score = W["play_pokemon_base"] + W["play_dun_ex"]
                else: score = W["play_pokemon_base"] - W["play_bench_penalty"]

            elif cid == Fezandipiti_ex:
                score = W["play_fez"] if (bench_free > 0 and field_counts[Fezandipiti_ex] == 0 and not overdraw) else -1
            elif cid == Genesect:
                score = W["play_genesect"] if (bench_free > 0 and field_counts[Genesect] == 0) else -1
            elif cid == Psyduck:
                score = W["play_psyduck"] if (bench_free > 0 and field_counts[Psyduck] == 0 and (op_has_duskull or op_has_grimmsnarl)) else -1
            elif cid == Shaymin:
                score = W["play_shaymin"] if (bench_free > 0 and field_counts[Shaymin] == 0 and (op_has_water_threat or op_has_dragapult_line)) else -1
            elif cid == Fan_Rotom:
                score = W["play_fanrotom"] if (bench_free > 0 and field_counts[Fan_Rotom] == 0 and state.turn <= 2) else -1

            # Trainers
            elif cid == Buddy_Buddy_Poffin:
                need_basics = (abra_line_on_field < 2) or (dunsparce_line_on_field < 1)
                if bench_free >= 2 and need_basics: score = W["poffin_early"]
                elif bench_free >= 1: score = W["poffin_fallback"]
                else: score = W["poffin_late"]
            elif cid == Poke_Pad:
                need_supporter = not any(hand_counts[s] > 0 for s in (Dawn, Hilda, Lillie_Det, Xerosic, Eri, Boss_Orders))
                if need_supporter: score = W["pokepad_early"] if state.turn <= 2 else W["pokepad_need"]
                else: score = W["pokepad_ok"]
            elif cid == Rare_Candy:
                score = W["rare_candy"] if (hand_counts[Alakazam] > 0 and field_counts[Abra] > 0) else -1
            elif cid == Night_Stretcher:
                dis_abra = sum(discard_counts[x] for x in ABRA_LINE)
                if dis_abra >= 1: score = W["night_stretcher_mon"]
                elif discard_counts[Basic_Psychic_Energy] + discard_counts[Telepath_Psychic_Energy] >= 1: score = W["night_stretcher_energy"]
                else: score = -1
            elif cid == Sacred_Ash:
                dis_abra = sum(discard_counts[x] for x in ABRA_LINE)
                score = W["sacred_ash_hi"] if dis_abra >= 2 else (W["sacred_ash_lo"] if dis_abra >= 1 else -1)
            elif cid == Enhanced_Hammer:
                score = W["hammer_any"] if any(count_special_defense_energies(p) > 0 for p in op_all_pokemon) else -1
            elif cid == Wondrous_Patch:
                bench_abra_no_energy = any(b.id in ABRA_LINE and len(b.energyCards) == 0 for b in my_state.bench if b)
                score = W["wondrous_patch"] if (discard_counts[Basic_Psychic_Energy] >= 1 and bench_abra_no_energy) else -1
            elif cid == Meddling_Memo:
                score = W["meddling_memo"] if op_state.handCount >= 5 else -1
            elif cid == Boss_Orders:
                score = -1

            # Layer 4 Supporters (Genome)
            elif cid == Hilda:
                score = W["hilda"] if (safe_draws >= 2 and not overdraw) else -1
            elif cid == Dawn:
                if overdraw: score = -1
                elif len(my_field) <= 1 and safe_draws >= 3: score = W["dawn_emergency"]
                elif safe_draws >= 3: score = W["dawn"]
                else: score = -1
            elif cid == Lillie_Det:
                if safe_draws < 6: score = -1
                elif hand_size <= (5 if my_prize_count == 6 else 4): score = W["lillie"]
                else: score = -1
            elif cid == Lanas_Aid:
                rec = sum(discard_counts[x] for x in (Abra, Kadabra, Alakazam, Dunsparce65, Dunsparce305, Basic_Psychic_Energy))
                score = W["lana"] if rec >= 2 else -1
            elif cid == Xerosic:
                score = W["xerosic"] if op_state.handCount >= 6 else -1
            elif cid == Eri:
                score = W["eri"] if op_state.handCount >= 4 else -1

            # Stadiums
            elif cid == Neutralization_Zone:
                if our_stadium_up and stadium_id == Neutralization_Zone: score = -1
                elif op_has_ex: score = W["nz_ex"]
                elif stadium_id != 0 and not our_stadium_up: score = W["nz_counter"]
                else: score = -1
            elif cid == Battle_Cage:
                if stadium_id == Battle_Cage: score = -1
                elif stadium_id != 0 and not our_stadium_up: score = W["cage_counter"]
                elif op_has_dragapult_line or op_has_grimmsnarl: score = W["cage_snipe"]
                else: score = -1
            elif cid == Nighttime_Mine:
                if stadium_id == Nighttime_Mine: score = -1
                elif stadium_id != 0 and not our_stadium_up: score = W["mine_counter"]
                else: score = -1
            elif cid == Jamming_Tower:
                if stadium_id == Jamming_Tower: score = -1
                elif stadium_id != 0 and not our_stadium_up: score = W["jamming_counter"]
                elif op_has_tools: score = W["jamming_tools"]
                else: score = -1

        elif o.type == OptionType.ATTACH:
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            pokemon = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)
            if card is None or pokemon is None:
                scores.append(0.0)
                continue
            cid = card.id
            pid = pokemon.id

            if cid == Lucky_Helmet: score = W["helmet"]
            elif cid == Fan_Rotom_Tool: score = W["fan_abra"] if pid in ABRA_LINE else (W["fan_genesect"] if pid == Genesect else 7000)
            elif cid == Air_Balloon: score = W["balloon"]
            elif cid == Hero_Cape:
                if pid == Alakazam: score = W["cape_alak"]
                elif pid == Kadabra: score = W["cape_kadabra"]
                elif pid == Abra: score = W["cape_abra"]
                else: score = 7000
            elif cid in PSYCHIC_ENERGY_IDS:
                if len(pokemon.energyCards) == 0:
                    score = W["energy_abra"] if pid in ABRA_LINE else W["energy_retreat"]
                else:
                    score = W["energy_abra"] - 500
            elif cid == Enriching_Energy:
                score = W["enriching_1st"] if len(pokemon.energyCards) == 0 else W["enriching_2nd"]
            elif cid == Mist_Energy:
                score = W["mist_retreat"] if len(pokemon.energyCards) == 0 else W["mist_2nd"]

        elif o.type == OptionType.EVOLVE:
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            pokemon = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)
            score = W["evolve_base"]
            if card and card.id == Alakazam:
                if safe_draws < 3: score = -1
                elif o.inPlayArea == AreaType.ACTIVE: score += 200
                else: score += 50
                if pokemon: score += len(pokemon.energyCards) * 10
            elif card and card.id == Kadabra:
                if safe_draws < 2: score = -1
                else:
                    score += 100
                    if pokemon and len(pokemon.energyCards) == 0: score += 50
                    elif hand_counts[Rare_Candy] > 0 and hand_counts[Alakazam] > 0: score -= 120
            elif card and card.id == Dudunsparce:
                score = -1 if safe_draws < 2 else score + 80
            else:
                score += 30

        elif o.type == OptionType.ABILITY:
            card = get_card(obs, o.area, o.index, my_index)
            if card is None: scores.append(0.0); continue
            if card.id == Dudunsparce:
                if len(my_field) <= 1: score = -1
                elif safe_draws < 3 or overdraw: score = -1
                elif hand_size < (9 if op_has_ex else 6): score = W["ability_dudun"]
                elif active_id not in ABRA_LINE and o.area == AreaType.ACTIVE: score = W["ability_dudun"]
                else: score = -1
            elif card.id == Fezandipiti_ex:
                score = W["ability_fez"] if safe_draws >= 3 else -1
            elif card.id == Fan_Rotom:
                score = W["ability_fanrotom"] if state.turn <= 2 else -1
            elif card.id in OUR_STADIUMS:
                score = 1
            else:
                score = W["ability_default"]

        elif o.type == OptionType.RETREAT:
            if active_id == Alakazam and active_has_psychic: score = -1
            elif active_id in (Abra, Dunsparce65, Dunsparce305, Dudunsparce, Psyduck, Shaymin, Genesect, Fan_Rotom):
                score = W["retreat_promote"] if (field_counts[Alakazam] >= 1 or field_counts[Kadabra] >= 1) else -1
            else: score = -1

        elif o.type == OptionType.ATTACK:
            score = W["attack_base"]
            if o.attackId == ATTACK_POWERFUL_HAND: score += W["attack_powerful"]
            elif o.attackId == ATTACK_SUPER_PSY_BOLT: score += W["attack_psybolt_kill"] if op_active_hp <= 30 else W["attack_psybolt"]
            elif o.attackId == ATTACK_TELEPORTATION: score += W["attack_teleport"]

        scores.append(score)
    return scores


def _post_pick(obs, picked_idx):
    global ability_used_dudunsparce, ability_used_fezandipiti
    sel = obs.select
    if sel.context != SelectContext.MAIN: return
    o = sel.option[picked_idx]
    if o.type == OptionType.ABILITY:
        card = get_card(obs, o.area, o.index, obs.current.yourIndex)
        if card is not None:
            if card.id == Dudunsparce: ability_used_dudunsparce = True
            elif card.id == Fezandipiti_ex: ability_used_fezandipiti = True


def _courage_teleportation_guard(obs_dict, action):
    try:
        select = obs_dict.get("select") or {}
        if select.get("context") != int(SelectContext.MAIN):
            return action
        options = select.get("option") or []
        if not isinstance(action, list) or not any(
            0 <= index < len(options)
            and options[index].get("type") == int(OptionType.RETREAT)
            for index in action
        ):
            return action
        state = obs_dict.get("current") or {}
        mine = (state.get("players") or [{}, {}])[state.get("yourIndex", 0)]
        active = (mine.get("active") or [None])[0]
        if not active or active.get("id") != Abra:
            return action
        active_energy = active.get("energyCards", active.get("energies", [])) or []
        if not active_energy:
            return action
        ready_alakazam = any(
            pokemon
            and pokemon.get("id") == Alakazam
            and (pokemon.get("energyCards", pokemon.get("energies", [])) or [])
            for pokemon in (mine.get("bench") or [])
        )
        if ready_alakazam:
            return action
        for index, option in enumerate(options):
            if (
                option.get("type") == int(OptionType.ATTACK)
                and option.get("attackId") == ATTACK_TELEPORTATION
            ):
                return [index]
    except Exception:
        return action
    return action


# ============================================================
# ENTRYPOINT: HYBRID STAGE 3 AGENT
# ============================================================

def hybrid_agent(obs_dict, configuration=None) -> List[int]:
    """
    Layered Hybrid Stage 3 Agent Entrypoint.
    Executes:
      Layer 1 Selection Contract & Type Validation
      Layer 2 Rich State Representation
      Layer 3 Deterministic Baseline Heuristic
      Layer 4 Parameterized Genome (Hilda=3150, Xerosic=3250, Dawn=3100)
      Layer 1 Egress Enforcement
    """
    if not isinstance(obs_dict, dict):
        return []

    # Deck setup prompt
    if "select" not in obs_dict or obs_dict.get("select") is None:
        return list(SOL_DECK)

    try:
        obs = to_observation_class(obs_dict)
        if obs.select is None or not obs.select.option:
            return []

        # Layer 1: Selection Contract
        contract = selection_contract(obs)
        if contract["option_count"] == 0:
            return []
        if contract["option_count"] == 1:
            return [0]

        # Layer 2, 3, 4: Heuristic Scoring
        scores = heuristic_scores(obs)

        # Deterministic multi-select ordering
        scored = [(scores[i], -i, i) for i in range(len(scores))]
        scored.sort(reverse=True)

        best_idx = scored[0][2]
        _post_pick(obs, best_idx)

        max_c = contract["max_count"]
        selected = [best_idx]
        if max_c > 1:
            for _, _, idx in scored:
                if idx != best_idx:
                    selected.append(idx)
                if len(selected) >= max_c:
                    break

        # Apply courage teleportation guard
        action = _courage_teleportation_guard(obs_dict, selected)

        # Layer 1: Final Legal Egress
        return legal_selection(obs, action)

    except Exception:
        # Layer 1 Fallback Cascade
        try:
            sel = obs_dict.get("select") or {}
            opts = sel.get("option", [])
            min_c = max(1, int(sel.get("minCount", 1) or 1))
            k = min(min_c, len(opts)) if opts else 0
            return list(range(k))
        except Exception:
            return [0]

# Competition Alias
agent = hybrid_agent
