import json
import os
from typing import List, Dict, Any
from datetime import datetime

PATIENTS_FILE = "patients.json"
DELIVERIES_FILE = "deliveries.json"

def load_data(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Creating empty.")
        return []
    with open(file_path, "r") as f:
        content = f.read().strip()
        if not content:
            print(f"File {file_path} empty. Returning empty list.")
            return []
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing {file_path}: {e}. Returning empty list.")
            return []

def convert_dates(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_dates(item) for item in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def save_data(data: List[Dict[str, Any]], file_path: str):
    serializable_data = convert_dates(data)
    with open(file_path, "w") as f:
        json.dump(serializable_data, f, indent=2)
    print(f"Data saved to {file_path}")
    
    serializable_data = convert_dates(data)
    with open(file_path, "w") as f:
        json.dump(serializable_data, f, indent=2)
    print(f"Data saved to {file_path}")

# Load patients
patients_db = load_data(PATIENTS_FILE)
next_patient_id = max(p.get("id", 0) for p in patients_db) + 1 if patients_db else 1

# Load deliveries
deliveries_db = load_data(DELIVERIES_FILE)
next_delivery_id = max(d.get("id", 0) for d in deliveries_db) + 1 if deliveries_db else 1