import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fb import key, ref

router = APIRouter(prefix="/medicamentos", tags=["Medicamentos"])


class Medicamento(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    presentacion: Optional[str] = None
    concentracion: Optional[str] = None
    laboratorio: Optional[str] = None
    precio: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    refill_dias: int = Field(default=30, ge=1)
    activo: bool = True


@router.post("")
def crear_medicamento(body: Medicamento):
    med_key = key(body.codigo)
    existing = ref(f"medicamentos/{med_key}").get()
    if existing:
        raise HTTPException(400, "El medicamento ya existe")
    payload = body.model_dump()
    payload["created_at"] = int(time.time())
    payload["updated_at"] = int(time.time())
    ref(f"medicamentos/{med_key}").set(payload)
    return {"id": med_key, **payload}


@router.get("")
def listar_medicamentos(q: Optional[str] = None, activos: Optional[bool] = None, bajo_stock: Optional[bool] = None):
    data = ref("medicamentos").get() or {}
    items = [{"id": mid, **item} for mid, item in data.items()]

    if activos is not None:
        items = [m for m in items if m.get("activo", True) == activos]

    if bajo_stock:
        items = [m for m in items if int(m.get("stock", 0)) <= int(m.get("stock_minimo", 0))]

    if q:
        ql = q.lower().strip()
        items = [
            m for m in items
            if ql in m.get("codigo", "").lower()
            or ql in m.get("nombre", "").lower()
            or ql in (m.get("descripcion") or "").lower()
        ]

    items.sort(key=lambda x: x.get("nombre", ""))
    return items


@router.get("/{codigo}")
def obtener_medicamento(codigo: str):
    med_key = key(codigo)
    data = ref(f"medicamentos/{med_key}").get()
    if not data:
        raise HTTPException(404, "Medicamento no encontrado")
    return {"id": med_key, **data}


@router.put("/{codigo}")
def actualizar_medicamento(codigo: str, body: Medicamento):
    med_key = key(codigo)
    current = ref(f"medicamentos/{med_key}").get()
    if not current:
        raise HTTPException(404, "Medicamento no encontrado")
    payload = body.model_dump()
    payload["updated_at"] = int(time.time())
    ref(f"medicamentos/{med_key}").update(payload)
    current.update(payload)
    return {"id": med_key, **current}


@router.delete("/{codigo}")
def eliminar_medicamento(codigo: str):
    med_key = key(codigo)
    current = ref(f"medicamentos/{med_key}").get()
    if not current:
        raise HTTPException(404, "Medicamento no encontrado")
    ref(f"medicamentos/{med_key}").delete()
    return {"ok": True, "message": "Medicamento eliminado"}
