from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sfi_api.backup_automation import (
    BackupAutomationError,
    _is_due,
    automatic_backup_status,
    configure_automatic_backup,
)


def test_daily_backup_becomes_due_after_configured_time_and_interval():
    now = datetime(2026, 11, 18, 10, 30, tzinfo=timezone.utc)
    config = {"cadence": "daily", "local_time": "10:00", "last_run": "2026-11-17T10:00:00+00:00"}
    assert _is_due(config, now)
    assert not _is_due(config, now.replace(hour=9, minute=59))
    assert not _is_due(config, now.replace(hour=10, minute=0) - timedelta(days=0, minutes=1))


def test_weekly_backup_requires_seven_days_after_last_success():
    now = datetime(2026, 11, 18, 10, 30, tzinfo=timezone.utc)
    config = {"cadence": "weekly", "local_time": "10:00", "last_run": (now - timedelta(days=6)).isoformat()}
    assert not _is_due(config, now)
    config["last_run"] = (now - timedelta(days=7)).isoformat()
    assert _is_due(config, now)


def test_first_automatic_backup_is_due_after_configured_time():
    config = {"cadence": "daily", "local_time": "08:30", "last_run": None}
    assert _is_due(config, datetime(2026, 11, 18, 8, 30, tzinfo=timezone.utc))
    assert not _is_due(config, datetime(2026, 11, 18, 8, 29, tzinfo=timezone.utc))


def test_schedule_status_is_not_visible_to_a_different_user(tmp_path, monkeypatch):
    monkeypatch.setenv("SFI_DATA_DIR", str(tmp_path))
    assert automatic_backup_status(uuid4())["enabled"] is False


def test_automatic_schedule_requires_windows_dpapi(monkeypatch):
    monkeypatch.setattr("sfi_api.backup_automation.sys.platform", "linux")
    with pytest.raises(BackupAutomationError, match="Windows"):
        configure_automatic_backup(uuid4(), "daily", "08:00", "senha-forte-backup-2026")
