"""
Generates embedded JS fallback for default datasets to guarantee immediate loading
both on GitHub Pages web servers and when opened locally via file:// protocol.
"""
import os
import json

base_dir = r"C:\Users\abidh\.gemini\antigravity\scratch\Online_Shopping_Behaviour_Analysis"
primary_csv_path = os.path.join(base_dir, "dataset", "online_shopping_data.csv")
alt_csv_path = os.path.join(base_dir, "dataset", "alternative_retail_transactions.csv")

with open(primary_csv_path, "r", encoding="utf-8") as f:
    primary_text = f.read()

with open(alt_csv_path, "r", encoding="utf-8") as f:
    alt_text = f.read()

js_content = f"""// Pre-embedded fallback datasets for offline & file:// execution
window.DEFAULT_CSV_TEXT = {json.dumps(primary_text)};
window.ALTERNATIVE_CSV_TEXT = {json.dumps(alt_text)};
"""

for target_dir in ["github-pages", "docs"]:
    dest = os.path.join(base_dir, target_dir, "assets", "data", "default_dataset.js")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"Generated {dest} ({len(js_content):,} bytes)")
