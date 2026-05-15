import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import fb
from alertas import router as alertas_router, run_alert_scan
from auth import legacy_router as auth_legacy_router
from auth import router as auth_router
from historial import router as historial_router
from medicamentos import router as medicamentos_router
from pacientes import router as pacientes_router
from pedidos import router as pedidos_router
from users_crud import router as users_router

ALERT_SCAN_INTERVAL_SECONDS = int(os.getenv("ALERT_SCAN_INTERVAL_SECONDS", "3600"))
ENABLE_ALERT_SCANNER = os.getenv("ENABLE_ALERT_SCANNER", "true").lower() == "true"


async def _alert_scanner_loop():
    while True:
        try:
            run_alert_scan()
        except Exception as exc:
            print(f"[alert_scanner] error: {exc}")
        await asyncio.sleep(ALERT_SCAN_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if ENABLE_ALERT_SCANNER:
        task = asyncio.create_task(_alert_scanner_loop())
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Sistema de Pacientes Crónicos API",
    version="1.0.0",
    description="API para gestión de pacientes, historial clínico, pedidos de medicamentos y alertas de refill.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "Sistema de Pacientes Crónicos API",
        "status": "ok",
        "modules": [
            "auth",
            "pacientes",
            "medicamentos",
            "historial_clinico",
            "pedidos",
            "alertas",
            "usuarios",
        ],
    }


app.include_router(auth_router)
app.include_router(auth_legacy_router)
app.include_router(pacientes_router)
app.include_router(medicamentos_router)
app.include_router(historial_router)
app.include_router(pedidos_router)
app.include_router(alertas_router)
app.include_router(users_router)
