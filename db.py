from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in environment variables")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class PatientDB(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    health_card_number = Column(String, unique=True, index=True)
    address = Column(String)

class DeliveryDB(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    invoice_number = Column(String)
    invoice_emission_date = Column(DateTime)
    delivery_date = Column(DateTime, nullable=True)
    status = Column(String, default="Pending")
    patient = relationship("PatientDB")

# Cria as tabelas (rode uma vez localmente ou no startup)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()