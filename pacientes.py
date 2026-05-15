import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from fb import push, ref

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])
PEDIDOS_PARA_DESCUENTO = 5


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

def generar_numero_expediente() -> str:
    counter_ref = ref("counters/pacientes_expediente")
    current = counter_ref.get() or 0
    next_value = int(current) + 1
    counter_ref.set(next_value)
    return f"PAC-{next_value:06d}"


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


@router.get("/with-discount/{paciente_id}")
def obtener_paciente_con_descuento(paciente_id: str):
    paciente = ref(f"pacientes/{paciente_id}").get()
    if not paciente:
        raise HTTPException(404, "Paciente no encontrado")

    todos_los_pedidos = ref("pedidos").get() or {}
    
    pedidos_paciente = [
        p for p in todos_los_pedidos.values()
        if p.get("paciente_id") == paciente_id
    ]
    descuentos_previos = [p for p in pedidos_paciente if p.get("descuento_aplicado")]
    ultima_fecha_descuento = max(
        [p.get("created_at", "") for p in descuentos_previos if p.get("created_at")],
        default="",
    )
    pedidos_completados_para_descuento = [
        p for p in pedidos_paciente
        if p.get("estado") == "completado" and p.get("created_at", "") > ultima_fecha_descuento
    ]

    total_compras = sum(float(p.get("total", 0)) for p in pedidos_paciente if p.get("estado") == "completado")
    conteo_pedidos = len(pedidos_completados_para_descuento)
    faltantes = max(PEDIDOS_PARA_DESCUENTO - conteo_pedidos, 0)
    es_frecuente = conteo_pedidos >= PEDIDOS_PARA_DESCUENTO
    descuento_sugerido = 0.10 if es_frecuente else 0.0

    return {
        "paciente": {
            "id": paciente_id,
            "nombre_completo": f"{paciente.get('nombres')} {paciente.get('apellidos')}",
            "tipo": "Con descuento disponible" if es_frecuente else "Regular"
        },
        "estadisticas": {
            "total_pedidos_completados": conteo_pedidos,
            "total_invertido": round(total_compras, 2),
            "proxima_recarga_mas_cercana": min([p.get("proxima_recarga_general") for p in pedidos_paciente if p.get("proxima_recarga_general")], default=None)
        },
        "beneficios": {
            "aplica_descuento": es_frecuente,
            "porcentaje_descuento": descuento_sugerido,
            "pedidos_requeridos": PEDIDOS_PARA_DESCUENTO,
            "pedidos_faltantes": faltantes,
            "mensaje": "Aplica 10% de descuento en el próximo pedido" if es_frecuente else "Le faltan {} pedidos para descuento".format(faltantes)
        }
    }




@router.post("")
def crear_paciente(body: PacienteCreate):
    paciente_id = push("pacientes")
    payload = body.model_dump(exclude_none=True)
    payload["created_at"] = int(time.time())
    payload["updated_at"] = int(time.time())
    payload["numero_expediente"] = generar_numero_expediente()
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
