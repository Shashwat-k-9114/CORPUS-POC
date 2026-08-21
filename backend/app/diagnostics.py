"""Deployment-safe database and object-storage diagnostics."""

from __future__ import annotations

import json

from app.blobstore import create_blob_store
from app.config import Settings
from app.database import Database


def main() -> int:
    try:
        settings = Settings.from_env()
        database_ok = Database(settings.database_url).ping()
        storage = create_blob_store(settings)
        storage.check()
        result = {"database": "ok" if database_ok else "failed", "storage": "ok", "backend": settings.blob_store_backend}
        print(json.dumps(result))
        return 0 if database_ok else 1
    except Exception as exc:
        print(json.dumps({"database": "unknown", "storage": "unknown", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
