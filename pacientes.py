import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from fb import push, ref

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


class PacienteBase(BaseModel):
    nombres: str = Field(min_length=2)
    apellidos: str = Field(min_length=2)
    fecha_nacimiento: Optional[str] = None
    sexo: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    contacto_emergencia_nombre: Optional[str] = None
    contacto_emergencia_telefono: Optional[str] = None
    enfermedades_cronicas: List[str] = []
    alergias: List[str] = []
    observaciones: Optional[str] = None
    activo: bool = True


class PacienteCreate(PacienteBase):
    dpi: Optional[str] = None
    numero_expediente: Optional[str] = None


class PacienteUpdate(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    sexo: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    contacto_emergencia_nombre: Optional[str] = None
    contacto_emergencia_telefono: Optional[str] = None
    enfermedades_cronicas: Optional[List[str]] = None
    alergias: Optional[List[str]] = None
    observaciones: Optional[str] = None
    dpi: Optional[str] = None
    numero_expediente: Optional[str] = None
    activo: Optional[bool] = None


def _with_id(paciente_id: str, data: dict) -> dict:
    return {"id": paciente_id, **(data or {})}


@router.get("")
def listar_pacientes(q: Optional[str] = None, activos: Optional[bool] = None):
    data = ref("pacientes").get() or {}
    items = [_with_id(pid, item) for pid, item in data.items()]

    if activos is not None:
        items = [p for p in items if p.get("activo", True) == activos]

    if q:
        ql = q.lower().strip()
        items = [
            p for p in items
            if ql in f"{p.get('nombres', '')} {p.get('apellidos', '')}".lower()
            or ql in str(p.get("dpi", "")).lower()
            or ql in str(p.get("numero_expediente", "")).lower()
            or ql in str(p.get("telefono", "")).lower()
        ]

    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return items


@router.post("")
def crear_paciente(body: PacienteCreate):
    paciente_id = push("pacientes")
    payload = body.model_dump(exclude_none=True)
    payload["created_at"] = int(time.time())
    payload["updated_at"] = int(time.time())
    ref(f"pacientes/{paciente_id}").set(payload)
    return _with_id(paciente_id, payload)


@router.get("/{paciente_id}")
def obtener_paciente(paciente_id: str):
    data = ref(f"pacientes/{paciente_id}").get()
    if not data:
        raise HTTPException(404, "Paciente no encontrado")
    return _with_id(paciente_id, data)


@router.put("/{paciente_id}")
def actualizar_paciente(paciente_id: str, body: PacienteUpdate):
    current = ref(f"pacientes/{paciente_id}").get()
    if not current:
        raise HTTPException(404, "Paciente no encontrado")

    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    updates["updated_at"] = int(time.time())
    ref(f"pacientes/{paciente_id}").update(updates)
    current.update(updates)
    return _with_id(paciente_id, current)


@router.delete("/{paciente_id}")
def eliminar_paciente(paciente_id: str):
    current = ref(f"pacientes/{paciente_id}").get()
    if not current:
        raise HTTPException(404, "Paciente no encontrado")
    ref(f"pacientes/{paciente_id}").delete()
    return {"ok": True, "message": "Paciente eliminado"}
