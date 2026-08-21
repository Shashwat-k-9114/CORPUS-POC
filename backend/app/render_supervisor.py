"""Run the API and durable worker as supervised OS processes on Render Free."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time


def main() -> int:
    migration = subprocess.run([sys.executable, "-m", "app.db.migrate"], check=False)
    if migration.returncode != 0:
        emit("migration_failed", code=migration.returncode)
        return migration.returncode

    port = os.environ.get("PORT", "8000")
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", port])
    worker = subprocess.Popen([sys.executable, "-m", "app.worker"])
    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        emit("shutdown_requested")
        for process in (worker, api):
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    emit("started", api_pid=api.pid, worker_pid=worker.pid, port=port)
    try:
        while True:
            api_code = api.poll()
            worker_code = worker.poll()
            if stopping:
                if api_code is not None and worker_code is not None:
                    return 0
            elif api_code is not None:
                emit("api_exited", code=api_code)
                worker.terminate()
                return api_code or 1
            elif worker_code is not None:
                emit("worker_exited", code=worker_code)
                api.terminate()
                return worker_code or 1
            time.sleep(1)
    finally:
        for process in (worker, api):
            if process.poll() is None:
                process.kill()


def emit(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
