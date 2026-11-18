from __future__ import annotations

import sys

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.backup_automation import (
    BackupAutomationError,
    automatic_backup_status,
    configure_automatic_backup,
    disable_automatic_backup,
)
from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models import User

router = APIRouter(prefix="/backup/automatic", tags=["backup"])


class AutomaticBackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cadence: str = Field(pattern="^(daily|weekly)$")
    local_time: str = Field(pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    passphrase: str = Field(min_length=12, max_length=1024)


@router.get("")
async def get_automatic_backup(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if sys.platform != "win32" or session.get_bind().dialect.name != "sqlite":
        raise HTTPException(409, "Backup automático está disponível somente no Desktop Windows.")
    try:
        return automatic_backup_status(user.id)
    except BackupAutomationError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.put("")
async def put_automatic_backup(
    payload: AutomaticBackupRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if session.get_bind().dialect.name != "sqlite":
        raise HTTPException(409, "Backup automático está disponível somente no Desktop local.")
    try:
        return configure_automatic_backup(
            user.id, payload.cadence, payload.local_time, payload.passphrase
        )
    except BackupAutomationError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.delete("")
async def delete_automatic_backup(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if session.get_bind().dialect.name != "sqlite":
        raise HTTPException(409, "Backup automático está disponível somente no Desktop local.")
    try:
        disable_automatic_backup(user.id)
    except BackupAutomationError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"enabled": False}
