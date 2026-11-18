import copy

import pytest

from sfi_api.backup_crypto import (
    BackupEncryptionError,
    decrypt_backup,
    encrypt_backup,
)


def sample_backup():
    return {
        "format": "sfi-personal-data",
        "version": 1,
        "tables": {"accounts": [{"id": "abc", "balance": "123.45"}]},
    }


def test_encrypted_backup_round_trip():
    original = sample_backup()
    envelope = encrypt_backup(original, "senha-forte-e-longa-2026")
    assert envelope["format"] == "sfi-encrypted-backup"
    assert "tables" not in envelope
    assert decrypt_backup(envelope, "senha-forte-e-longa-2026") == original


def test_encrypted_backup_rejects_wrong_passphrase():
    envelope = encrypt_backup(sample_backup(), "senha-forte-e-longa-2026")
    with pytest.raises(BackupEncryptionError, match="senha ou a integridade"):
        decrypt_backup(envelope, "senha-totalmente-incorreta")


def test_encrypted_backup_rejects_tampering():
    envelope = encrypt_backup(sample_backup(), "senha-forte-e-longa-2026")
    changed = copy.deepcopy(envelope)
    changed["ciphertext"] = changed["ciphertext"][:-4] + "AAAA"
    with pytest.raises(BackupEncryptionError):
        decrypt_backup(changed, "senha-forte-e-longa-2026")


def test_encrypted_backup_rejects_unsupported_parameters():
    envelope = encrypt_backup(sample_backup(), "senha-forte-e-longa-2026")
    envelope["scrypt"]["n"] = 2**14
    with pytest.raises(BackupEncryptionError, match="parâmetros criptográficos"):
        decrypt_backup(envelope, "senha-forte-e-longa-2026")


def test_encrypted_backup_requires_strong_passphrase():
    with pytest.raises(BackupEncryptionError, match="pelo menos 12"):
        encrypt_backup(sample_backup(), "curta")
