import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query, Body, Path
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

from db import get_db, PatientDB, DeliveryDB, Base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from models import Patient, Delivery, Invoice, PatientUpdate, DeliveryUpdate
from database import patients_db, deliveries_db, next_patient_id, next_delivery_id, save_data, PATIENTS_FILE, DELIVERIES_FILE

load_dotenv()  # Mantém isso simples — ele procura .env na raiz automaticamente

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in environment variables")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set in environment variables")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD not set in environment variables")


fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash(ADMIN_PASSWORD),
    }
}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    if username in db:
        return db[username]

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=username)
    if user is None:
        raise credentials_exception
    return user

def get_db_dependency():
    return Depends(get_db, use_cache=False)


app = FastAPI(title="Medicine Delivery API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
async def root():
    return {"message": "Medicine Delivery API running! Visit /docs for Swagger UI"}

@app.post("/patients/", response_model=Patient)
async def create_patient(
    patient: Patient,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]  # <--- Annotated esconde do Swagger
):
    db_patient = PatientDB(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    patient.id = db_patient.id
    return patient

@app.get("/patients/")
async def list_patients(db: Session = Depends(lambda: next(get_db(SessionLocal())))):
    return db.query(PatientDB).all()

@app.put("/patients/{patient_id}", response_model=Patient)
async def update_patient(
    patient_id: int,
    update_data: PatientUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    db_patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    update_dict = update_data.dict(exclude_unset=True, exclude_none=True)
    for key, value in update_dict.items():
        setattr(db_patient, key, value)
    
    db.commit()
    db.refresh(db_patient)
    return Patient(id=db_patient.id, name=db_patient.name, health_card_number=db_patient.health_card_number, address=db_patient.address)

@app.delete("/patients/{patient_id}")
async def delete_patient(
    patient_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    db_patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db.delete(db_patient)
    db.commit()
    return {"message": f"Patient {patient_id} deleted successfully"}

@app.post("/deliveries/", response_model=Delivery)
async def create_delivery(
    delivery: Delivery,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    db_delivery = DeliveryDB(**delivery.dict())
    db.add(db_delivery)
    db.commit()
    db.refresh(db_delivery)
    delivery.id = db_delivery.id
    return delivery    
    

@app.get("/deliveries/")
async def list_deliveries(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    patient_id: Optional[int] = None,   
    status: Optional[str] = None,
    emission_date_from: Optional[datetime] = None,
    emission_date_to: Optional[datetime] = None,
    delivery_date_from: Optional[datetime] = None,
    delivery_date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 10,
):
    query = db.query(DeliveryDB)
    
    if patient_id is not None:
        query = query.filter(DeliveryDB.patient_id == patient_id)
    
    if status is not None:
        query = query.filter(DeliveryDB.status == status)
    
    if emission_date_from is not None:
        query = query.filter(DeliveryDB.invoice_emission_date >= emission_date_from)
    
    if emission_date_to is not None:
        query = query.filter(DeliveryDB.invoice_emission_date <= emission_date_to)
    
    if delivery_date_from is not None:
        query = query.filter(DeliveryDB.delivery_date >= delivery_date_from)
    
    if delivery_date_to is not None:
        query = query.filter(DeliveryDB.delivery_date <= delivery_date_to)
    
    return query.offset(skip).limit(limit).all()