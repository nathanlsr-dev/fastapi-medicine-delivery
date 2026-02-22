import json
import os
from typing import List, Dict, Any

DELIVERIES_FILE = "deliveries.json"

def load_deliveries() -> List[Dict[str, Any]]:
    if os.path.exists(DELIVERIES_FILE):
        with open(DELIVERIES_FILE, "r") as f:
            return json.load(f)
    return []

def save_deliveries(data: List[Dict[str, Any]]):
    with open(DELIVERIES_FILE, "w") as f:
        json.dump(data, f, indent=2)

patients_db: List[Dict[str, Any]] = []  # Temporário em memória (migramos depois)
deliveries_db = load_deliveries()
next_delivery_id = max(d.get("id", 0) for d in deliveries_db) + 1 if deliveries_db else 1