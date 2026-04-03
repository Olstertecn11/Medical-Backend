import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fb import push, ref

router = APIRouter(prefix="/historial-clinico", tags=["Historial Clínico"])


class HistorialCreate(BaseModel):
    paciente_id: str
    fecha: str
    motivo_consulta: Optional[str] = None
    diagnostico: str
    tratamiento: Optional[str] = None
    notas: Optional[str] = None
    signos_vitales: Optional[dict] = None
    medico: Optional[str] = None
    proxima_cita: Optional[str] = None
    archivos: List[str] = Field(default_factory=list)


class HistorialUpdate(BaseModel):
    fecha: Optional[str] = None
    motivo_consulta: Optional[str] = None
    diagnostico: Optional[str] = None
    tratamiento: Optional[str] = None
    notas: Optional[str] = None
    signos_vitales: Optional[dict] = None
    medico: Optional[str] = None
    proxima_cita: Optional[str] = None
    archivos: Optional[List[str]] = None


@router.post("")
def crear_historial(body: HistorialCreate):
    paciente = ref(f"pacientes/{body.paciente_id}").get()
    if not paciente:
        raise HTTPException(404, "Paciente no encontrado")

    historial_id = push("historial_clinico")
    payload = body.model_dump(exclude_none=True)
    payload["created_at"] = int(time.time())
    payload["updated_at"] = int(time.time())
    ref(f"historial_clinico/{historial_id}").set(payload)
    return {"id": historial_id, **payload}


@router.get("/paciente/{paciente_id}")
def listar_historial_paciente(paciente_id: str):
    paciente = ref(f"pacientes/{paciente_id}").get()
    if not paciente:
        raise HTTPException(404, "Paciente no encontrado")

    data = ref("historial_clinico").get() or {}
    items = [
        {"id": hid, **item}
        for hid, item in data.items()
        if item.get("paciente_id") == paciente_id
    ]
    items.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return items


@router.get("/{historial_id}")
def obtener_historial(historial_id: str):
    data = ref(f"historial_clinico/{historial_id}").get()
    if not data:
        raise HTTPException(404, "Registro clínico no encontrado")
    return {"id": historial_id, **data}


@router.put("/{historial_id}")
def actualizar_historial(historial_id: str, body: HistorialUpdate):
    current = ref(f"historial_clinico/{historial_id}").get()
    if not current:
        raise HTTPException(404, "Registro clínico no encontrado")

    updates = body.model_dump(exclude_none=True)
    updates["updated_at"] = int(time.time())
    ref(f"historial_clinico/{historial_id}").update(updates)
    current.update(updates)
    return {"id": historial_id, **current}


@router.delete("/{historial_id}")
def eliminar_historial(historial_id: str):
    current = ref(f"historial_clinico/{historial_id}").get()
    if not current:
        raise HTTPException(404, "Registro clínico no encontrado")
    ref(f"historial_clinico/{historial_id}").delete()
    return {"ok": True, "message": "Registro clínico eliminado"}
