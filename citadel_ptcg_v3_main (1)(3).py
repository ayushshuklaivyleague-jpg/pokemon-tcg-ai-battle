
import csv
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from cg.api import (
    to_observation_class,
    SelectContext,
    OptionType,
    AreaType,
    CardType,
    all_card_data,
)

# ------------------------------------------------------------
# Deck
# ------------------------------------------------------------

def _load_deck():
    candidates = [
        _HERE / "deck.csv",
        Path("/kaggle_simulations/agent/deck.csv"),
    ]
    for p in candidates:
        try:
            if p.exists():
                with open(p, newline="") as f:
                    deck = [
                        int(r[0]) for r in csv.reader(f)
                        if r and r[0].strip()
                    ]
                if len(deck) == 60:
                    return deck
        except Exception:
            pass
    return []

DECK = _load_deck()

# ------------------------------------------------------------
# Card metadata
# ------------------------------------------------------------

try:
    _CARD_TABLE = {c.cardId: c for c in all_card_data()}
except Exception:
    _CARD_TABLE = {}

def _card(obs, option):
    try:
        if option.area == AreaType.HAND and option.index is not None:
            me = obs.current.players[obs.current.yourIndex]
            if me.hand is not None and 0 <= option.index < len(me.hand):
                return me.hand[option.index]
        if option.area == AreaType.ACTIVE and option.index is not None:
            p = obs.current.players[option.playerIndex]
            return p.active[option.index]
        if option.area == AreaType.BENCH and option.index is not None:
            p = obs.current.players[option.playerIndex]
            return p.bench[option.index]
        if option.area == AreaType.DISCARD and option.index is not None:
            p = obs.current.players[option.playerIndex]
            return p.discard[option.index]
    except Exception:
        pass
    return None

def _card_data(card):
    try:
        return _CARD_TABLE.get(int(card.id))
    except Exception:
        return None

def _card_type(card):
    data = _card_data(card)
    return getattr(data, "cardType", None) if data is not None else None

def _is_pokemon(card):
    try:
        return _card_type(card) == CardType.POKEMON
    except Exception:
        return False

def _is_energy(card):
    try:
        return _card_type(card) == CardType.BASIC_ENERGY
    except Exception:
        return False

def _is_supporter(card):
    try:
        return _card_type(card) == CardType.SUPPORTER
    except Exception:
        return False

# ------------------------------------------------------------
# Board helpers
# ------------------------------------------------------------

def _active(obs, player_index):
    try:
        p = obs.current.players[player_index]
        return p.active[0] if p.active else None
    except Exception:
        return None

def _bench(obs, player_index):
    try:
        return list(obs.current.players[player_index].bench or [])
    except Exception:
        return []

def _hand(obs):
    try:
        return list(obs.current.players[obs.current.yourIndex].hand or [])
    except Exception:
        return []

def _energy_count(pokemon):
    try:
        return len(pokemon.energyCards or [])
    except Exception:
        try:
            return len(pokemon.energies or [])
        except Exception:
            return 0

def _hp(pokemon):
    try:
        return float(pokemon.hp)
    except Exception:
        return 0.0

def _max_hp(pokemon):
    try:
        return float(pokemon.maxHp)
    except Exception:
        return 0.0

# ------------------------------------------------------------
# V3 action scorer
#
# This is intentionally hidden-information safe:
# it only uses the observation actually supplied to the agent.
# ------------------------------------------------------------

def _score_action(obs, option, context):
    try:
        typ = OptionType(option.type).name
    except Exception:
        return -10**9

    me_idx = obs.current.yourIndex
    me = obs.current.players[me_idx]
    opp = obs.current.players[1 - me_idx]

    card = _card(obs, option)
    score = 0.0

    # --------------------------------------------------------
    # Non-MAIN contexts: choose based on what the engine asks.
    # --------------------------------------------------------

    if context == "ATTACK":
        return 100000.0 + float(getattr(option, "attackId", 0) or 0)

    if typ == "ATTACK":
        # Attacking is terminal for the turn, so only choose it
        # when no stronger setup action is currently available.
        score = 18000.0

        # Prefer attacks with a known attack ID deterministically.
        score += min(float(getattr(option, "attackId", 0) or 0), 5000.0) * 0.1
        return score

    if typ == "EVOLVE":
        # Evolution is generally a strong irreversible board improvement.
        target = None
        try:
            target = _active(obs, me_idx) if option.inPlayArea == AreaType.ACTIVE \
                else _bench(obs, me_idx)[option.inPlayIndex]
        except Exception:
            pass
        score = 70000.0
        score += _energy_count(target) * 500.0 if target is not None else 0.0
        return score

    if typ == "ATTACH":
        target = None
        try:
            target = (
                _active(obs, me_idx)
                if option.inPlayArea == AreaType.ACTIVE
                else _bench(obs, me_idx)[option.inPlayIndex]
            )
        except Exception:
            pass

        score = 35000.0
        if target is not None:
            # Prefer building an active attacker, then an energy-bearing bench.
            if option.inPlayArea == AreaType.ACTIVE:
                score += 4000.0
            score += min(_energy_count(target), 4) * 700.0
        return score

    if typ == "RETREAT":
        # Retreat only becomes attractive when active is in poor shape and
        # a bench exists; otherwise preserve the attack position.
        active = _active(obs, me_idx)
        bench = _bench(obs, me_idx)
        if active is not None and bench:
            hp = _hp(active)
            mx = _max_hp(active)
            if mx > 0 and hp / mx < 0.45:
                return 30000.0
        return 1000.0

    if typ == "PLAY":
        if card is None:
            return 12000.0

        cid = getattr(card, "id", None)
        name = str(getattr(_card_data(card), "name", "")).lower()

        # Basic Pokémon: setup value.
        if _is_pokemon(card):
            score = 50000.0
            if not _bench(obs, me_idx) and _active(obs, me_idx) is None:
                score += 15000.0
            # Basic-looking names are not assumed; metadata decides Pokémon.
            return score

        # Supporters are strong, but avoid blindly burning every supporter.
        if _is_supporter(card):
            if getattr(obs.current, "supporterPlayed", False):
                return -100000.0
            score = 42000.0
            # Draw/search-style supporters are generally useful when hand is small.
            if len(_hand(obs)) <= 4:
                score += 4000.0
            return score

        # Generic Item / Trainer play.
        score = 32000.0

        if "ultra ball" in name:
            score += 5000.0
        elif "poffin" in name or "nest ball" in name:
            score += 7000.0
        elif "boss" in name:
            score += 6500.0
        elif "switch" in name or "retreat" in name:
            score += 2500.0
        elif "energy" in name:
            score += 1000.0

        return score

    if typ in ("ENERGY", "ENERGY_CARD"):
        return 30000.0

    if typ == "CARD":
        # In a CARD-choice context, prefer Pokémon with energy/HP,
        # otherwise retain deterministic lowest-index behavior.
        if card is None:
            return 1000.0
        if _is_pokemon(card):
            return 10000.0 + _energy_count(card) * 500.0 + _hp(card)
        return 5000.0

    if typ == "DAMAGE_COUNTER":
        return 10000.0

    if typ == "YES":
        return 1000.0

    if typ == "NUMBER":
        return float(getattr(option, "number", 0) or 0)

    if typ == "END":
        # Ending is the least desirable action unless nothing else is useful.
        return 0.0

    return 5000.0

# ------------------------------------------------------------
# Choose legal option(s)
# ------------------------------------------------------------

def _choose(obs):
    if obs.select is None or not obs.select.option:
        return []

    options = obs.select.option
    try:
        context = SelectContext(obs.select.context).name
    except Exception:
        context = None

    scored = []
    for i, option in enumerate(options):
        try:
            score = _score_action(obs, option, context)
        except Exception:
            score = -10**8
        scored.append((score, -i, i))

    scored.sort(reverse=True)
    best = scored[0][2]

    max_count = getattr(obs.select, "maxCount", 1) or 1
    min_count = getattr(obs.select, "minCount", 1) or 1
    max_count = max(min_count, min(int(max_count), len(options)))

    # Usually select one action. If CABT requires multiple selections,
    # fill remaining slots by descending score.
    selected = [best]
    if max_count > 1:
        for _, _, i in scored:
            if i != best:
                selected.append(i)
            if len(selected) >= max_count:
                break

    return selected

# ------------------------------------------------------------
# Competition entry point
# ------------------------------------------------------------

def agent(obs_dict, configuration=None):
    # Deck-selection phase.
    if not isinstance(obs_dict, dict):
        return []

    if "select" not in obs_dict:
        return list(DECK)

    if obs_dict.get("select") is None:
        return []

    try:
        obs = to_observation_class(obs_dict)
        return _choose(obs)
    except Exception:
        # Never crash and never fabricate an out-of-range selection.
        try:
            select = obs_dict.get("select")
            options = select.get("option", [])
            if not options:
                return []
            max_count = int(select.get("maxCount", 1) or 1)
            max_count = max(1, min(max_count, len(options)))
            return list(range(max_count))
        except Exception:
            return []

if __name__ == "__main__":
    print("CITADEL PTCG V3 agent module loaded.")
