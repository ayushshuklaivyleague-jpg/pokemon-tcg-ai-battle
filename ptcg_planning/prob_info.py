"""
Information-Boundary & Probability Modeling.
Calculates legitimate probabilities for deck drawing and search utility without leaking hidden variables.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from collections import Counter
import main


@dataclass
class ProbabilityFeatures:
    estimated_deck_size: int
    prob_draw_energy: float
    prob_draw_pokemon: float
    prob_draw_supporter: float
    pokemon_remaining_in_deck: int
    energy_remaining_in_deck: int
    supporter_remaining_in_deck: int
    search_item_utility: float


def compute_probability_features(obs: Any) -> ProbabilityFeatures:
    """
    Compute deck composition probabilities based strictly on known visible cards.
    """
    try:
        my_idx = main.safe_get(obs.current, "yourIndex", 0)
        my_p = obs.current.players[my_idx]

        # 1. Total deck composition from DECK
        deck_counter = Counter(main.DECK)
        total_deck_cards = len(main.DECK)

        # 2. Accumulate all known cards
        known_counter = Counter()

        # In Hand
        for c in main.v4_hand(obs):
            cid = int(main.safe_get(c, "id", -1) or -1)
            if cid > 0:
                known_counter[cid] += 1

        # In Discard
        discard = main.safe_list(main.safe_get(my_p, "discard", []))
        for c in discard:
            cid = int(main.safe_get(c, "id", -1) or -1)
            if cid > 0:
                known_counter[cid] += 1

        # On Active
        active = main.v4_active(obs, my_idx)
        if active is not None:
            cid = int(main.safe_get(active, "id", -1) or -1)
            if cid > 0:
                known_counter[cid] += 1
            # Energies on active
            for field in ("energyCards", "energies", "energy"):
                for e in main.safe_list(main.safe_get(active, field, [])):
                    eid = int(main.safe_get(e, "id", -1) or -1)
                    if eid > 0:
                        known_counter[eid] += 1

        # On Bench
        for b in main.v4_bench(obs, my_idx):
            if b is not None:
                cid = int(main.safe_get(b, "id", -1) or -1)
                if cid > 0:
                    known_counter[cid] += 1
                for field in ("energyCards", "energies", "energy"):
                    for e in main.safe_list(main.safe_get(b, field, [])):
                        eid = int(main.safe_get(e, "id", -1) or -1)
                        if eid > 0:
                            known_counter[eid] += 1

        # Remaining unknown cards (Deck + Prizes)
        remaining_counter = Counter()
        for cid, count in deck_counter.items():
            remaining_counter[cid] = max(0, count - known_counter[cid])

        total_remaining = sum(remaining_counter.values())
        estimated_deck_size = max(1, total_remaining - len(main.safe_list(main.safe_get(my_p, "prize", []))))

        # Card type counts in remaining cards
        poke_count = 0
        energy_count = 0
        supporter_count = 0

        for cid, count in remaining_counter.items():
            cdata = main.CARD_BY_ID.get(cid)
            if cdata is not None:
                ctype = main.safe_get(cdata, "cardType", None)
                if ctype == main.CardType.POKEMON:
                    poke_count += count
                elif ctype == main.CardType.BASIC_ENERGY:
                    energy_count += count
                elif ctype == main.CardType.SUPPORTER:
                    supporter_count += count

        tot = max(1.0, float(total_remaining))
        prob_energy = energy_count / tot
        prob_poke = poke_count / tot
        prob_supp = supporter_count / tot

        # Search item utility: higher if key targets exist in deck
        search_utility = 1.0 if poke_count > 0 else 0.1

        return ProbabilityFeatures(
            estimated_deck_size=estimated_deck_size,
            prob_draw_energy=prob_energy,
            prob_draw_pokemon=prob_poke,
            prob_draw_supporter=prob_supp,
            pokemon_remaining_in_deck=poke_count,
            energy_remaining_in_deck=energy_count,
            supporter_remaining_in_deck=supporter_count,
            search_item_utility=search_utility,
        )

    except Exception:
        return ProbabilityFeatures(
            estimated_deck_size=30,
            prob_draw_energy=0.3,
            prob_draw_pokemon=0.3,
            prob_draw_supporter=0.2,
            pokemon_remaining_in_deck=10,
            energy_remaining_in_deck=10,
            supporter_remaining_in_deck=6,
            search_item_utility=1.0,
        )
