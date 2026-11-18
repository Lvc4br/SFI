"""Windows DPAPI-backed automatic encrypted backup scheduler for the desktop runtime."""

from __future__ import annotations

import asyncio
import base64
import ctypes
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from sfi_api.backup_crypto import encrypt_backup
from sfi_api.config import get_settings
from sfi_api.database import _session_factory
from sfi_api.models import User
from sfi_api.routers.backup import _collect_backup

_CONFIG_LOCK = threading.Lock()
_STOP_EVENT = threading.Event()
_RETENTION_COUNT = 10
_BACKUP_SUFFIX = ".sfi-backup.json"


class BackupAutomationError(RuntimeError):
    """Raised when automatic backup configuration is unavailable or invalid."""


def _data_dir() -> Path:
    value = os.environ.get("SFI_DATA_DIR")
    if not value:
        raise BackupAutomationError("Diretório local do SFI não configurado.")
    return Path(value).expanduser().resolve()


def _dpapi_transform(value: bytes, *, protect: bool) -> bytes:
    if sys.platform != "win32":
        raise BackupAutomationError("Proteção automática de senha exige Windows DPAPI.")
    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    source_buffer = ctypes.create_string_buffer(value)
    source = DataBlob(len(value), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    destination = DataBlob()
    crypt = ctypes.WinDLL("Crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("Kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    function.argtypes = [
        ctypes.POINTER(DataBlob),
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    function.restype = ctypes.wintypes.BOOL
    if not function(ctypes.byref(source), "SFI automatic backup", None, None, None, 0, ctypes.byref(destination)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        kernel.LocalFree(destination.pbData)


def protect_passphrase(passphrase: str) -> str:
    if len(passphrase) < 12 or len(passphrase.encode("utf-8")) > 1024:
        raise BackupAutomationError("A senha do backup deve ter de 12 a 1024 bytes.")
    return base64.b64encode(_dpapi_transform(passphrase.encode("utf-8"), protect=True)).decode("ascii")


def _unprotect_passphrase(value: str) -> str:
    try:
        protected = base64.b64decode(value, validate=True)
        return _dpapi_transform(protected, protect=False).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise BackupAutomationError("A credencial protegida do backup está inválida.") from exc


def _config_path() -> Path:
    return _data_dir() / "secrets" / "backup-automation.json"


def _read_config() -> dict[str, Any] | None:
    path = _config_path()
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupAutomationError("Configuração de backup automático inválida.") from exc
    if not isinstance(value, dict):
        raise BackupAutomationError("Configuração de backup automático inválida.")
    return value


def _write_config(value: dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def configure_automatic_backup(
    user_id: UUID, cadence: str, local_time: str, passphrase: str
) -> dict[str, Any]:
    if sys.platform != "win32":
        raise BackupAutomationError("Agendamento com proteção DPAPI está disponível no Desktop Windows.")
    if cadence not in {"daily", "weekly"}:
        raise BackupAutomationError("A frequência deve ser daily ou weekly.")
    try:
        datetime.strptime(local_time, "%H:%M")
    except ValueError as exc:
        raise BackupAutomationError("Horário inválido; use HH:MM.") from exc
    protected = protect_passphrase(passphrase)
    with _CONFIG_LOCK:
        existing = _read_config()
        if existing and existing.get("user_id") != str(user_id):
            raise BackupAutomationError("Outro usuário já possui um agendamento de backup nesta instalação.")
        _write_config({
            "version": 1,
            "enabled": True,
            "user_id": str(user_id),
            "cadence": cadence,
            "local_time": local_time,
            "protected_passphrase": protected,
            "last_run": None,
        })
    return {"enabled": True, "cadence": cadence, "local_time": local_time, "retention": _RETENTION_COUNT}


def disable_automatic_backup(user_id: UUID) -> None:
    with _CONFIG_LOCK:
        config = _read_config()
        if config and config.get("user_id") != str(user_id):
            raise BackupAutomationError("Configuração de backup pertence a outro usuário.")
        path = _config_path()
        if path.exists():
            path.unlink()


def automatic_backup_status(user_id: UUID) -> dict[str, Any]:
    with _CONFIG_LOCK:
        config = _read_config()
    if not config or not config.get("enabled") or config.get("user_id") != str(user_id):
        return {"enabled": False, "retention": _RETENTION_COUNT, "history": []}
    return {
        "enabled": True,
        "cadence": config.get("cadence"),
        "local_time": config.get("local_time"),
        "last_run": config.get("last_run"),
        "retention": _RETENTION_COUNT,
        "history": _backup_history(),
    }


def _backup_history() -> list[dict[str, Any]]:
    directory = _data_dir() / "backups"
    if not directory.exists():
        return []
    files = sorted(directory.glob("*" + _BACKUP_SUFFIX), key=lambda item: item.stat().st_mtime, reverse=True)
    history = []
    for path in files[:_RETENTION_COUNT]:
        stat = path.stat()
        history.append({
            "filename": path.name,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
        })
    return history


def _is_due(config: dict[str, Any], now: datetime) -> bool:
    try:
        target = datetime.strptime(config["local_time"], "%H:%M").time()
        last_run = datetime.fromisoformat(config["last_run"]) if config.get("last_run") else None
        cadence = config["cadence"]
    except (KeyError, TypeError, ValueError):
        return False
    if now.time().replace(tzinfo=None) < target:
        return False
    if last_run is None:
        return True
    elapsed = now - last_run.astimezone(now.tzinfo)
    if cadence == "daily":
        return elapsed >= timedelta(days=1)
    return cadence == "weekly" and elapsed >= timedelta(days=7)


async def _create_scheduled_backup(config: dict[str, Any]) -> None:
    if _session_factory is None:
        raise BackupAutomationError("Banco local ainda não está disponível.")
    user_id = UUID(config["user_id"])
    passphrase = _unprotect_passphrase(config["protected_passphrase"])
    async with _session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise BackupAutomationError("Usuário da configuração de backup não existe.")
        backup = await _collect_backup(session, user)
    envelope = encrypt_backup(backup, passphrase)
    directory = _data_dir() / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    destination = directory / f"sfi-{timestamp}{_BACKUP_SUFFIX}"
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(envelope, stream, ensure_ascii=False, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, destination)
    backups = sorted(directory.glob("*" + _BACKUP_SUFFIX), key=lambda item: item.stat().st_mtime, reverse=True)
    for old_backup in backups[_RETENTION_COUNT:]:
        old_backup.unlink(missing_ok=True)


def _record_run(config: dict[str, Any], timestamp: str) -> None:
    config["last_run"] = timestamp
    with _CONFIG_LOCK:
        _write_config(config)


async def automatic_backup_worker() -> None:
    """Runs only in the packaged Windows desktop process."""
    if sys.platform != "win32":
        return
    while not _STOP_EVENT.is_set():
        try:
            with _CONFIG_LOCK:
                config = _read_config()
            now = datetime.now().astimezone()
            if config and config.get("enabled") and _is_due(config, now):
                await _create_scheduled_backup(config)
                _record_run(config, now.isoformat())
        except Exception:
            # Keep the desktop process alive; status exposes the last successful run.
            pass
        await asyncio.sleep(60)


def start_automatic_backup_worker() -> threading.Thread | None:
    if sys.platform != "win32":
        return None
    _STOP_EVENT.clear()
    worker = threading.Thread(
        target=lambda: asyncio.run(automatic_backup_worker()),
        name="sfi-automatic-backup",
        daemon=True,
    )
    worker.start()
    return worker


def stop_automatic_backup_worker() -> None:
    _STOP_EVENT.set()
