"""
Módulo legado. Se conserva para no romper imports viejos.
Ahora el flujo principal vive en pedidos.py y alertas.py
"""
from fastapi import APIRouter

router = APIRouter(prefix="/facturacion", tags=["Legacy Facturación"])


@router.get("")
def legacy_facturacion_info():
    return {
        "message": "Este módulo quedó en desuso. Usa /pedidos y /alertas para el nuevo sistema de pacientes crónicos."
    }
