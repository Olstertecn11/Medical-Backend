import time
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fb import ref, push # Asegúrate de tener push para generar IDs únicos si prefieres

router = APIRouter(prefix="/medicamentos", tags=["Medicamentos"])

class MedicamentoBase(BaseModel):
    nombre: str = Field(min_length=2)
    descripcion: Optional[str] = None
    presentacion: Optional[str] = None
    concentracion: Optional[str] = None
    laboratorio: Optional[str] = None
    precio: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    refill_dias: int = Field(default=30, ge=1)
    activo: bool = True

class MedicamentoCreate(MedicamentoBase):
    codigo: Optional[str] = None # Se generará automáticamente si no se envía

def generar_codigo_medicamento() -> str:
    counter_ref = ref("counters/medicamentos_codigo")
    current = counter_ref.get() or 0
    next_value = int(current) + 1
    counter_ref.set(next_value)
    # Formato MED-000001
    return f"MED-{next_value:06d}"

@router.post("")
def crear_medicamento(body: MedicamentoCreate):
    # Generamos el código automático
    nuevo_codigo = generar_codigo_medicamento()
    
    payload = body.model_dump()
    payload["codigo"] = nuevo_codigo
    payload["created_at"] = int(time.time())
    payload["updated_at"] = int(time.time())
    
    # Usamos el código generado como la llave en la base de datos
    ref(f"medicamentos/{nuevo_codigo}").set(payload)
    
    return {"id": nuevo_codigo, **payload}

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

@router.get("/{id}") # Cambiamos a ID para ser consistentes
def obtener_medicamento(id: str):
    data = ref(f"medicamentos/{id}").get()
    if not data:
        raise HTTPException(404, "Medicamento no encontrado")
    return {"id": id, **data}

@router.put("/{id}")
def actualizar_medicamento(id: str, body: MedicamentoBase):
    current_ref = ref(f"medicamentos/{id}")
    current_data = current_ref.get()
    
    if not current_data:
        raise HTTPException(404, "Medicamento no encontrado")
    
    payload = body.model_dump()
    payload["updated_at"] = int(time.time())
    
    current_ref.update(payload)
    return {"id": id, **payload}

@router.delete("/{id}")
def eliminar_medicamento(id: str):
    current_ref = ref(f"medicamentos/{id}")
    if not current_ref.get():
        raise HTTPException(404, "Medicamento no encontrado")
    current_ref.delete()
    return {"ok": True, "message": "Medicamento eliminado"}
