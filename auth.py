# backend/auth.py
import os, re, time, bcrypt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from jose import jwt
from firebase_admin import db  # usa la app ya inicializada en main.py

JWT_SECRET  = os.getenv("JWT_SECRET", "mi_jwt_secreto")
JWT_EXPIRES = int(os.getenv("JWT_EXPIRES", "2"))

def email_key(email: str) -> str:
    return re.sub(r"[.#$/\[\]]", "_", email.lower())

def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(uid: str, email: str) -> str:
    exp = datetime.utcnow() + timedelta(hours=JWT_EXPIRES)
    return jwt.encode({"sub": uid, "email": email, "exp": exp}, JWT_SECRET, "HS256")

router = APIRouter(prefix="", tags=["Auth"])

class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str

@router.post("/register")
def register(body: RegisterIn):
    key = email_key(body.email)
    if db.reference(f"users/{key}").get():
        raise HTTPException(400, "Usuario ya existe")
    user = {
        "username": body.username,
        "email": body.email,
        "password": hash_pw(body.password),
        "createdAt": int(time.time())
    }
    db.reference(f"users/{key}").set(user)
    token = create_token(key, body.email)
    return {"token": token, "user": user}

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login(body: LoginIn):
    key = email_key(body.email)
    user = db.reference(f"users/{key}").get()
    if not user or not check_pw(body.password, user["password"]):
        raise HTTPException(401, "Credenciales incorrectas")
    token = create_token(key, body.email)
    return {"token": token, "user": user}

@router.get("/me")
def me(authorization: str = Header(default="")):
    token = authorization.replace("Bearer", "").strip()
    if not token:
        raise HTTPException(401, "Falta token Bearer")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Token inválido")
    key = email_key(payload["email"])
    user = db.reference(f"users/{key}").get()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    return {"user": user}
