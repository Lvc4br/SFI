import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sfi_api.config import Settings

API_ROOT = Path(__file__).resolve().parents[1]


def test_data_directory_derives_a_private_sqlite_database(tmp_path: Path) -> None:
    from sqlalchemy.engine import make_url

    settings = Settings(data_dir=tmp_path, _env_file=None)

    assert settings.database_url is not None
    url = make_url(settings.database_url)
    assert url.drivername == "sqlite+aiosqlite"
    assert Path(url.database or "").resolve() == (
        tmp_path / "database" / "sfi.sqlite3"
    ).resolve()
    assert (tmp_path / "database").is_dir()


def test_alembic_bootstraps_empty_sqlite_from_current_domain_metadata(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "database" / "sfi.sqlite3"
    database_path.parent.mkdir(parents=True)
    env = os.environ.copy()
    env["SFI_DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    env.pop("SFI_DATA_DIR", None)
    env["PYTHONPATH"] = str(API_ROOT / "src")

    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from alembic import command; "
                "from alembic.config import Config; "
                "command.upgrade(Config('alembic.ini'), 'head')"
            ),
        ],
        cwd=API_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()

    assert {
        "users",
        "accounts",
        "categories",
        "transactions",
        "transfers",
        "budgets",
        "recurrences",
        "security_events",
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
    }.issubset(tables)
    assert revision == ("0021_investments",)
