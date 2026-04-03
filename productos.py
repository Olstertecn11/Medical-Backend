"""
Módulo legado. Se conserva para no romper imports viejos.
Ahora el CRUD principal de inventario vive en medicamentos.py
"""
from fastapi import APIRouter

router = APIRouter(prefix="/productos", tags=["Legacy Productos"])


@router.get("")
def legacy_productos_info():
    return {
        "message": "Este módulo quedó en desuso. Usa /medicamentos para el nuevo sistema de pacientes crónicos."
    }
