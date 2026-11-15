from pathlib import Path

import pytest

from sfi_api.desktop_runtime import ensure_local_secret


def test_local_secret_is_persistent_and_not_replaced(tmp_path: Path):
    first = ensure_local_secret(tmp_path)
    second = ensure_local_secret(tmp_path)

    assert len(first) >= 48
    assert second == first
    assert (tmp_path / "secrets" / "jwt.key").is_file()


def test_invalid_existing_secret_fails_without_overwriting(tmp_path: Path):
    secret_path = tmp_path / "secrets" / "jwt.key"
    secret_path.parent.mkdir(parents=True)
    secret_path.write_text("invalid", encoding="utf-8")

    with pytest.raises(RuntimeError, match="chave local"):
        ensure_local_secret(tmp_path)

    assert secret_path.read_text(encoding="utf-8") == "invalid"


def test_desktop_runtime_starts_local_api_and_shuts_down_cleanly(tmp_path: Path):
    import os
    import queue
    import sqlite3
    import subprocess
    import sys
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
        assert revision == "0016_shopping_catalog_templates"
        assert {
            "shopping_lists",
            "shopping_list_items",
            "shopping_products",
            "product_price_observations",
            "shopping_products",
        } <= tables
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
