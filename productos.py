# backend/productos.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from fb import ref, key

router = APIRouter(prefix="/productos", tags=["Productos"])

class Producto(BaseModel):
    code: str
    name: str
    price: float = Field(ge=0)
    tax: float = 0.12
    stock: int = 0
    image: Optional[str] = None

@router.post("")
def crear(p: Producto):
    r = ref(f"productos/{key(p.code)}")
    if r.get():
        raise HTTPException(400, "El producto ya existe")
    r.set(p.model_dump())
    return {"ok": True}

@router.get("")
def listar(q: Optional[str] = None):
    data = ref("productos").get() or {}
    items = list(data.values())
    if q:
        ql = q.lower()
        items = [i for i in items if ql in i["code"].lower() or ql in i["name"].lower()]
    return items

@router.get("/{code}")
def obtener(code: str):
    data = ref(f"productos/{key(code)}").get()
    if not data:
        raise HTTPException(404, "Producto no encontrado")
    return data

@router.put("/{code}")
def actualizar(code: str, p: Producto):
    r = ref(f"productos/{key(code)}")
    if not r.get():
        raise HTTPException(404, "Producto no encontrado")
    r.update(p.model_dump())
    return {"ok": True}

@router.delete("/{code}")
def borrar(code: str):
    r = ref(f"productos/{key(code)}")
    if not r.get():
        raise HTTPException(404, "Producto no encontrado")
    r.delete()
    return {"ok": True}
