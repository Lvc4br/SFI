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
