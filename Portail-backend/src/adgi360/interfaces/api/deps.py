"""Dépendances FastAPI partagées : utilisateur courant et périmètre d'organisation.

Tout endpoint métier passe par `CurrentUser`. C'est le point unique où l'on
vérifie le jeton et où l'on récupère l'organisation — impossible d'écrire par
inadvertance une route qui lirait les données d'une autre agence, puisque les
requêtes filtrent sur `user.organization_id`.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.accounts.entities import UserRole
from adgi360.infrastructure.db.models import OrganizationModel, UserModel
from adgi360.infrastructure.db.session import get_session
from adgi360.infrastructure.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Authentification requise ou session expirée",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: AsyncSession = Depends(get_session),
) -> UserModel:
    if credentials is None:
        raise CREDENTIALS_ERROR

    payload = decode_access_token(credentials.credentials)
    if payload is None or not payload.get("sub"):
        raise CREDENTIALS_ERROR

    user = await session.get(UserModel, payload["sub"])
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR

    # Le jeton porte l'organisation, mais la base fait foi : si un compte a été
    # déplacé ou désactivé, un ancien jeton ne doit pas rester valable.
    if user.organization_id != payload.get("org"):
        raise CREDENTIALS_ERROR

    return user


CurrentUser = Annotated[UserModel, Depends(get_current_user)]


async def get_current_organization(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> OrganizationModel:
    organization = await session.get(OrganizationModel, user.organization_id)
    if organization is None:
        raise CREDENTIALS_ERROR
    return organization


CurrentOrganization = Annotated[OrganizationModel, Depends(get_current_organization)]


def require_role(minimum: UserRole):
    """Garde de rôle pour les actions sensibles (branding, connecteurs, membres)."""

    async def guard(user: CurrentUser) -> UserModel:
        try:
            role = UserRole(user.role)
        except ValueError:
            raise CREDENTIALS_ERROR from None
        if not role.can(minimum):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Action réservée au rôle « {minimum.label} » ou supérieur",
            )
        return user

    return guard
