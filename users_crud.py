# backend/users_crud.py
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from firebase_admin import db

# Reutilizamos helpers de auth.py (usan la misma clave y hash)
from auth import email_key, hash_pw

router = APIRouter(prefix="/users", tags=["Users"])

class CreateUser(BaseModel):
    username: str
    email: EmailStr
    password: str

class UpdateUser(BaseModel):
    username: Optional[str] = None
    # Para mantener consistente la clave (key = email saneado) NO permitimos cambiar email aquí
    email: Optional[EmailStr] = None
    password: Optional[str] = None

def _public_user(key: str, u: dict) -> dict:
    """Devuelve el usuario sin password y con nombres consistentes con Angular."""
    return {
        "key": key,
        "username": u.get("username", ""),
        "email": u.get("email", ""),
        # Angular espera created_at (o lo usas así en tu plantilla)
        "created_at": u.get("createdAt", 0),
    }

@router.get("")
def list_users():
    data = db.reference("users").get() or {}
    return [_public_user(k, v) for k, v in data.items()]

@router.post("")
def create_user(body: CreateUser):
    key = email_key(body.email)
    ref = db.reference(f"users/{key}")
    if ref.get():
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    user = {
        "username": body.username,
        "email": body.email,
        "password": hash_pw(body.password),
        "createdAt": int(time.time()),
    }
    ref.set(user)
    return _public_user(key, user)

@router.put("/{key}")
def update_user(key: str, body: UpdateUser):
    ref = db.reference(f"users/{key}")
    cur = ref.get()
    if not cur:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    updates = {}
    if body.username is not None:
        updates["username"] = body.username
    if body.email is not None and body.email != cur.get("email"):
        # Para no romper el login (key depende del email) bloqueamos cambio de email aquí
        raise HTTPException(status_code=400, detail="No se permite cambiar el email desde esta ruta")
    if body.password:
        updates["password"] = hash_pw(body.password)

    if not updates:
        return _public_user(key, cur)

    ref.update(updates)
    cur.update(updates)
    return _public_user(key, cur)

@router.delete("/{key}")
def delete_user(key: str):
    ref = db.reference(f"users/{key}")
    if not ref.get():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    ref.delete()
    return {"ok": True}
