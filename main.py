import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Database
from db import get_db, PatientDB, DeliveryDB
from sqlalchemy.orm import Session

# Schemas
from models import Patient, Delivery, Invoice, PatientUpdate, DeliveryUpdate

# JWT
from jose import jwt, JWTError

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set in environment variables")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

from passlib.context import CryptContext
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
    """Verify plain password against hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    """Get user from fake db."""
    if username in db:
        return db[username]

def authenticate_user(fake_db, username: str, password: str):
    """Authenticate user and return user data if valid."""
    user = get_user(fake_db, username)
    if not user or not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """Get current authenticated user from JWT token."""
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


app = FastAPI(
    title="Medicine Delivery API",
    description="Complete patient registration and medicine delivery management system - Portfolio & Enterprise Ready",
    version="1.0.0",
    contact={
        "name": "Nathan LS Rodrigues",
        "email": "nathanlsr.dev@gmail.com",
    },
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login", tags=["Auth"])
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Login with admin credentials."""
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(
        data={"sub": user["username"]}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "🚀 Medicine Delivery API is running! Go to /docs for Swagger UI"}

# ===================== PATIENTS =====================
@app.post("/patients/", response_model=Patient, tags=["Patients"])
async def create_patient(
    patient: Patient,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new patient."""
    patient_data = patient.model_dump(exclude={"id"})
    db_patient = PatientDB(**patient_data)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/patients/", tags=["Patients"])
async def list_patients(
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
):
    """List all patients with pagination."""
    return db.query(PatientDB).offset(skip).limit(limit).all()

@app.put("/patients/{patient_id}", response_model=Patient, tags=["Patients"])
async def update_patient(
    patient_id: int,
    update_data: PatientUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update patient data."""
    db_patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(db_patient, key, value)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.delete("/patients/{patient_id}", tags=["Patients"])
async def delete_patient(
    patient_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a patient."""
    db_patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(db_patient)
    db.commit()
    return {"message": f"Patient {patient_id} deleted successfully"}

# ===================== DELIVERIES =====================
@app.post("/deliveries/", response_model=Delivery, tags=["Deliveries"])
async def create_delivery(
    delivery: Delivery,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new medicine delivery."""
    db_delivery = DeliveryDB(
        patient_id=delivery.patient_id,
        invoice_number=delivery.invoice.number,
        invoice_emission_date=delivery.invoice.emission_date,
        delivery_date=delivery.delivery_date,
        status=delivery.status,
    )
    db.add(db_delivery)
    db.commit()
    db.refresh(db_delivery)
    
    return Delivery(
        id=db_delivery.id,
        patient_id=db_delivery.patient_id,
        invoice=Invoice(
            number=db_delivery.invoice_number,
            emission_date=db_delivery.invoice_emission_date
        ),
        delivery_date=db_delivery.delivery_date,
        status=db_delivery.status,
    )

@app.get("/deliveries/", tags=["Deliveries"])
async def list_deliveries(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    patient_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """List deliveries with optional filters."""
    query = db.query(DeliveryDB)
    if patient_id is not None:
        query = query.filter(DeliveryDB.patient_id == patient_id)
    if status is not None:
        query = query.filter(DeliveryDB.status == status)
    deliveries = query.offset(skip).limit(limit).all()
    
    return [
        Delivery(
            id=d.id,
            patient_id=d.patient_id,
            invoice=Invoice(number=d.invoice_number, emission_date=d.invoice_emission_date),
            delivery_date=d.delivery_date,
            status=d.status,
        ) for d in deliveries
    ]