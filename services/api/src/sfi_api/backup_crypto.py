from __future__ import annotations

import base64
import binascii
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

ENCRYPTED_BACKUP_FORMAT = "sfi-encrypted-backup"
ENCRYPTED_BACKUP_VERSION = 1
KDF_NAME = "scrypt"
CIPHER_NAME = "aes-256-gcm"
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32
MAX_PLAINTEXT_BYTES = 50 * 1024 * 1024
MIN_PASSPHRASE_LENGTH = 12


class BackupEncryptionError(ValueError):
    """Raised when an encrypted backup cannot safely be created or opened."""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if not isinstance(passphrase, str) or len(passphrase) < MIN_PASSPHRASE_LENGTH:
        raise BackupEncryptionError(
            f"A senha do backup deve possuir pelo menos {MIN_PASSPHRASE_LENGTH} caracteres."
        )
    if len(passphrase.encode("utf-8")) > 1024:
        raise BackupEncryptionError("A senha do backup excede o limite permitido.")
    return Scrypt(
        salt=salt,
        length=KEY_BYTES,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    ).derive(passphrase.encode("utf-8"))


def _aad() -> bytes:
    return json.dumps(
        {
            "format": ENCRYPTED_BACKUP_FORMAT,
            "version": ENCRYPTED_BACKUP_VERSION,
            "kdf": KDF_NAME,
            "cipher": CIPHER_NAME,
            "scrypt": {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def encrypt_backup(backup: dict[str, Any], passphrase: str) -> dict[str, Any]:
    try:
        plaintext = json.dumps(
            backup, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BackupEncryptionError("O backup não é um documento JSON válido.") from exc
    if len(plaintext) > MAX_PLAINTEXT_BYTES:
        raise BackupEncryptionError("O backup excede o limite de 50 MiB.")
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    key = _derive_key(passphrase, salt)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, _aad())
    return {
        "format": ENCRYPTED_BACKUP_FORMAT,
        "version": ENCRYPTED_BACKUP_VERSION,
        "kdf": KDF_NAME,
        "cipher": CIPHER_NAME,
        "scrypt": {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_backup(envelope: dict[str, Any], passphrase: str) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise BackupEncryptionError("Envelope de backup criptografado inválido.")
    expected = {
        "format": ENCRYPTED_BACKUP_FORMAT,
        "version": ENCRYPTED_BACKUP_VERSION,
        "kdf": KDF_NAME,
        "cipher": CIPHER_NAME,
        "scrypt": {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
    }
    if any(envelope.get(key) != value for key, value in expected.items()):
        raise BackupEncryptionError("Formato ou parâmetros criptográficos não suportados.")
    try:
        salt = base64.b64decode(envelope["salt"], validate=True)
        nonce = base64.b64decode(envelope["nonce"], validate=True)
        ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
    except (KeyError, TypeError, binascii.Error, ValueError) as exc:
        raise BackupEncryptionError("Dados Base64 do backup criptografado são inválidos.") from exc
    if len(salt) != SALT_BYTES or len(nonce) != NONCE_BYTES:
        raise BackupEncryptionError(
            "Salt ou nonce do backup criptografado possui tamanho inválido."
        )
    if len(ciphertext) < 16 or len(ciphertext) > MAX_PLAINTEXT_BYTES + 16:
        raise BackupEncryptionError("Tamanho do backup criptografado inválido.")
    key = _derive_key(passphrase, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, _aad())
    except InvalidTag as exc:
        raise BackupEncryptionError(
            "Não foi possível abrir o backup. Verifique a senha ou a integridade do arquivo."
        ) from exc
    try:
        result = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupEncryptionError("O conteúdo descriptografado não é um JSON válido.") from exc
    if not isinstance(result, dict):
        raise BackupEncryptionError("O conteúdo descriptografado não é um backup SFI válido.")
    return result
