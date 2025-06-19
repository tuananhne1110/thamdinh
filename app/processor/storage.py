import json
import os
from datetime import datetime

def save_to_json(data, folder="output"):
    os.makedirs(folder, exist_ok=True)
    fname = f"{folder}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fname