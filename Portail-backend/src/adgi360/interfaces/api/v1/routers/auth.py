from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.accounts.entities import (
    UserRole,
    normalize_email,
    normalize_phone,
    slugify,
)
from adgi360.infrastructure.db.models import OrganizationModel, UserModel
from adgi360.infrastructure.db.session import get_session
from adgi360.infrastructure.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from adgi360.interfaces.api.deps import CurrentUser
from adgi360.interfaces.api.v1.schemas.auth_schemas import (
    LoginRequest,
    MeOut,
    OrganizationOut,
    PhoneUpdate,
    SignupRequest,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _unique_slug(session: AsyncSession, name: str) -> str:
    """Deux agences peuvent porter le même nom : on suffixe jusqu'à trouver
    un identifiant libre plutôt que de refuser l'inscription."""
    base = slugify(name)
    candidate, suffix = base, 2
    while True:
        exists = await session.execute(
            select(OrganizationModel.id).where(OrganizationModel.slug == candidate)
        )
        if exists.scalar_one_or_none() is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    """Crée une agence et son premier compte, qui en devient propriétaire.

    C'est le seul moyen de créer une organisation : les collaborateurs suivants
    sont invités depuis l'intérieur, ce qui évite qu'un membre crée par erreur
    une agence parallèle avec des données isolées de celles de son équipe.
    """
    email = normalize_email(payload.email)

    existing = await session.execute(select(UserModel.id).where(UserModel.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà pour cet email")

    organization = OrganizationModel(
        name=payload.organization_name,
        slug=await _unique_slug(session, payload.organization_name),
        legal_name=payload.organization_name,
    )
    session.add(organization)
    await session.flush()

    user = UserModel(
        organization_id=organization.id,
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER.value,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await session.refresh(organization)

    return TokenOut(
        access_token=create_access_token(user.id, user.organization_id, user.role),
        user=UserOut.model_validate(user, from_attributes=True),
        organization=OrganizationOut.model_validate(organization, from_attributes=True),
    )


@router.post("/login", response_model=TokenOut)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    email = normalize_email(payload.email)
    result = await session.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()

    # Message identique dans les deux cas : ne pas révéler quels emails existent.
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce compte a été désactivé")

    organization = await session.get(OrganizationModel, user.organization_id)
    return TokenOut(
        access_token=create_access_token(user.id, user.organization_id, user.role),
        user=UserOut.model_validate(user, from_attributes=True),
        organization=OrganizationOut.model_validate(organization, from_attributes=True),
    )


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser, session: AsyncSession = Depends(get_session)) -> MeOut:
    """Appelé au chargement du portail pour restaurer la session."""
    organization = await session.get(OrganizationModel, user.organization_id)
    return MeOut(
        user=UserOut.model_validate(user, from_attributes=True),
        organization=OrganizationOut.model_validate(organization, from_attributes=True),
    )


@router.get("/members", response_model=list[UserOut])
async def list_members(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[UserModel]:
    result = await session.execute(
        select(UserModel)
        .where(UserModel.organization_id == user.organization_id)
        .order_by(func.lower(UserModel.full_name))
    )
    return list(result.scalars().all())


@router.put("/me/phone", response_model=UserOut)
async def update_my_phone(
    payload: PhoneUpdate, user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> UserModel:
    """Enregistre le numéro qui autorise l'accès au bot Telegram.

    Changer de numéro coupe la liaison Telegram existante : l'ancien téléphone
    ne doit plus donner accès aux rapports de l'agence.
    """
    phone: str | None = None
    if payload.phone and payload.phone.strip():
        try:
            phone = normalize_phone(payload.phone)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        taken = await session.execute(
            select(UserModel.id).where(UserModel.phone == phone, UserModel.id != user.id)
        )
        if taken.scalar_one_or_none() is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ce numéro est déjà associé à un autre compte"
            )

    if phone != user.phone:
        user.phone = phone
        user.telegram_user_id = None
        user.telegram_linked_at = None
        await session.commit()
        await session.refresh(user)
    return user


@router.delete("/me/telegram", response_model=UserOut)
async def unlink_my_telegram(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> UserModel:
    """Délie le compte Telegram (téléphone perdu, changement d'appareil)."""
    user.telegram_user_id = None
    user.telegram_linked_at = None
    await session.commit()
    await session.refresh(user)
    return user
