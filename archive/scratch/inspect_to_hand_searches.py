import sys
from pathlib import Path
import pandas as pd
from collections import defaultdict

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import main
from cg.api import LogType
from cg.game import battle_start, battle_select, battle_finish
from ptcg_planning.state_features import extract_state_features

print("=" * 80)
print("INSPECTING TO_HAND SEARCH SELECTIONS (100 MATCHES)")
print("=" * 80)

# In TO_HAND:
# When Mega Signal or Cyrano is played, what cards are presented in the deck search list?
# What does V4 score each card?
# Does V4 pick Mega Abomasnow ex vs Snover vs Abomasnow vs Kyogre?

search_events = []

for g in range(100):
    obs, _ = battle_start(main.DECK, main.DECK)
    try:
        step = 0
        while True:
            res = obs.get("current", {}).get("result", None)
            if res is not None and res != -1:
                break
            select = obs.get("select")
            if not select:
                break

            ctx = select.get("context")
            ctx_name = main.SelectContext(ctx).name if ctx is not None else "NONE"
            obs_cls = main.to_observation_class(obs)
            player_idx = obs_cls.current.yourIndex
            player = obs_cls.current.players[player_idx]

            if ctx_name == "TO_HAND" and len(obs_cls.select.option) > 1:
                options = obs_cls.select.option
                cards_info = []
                for i, opt in enumerate(options):
                    c = main.v4_card_from_option(obs_cls, opt)
                    cdata = main.v4_card_data(c)
                    cname = str(getattr(cdata, "name", "None")) if cdata else "None"
                    cid = getattr(c, "id", -1) if c else -1
                    v4_s = main.v4_score_action(obs_cls, opt, "TO_HAND")
                    cards_info.append((i, cid, cname, v4_s))
                
                # Check minCount and maxCount
                min_c = getattr(obs_cls.select, "minCount", 1)
                max_c = getattr(obs_cls.select, "maxCount", 1)
                
                search_events.append({
                    "game": g, "step": step,
                    "min_count": min_c, "max_count": max_c,
                    "num_options": len(options),
                    "options": cards_info,
                    "hand_size": len(player.hand or []),
                    "bench_count": len(player.bench or []),
                })

            choice = main.agent(obs)
            obs = battle_select(choice)
            step += 1
    finally:
        battle_finish()

print(f"Total TO_HAND search events: {len(search_events)}")
for e in search_events[:10]:
    print(f"Game {e['game']}, Step {e['step']}: minCount={e['min_count']}, maxCount={e['max_count']}, NumOptions={e['num_options']}, Hand={e['hand_size']}, Bench={e['bench_count']}")
    for opt in e['options'][:5]:
        print(f"   Opt {opt[0]}: ID={opt[1]}, Name={opt[2]}, Score={opt[3]}")
