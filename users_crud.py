"""
Módulo legado. Se conserva para no romper imports viejos.
Ahora el CRUD principal de negocio vive en pacientes.py
"""
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Legacy Users"])


@router.get("")
def legacy_users_info():
    return {
        "message": "Este módulo quedó en desuso. Usa /pacientes para el nuevo sistema de pacientes crónicos."
    }
