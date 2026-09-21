"""Hachage des mots de passe et jetons de session.

bcrypt est utilisé directement plutôt que via passlib : une dépendance en moins,
et passlib traîne des incompatibilités connues avec les versions récentes de
bcrypt.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from adgi360.infrastructure.config.settings import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """bcrypt ignore silencieusement les octets au-delà de 72 : on tronque
    explicitement pour que le comportement soit visible et reproductible."""
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Hachage corrompu ou format inattendu : on refuse plutôt que de lever.
        return False


def create_access_token(user_id: str, organization_id: str, role: str) -> str:
    """Le jeton porte l'organisation : chaque requête sait à quel périmètre elle
    appartient sans relire la base."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Renvoie None sur jeton invalide ou expiré — l'appelant décide du code HTTP."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def create_callback_token(review_id: str) -> str:
    """Jeton de rappel pour n8n.

    n8n n'a pas de compte utilisateur : il ne peut donc pas présenter de session.
    Plutôt que d'ouvrir l'endpoint de rendu à tout le monde, on lui transmet un
    jeton HMAC lié à la review, valable pour elle seule. Il ne donne aucun autre
    droit et ne permet pas de lire des données.
    """
    import hashlib
    import hmac

    return hmac.new(
        settings.secret_key.encode("utf-8"),
        f"render:{review_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_callback_token(review_id: str, token: str) -> bool:
    import hmac

    return hmac.compare_digest(create_callback_token(review_id), token or "")
