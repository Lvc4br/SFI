from __future__ import annotations

import base64
import binascii
import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models import Base, User

router = APIRouter(prefix="/backup", tags=["backup"])
BACKUP_FORMAT = "sfi-personal-data"
BACKUP_VERSION = 1
MAX_BACKUP_BYTES = 50 * 1024 * 1024
MAX_BACKUP_ROWS = 250_000
EXCLUDED_TABLES = {
    "login_attempts",
    "refresh_tokens",
    "revoked_access_tokens",
    "security_events",
}


class BackupRestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backup: dict[str, Any]
    confirmed: bool = False


def _owned_tables():
    return [
        table
        for table in Base.metadata.sorted_tables
        if "user_id" in table.c and table.name not in EXCLUDED_TABLES
    ]


def _encode(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return {"$type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"$type": "date", "value": value.isoformat()}
    if isinstance(value, bytes):
        return {"$type": "bytes", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (dict, list)):
        return value
    raise TypeError(f"Tipo não suportado no backup: {type(value).__name__}")


def _decode(value: Any, column) -> Any:
    if value is None:
        return None
    if isinstance(value, dict) and "$type" in value:
        kind = value["$type"]
        raw = value.get("value")
        if kind == "datetime":
            return datetime.fromisoformat(raw)
        if kind == "date":
            return date.fromisoformat(raw)
        if kind == "bytes":
            try:
                return base64.b64decode(raw, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError("Campo binário Base64 inválido.") from exc
        raise ValueError("Tipo especial desconhecido no backup.")
    python_type = column.type.python_type
    if python_type is uuid.UUID:
        return uuid.UUID(str(value))
    if python_type is Decimal:
        return Decimal(str(value))
    if python_type is datetime:
        return datetime.fromisoformat(str(value))
    if python_type is date:
        return date.fromisoformat(str(value))
    if python_type is bytes and isinstance(value, str):
        return base64.b64decode(value, validate=True)
    return value


def _build_backup(user: User, rows_by_table: dict[str, list[dict]]) -> dict:
    return {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "exported_at": datetime.now().astimezone().isoformat(),
        "profile": {"timezone": user.timezone},
        "tables": rows_by_table,
    }


async def _collect_backup(session: AsyncSession, user: User) -> dict:
    rows_by_table: dict[str, list[dict]] = {}
    total_rows = 0
    for table in _owned_tables():
        result = await session.execute(
            select(table).where(table.c.user_id == user.id)
        )
        rows = [
            {column.name: _encode(value) for column, value in zip(table.columns, row, strict=True)}
            for row in result.fetchall()
        ]
        rows_by_table[table.name] = rows
        total_rows += len(rows)
        if total_rows > MAX_BACKUP_ROWS:
            raise HTTPException(413, "O backup excede o limite de 250.000 registros.")
    return _build_backup(user, rows_by_table)


def _validate_backup(backup: dict) -> tuple[dict[str, list[dict]], int]:
    if backup.get("format") != BACKUP_FORMAT or backup.get("version") != BACKUP_VERSION:
        raise HTTPException(
            422,
            "Formato ou versão de backup não compatível com esta versão do SFI.",
        )
    tables = backup.get("tables")
    if not isinstance(tables, dict):
        raise HTTPException(422, "O backup não contém a seção de tabelas.")
    expected = {table.name: table for table in _owned_tables()}
    if set(tables) != set(expected):
        raise HTTPException(422, "O backup está incompleto ou contém tabelas desconhecidas.")
    total_rows = 0
    validated: dict[str, list[dict]] = {}
    for table_name, records in tables.items():
        table = expected[table_name]
        if not isinstance(records, list):
            raise HTTPException(422, f"A tabela {table_name} não contém uma lista de registros.")
        total_rows += len(records)
        if total_rows > MAX_BACKUP_ROWS:
            raise HTTPException(413, "O backup excede o limite de 250.000 registros.")
        validated_records = []
        column_names = {column.name for column in table.columns}
        for index, record in enumerate(records):
            if not isinstance(record, dict) or set(record) != column_names:
                raise HTTPException(
                    422,
                    f"Registro {index + 1} da tabela {table_name} possui colunas incompatíveis.",
                )
            try:
                decoded = {
                    column.name: _decode(record[column.name], column)
                    for column in table.columns
                }
            except (ValueError, TypeError, binascii.Error) as exc:
                raise HTTPException(
                    422, f"Registro {index + 1} da tabela {table_name} contém valor inválido."
                ) from exc
            validated_records.append(decoded)
        validated[table_name] = validated_records
    profile = backup.get("profile")
    if not isinstance(profile, dict) or not isinstance(profile.get("timezone"), str):
        raise HTTPException(422, "O perfil do backup está incompleto.")
    if len(profile["timezone"]) > 64:
        raise HTTPException(422, "O fuso horário do perfil é inválido.")
    try:
        ZoneInfo(profile["timezone"])
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(422, "O fuso horário do perfil não é reconhecido.") from exc
    return validated, total_rows


def _payload_size(backup: dict) -> int:
    try:
        return len(json.dumps(backup, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, "O backup não é um documento JSON válido.") from exc


@router.get("/export")
async def export_backup(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    backup = await _collect_backup(session, user)
    content = json.dumps(backup, ensure_ascii=False, separators=(",", ":"))
    if len(content.encode("utf-8")) > MAX_BACKUP_BYTES:
        raise HTTPException(413, "O backup excede o limite de 50 MB.")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="sfi-backup.json"'},
    )


@router.post("/preview")
async def preview_restore(
    payload: BackupRestoreRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if _payload_size(payload.backup) > MAX_BACKUP_BYTES:
        raise HTTPException(413, "O backup excede o limite de 50 MB.")
    tables, total_rows = _validate_backup(payload.backup)
    current_counts = {}
    for table in _owned_tables():
        current_counts[table.name] = await session.scalar(
            select(func.count()).select_from(table).where(
                table.c.user_id == user.id
            )
        )
    return {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
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
    }


@router.post("/restore")
async def restore_backup(
    payload: BackupRestoreRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if not payload.confirmed:
        raise HTTPException(409, "A restauração exige confirmação explícita.")
    if _payload_size(payload.backup) > MAX_BACKUP_BYTES:
        raise HTTPException(413, "O backup excede o limite de 50 MB.")
    tables, total_rows = _validate_backup(payload.backup)
    bind = session.get_bind()
    if bind.dialect.name != "sqlite":
        raise HTTPException(
            409,
            "A restauração integral está disponível somente no banco SQLite local. "
            "A sincronização remota não é alterada por este recurso.",
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
            .values(timezone=payload.backup["profile"]["timezone"])
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            422,
            "Restauração cancelada: os dados atuais foram preservados porque o backup "
            "não passou pelas restrições de integridade.",
        ) from exc
    return {
        "restored": True,
        "records_restored": total_rows,
        "tables_restored": len(tables),
        "mode": "replace",
    }
