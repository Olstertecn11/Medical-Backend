# backend/fb.py
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db

load_dotenv()

FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
CRED_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "firebase.json")

if not FIREBASE_DB_URL:
    raise RuntimeError("Falta FIREBASE_DB_URL en .env")

if not os.path.isabs(CRED_PATH):
    CRED_PATH = os.path.join(os.path.dirname(__file__), CRED_PATH)

if not firebase_admin._apps:
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

def ref(path: str):
    """Atajo para obtener una referencia a RTDB."""
    return db.reference(path)

def key(s: str) -> str:
    """Llave segura para RTDB (evita . # $ [ ])"""
    return s.lower().replace(".", "_").replace("#", "_").replace("$", "_").replace("[", "_").replace("]", "_").replace(" ", "_")
