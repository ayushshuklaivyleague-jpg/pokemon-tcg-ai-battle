import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cg.api as api
from cg.game import battle_start, battle_select, battle_finish
import re

source_file = HERE / "codex_sol_eclipse_alakazam.py"
raw_code = source_file.read_text(encoding="utf-8")

main_match = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
main_source = main_match.group(1)
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]

sol_ns = {"__file__": str(source_file)}
exec(main_source, sol_ns)
agent_fn = sol_ns["agent"]

print("Starting single game test...")
obs, sd = battle_start(SOL_DECK, SOL_DECK)
print("Battle started.")

step = 0
while step < 100:
    step += 1
    res = obs.get("current", {}).get("result")
    if res is not None and res >= 0:
        print(f"Game finished at step {step} with result {res}")
        break
    
    y_idx = obs.get("current", {}).get("yourIndex", 0)
    opts = obs.get("select", {}).get("option", [])
    ctx = obs.get("select", {}).get("context", 0)
    min_c = obs.get("select", {}).get("minCount", 0)
    max_c = obs.get("select", {}).get("maxCount", 1)
    
    action = agent_fn(obs)
    print(f"Step {step}: Player {y_idx} Context {ctx} Options {len(opts)} min={min_c} max={max_c} -> Choice: {action}")
    
    try:
        obs = battle_select(action)
    except Exception as e:
        print(f"ERROR at step {step} with action {action}: {e}")
        import traceback
        traceback.print_exc()
        break

battle_finish()
