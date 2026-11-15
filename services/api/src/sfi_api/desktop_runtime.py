"""Private local runtime used by the Windows desktop sidecar."""

from __future__ import annotations

import os
import secrets
import socket
import sys
import threading
import time
from pathlib import Path

from sqlalchemy.engine import URL


def ensure_local_secret(data_dir: Path) -> str:
    """Create a persistent per-install JWT key without overwriting an existing key."""
    secret_dir = data_dir / "secrets"
    secret_dir.mkdir(parents=True, exist_ok=True)
    secret_path = secret_dir / "jwt.key"

    try:
        descriptor = os.open(
            secret_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        pass
    else:
        value = secrets.token_urlsafe(48)
        with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
            secret_file.write(value)
            secret_file.flush()
            os.fsync(secret_file.fileno())

    value = secret_path.read_text(encoding="utf-8").strip()
    if len(value) < 48:
        raise RuntimeError("A chave local do SFI está inválida; os dados foram preservados.")
    return value


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def run() -> None:
    data_dir_value = os.environ.get("SFI_DATA_DIR")
    if not data_dir_value:
        raise RuntimeError("SFI_DATA_DIR é obrigatório no runtime Desktop.")

    data_dir = Path(data_dir_value).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["SFI_DATA_DIR"] = str(data_dir)
    os.environ["SFI_ENVIRONMENT"] = "desktop"
    os.environ["SFI_JWT_SECRET_KEY"] = ensure_local_secret(data_dir)
    local_database = data_dir / "database" / "sfi.sqlite3"
    local_database.parent.mkdir(parents=True, exist_ok=True)
    os.environ["SFI_DATABASE_URL"] = URL.create(
        "sqlite+aiosqlite",
        database=str(local_database),
    ).render_as_string(hide_password=False)
    os.environ["SFI_CORS_ORIGINS"] = "tauri://localhost,http://tauri.localhost"

    root = runtime_root()
    from alembic import command
    from alembic.config import Config

    migration_config = Config(str(root / "alembic.ini"))
    migration_config.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(migration_config, "head")

    import uvicorn

    from sfi_api.main import app

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)

    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="critical",
            access_log=False,
            workers=1,
            timeout_graceful_shutdown=4,
        )
    )
    server_thread = threading.Thread(
        target=server.run,
        kwargs={"sockets": [listener]},
        name="sfi-local-api",
        daemon=True,
    )
    server_thread.start()
    def watch_shutdown() -> None:
        sys.stdin.readline()
        server.should_exit = True

    shutdown_thread = threading.Thread(
        target=watch_shutdown,
        name="sfi-shutdown-listener",
        daemon=True,
    )
    shutdown_thread.start()
    deadline = time.monotonic() + 15
    while not server.started and server_thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.025)
    if not server.started:
        raise RuntimeError("A API local não ficou pronta dentro do prazo de inicialização.")

    print(f"SFI_API_READY {port}", flush=True)
    server_thread.join()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"SFI_API_STARTUP_ERROR {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
