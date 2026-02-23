import json
import os
from typing import List, Dict, Any

PATIENTS_FILE = "patients.json"
DELIVERIES_FILE = "deliveries.json"

def load_data(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        print(f"Arquivo {file_path} não encontrado. Criando vazio.")
        return []
    with open(file_path, "r") as f:
        content = f.read().strip()
        if not content or content.isspace():
            print(f"Arquivo {file_path} vazio. Retornando lista vazia.")
            return []
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Erro ao parsear {file_path}: {e}. Retornando lista vazia.")
            return []

def save_data(data: List[Dict[str, Any]], file_path: str):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Dados salvos em {file_path}")

# Load data
patients_db = load_data(PATIENTS_FILE)
next_patient_id = max(p.get("id", 0) for p in patients_db) + 1 if patients_db else 1

deliveries_db = load_data(DELIVERIES_FILE)
next_delivery_id = max(d.get("id", 0) for d in deliveries_db) + 1 if deliveries_db else 1