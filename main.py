import os
from datetime import datetime, timedelta, timezone
from typing import Annotated
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status # type: ignore
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from pydantic import BaseModel # type: ignore
from passlib.context import CryptContext # type: ignore
from jose import JWTError, jwt # type: ignore
from dotenv import load_dotenv # type: ignore
from models import Patient, Delivery, Invoice, PatientUpdate, DeliveryUpdate
from database import patients_db, deliveries_db, next_delivery_id, next_patient_id, save_data, PATIENTS_FILE, DELIVERIES_FILE

load_dotenv()

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
    current_user: Annotated[dict, Depends(get_current_user)]
):
    global next_patient_id
    patient.id = next_patient_id
    patients_db.append(patient.dict())
    save_data(patients_db, PATIENTS_FILE) # Save patients
    next_patient_id += 1
    return patient

@app.get("/patients/")
async def list_patients():
    return patients_db

@app.post("/deliveries/", response_model=Delivery)
async def create_delivery(
    delivery: Delivery,
    current_user: Annotated[dict, Depends(get_current_user)]
):
    global next_delivery_id
    delivery.id = next_delivery_id
    deliveries_db.append(delivery.dict())
    save_data(deliveries_db, DELIVERIES_FILE) # Save deliveries
    next_delivery_id += 1
    return delivery

@app.get("/deliveries/")
async def list_deliveries(
    patient_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10
):
    filtered = deliveries_db
    
    if patient_id is not None:
        filtered = [d for d in filtered if d["patient_id"] == patient_id]    
    if status is not None:
        filtered = [d for d in filtered if d["status"] == status]
        
    return filtered[skip:skip + limit]

@app.put("/patients/{patient_id}", response_model=Patient)
async def update_patient(
    patient_id: int,
    update_data: PatientUpdate,
    current_user: Annotated[dict, Depends(get_current_user)]
):
    for i, existing in enumerate(patients_db):
        if existing["id"] == patient_id:
            # Converte pra dict ignorando campos não enviados e None
            update_dict = update_data.dict(exclude_unset=True, exclude_none=True)
            # Atualiza apenas os campos que vieram
            updated = {**existing, **update_dict}
            patients_db[i] = updated
            save_data(patients_db, PATIENTS_FILE)
            return updated
    raise HTTPException(status_code=404, detail="Patient not found")


@app.put("/deliveries/{delivery_id}", response_model=Delivery)
async def update_delivery(
    delivery_id: int,
    update_data: DeliveryUpdate,
    current_user: Annotated[dict, Depends(get_current_user)]
):
    for i, existing in enumerate(deliveries_db):
        if existing["id"] == delivery_id:
            update_dict = update_data.dict(exclude_unset=True, exclude_none=True)
            updated = {**existing, **update_dict}
            deliveries_db[i] = updated
            save_data(deliveries_db, DELIVERIES_FILE)
            return updated
    raise HTTPException(status_code=404, detail="Delivery not found")

@app.delete("/patients/{patient_id}")
async def delete_patient(
    patient_id: int,
    current_user: Annotated[dict, Depends(get_current_user)]
):
    for i, patient in enumerate(patients_db):
        if patient["id"] == patient_id:
            patients_db.pop(i)
            save_data(patients_db, PATIENTS_FILE)
            return {"message": f"Patient {patient_id} deleted successfully"}
    raise HTTPException(status_code=404, detail="Patient not found")

@app.delete("/deliveries/{delivery_id}")
async def delete_delivery(
    delivery_id: int,
    current_user: Annotated[dict, Depends(get_current_user)]
):
    for i, delivery in enumerate(deliveries_db):
        if delivery["id"] == delivery_id:
            deliveries_db.pop(i)
            save_data(deliveries_db, DELIVERIES_FILE)
            return {"message": f"Delivery {delivery_id} deleted successfully"}
    raise HTTPException(status_code=404, detail="Delivery not found")