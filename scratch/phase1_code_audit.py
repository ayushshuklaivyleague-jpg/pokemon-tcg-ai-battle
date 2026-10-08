import ast
import re
import json
from pathlib import Path

source_path = Path("codex_sol_eclipse_alakazam.py")
content = source_path.read_text(encoding="utf-8")

# Extract MAIN_SOURCE
main_source_match = re.search(r"MAIN_SOURCE\s*=\s*r?'''(.*?)'''", content, re.DOTALL)
if not main_source_match:
    print("Could not find MAIN_SOURCE")
    exit(1)

main_source = main_source_match.group(1)

# Extract deck
deck_match = re.search(r"DECK_SOURCE\s*=\s*r?'''(.*?)'''", content, re.DOTALL)
deck_cards = [int(x) for x in deck_match.group(1).splitlines() if x.strip()]
print(f"Sol Eclipse Deck Card Count: {len(deck_cards)}")
print(f"Distinct Cards in Sol Eclipse: {len(set(deck_cards))}")

# Parse weights
weights_initial_match = re.search(r"WEIGHTS\s*=\s*(\{.*?\})", main_source, re.DOTALL)
weights_update_match = re.search(r"WEIGHTS\.update\((\{.*?\})\)", main_source, re.DOTALL)

# We can safely evaluate the dict literals
weights_initial = eval(weights_initial_match.group(1))
weights_update = eval(weights_update_match.group(1))
final_weights = dict(weights_initial)
final_weights.update(weights_update)

print(f"Total defined weights: {len(final_weights)}")

# Find usages of W[...] or WEIGHTS[...]
w_usages = re.findall(r'W\["([^"]+)"\]', main_source) + re.findall(r'WEIGHTS\["([^"]+)"\]', main_source)
w_usage_counts = {k: w_usages.count(k) for k in final_weights}

print("\n--- WEIGHTS USAGE AUDIT ---")
for k, v in final_weights.items():
    print(f"Weight '{k}': default={weights_initial.get(k)}, baked={v}, code_occurrences={w_usage_counts.get(k, 0)}")

# Check for unreferenced weights
unreferenced = [k for k, count in w_usage_counts.items() if count == 0]
print(f"\nUnreferenced weights (count=0 in code): {unreferenced}")
