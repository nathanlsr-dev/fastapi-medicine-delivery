import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não encontrada no .env")

print(f"🔗 Conectando ao banco: {DATABASE_URL}")

engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ===================== PACIENTES =====================
class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    health_card_number = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=False)
    
    deliveries = relationship("Delivery", back_populates="patient", foreign_keys="Delivery.patient_id")

    def __str__(self):
        return f"{self.name} - {self.health_card_number}"

# ===================== HOSPITAIS =====================
class Hospital(Base):
    __tablename__ = "hospitals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    
    deliveries = relationship("Delivery", back_populates="hospital", foreign_keys="Delivery.hospital_id")

# ===================== MOTORISTAS =====================
class Driver(Base):
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    deliveries = relationship("Delivery", back_populates="driver", foreign_keys="Delivery.driver_id")

# ===================== DELIVERIES =====================
class Delivery(Base):
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="deliveries")
    hospital = relationship("Hospital", back_populates="deliveries")
    driver = relationship("Driver", back_populates="deliveries")
    attempts = relationship("DeliveryAttempt", back_populates="delivery")
    invoices = relationship("Invoice", back_populates="delivery")

# ===================== INVOICES =====================
class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(String, nullable=False)
    emission_date = Column(DateTime, nullable=False)
    pdf_path = Column(String)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"))
    
    delivery = relationship("Delivery", back_populates="invoices")

# ===================== DELIVERY ATTEMPTS =====================
class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    status = Column(String, nullable=False)
    attempt_date = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text)
    signed_receipt_photo = Column(String)
    delivered_by = Column(String)
    
    delivery = relationship("Delivery", back_populates="attempts")
    driver = relationship("Driver")

# Cria todas as tabelas
# === APENAS PARA DESENVOLVIMENTO ===
# Remove todas as tabelas antigas e recria com a nova estrutura
Base.metadata.drop_all(bind=engine)
# ===================================

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()