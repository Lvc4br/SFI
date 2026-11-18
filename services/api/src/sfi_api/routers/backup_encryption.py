from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.backup_crypto import BackupEncryptionError, decrypt_backup, encrypt_backup
from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models import User
from sfi_api.routers.backup import (
    MAX_BACKUP_BYTES,
    BackupRestoreRequest,
    _collect_backup,
    _owned_tables,
    _payload_size,
    _validate_backup,
)

router = APIRouter(prefix="/backup/encrypted", tags=["backup"])


class EncryptedBackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passphrase: str = Field(min_length=12, max_length=1024)
    envelope: dict[str, Any] | None = None
    confirmed: bool = False


def _open_envelope(payload: EncryptedBackupRequest) -> dict:
    if payload.envelope is None:
        raise HTTPException(422, "Arquivo de backup criptografado ausente.")
    try:
        backup = decrypt_backup(payload.envelope, payload.passphrase)
    except BackupEncryptionError as exc:
        raise HTTPException(422, str(exc)) from exc
    if _payload_size(backup) > MAX_BACKUP_BYTES:
        raise HTTPException(413, "O backup descriptografado excede o limite de 50 MiB.")
    return backup


@router.post("/export")
async def export_encrypted_backup(
    payload: EncryptedBackupRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    backup = await _collect_backup(session, user)
    try:
        envelope = encrypt_backup(backup, payload.passphrase)
    except BackupEncryptionError as exc:
        raise HTTPException(422, str(exc)) from exc
    return JSONResponse(
        content=envelope,
        headers={"Content-Disposition": 'attachment; filename="sfi-backup-encrypted.json"'},
    )


@router.post("/preview")
async def preview_encrypted_restore(
    payload: EncryptedBackupRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    backup = _open_envelope(payload)
    tables, total_rows = _validate_backup(backup)
    current_counts = {}
    for table in _owned_tables():
        current_counts[table.name] = await session.scalar(
            select(func.count()).select_from(table).where(table.c.user_id == user.id)
        )
    return {
        "format": backup["format"],
        "version": backup["version"],
        "records_in_backup": total_rows,
        "records_current": sum(current_counts.values()),
        "tables": [
            {
                "name": table.name,
                "backup_records": len(tables[table.name]),
                "current_records": current_counts[table.name],
            }
            for table in _owned_tables()
        ],
        "restore_mode": "replace",
        "requires_confirmation": True,
        "encrypted": True,
    }


@router.post("/restore")
async def restore_encrypted_backup(
    payload: EncryptedBackupRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if not payload.confirmed:
        raise HTTPException(409, "A restauração exige confirmação explícita.")
    backup = _open_envelope(payload)
    tables, total_rows = _validate_backup(backup)
    if session.get_bind().dialect.name != "sqlite":
        raise HTTPException(
            409,
            "A restauração integral está disponível somente no SQLite local.",
        )
    try:
        await session.execute(text("PRAGMA defer_foreign_keys=ON"))
        ordered_tables = _owned_tables()
        for table in reversed(ordered_tables):
            await session.execute(delete(table).where(table.c.user_id == user.id))
        for table in ordered_tables:
            records = tables[table.name]
            if not records:
                continue
            for record in records:
                record["user_id"] = user.id
            await session.execute(insert(table), records)
        await session.execute(
            update(User)
            .where(User.id == user.id)
            .values(timezone=backup["profile"]["timezone"])
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            422,
            "Restauração cancelada: os dados atuais foram preservados por falha de integridade.",
        ) from exc
    return {
        "restored": True,
        "records_restored": total_rows,
        "tables_restored": len(tables),
        "mode": "replace",
        "encrypted": True,
    }
