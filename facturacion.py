# backend/facturacion.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, HTTPException, Query
from firebase_admin import db
import fb  # inicializa la app y expone fb.ref(), fb.key()

router = APIRouter(prefix="/facturacion", tags=["Facturación"])

# =========================================================
# CONFIGURACIÓN
# =========================================================
# Usa el MISMO nodo que tu CRUD de productos
# (en tu RTDB se ve como /productos)
PRODUCTS_NODE = "productos"

# Correlativo almacenado en /counters/invoice_seq
COUNTER_PATH = "counters/invoice_seq"
INVOICES_NODE = "facturas"


# =========================================================
# MODELOS
# =========================================================
class Item(BaseModel):
    code: str
    description: str
    price: float = Field(ge=0)
    qty: int = Field(ge=1)

    @validator("code", pre=True)
    def norm_code(cls, v):
        return fb.key(str(v))

class InvoiceCreate(BaseModel):
    customer: Optional[str] = None
    cashier: Optional[str] = None   # usuario que factura (opcional)
    tax_rate: float = 0.12          # 12% por defecto
    items: List[Item]

class Invoice(InvoiceCreate):
    id: str
    number: str
    subtotal: float
    tax: float
    total: float
    created_at: str


# =========================================================
# HELPERS
# =========================================================
def _round2(x: float) -> float:
    return float(f"{x:.2f}")

def calc_totals(items: List[Item], tax_rate: float) -> Dict[str, float]:
    subtotal = sum(i.price * i.qty for i in items)
    tax = subtotal * tax_rate
    total = subtotal + tax
    return {
        "subtotal": _round2(subtotal),
        "tax": _round2(tax),
        "total": _round2(total),
    }

def next_invoice_number() -> str:
    """
    Incrementa correlativo en RTDB:
      /counters/invoice_seq => 1, 2, 3, ...
    Devuelve: 'RPT-001', 'RPT-002', ...
    """
    def txn(current):
        current = int(current or 0)
        return current + 1

    ref_seq = fb.ref(COUNTER_PATH)
    seq = ref_seq.transaction(txn)  # atómico
    return f"RPT-{seq:03d}"

def get_product_by_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Busca el producto en /productos usando:
      1) clave normalizada (fb.key)
      2) fallback clave tal cual (por si ya existe en mayúsculas)
    """
    code_key = fb.key(code)
    snap = fb.ref(f"{PRODUCTS_NODE}/{code_key}").get()
    if not snap:
        snap = fb.ref(f"{PRODUCTS_NODE}/{code}").get()

    return snap if isinstance(snap, dict) else None

def dec_stock_transaction(code_key: str, qty: int):
    """
    Descuenta stock en /productos/{code_key}/stock de forma atómica.
    Lanza 409 si no hay suficiente.
    """
    stock_ref = fb.ref(f"{PRODUCTS_NODE}/{code_key}/stock")

    def txn(current):
        current = int(current or 0)
        if current < qty:
            raise ValueError("STOCK_INSUFFICIENT")
        return current - qty

    try:
        stock_ref.transaction(txn)
    except ValueError as e:
        if str(e) == "STOCK_INSUFFICIENT":
            raise HTTPException(status_code=409, detail=f"Stock insuficiente para {code_key}")
        raise


# =========================================================
# ENDPOINTS
# =========================================================
@router.get("/producto", summary="Busca producto por código")
def producto_por_codigo(code: str = Query(..., description="Código del producto, ej. R001")):
    prod = get_product_by_code(code)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Mapeo flexible de campos
    desc = prod.get("description") or prod.get("name") or ""
    price = float(prod.get("price") or prod.get("precio") or 0)
    stock = int(prod.get("stock") or 0)

    return {
        "code": fb.key(code),  # devolvemos clave normalizada
        "description": desc,
        "price": price,
        "stock": stock,
    }

@router.post("/facturas", response_model=Invoice, summary="Crea una factura")
def crear_factura(payload: InvoiceCreate):
    if not payload.items:
        raise HTTPException(status_code=400, detail="La factura requiere al menos un ítem")

    # 1) Valida y normaliza ítems contra RTDB
    items_ok: List[Item] = []
    for it in payload.items:
        prod = get_product_by_code(it.code)
        if not prod:
            raise HTTPException(status_code=404, detail=f"Producto {it.code} no existe")

        # usa los datos “oficiales” del producto
        desc = (prod.get("description") or prod.get("name") or it.description or "").strip()
        price = float(prod.get("price") or prod.get("precio") or it.price or 0)
        stock = int(prod.get("stock") or 0)
        if stock < it.qty:
            raise HTTPException(status_code=409, detail=f"Stock insuficiente para {it.code}")

        items_ok.append(
            Item(
                code=fb.key(it.code),
                description=desc,
                price=price,
                qty=it.qty
            )
        )

    # 2) Totales
    totals = calc_totals(items_ok, payload.tax_rate)

    # 3) Número e ID
    number = next_invoice_number()
    inv_id = fb.key(number)  # ej. "rpt_001"

    # 4) Descontar stock (transacciones)
    for it in items_ok:
        dec_stock_transaction(it.code, it.qty)

    # 5) Guardar factura
    now = datetime.utcnow().isoformat() + "Z"
    invoice_data = {
        "id": inv_id,
        "number": number,
        "created_at": now,
        "customer": (payload.customer or "").strip(),
        "cashier": (payload.cashier or "").strip(),
        "tax_rate": payload.tax_rate,
        "subtotal": totals["subtotal"],
        "tax": totals["tax"],
        "total": totals["total"],
        "items": [it.dict() for it in items_ok],
    }
    fb.ref(f"{INVOICES_NODE}/{inv_id}").set(invoice_data)
    return invoice_data

@router.get("/facturas/{invoice_id}", response_model=Invoice, summary="Obtiene una factura por id")
def obtener_factura(invoice_id: str):
    data = fb.ref(f"{INVOICES_NODE}/{fb.key(invoice_id)}").get()
    if not data:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return data

@router.get("/facturas", summary="Lista facturas (más recientes primero)")
def listar_facturas(limit: int = 50):
    snap = fb.ref(INVOICES_NODE).order_by_key().get() or {}
    # RTDB devuelve dict; ordenamos por número desc
    arr = list(snap.values())
    arr.sort(key=lambda x: x.get("number", ""), reverse=True)
    return arr[:limit]
