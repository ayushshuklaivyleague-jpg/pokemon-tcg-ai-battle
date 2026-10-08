# ============================================================
# CITADEL PTCG — MIKE V4
# PRODUCTION SUBMISSION
#
# Champion benchmark: 14 / 20 wins — 70.0%
# Exact decision policy used by the successful V4 benchmark.
# ============================================================

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from cg.api import (
    to_observation_class,
    SelectContext,
    OptionType,
    AreaType,
    CardType,
    all_card_data,
)

# ------------------------------------------------------------
# DECK
# ------------------------------------------------------------

def _load_deck():
    candidates = [
        HERE / 'deck.csv',
        Path('/kaggle_simulations/agent/deck.csv'),
    ]

    for path in candidates:
        try:
            if path.exists():
                with open(path, newline='') as deck_file:
                    deck = [
                        int(row[0])
                        for row in csv.reader(deck_file)
                        if row and row[0].strip()
                    ]

                if len(deck) == 60:
                    return deck

        except Exception:
            pass

    return []

DECK = _load_deck()

if len(DECK) != 60:
    raise RuntimeError(
        f'Invalid deck: expected 60 cards, got {len(DECK)}'
    )

# ------------------------------------------------------------
# CARD DATABASE
# ------------------------------------------------------------

try:
    CARD_BY_ID = {
        c.cardId: c
        for c in all_card_data()
    }
except Exception:
    CARD_BY_ID = {}


# ------------------------------------------------------------
def safe_get(obj, name, default=None):
    """
    Safely read an attribute from an SDK object.
    """
    try:
        return getattr(obj, name)
    except Exception:
        return default


# ------------------------------------------------------------
def safe_list(value):
    """
    Convert None / iterable-like SDK fields into a normal list.
    """
    if value is None:
        return []

    try:
        return list(value)
    except Exception:
        return []


# ------------------------------------------------------------
def get_select(obs):
    """
    Return the current selection object.
    """
    return safe_get(obs, "select", None)


# ------------------------------------------------------------
def get_options(obs):
    """
    Return ONLY the options supplied by the engine.
    """
    select = get_select(obs)

    if select is None:
        return []

    return safe_list(
        safe_get(select, "option", [])
    )


# ------------------------------------------------------------
def get_min_count(obs):
    select = get_select(obs)

    if select is None:
        return 0

    return int(
        safe_get(select, "minCount", 0) or 0
    )


# ------------------------------------------------------------
def get_max_count(obs):
    select = get_select(obs)

    if select is None:
        return 0

    return int(
        safe_get(select, "maxCount", 0) or 0
    )


# ------------------------------------------------------------
def get_select_context(obs):
    select = get_select(obs)

    if select is None:
        return None

    return safe_get(
        select,
        "context",
        None
    )


# ------------------------------------------------------------
def get_select_type(obs):
    select = get_select(obs)

    if select is None:
        return None

    return safe_get(
        select,
        "type",
        None
    )


# ------------------------------------------------------------
def option_type(option):
    """
    Return the OptionType enum when possible.
    """
    value = safe_get(option, "type", None)

    if value is None:
        return None

    try:
        return OptionType(int(value))
    except Exception:
        return value


# ------------------------------------------------------------
def option_type_name(option):
    """
    Human-readable option type.
    """
    value = option_type(option)

    return getattr(
        value,
        "name",
        str(value)
    )


# ------------------------------------------------------------
def selection_contract(obs):
    """
    Exact selection constraints supplied by the engine.
    """

    options = get_options(obs)

    minimum = max(
        0,
        get_min_count(obs)
    )

    maximum = max(
        0,
        get_max_count(obs)
    )

    # Never claim the engine allows more selections
    # than the number of options it actually supplied.
    maximum = min(
        maximum,
        len(options)
    )

    minimum = min(
        minimum,
        maximum
    )

    return {
        "option_count": len(options),
        "min_count": minimum,
        "max_count": maximum,
        "context": get_select_context(obs),
        "type": get_select_type(obs),
    }


# ------------------------------------------------------------
def validate_selection(obs, selection):
    """
    Validate a proposed selection against the CURRENT
    engine-provided selection contract.

    Returns:
        (True, "OK")
        or
        (False, reason)
    """

    contract = selection_contract(obs)

    minimum = contract["min_count"]
    maximum = contract["max_count"]
    option_count = contract["option_count"]

    # Must be a list.
    if not isinstance(selection, list):
        return False, "selection_not_list"

    # Every entry must be an integer.
    if any(
        not isinstance(index, int)
        for index in selection
    ):
        return False, "non_integer_index"

    # Correct number of selections.
    if len(selection) < minimum:
        return False, "below_min_count"

    if len(selection) > maximum:
        return False, "above_max_count"

    # No duplicates.
    if len(selection) != len(set(selection)):
        return False, "duplicate_index"

    # Every index must refer to an option
    # PRESENT IN THIS OBSERVATION.
    for index in selection:

        if index < 0:
            return False, "negative_index"

        if index >= option_count:
            return False, "index_out_of_range"

    return True, "OK"


# ------------------------------------------------------------
def legal_selection(obs, proposed):
    """
    Return a legal selection derived ONLY from the options
    currently exposed by the engine.

    This function never invents an option.
    """

    contract = selection_contract(obs)

    minimum = contract["min_count"]
    maximum = contract["max_count"]
    option_count = contract["option_count"]

    # No options means no selection.
    if option_count == 0:
        return []

    if not isinstance(
        proposed,
        (list, tuple)
    ):
        proposed = []

    clean = []

    # Keep proposed choices that are actually legal.
    for index in proposed:

        if not isinstance(index, int):
            continue

        if index < 0 or index >= option_count:
            continue

        if index in clean:
            continue

        clean.append(index)

        if len(clean) == maximum:
            break

    # If the strategy didn't provide enough choices,
    # fill from the CURRENT legal option set.
    for index in range(option_count):

        if len(clean) >= minimum:
            break

        if index not in clean:
            clean.append(index)

    clean = clean[:maximum]

    valid, reason = validate_selection(
        obs,
        clean
    )

    if not valid:
        raise RuntimeError(
            f"V4 selection contract failure: {reason}"
        )

    return clean


# ------------------------------------------------------------
def v4_card_from_option(obs, option):
    """
    Resolve the card associated with an option.
    """

    try:
        area = safe_get(
            option,
            "area",
            None
        )

        index = safe_get(
            option,
            "index",
            None
        )

        player_index = safe_get(
            option,
            "playerIndex",
            obs.current.yourIndex
        )

        if index is None:
            return None

        player = obs.current.players[
            player_index
        ]

        # Hand / deck / discard / prize / bench style areas
        for field in (
            "hand",
            "deck",
            "discard",
            "prize",
            "bench",
        ):
            cards = safe_list(
                safe_get(
                    player,
                    field,
                    []
                )
            )

            if (
                index < len(cards)
                and cards[index] is not None
            ):
                return cards[index]

    except Exception:
        pass

    return None


# ------------------------------------------------------------
def v4_active(obs, player_index):
    try:
        player = obs.current.players[
            player_index
        ]

        active = safe_list(
            safe_get(
                player,
                "active",
                []
            )
        )

        return active[0] if active else None

    except Exception:
        return None


# ------------------------------------------------------------
def v4_bench(obs, player_index):
    try:
        return safe_list(
            safe_get(
                obs.current.players[
                    player_index
                ],
                "bench",
                []
            )
        )
    except Exception:
        return []


# ------------------------------------------------------------
def v4_energy_count(pokemon):
    if pokemon is None:
        return 0

    for field in (
        "energyCards",
        "energies",
        "energy",
    ):
        try:
            value = safe_get(
                pokemon,
                field,
                None
            )

            if value is not None:
                return len(value)

        except Exception:
            pass

    return 0


# ------------------------------------------------------------
def v4_hp(pokemon):
    try:
        return float(
            safe_get(
                pokemon,
                "hp",
                0
            )
        )
    except Exception:
        return 0.0


# ------------------------------------------------------------
def v4_max_hp(pokemon):
    try:
        return float(
            safe_get(
                pokemon,
                "maxHp",
                0
            )
        )
    except Exception:
        return 0.0


# ------------------------------------------------------------
def v4_card_data(card):
    try:
        card_id = int(
            safe_get(
                card,
                "id",
                -1
            )
        )

        return CARD_BY_ID.get(
            card_id
        )

    except Exception:
        return None


# ------------------------------------------------------------
def v4_card_type(card):
    data = v4_card_data(card)

    if data is None:
        return None

    return safe_get(
        data,
        "cardType",
        None
    )


# ------------------------------------------------------------
def v4_is_pokemon(card):
    try:
        return (
            v4_card_type(card)
            == CardType.POKEMON
        )
    except Exception:
        return False


# ------------------------------------------------------------
def v4_is_energy(card):
    try:
        return (
            v4_card_type(card)
            == CardType.BASIC_ENERGY
        )
    except Exception:
        return False


# ------------------------------------------------------------
def v4_is_supporter(card):
    try:
        return (
            v4_card_type(card)
            == CardType.SUPPORTER
        )
    except Exception:
        return False


# ------------------------------------------------------------
def v4_hand(obs):
    try:
        return safe_list(
            safe_get(
                obs.current.players[
                    obs.current.yourIndex
                ],
                "hand",
                []
            )
        )
    except Exception:
        return []


# ------------------------------------------------------------
def v4_score_action(
    obs,
    option,
    context
):
    """
    Proven V3 scoring policy adapted into V4.
    """

    try:
        typ = OptionType(
            int(
                safe_get(
                    option,
                    "type",
                    -1
                )
            )
        ).name

    except Exception:
        return -10**9

    me_idx = obs.current.yourIndex

    card = v4_card_from_option(
        obs,
        option
    )

    # --------------------------------------------------------
    # ATTACK CONTEXT
    # --------------------------------------------------------

    if context == "ATTACK":
        return (
            100000.0
            + float(
                safe_get(
                    option,
                    "attackId",
                    0
                ) or 0
            )
        )

    # --------------------------------------------------------
    # ATTACK
    # --------------------------------------------------------

    if typ == "ATTACK":

        score = 18000.0

        score += min(
            float(
                safe_get(
                    option,
                    "attackId",
                    0
                ) or 0
            ),
            5000.0
        ) * 0.1

        return score

    # --------------------------------------------------------
    # EVOLVE
    # --------------------------------------------------------

    if typ == "EVOLVE":

        target = None

        try:

            area = safe_get(
                option,
                "inPlayArea",
                None
            )

            if area == AreaType.ACTIVE:

                target = v4_active(
                    obs,
                    me_idx
                )

            else:

                bench = v4_bench(
                    obs,
                    me_idx
                )

                index = safe_get(
                    option,
                    "inPlayIndex",
                    -1
                )

                if 0 <= index < len(bench):
                    target = bench[index]

        except Exception:
            pass

        score = 70000.0

        if target is not None:
            score += (
                v4_energy_count(target)
                * 500.0
            )

        return score

    # --------------------------------------------------------
    # ATTACH ENERGY
    # --------------------------------------------------------

    if typ == "ATTACH":

        target = None

        try:

            area = safe_get(
                option,
                "inPlayArea",
                None
            )

            if area == AreaType.ACTIVE:

                target = v4_active(
                    obs,
                    me_idx
                )

            else:

                bench = v4_bench(
                    obs,
                    me_idx
                )

                index = safe_get(
                    option,
                    "inPlayIndex",
                    -1
                )

                if 0 <= index < len(bench):
                    target = bench[index]

        except Exception:
            pass

        score = 35000.0

        if target is not None:

            if (
                safe_get(
                    option,
                    "inPlayArea",
                    None
                )
                == AreaType.ACTIVE
            ):
                score += 4000.0

            score += min(
                v4_energy_count(target),
                4
            ) * 700.0

        return score

    # --------------------------------------------------------
    # RETREAT
    # --------------------------------------------------------

    if typ == "RETREAT":

        active = v4_active(
            obs,
            me_idx
        )

        bench = v4_bench(
            obs,
            me_idx
        )

        if active is not None and bench:

            hp = v4_hp(active)
            maximum = v4_max_hp(active)

            if (
                maximum > 0
                and hp / maximum < 0.45
            ):
                return 30000.0

        return 1000.0

    # --------------------------------------------------------
    # PLAY
    # --------------------------------------------------------

    if typ == "PLAY":

        if card is None:
            return 12000.0

        name = str(
            safe_get(
                v4_card_data(card),
                "name",
                ""
            )
        ).lower()

        if v4_is_pokemon(card):

            score = 50000.0

            if (
                not v4_bench(obs, me_idx)
                and v4_active(obs, me_idx) is None
            ):
                score += 15000.0

            return score

        if v4_is_supporter(card):

            if safe_get(
                obs.current,
                "supporterPlayed",
                False
            ):
                return -100000.0

            score = 42000.0

            if len(v4_hand(obs)) <= 4:
                score += 4000.0

            return score

        score = 32000.0

        if "ultra ball" in name:
            score += 5000.0

        elif (
            "poffin" in name
            or "nest ball" in name
        ):
            score += 7000.0

        elif "boss" in name:
            score += 6500.0

        elif (
            "switch" in name
            or "retreat" in name
        ):
            score += 2500.0

        elif "energy" in name:
            score += 1000.0

        return score

    # --------------------------------------------------------
    # ENERGY
    # --------------------------------------------------------

    if typ in (
        "ENERGY",
        "ENERGY_CARD",
    ):
        return 30000.0

    # --------------------------------------------------------
    # CARD SELECTION
    # --------------------------------------------------------

    if typ == "CARD":

        if card is None:
            return 1000.0

        if v4_is_pokemon(card):

            return (
                10000.0
                + v4_energy_count(card) * 500.0
                + v4_hp(card)
            )

        return 5000.0

    # --------------------------------------------------------
    # DAMAGE / YES / NUMBER / END
    # --------------------------------------------------------

    if typ == "DAMAGE_COUNTER":
        return 10000.0

    if typ == "YES":
        return 1000.0

    if typ == "NUMBER":
        return float(
            safe_get(
                option,
                "number",
                0
            ) or 0
        )

    if typ == "END":
        return 0.0

    return 5000.0


# ------------------------------------------------------------
def choose_v4_action(obs):

    if (
        obs.select is None
        or not obs.select.option
    ):
        return []

    options = list(
        obs.select.option
    )

    try:
        context = SelectContext(
            obs.select.context
        ).name
    except Exception:
        context = None

    scored = []

    for i, option in enumerate(options):

        try:
            score = v4_score_action(
                obs,
                option,
                context
            )

        except Exception:
            score = -10**8

        scored.append(
            (
                score,
                -i,
                i
            )
        )

    scored.sort(
        reverse=True
    )

    best = scored[0][2]

    max_count = getattr(
        obs.select,
        "maxCount",
        1
    ) or 1

    min_count = getattr(
        obs.select,
        "minCount",
        1
    ) or 1

    max_count = max(
        min_count,
        min(
            int(max_count),
            len(options)
        )
    )

    selected = [best]

    if max_count > 1:

        for _, _, index in scored:

            if index != best:
                selected.append(index)

            if len(selected) >= max_count:
                break

    return legal_selection(
        obs,
        selected
    )


# ============================================================
# COMPETITION ENTRY POINT
# ============================================================

def agent(obs_dict, configuration=None):
    if not isinstance(obs_dict, dict):
        return []

    if 'select' not in obs_dict:
        return list(DECK)

    if obs_dict.get('select') is None:
        return list(DECK)

    try:
        obs = to_observation_class(obs_dict)
        return choose_v4_action(obs)

    except Exception:
        try:
            select = obs_dict.get('select')
            options = select.get('option', [])

            if not options:
                return []

            max_count = int(
                select.get('maxCount', 1) or 1
            )

            max_count = max(
                1,
                min(max_count, len(options))
            )

            return list(range(max_count))

        except Exception:
            return []

if __name__ == '__main__':
    print('MIKE V4 submission loaded.')
