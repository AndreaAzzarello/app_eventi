"""Client Firestore via service account. Le credenziali arrivano SOLO da variabili d'ambiente:
- FIREBASE_SERVICE_ACCOUNT: contenuto JSON della chiave (GitHub Actions), oppure
- GOOGLE_APPLICATION_CREDENTIALS: percorso di un file fuori da git."""

from __future__ import annotations

import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

PROJECT_ID = "appeventi-1e860"


def client():
    if not firebase_admin._apps:
        raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if raw:
            cred = credentials.Certificate(json.loads(raw))
        elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            cred = credentials.ApplicationDefault()
        else:
            raise SystemExit(
                "Credenziali mancanti: imposta FIREBASE_SERVICE_ACCOUNT o "
                "GOOGLE_APPLICATION_CREDENTIALS (vedi README, sezione Importer)."
            )
        firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
    return firestore.client()
