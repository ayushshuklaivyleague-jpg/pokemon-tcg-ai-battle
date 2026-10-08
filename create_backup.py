from pathlib import Path

prod_path = Path("codex_sol_eclipse_alakazam.py")
bak_path = Path("codex_sol_eclipse_alakazam.py.bak_pre_hilda3150")

prod_text = prod_path.read_text(encoding="utf-8")
bak_text = prod_text.replace('"hilda": 3150', '"hilda": 3000')
bak_path.write_text(bak_text, encoding="utf-8")
print("Backup created successfully.")
