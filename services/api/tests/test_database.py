from sfi_api.database import _async_database_url, _is_neon_pooler_url


def test_postgres_url_uses_asyncpg_driver():
    url = _async_database_url("postgres://user:pass@localhost:5432/db")
    assert url.drivername == "postgresql+asyncpg"


def test_sslmode_is_translated_to_ssl():
    url = _async_database_url("postgresql://user:pass@localhost/db?sslmode=require")
    assert url.query.get("ssl") == "require"
    assert "sslmode" not in url.query


def test_channel_binding_is_removed():
    url = _async_database_url("postgresql://user:pass@localhost/db?channel_binding=require")
    assert "channel_binding" not in url.query


def test_neon_pooler_detection_is_host_based():
    pooler_url = "postgresql://user:pass@ep-example-pooler.region.aws.neon.tech/db"
    assert _is_neon_pooler_url(pooler_url)
    assert not _is_neon_pooler_url("postgresql://user:pass@ep-example.region.aws.neon.tech/db")


def test_non_postgres_url_is_preserved():
    url = _async_database_url("sqlite:///test.db")
    assert url.drivername == "sqlite"
