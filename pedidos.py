import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from fb import key, ref

router = APIRouter(prefix="/pedidos", tags=["Pedidos de Medicamentos"])

COUNTER_PATH = "counters/pedido_seq"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_number() -> str:
    def txn(current):
        current = int(current or 0)
        return current + 1

    seq = ref(COUNTER_PATH).transaction(txn)
    return f"PED-{seq:05d}"


class PedidoItem(BaseModel):
    medicamento_codigo: str
    medicamento_id: str
    cantidad: int = Field(ge=1)
    discount: bool

    @field_validator("medicamento_codigo")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        # 1. strip() elimina espacios al inicio/final
        # 2. upper() convierte "med-001" en "MED-001"
        # 3. key() aplica tu lógica de limpieza de Firebase
        normalized = value.strip().upper()
        return key(normalized)


class PedidoCreate(BaseModel):
    paciente_id: str
    fecha_pedido: Optional[str] = None
    notas: Optional[str] = None
    dias_alerta_anticipacion: int = Field(default=5, ge=0)
    items: List[PedidoItem]


@router.post("")
def crear_pedido(body: PedidoCreate):
    paciente = ref(f"pacientes/{body.paciente_id}").get()
    if not paciente:
        raise HTTPException(404, "Paciente no encontrado")
    if not body.items:
        raise HTTPException(400, "Debes enviar al menos un medicamento")

    items_finales = []
    refill_dates = []
    subtotal = 0.0

    for item in body.items:
        medicamento = ref(f"medicamentos/{item.medicamento_id}").get()
        item.medicamento_codigo = item.medicamento_codigo.split("-")[0].upper() + "-" + item.medicamento_codigo.split("-")[1]
        if not medicamento:
            raise HTTPException(404, f"Medicamento {item.medicamento_codigo} no encontrado")
        stock = int(medicamento.get("stock", 0))
        if stock < item.cantidad:
            raise HTTPException(409, f"Stock insuficiente para {medicamento.get('nombre', item.medicamento_codigo)}")

        precio = float(medicamento.get("precio", 0))
        precio = precio +(precio* (0.1 if item.discount else 1.0)) 
        refill_dias = int(medicamento.get("refill_dias", 30))
        next_refill = (datetime.now(timezone.utc) + timedelta(days=refill_dias)).isoformat()
        refill_dates.append(next_refill)
        subtotal += precio * item.cantidad

        items_finales.append({
            "medicamento_codigo": item.medicamento_codigo,
            "medicamento_nombre": medicamento.get("nombre"),
            "cantidad": item.cantidad,
            "precio_unitario": precio,
            "subtotal": round(precio * item.cantidad, 2),
            "refill_dias": refill_dias,
            "proxima_recarga": next_refill,
        })

    for item in items_finales:
        stock_ref = ref(f"medicamentos/{item['medicamento_codigo']}/stock")

        def txn(current, qty=item["cantidad"]):
            current = int(current or 0)
            if current < qty:
                raise ValueError("STOCK_INSUFFICIENT")
            return current - qty

        try:
            stock_ref.transaction(txn)
        except ValueError:
            raise HTTPException(409, f"Stock insuficiente para {item['medicamento_nombre']}")

    number = _next_number()
    pedido_id = key(number)
    created_at = _utc_now_iso()
    overall_next_refill = min(refill_dates)

    payload = {
        "id": pedido_id,
        "numero": number,
        "paciente_id": body.paciente_id,
        "paciente_nombre": f"{paciente.get('nombres', '')} {paciente.get('apellidos', '')}".strip(),
        "fecha_pedido": body.fecha_pedido or created_at,
        "created_at": created_at,
        "updated_at": created_at,
        "notas": body.notas,
        "dias_alerta_anticipacion": body.dias_alerta_anticipacion,
        "estado": "activo",
        "total": round(subtotal, 2),
        "proxima_recarga_general": overall_next_refill,
        "items": items_finales,
    }
    ref(f"pedidos/{pedido_id}").set(payload)
    return payload


@router.get("")
def listar_pedidos(paciente_id: Optional[str] = None, estado: Optional[str] = None):
    data = ref("pedidos").get() or {}
    items = [{"id": pid, **item} for pid, item in data.items()]

    if paciente_id:
        items = [p for p in items if p.get("paciente_id") == paciente_id]
    if estado:
        items = [p for p in items if p.get("estado") == estado]

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


@router.get("/{pedido_id}")
def obtener_pedido(pedido_id: str):
    data = ref(f"pedidos/{key(pedido_id)}").get()
    if not data:
        raise HTTPException(404, "Pedido no encontrado")
    return data


@router.put("/{pedido_id}/estado")
def actualizar_estado_pedido(pedido_id: str, estado: str):
    pedido_key = key(pedido_id)
    current = ref(f"pedidos/{pedido_key}").get()
    if not current:
        raise HTTPException(404, "Pedido no encontrado")
    if estado not in {"activo", "completado", "cancelado"}:
        raise HTTPException(400, "Estado no válido")
    updates = {"estado": estado, "updated_at": _utc_now_iso()}
    ref(f"pedidos/{pedido_key}").update(updates)
    current.update(updates)
    return current
