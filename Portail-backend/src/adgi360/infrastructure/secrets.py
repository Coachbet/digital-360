"""Chiffrement des identifiants de services externes stockés en base."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from adgi360.infrastructure.config.settings import settings
from adgi360.shared.exceptions import ValidationError


def _fernet() -> Fernet:
    """Dérive une clé de chiffrement stable depuis SECRET_KEY.

    SECRET_KEY doit donc être sauvegardée et ne jamais changer sans migration des
    secrets existants. Fernet apporte chiffrement authentifié et détection des
    données altérées, contrairement à un simple encodage ou à une signature.
    """

    passphrase = settings.credentials_encryption_key or settings.secret_key
    key = hashlib.sha256(passphrase.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, ValueError) as exc:
        raise ValidationError(
            "Les identifiants Meta enregistrés ne peuvent plus être déchiffrés"
        ) from exc
