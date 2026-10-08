"""
Generate next_sol_eclipse_decision_audit.csv containing all 401 Dawn vs Hilda competitive decisions
with complete context, state variables, and game outcomes.
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

def load_and_export():
    records = []
    p1 = HERE / "h_xerosic_decision_audit.csv"
    if p1.exists():
        with open(p1, "r", encoding="utf-8") as f:
            records.extend(list(csv.DictReader(f)))
            
    p2 = HERE / "sol_eclipse_decision_audit.csv"
    if p2.exists():
        with open(p2, "r", encoding="utf-8") as f:
            records.extend(list(csv.DictReader(f)))

    target_records = []
    for r in records:
        if r["context"] != "MAIN": continue
        opts = r["legal_options"].split(" | ")
        has_dawn = any("PLAY(Dawn)" in o for o in opts)
        has_hilda = any("PLAY(Hilda)" in o for o in opts)
        if has_dawn and has_hilda:
            target_records.append(r)

    out_file = HERE / "next_sol_eclipse_decision_audit.csv"
    if target_records:
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(target_records[0].keys()))
            writer.writeheader()
            writer.writerows(target_records)
            
    print(f"Exported {len(target_records)} competitive decision records to {out_file}")

if __name__ == "__main__":
    load_and_export()
