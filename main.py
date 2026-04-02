# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ⚠️ usa 'auth' (no 'users')
from auth import router as auth_router            # /register, /login, /me
from users_crud import router as users_crud_router  # /users (nuevo CRUD)
from productos import router as productos_router     # si ya lo tienes
from facturacion import router as facturacion_router # si ya lo tienes

# --- Si inicializas Firebase en otro módulo (fb.py), impórtalo para que se ejecute:
import fb  # asegura que fb.py hace el initialize_app()

app = FastAPI(title="POS API (FastAPI + Firebase)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(users_crud_router)
app.include_router(productos_router)
app.include_router(facturacion_router)
