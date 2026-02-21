import json
import os
from typing import List, Dict, Any

DATA_FILE = "deliveries.json"

def load_data() -> List[Dict[str, Any]]:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data: List[Dict[str, Any]]):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Funções simples para pacientes e entregas (futuro: DB real)
patients_db = []  # Lista temporária - depois migramos pra JSON/DB
deliveries_db = load_data()
next_delivery_id = max(d["id"] for d in deliveries_db) + 1 if deliveries_db else 1