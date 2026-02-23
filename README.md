# Medicine Delivery API

A simple, secure, and scalable RESTful API for managing medicine deliveries, built with **FastAPI** (Python). This project demonstrates CRUD operations, JWT authentication, environment variable security, CORS support, and JSON persistence (with future plans for PostgreSQL migration).

## Features
- **JWT Authentication** (login with username/password)
- **Protected Endpoints** (create/update/delete deliveries require auth)
- **Patient Management** (create/list patients)
- **Delivery Management** (create/list/update deliveries with status tracking)
- **Invoice Integration** (nota fiscal number and emission date)
- **Environment Variables** for secrets (no hardcoded passwords/keys)
- **CORS** enabled for frontend integration
- **Interactive Swagger Docs** at `/docs`
- Deployed on Render (live demo below)

## Tech Stack
- Python 3.12
- FastAPI (modern, fast, high-performance API framework)
- Pydantic (data validation and serialization)
- Passlib + python-jose (JWT authentication with bcrypt)
- python-dotenv (load environment variables from .env)
- JSON file persistence (temporary, will migrate to PostgreSQL + SQLAlchemy)

## Live Demo
- **Swagger UI (interactive docs)**: https://fastapi-medicine-delivery.onrender.com/docs (use username: `admin`, password from environment)
- **API Root**: https://fastapi-medicine-delivery.onrender.com/

## Local Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/nathanlsr-dev/fastapi-medicine-delivery.git
   cd fastapi-medicine-delivery