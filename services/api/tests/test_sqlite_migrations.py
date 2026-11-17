import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from sfi_api.models import Base


@pytest.mark.parametrize("shopping_tables_already_exist", [False, True])
def test_sqlite_upgrade_from_previous_desktop_baseline(
    tmp_path: Path,
    shopping_tables_already_exist: bool,
):
    api_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "existing-sfi.sqlite3"
    engine = create_engine(f"sqlite:///{database_path}")
    excluded = {
        "shopping_products",
        "product_price_observations",
        "stock_movements",
        "credit_cards",
        "credit_invoices",
        "credit_purchase_installments",
        "credit_invoice_payments",
        "debts",
        "debt_payments",
        "financial_goals",
        "goal_entries",
        "investment_assets",
        "investment_operations",
    }
    if not shopping_tables_already_exist:
        excluded.update({"shopping_lists", "shopping_list_items"})
    with engine.begin() as connection:
        Base.metadata.create_all(
            connection,
            tables=[
                table
                for table in Base.metadata.sorted_tables
                if table.name not in excluded
            ],
        )
        connection.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('0013_security_events')"
            )
        )
    engine.dispose()

    environment = os.environ.copy()
    environment["SFI_DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path}"
    environment["PYTHONPATH"] = str(api_root / "src")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(api_root / "alembic.ini"),
            "upgrade",
            "head",
        ],
        cwd=api_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

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
        list_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(shopping_lists)")
        }
        item_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(shopping_list_items)")
        }
        item_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(shopping_list_items)"
        ).fetchall()

    assert revision == "0021_investments"
    assert {
        "shopping_lists",
        "shopping_list_items",
        "shopping_products",
        "product_price_observations",
        "credit_cards",
        "credit_invoices",
        "credit_purchase_installments",
        "credit_invoice_payments",
        "debts",
        "debt_payments",
        "financial_goals",
        "goal_entries",
        "investment_assets",
        "investment_operations",
    } <= tables
    assert "is_template" in list_columns
    assert "product_id" in item_columns
    assert any(row[2] == "shopping_products" for row in item_foreign_keys)
