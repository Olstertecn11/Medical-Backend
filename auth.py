import os
import re
import time
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Header, HTTPException
from jose import jwt
from pydantic import BaseModel, EmailStr
from firebase_admin import db

JWT_SECRET = os.getenv("JWT_SECRET", "mi_jwt_secreto")
JWT_EXPIRES = int(os.getenv("JWT_EXPIRES", "12"))


def email_key(email: str) -> str:
    return re.sub(r"[.#$/\[\]]", "_", email.lower())


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(uid: str, email: str, role: str = "admin") -> str:
    exp = datetime.utcnow() + timedelta(hours=JWT_EXPIRES)
    return jwt.encode({"sub": uid, "email": email, "role": role, "exp": exp}, JWT_SECRET, "HS256")


def decode_token(authorization: str = "") -> dict:
    token = authorization.replace("Bearer", "").strip()
    if not token:
        raise HTTPException(401, "Falta token Bearer")
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Token inválido")


router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "admin"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(body: RegisterIn):
    user_key = email_key(body.email)
    if db.reference(f"users/{user_key}").get():
        raise HTTPException(400, "Usuario ya existe")

    user = {
        "id": user_key,
        "username": body.username,
        "email": body.email,
        "password": hash_pw(body.password),
        "role": body.role,
        "createdAt": int(time.time()),
    }
    db.reference(f"users/{user_key}").set(user)
    token = create_token(user_key, body.email, body.role)
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}


@router.post("/login")
def login(body: LoginIn):
    user_key = email_key(body.email)
    user = db.reference(f"users/{user_key}").get()
    if not user or not check_pw(body.password, user["password"]):
        raise HTTPException(401, "Credenciales incorrectas")
    token = create_token(user_key, user["email"], user.get("role", "admin"))
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}


@router.get("/me")
def me(authorization: str = Header(default="")):
    payload = decode_token(authorization)
    user_key = email_key(payload["email"])
    user = db.reference(f"users/{user_key}").get()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    return {"user": {k: v for k, v in user.items() if k != "password"}}


# Compatibilidad opcional con rutas antiguas
legacy_router = APIRouter(prefix="", tags=["Auth Legacy"])
legacy_router.add_api_route("/register", register, methods=["POST"])
legacy_router.add_api_route("/login", login, methods=["POST"])
legacy_router.add_api_route("/me", me, methods=["GET"])
