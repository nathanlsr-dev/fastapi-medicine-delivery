from pydantic import BaseModel # type: ignore
from datetime import datetime
from typing import Optional

class Patient(BaseModel):
    id: Optional[int] = None
    name: str
    health_card_number: str  # Carteirinha
    address: str

class Invoice(BaseModel):
    number: str
    emission_date: datetime

class Delivery(BaseModel):
    id: Optional[int] = None
    patient_id: int
    invoice: Invoice
    delivery_date: Optional[datetime] = None
    status: str = "Pending"  # Pending, In Progress, Delivered, Cancelled