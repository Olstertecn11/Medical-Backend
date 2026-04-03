import os
from typing import Optional

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
    return db.reference(path)


def key(value: str) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(".", "_")
        .replace("#", "_")
        .replace("$", "_")
        .replace("[", "_")
        .replace("]", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )


def push(path: str) -> str:
    new_ref = ref(path).push()
    return new_ref.key


def get_one(path: str) -> Optional[dict]:
    data = ref(path).get()
    return data if isinstance(data, dict) else None
