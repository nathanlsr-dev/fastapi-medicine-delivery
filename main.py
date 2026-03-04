import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Database
from db import (
    get_db, 
    Patient as PatientDB,
    Delivery as DeliveryDB,
    Hospital,
    Driver,
    Invoice,
    DeliveryAttempt,
    engine
)
from sqlalchemy.orm import Session

# Schemas
from models import Patient, Delivery, Invoice, PatientUpdate, DeliveryUpdate

# JWT
from jose import jwt, JWTError
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

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
        "name": "Nathan LSR",
        "email": "nathanlsr@outlook.com",
    },
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == "admin" and password == ADMIN_PASSWORD:
            # Salva na sessão que está logado
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("authenticated", False)

# ===================== ADMIN PANEL - CD BETIM =====================
from sqladmin import Admin, ModelView

admin = Admin(app, engine, title="CD Betim - Painel Administrativo")

class PatientAdmin(ModelView, model=PatientDB):
    column_list = ["id", "name", "health_card_number", "address"]
    column_searchable_list = ["name", "health_card_number"]
    name_plural = "Pacientes"
    icon = "fa-solid fa-user"

class HospitalAdmin(ModelView, model=Hospital):
    column_list = ["id", "name", "address"]
    column_searchable_list = ["name"]
    name_plural = "Hospitais"
    icon = "fa-solid fa-hospital"

class DriverAdmin(ModelView, model=Driver):
    column_list = ["id", "name", "username"]
    column_searchable_list = ["name", "username"]
    name_plural = "Motoristas"
    icon = "fa-solid fa-motorcycle"

class DeliveryAdmin(ModelView, model=DeliveryDB):
    column_list = ["id", "patient", "hospital", "status", "created_at", "attempts_count"]
    column_searchable_list = ["patient", "hospital", "status"]
    column_sortable_list = ["id", "created_at", "status"]
    name_plural = "Entregas"
    icon = "fa-solid fa-truck"

    form_columns = ["patient", "hospital", "status", "invoices"]
    column_labels = {
        "patient": "Paciente",
        "hospital": "Hospital",
        "status": "Status",
        "attempts_count": "Tentativas"
    }

    def attempts_count(self, model):
        return len(model.attempts)
    
    attempts_count.column_label = "Tentativas"

admin.add_view(PatientAdmin)
admin.add_view(HospitalAdmin)
admin.add_view(DriverAdmin)
admin.add_view(DeliveryAdmin)

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
    db_patient = Patient(**patient_data)
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
    return db.query(Patient).offset(skip).limit(limit).all()

@app.put("/patients/{patient_id}", response_model=Patient, tags=["Patients"])
async def update_patient(
    patient_id: int,
    update_data: PatientUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update patient data."""
    db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
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
    db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
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
    db_delivery = Delivery(
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
    query = db.query(Delivery)
    if patient_id is not None:
        query = query.filter(Delivery.patient_id == patient_id)
    if status is not None:
        query = query.filter(Delivery.status == status)
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


# ===================== ENDPOINTS PARA MOTORISTAS =====================

@app.get("/driver/pending", tags=["Motorista"])
async def list_pending_deliveries(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Lista entregas pendentes para o motorista atual"""
    deliveries = db.query(DeliveryDB).filter(DeliveryDB.status == "PENDING").all()
    return deliveries

@app.post("/driver/take/{delivery_id}", tags=["Motorista"])
async def take_delivery(
    delivery_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Motorista pega uma entrega"""
    delivery = db.query(DeliveryDB).filter(
        DeliveryDB.id == delivery_id, 
        DeliveryDB.status == "PENDING"
    ).first()
    if not delivery:
        raise HTTPException(404, detail="Entrega não encontrada ou já foi pega")
    
    delivery.status = "IN_PROGRESS"
    db.commit()
    return {"message": "Entrega pega com sucesso", "delivery_id": delivery.id}

@app.post("/driver/complete/{delivery_id}", tags=["Motorista"])
async def complete_delivery(
    delivery_id: int,
    photo_path: str,                     # agora vem antes dos Depends
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Motorista conclui entrega com foto assinada"""
    delivery = db.query(DeliveryDB).filter(DeliveryDB.id == delivery_id).first()
    if not delivery:
        raise HTTPException(404, detail="Entrega não encontrada")
    
    attempt = DeliveryAttempt(
        delivery_id=delivery.id,
        driver_id=1,   # temporário
        status="COMPLETED",
        signed_receipt_photo=photo_path,
        delivered_by="Motorista Teste"
    )
    db.add(attempt)
    delivery.status = "COMPLETED"
    db.commit()
    return {"message": "Entrega concluída com sucesso"}

@app.post("/driver/cancel/{delivery_id}", tags=["Motorista"])
async def cancel_delivery(
    delivery_id: int,
    reason: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Motorista cancela entrega"""
    delivery = db.query(DeliveryDB).filter(DeliveryDB.id == delivery_id).first()
    if not delivery:
        raise HTTPException(404, detail="Entrega não encontrada")
    
    attempt = DeliveryAttempt(
        delivery_id=delivery.id,
        driver_id=1,
        status="CANCELLED",
        reason=reason
    )
    db.add(attempt)
    delivery.status = "CANCELLED"
    db.commit()
    return {"message": "Entrega cancelada"}

@app.post("/driver/unavailable/{delivery_id}", tags=["Motorista"])
async def recipient_unavailable(
    delivery_id: int,
    reason: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Motorista marca como Destinatário Indisponível"""
    delivery = db.query(DeliveryDB).filter(DeliveryDB.id == delivery_id).first()
    if not delivery:
        raise HTTPException(404, detail="Entrega não encontrada")
    
    attempt = DeliveryAttempt(
        delivery_id=delivery.id,
        driver_id=1,
        status="RECIPIENT_UNAVAILABLE",
        reason=reason
    )
    db.add(attempt)
    db.commit()
    return {"message": "Marcado como destinatário indisponível (será cobrado)"}

# ===================== UPLOAD DE FOTO =====================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload/receipt", tags=["Motorista"])
async def upload_signed_receipt(
    current_user: Annotated[dict, Depends(get_current_user)],   # ← vem primeiro
    file: UploadFile = File(...)                                # ← vem por último
):
    """Upload da foto do comprovante assinado"""
    file_path = f"{UPLOAD_DIR}/{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"filename": file.filename, "path": file_path}

# ===================== PERFIL DO MOTORISTA =====================
@app.get("/driver/profile", tags=["Motorista"])
async def driver_profile(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Retorna o perfil completo do motorista com histórico de ações"""
    attempts = db.query(DeliveryAttempt).filter(
        DeliveryAttempt.driver_id == 1  # temporário - vamos trocar pelo ID real depois
    ).all()
    
    return {
        "motorista": "Motorista Teste",
        "total_tentativas": len(attempts),
        "concluidas": len([a for a in attempts if a.status == "COMPLETED"]),
        "canceladas": len([a for a in attempts if a.status == "CANCELLED"]),
        "indisponiveis": len([a for a in attempts if a.status == "RECIPIENT_UNAVAILABLE"]),
        "historico": [
            {
                "data": a.attempt_date,
                "status": a.status,
                "motivo": a.reason,
                "foto": a.signed_receipt_photo
            } for a in attempts
        ]
    }