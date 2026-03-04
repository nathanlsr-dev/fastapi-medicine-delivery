# 🚀 Medicine Delivery API

**Complete patient registration and medicine delivery management system**  
FastAPI + PostgreSQL + JWT — Portfolio & Enterprise Ready!

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-black?style=for-the-badge&logo=JSON%20web%20tokens)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

### ✨ Features
- Full Patient & Hospital CRUD management (separate entities)
- Medicine Delivery tracking with invoice
- Multiple invoices per delivery
- Photo upload of signed receipt
- Delivery attempts system (Completed, Cancelled, Recipient Unavailable)
- Advanced Delivery status tracking
- Beautiful Admin Panel with search and filters
- Advanced filters (patient, status, dates, pagination)
- Secure JWT authentication
- Relational PostgreSQL database (1:N)
- Ready for production and sale

### 🛠 Technologies
- FastAPI 0.115+
- SQLAlchemy 2.0
- PostgreSQL with Alembic-ready structure
- SQLAdmin (professional admin panel)
- Pydantic v2
- JWT + bcrypt
- Docker & docker-compose
- File upload (signed receipt photos)

### 🚀 How to Run

**Local (Docker recommended):**
```bash
docker-compose up --build
```

**Without Docker:**
```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

**Access:**
- API Docs: http://127.0.0.1:8000/docs
- Admin Panel: http://127.0.0.1:8000/admin

**Login: admin / admin123**

### 🐳 Docker Compose 
- Includes API + PostgreSQL with persistent data.


### 💼 For Sale / Customization
Perfect for pharmacies or clinics.
Contact: nathanlsr@outlook.com
