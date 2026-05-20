from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fb import key, ref

router = APIRouter(prefix="/facturacion", tags=["Facturacion"])

COUNTER_PATH = "counters/factura_seq"
IVA_RATE = 0.12


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_number() -> str:
    def txn(current):
        current = int(current or 0)
        return current + 1

    seq = ref(COUNTER_PATH).transaction(txn)
    return f"FAC-{seq:06d}"


class FacturaCreate(BaseModel):
    pedido_id: str
    nit: str = Field(default="CF", min_length=2)
    razon_social: Optional[str] = None
    direccion_fiscal: Optional[str] = None
    forma_pago: str = "Efectivo"
    observaciones: Optional[str] = None


def _find_invoice_by_order(pedido_id: str) -> Optional[dict]:
    facturas = ref("facturas").get() or {}
    for factura_id, factura in facturas.items():
        if factura.get("pedido_id") == pedido_id:
            return {"id": factura_id, **factura}
    return None


def _build_invoice_items(pedido: dict) -> tuple[list[dict], float, float, float]:
    items = []
    subtotal_bruto = 0.0
    descuento_total = 0.0
    total = 0.0

    for item in pedido.get("items", []):
        cantidad = int(item.get("cantidad", 0))
        precio_original = float(item.get("precio_original", item.get("precio_unitario", 0)))
        precio_unitario = float(item.get("precio_unitario", precio_original))
        descuento_unitario = max(precio_original - precio_unitario, 0)
        subtotal_linea = round(precio_unitario * cantidad, 2)

        subtotal_bruto += precio_original * cantidad
        descuento_total += descuento_unitario * cantidad
        total += subtotal_linea

        items.append({
            "codigo": item.get("medicamento_codigo"),
            "descripcion": item.get("medicamento_nombre"),
            "cantidad": cantidad,
            "precio_unitario": round(precio_unitario, 2),
            "precio_original": round(precio_original, 2),
            "descuento": round(descuento_unitario * cantidad, 2),
            "subtotal": subtotal_linea,
        })

    return items, round(subtotal_bruto, 2), round(descuento_total, 2), round(total, 2)


@router.get("")
def listar_facturas():
    data = ref("facturas").get() or {}
    facturas = [{"id": factura_id, **factura} for factura_id, factura in data.items()]
    facturas.sort(key=lambda factura: factura.get("created_at", ""), reverse=True)
    return facturas


@router.post("")
def emitir_factura(body: FacturaCreate):
    pedido_id = key(body.pedido_id)
    pedido = ref(f"pedidos/{pedido_id}").get()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    if pedido.get("estado") == "cancelado":
        raise HTTPException(400, "No se puede facturar un pedido cancelado")

    existing = _find_invoice_by_order(pedido_id)
    if existing:
        raise HTTPException(409, "Este pedido ya tiene una factura emitida")

    items, subtotal_bruto, descuento_total, total = _build_invoice_items(pedido)
    if not items:
        raise HTTPException(400, "El pedido no tiene items facturables")

    numero = _next_number()
    factura_id = key(numero)
    created_at = _utc_now_iso()
    total_sin_iva = round(total / (1 + IVA_RATE), 2)
    iva = round(total - total_sin_iva, 2)

    payload = {
        "id": factura_id,
        "numero": numero,
        "pedido_id": pedido_id,
        "pedido_numero": pedido.get("numero"),
        "paciente_id": pedido.get("paciente_id"),
        "paciente_nombre": pedido.get("paciente_nombre"),
        "nit": body.nit.strip().upper() or "CF",
        "razon_social": body.razon_social or pedido.get("paciente_nombre") or "Consumidor final",
        "direccion_fiscal": body.direccion_fiscal or "Ciudad",
        "forma_pago": body.forma_pago,
        "observaciones": body.observaciones,
        "fecha_emision": created_at,
        "created_at": created_at,
        "estado": "emitida",
        "moneda": "GTQ",
        "subtotal_bruto": subtotal_bruto,
        "descuento_total": descuento_total,
        "subtotal": total_sin_iva,
        "iva": iva,
        "total": total,
        "items": items,
    }

    ref(f"facturas/{factura_id}").set(payload)
    ref(f"pedidos/{pedido_id}").update({
        "factura_id": factura_id,
        "factura_numero": numero,
        "estado_facturacion": "facturado",
        "updated_at": created_at,
    })
    return payload


@router.get("/{factura_id}")
def obtener_factura(factura_id: str):
    clean_id = key(factura_id)
    factura = ref(f"facturas/{clean_id}").get()
    if not factura:
        raise HTTPException(404, "Factura no encontrada")
    return {"id": clean_id, **factura}
