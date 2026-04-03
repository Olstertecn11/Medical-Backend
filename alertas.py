import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from fb import push, ref

router = APIRouter(prefix="/alertas", tags=["Alertas"])

ALERT_WINDOW_DAYS = int(os.getenv("ALERT_WINDOW_DAYS", "5"))


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _alert_exists(pedido_id: str, item_code: str, due_iso: str) -> bool:
    data = ref("alertas").get() or {}
    for _, item in data.items():
        if (
            item.get("pedido_id") == pedido_id
            and item.get("medicamento_codigo") == item_code
            and item.get("proxima_recarga") == due_iso
            and item.get("estado") in {"pendiente", "enviada", "vista"}
        ):
            return True
    return False


def run_alert_scan() -> dict:
    now = datetime.now(timezone.utc)
    created = 0
    revisados = 0
    pedidos = ref("pedidos").get() or {}

    for pedido_id, pedido in pedidos.items():
        if pedido.get("estado") != "activo":
            continue
        dias_anticipacion = int(pedido.get("dias_alerta_anticipacion", ALERT_WINDOW_DAYS))
        limite = now + timedelta(days=dias_anticipacion)
        for item in pedido.get("items", []):
            revisados += 1
            due_dt = _parse_iso(item.get("proxima_recarga", ""))
            if not due_dt:
                continue
            if due_dt <= limite and not _alert_exists(pedido_id, item.get("medicamento_codigo"), item.get("proxima_recarga")):
                alert_id = push("alertas")
                payload = {
                    "pedido_id": pedido_id,
                    "paciente_id": pedido.get("paciente_id"),
                    "paciente_nombre": pedido.get("paciente_nombre"),
                    "medicamento_codigo": item.get("medicamento_codigo"),
                    "medicamento_nombre": item.get("medicamento_nombre"),
                    "cantidad": item.get("cantidad"),
                    "proxima_recarga": item.get("proxima_recarga"),
                    "mensaje": f"El paciente {pedido.get('paciente_nombre')} requiere refilling de {item.get('medicamento_nombre')}.",
                    "estado": "pendiente",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "trigger": "automatico",
                }
                ref(f"alertas/{alert_id}").set(payload)
                created += 1

    return {"ok": True, "revisados": revisados, "alertas_creadas": created, "fecha": now.isoformat()}


@router.post("/scan")
def ejecutar_scan_manual():
    return run_alert_scan()


@router.get("")
def listar_alertas(estado: Optional[str] = None, paciente_id: Optional[str] = None):
    data = ref("alertas").get() or {}
    items = [{"id": aid, **item} for aid, item in data.items()]
    if estado:
        items = [a for a in items if a.get("estado") == estado]
    if paciente_id:
        items = [a for a in items if a.get("paciente_id") == paciente_id]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


@router.put("/{alerta_id}/estado")
def cambiar_estado_alerta(alerta_id: str, estado: str):
    if estado not in {"pendiente", "enviada", "vista", "resuelta"}:
        raise HTTPException(400, "Estado no válido")
    current = ref(f"alertas/{alerta_id}").get()
    if not current:
        raise HTTPException(404, "Alerta no encontrada")
    updates = {"estado": estado, "updated_at": datetime.now(timezone.utc).isoformat()}
    ref(f"alertas/{alerta_id}").update(updates)
    current.update(updates)
    return {"id": alerta_id, **current}


@router.delete("/{alerta_id}")
def eliminar_alerta(alerta_id: str):
    current = ref(f"alertas/{alerta_id}").get()
    if not current:
        raise HTTPException(404, "Alerta no encontrada")
    ref(f"alertas/{alerta_id}").delete()
    return {"ok": True, "message": "Alerta eliminada"}
