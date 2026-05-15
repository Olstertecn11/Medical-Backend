import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth import email_key, hash_pw
from fb import ref

router = APIRouter(prefix="/users", tags=["Usuarios"])


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "admin"


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6)
    role: Optional[str] = None


def _public_user(user_key: str, data: dict) -> dict:
    public = {k: v for k, v in (data or {}).items() if k != "password"}
    public["key"] = user_key
    public["id"] = public.get("id", user_key)
    return public


@router.get("")
def listar_usuarios():
    data = ref("users").get() or {}
    users = [_public_user(user_key, user) for user_key, user in data.items()]
    users.sort(key=lambda user: user.get("createdAt", 0), reverse=True)
    return users


@router.post("")
def crear_usuario(body: UserCreate):
    user_key = email_key(body.email)
    if ref(f"users/{user_key}").get():
        raise HTTPException(400, "Usuario ya existe")

    now = int(time.time())
    user = {
        "id": user_key,
        "username": body.username,
        "email": body.email,
        "password": hash_pw(body.password),
        "role": body.role,
        "createdAt": now,
        "updatedAt": now,
    }
    ref(f"users/{user_key}").set(user)
    return _public_user(user_key, user)


@router.put("/{user_key}")
def actualizar_usuario(user_key: str, body: UserUpdate):
    current_key = email_key(user_key)
    current = ref(f"users/{current_key}").get()
    if not current:
        raise HTTPException(404, "Usuario no encontrado")

    target_key = email_key(body.email) if body.email else current_key
    if target_key != current_key and ref(f"users/{target_key}").get():
        raise HTTPException(400, "Ya existe un usuario con ese email")

    updates = body.model_dump(exclude_none=True)
    if "password" in updates:
        updates["password"] = hash_pw(updates["password"])
    updates["updatedAt"] = int(time.time())
    if body.email:
        updates["id"] = target_key

    updated = {**current, **updates}
    if target_key != current_key:
        ref(f"users/{target_key}").set(updated)
        ref(f"users/{current_key}").delete()
    else:
        ref(f"users/{current_key}").update(updates)

    return _public_user(target_key, updated)


@router.delete("/{user_key}")
def eliminar_usuario(user_key: str):
    clean_key = email_key(user_key)
    current = ref(f"users/{clean_key}").get()
    if not current:
        raise HTTPException(404, "Usuario no encontrado")
    ref(f"users/{clean_key}").delete()
    return {"ok": True, "message": "Usuario eliminado"}
