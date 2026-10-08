import sys
import time
import re
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import cg.api as api
from cg.game import battle_start, battle_select, battle_finish

HERE = Path(__file__).resolve().parent.parent
source_file = HERE / "codex_sol_eclipse_alakazam.py"
raw_code = source_file.read_text(encoding="utf-8")
main_match = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", raw_code, re.DOTALL)
main_source = main_match.group(1)
SOL_DECK = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]

sol_ns = {"__file__": str(source_file)}
exec(main_source, sol_ns)
agent_fn = sol_ns["agent"]

print("Starting 1 game timing test...", flush=True)
t0 = time.time()
obs, sd = battle_start(SOL_DECK, SOL_DECK)
step = 0
while step < 150:
    step += 1
    res = obs.get("current", {}).get("result")
    if res is not None and res >= 0:
        print(f"Finished at step {step}, res={res}, elapsed={time.time()-t0:.2f}s", flush=True)
        break
    act = agent_fn(obs)
    obs = battle_select(act)

battle_finish()
print(f"Total time for 1 game: {time.time()-t0:.2f}s, steps: {step}", flush=True)
