from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime

Base = declarative_base()

class PatientDB(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Adicione autoincrement=True
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

def get_db(db_session):
    try:
        yield db_session
    finally:
        db_session.close()