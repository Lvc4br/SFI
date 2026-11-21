import sys
from pathlib import Path

import pytest

from sfi_api.desktop_runtime import (
    _DPAPI_LEGACY_MAGICS,
    _decode_dpapi_envelope,
    _encode_dpapi_envelope,
    ensure_local_secret,
)


def test_dpapi_envelope_rejects_trailing_and_truncated_data():
    protected = b"opaque-dpapi-payload"
    envelope = _encode_dpapi_envelope(protected)

    assert _decode_dpapi_envelope(envelope) == protected
    for tampered in (envelope + b"tamper", envelope[:-1]):
        with pytest.raises(RuntimeError, match="inválida"):
            _decode_dpapi_envelope(tampered)


def test_legacy_dpapi_envelope_remains_readable():
    protected = b"legacy-dpapi-payload"
    envelope = _DPAPI_LEGACY_MAGICS[0] + protected

    assert _decode_dpapi_envelope(envelope) == protected


def test_local_secret_is_persistent_and_not_replaced(tmp_path: Path):
    first = ensure_local_secret(tmp_path)
    second = ensure_local_secret(tmp_path)

    assert len(first) >= 48
    assert second == first
    if sys.platform == "win32":
        assert (tmp_path / "secrets" / "jwt.key.dpapi").is_file()
        assert not (tmp_path / "secrets" / "jwt.key").exists()
    else:
        assert (tmp_path / "secrets" / "jwt.key").is_file()


def test_invalid_existing_secret_fails_without_overwriting(tmp_path: Path):
    secret_path = tmp_path / "secrets" / "jwt.key"
    secret_path.parent.mkdir(parents=True)
    secret_path.write_text("invalid", encoding="utf-8")

    with pytest.raises(RuntimeError, match="chave local"):
        ensure_local_secret(tmp_path)

    assert secret_path.read_text(encoding="utf-8") == "invalid"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI integration test")
def test_legacy_plaintext_secret_is_migrated_to_dpapi(tmp_path: Path):
    secret_path = tmp_path / "secrets" / "jwt.key"
    secret_path.parent.mkdir(parents=True)
    secret_path.write_text("x" * 64, encoding="utf-8")

    assert ensure_local_secret(tmp_path) == "x" * 64
    assert not secret_path.exists()
    protected_path = tmp_path / "secrets" / "jwt.key.dpapi"
    assert protected_path.is_file()

    # Simulate interruption after DPAPI file creation but before legacy cleanup.
    secret_path.write_text("x" * 64, encoding="utf-8")
    assert ensure_local_secret(tmp_path) == "x" * 64
    assert not secret_path.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI integration test")
def test_tampered_dpapi_secret_fails_without_replacing_file(tmp_path: Path):
    secret = ensure_local_secret(tmp_path)
    protected_path = tmp_path / "secrets" / "jwt.key.dpapi"
    original = protected_path.read_bytes()
    protected_path.write_bytes(original + b"tamper")

    with pytest.raises(RuntimeError, match="inválida|desbloquear"):
        ensure_local_secret(tmp_path)

    assert protected_path.read_bytes() == original + b"tamper"
    assert secret


def test_desktop_runtime_starts_local_api_and_shuts_down_cleanly(tmp_path: Path):
    import os
    import queue
    import sqlite3
    import subprocess
    import threading
    from urllib.request import urlopen

    api_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.pop("SFI_DATABASE_URL", None)
    environment.pop("SFI_JWT_SECRET_KEY", None)
    environment["SFI_DATA_DIR"] = str(tmp_path / "private-data")
    environment["PYTHONPATH"] = str(api_root / "src")

    process = subprocess.Popen(
        [sys.executable, "-m", "sfi_api.desktop_runtime"],
        cwd=api_root,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    ready_line: queue.Queue[str] = queue.Queue()
    reader = threading.Thread(
        target=lambda: ready_line.put(process.stdout.readline()),
        daemon=True,
    )
    reader.start()

    try:
        line = ready_line.get(timeout=30)
        assert line.startswith("SFI_API_READY ")
        port = int(line.split()[1])
        with urlopen(f"http://127.0.0.1:{port}/api/v1/health/ready", timeout=5) as response:
            assert response.status == 200
            assert '"ready":true' in response.read().decode("utf-8")

        process.stdin.write("shutdown\n")
        process.stdin.flush()
        assert process.wait(timeout=10) == 0

        database_path = tmp_path / "private-data" / "database" / "sfi.sqlite3"
        with sqlite3.connect(database_path) as connection:
            revision = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert revision == "0024_bank_reconciliation"
        assert {
            "shopping_lists",
            "shopping_list_items",
            "shopping_products",
            "product_price_observations",
            "stock_movements",
            "credit_cards",
            "credit_invoices",
            "credit_purchase_installments",
            "credit_invoice_payments",
            "financial_goals",
            "goal_entries",
            "investment_assets",
            "investment_operations",
        "patrimony_items",
        "patrimony_valuations",
        "fiscal_documents",
        "bank_statement_entries",
        } <= tables
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_pre_migration_snapshot_copies_and_checks_sqlite_database(tmp_path: Path):
    import sqlite3

    from sfi_api.desktop_runtime import _create_pre_migration_snapshot

    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES ('preserve-me')")
        connection.commit()

    snapshot = _create_pre_migration_snapshot(source, tmp_path / "snapshots")
    assert snapshot is not None and snapshot.is_file()
    with sqlite3.connect(snapshot) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "preserve-me"


def test_pre_migration_snapshot_skips_missing_database(tmp_path: Path):
    from sfi_api.desktop_runtime import _create_pre_migration_snapshot

    assert _create_pre_migration_snapshot(tmp_path / "missing.sqlite3", tmp_path / "snapshots") is None
    assert not (tmp_path / "snapshots").exists()
