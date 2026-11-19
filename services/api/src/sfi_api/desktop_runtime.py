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


_DPAPI_MAGIC = b"SFI-DPAPI-V1\\x00"


def _dpapi_transform(value: bytes, *, decrypt: bool) -> bytes:
    """Protect/unprotect bytes with Windows DPAPI for the current Windows user."""
    if sys.platform != "win32":
        raise RuntimeError("DPAPI só está disponível no Windows.")

    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    if decrypt:
        function.argtypes = [
            ctypes.POINTER(DataBlob),
            ctypes.c_void_p,
            ctypes.POINTER(DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DataBlob),
        ]
    else:
        function.argtypes = [
            ctypes.POINTER(DataBlob),
            wintypes.LPCWSTR,
            ctypes.POINTER(DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DataBlob),
        ]
    function.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    input_buffer = ctypes.create_string_buffer(value)
    input_blob = DataBlob(
        len(value),
        ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    output_blob = DataBlob()
    if decrypt:
        success = function(
            ctypes.byref(input_blob),
            None,
            None,
            None,
            None,
            0x1,
            ctypes.byref(output_blob),
        )
    else:
        success = function(
            ctypes.byref(input_blob),
            "SFI local JWT signing key",
            None,
            None,
            None,
            0x1,
            ctypes.byref(output_blob),
        )
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _validate_secret(value: str) -> str:
    if len(value) < 48:
        raise RuntimeError("A chave local do SFI está inválida; os dados foram preservados.")
    return value


def _write_exclusive(path: Path, value: bytes) -> bool:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "wb") as secret_file:
        secret_file.write(value)
        secret_file.flush()
        os.fsync(secret_file.fileno())
    return True


def ensure_local_secret(data_dir: Path) -> str:
    """Create a per-install JWT key; protect it with DPAPI on Windows."""
    secret_dir = data_dir / "secrets"
    secret_dir.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        protected_path = secret_dir / "jwt.key.dpapi"
        legacy_path = secret_dir / "jwt.key"

        if protected_path.exists():
            encrypted = protected_path.read_bytes()
            if not encrypted.startswith(_DPAPI_MAGIC):
                raise RuntimeError(
                    "A chave DPAPI local do SFI está inválida; os dados foram preservados."
                )
            try:
                value = _dpapi_transform(encrypted[len(_DPAPI_MAGIC):], decrypt=True).decode(
                    "utf-8"
                )
            except (OSError, UnicodeDecodeError) as exc:
                raise RuntimeError(
                    "Não foi possível desbloquear a chave DPAPI deste usuário Windows."
                ) from exc
            return _validate_secret(value)

        if legacy_path.exists():
            value = _validate_secret(legacy_path.read_text(encoding="utf-8").strip())
            encrypted = _DPAPI_MAGIC + _dpapi_transform(value.encode("utf-8"), decrypt=False)
            if _write_exclusive(protected_path, encrypted):
                legacy_path.unlink()
                return value
            return ensure_local_secret(data_dir)

        value = secrets.token_urlsafe(48)
        encrypted = _DPAPI_MAGIC + _dpapi_transform(value.encode("utf-8"), decrypt=False)
        if _write_exclusive(protected_path, encrypted):
            return value
        return ensure_local_secret(data_dir)

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

    return _validate_secret(secret_path.read_text(encoding="utf-8").strip())

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

    from sfi_api.backup_automation import (
        start_automatic_backup_worker,
        stop_automatic_backup_worker,
    )

    start_automatic_backup_worker()
    print(f"SFI_API_READY {port}", flush=True)
    server_thread.join()
    stop_automatic_backup_worker()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"SFI_API_STARTUP_ERROR {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
