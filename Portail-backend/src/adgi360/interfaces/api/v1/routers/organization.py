from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.accounts.entities import UserRole
from adgi360.domain.data.entities import build_branding_key
from adgi360.infrastructure.db.session import get_session
from adgi360.infrastructure.storage.client import FileStorage, get_storage
from adgi360.interfaces.api.deps import CurrentOrganization, CurrentUser, require_role
from adgi360.interfaces.api.v1.schemas.organization_schemas import (
    BrandingOut,
    OrganizationProfileOut,
    OrganizationProfileUpdate,
)

router = APIRouter(prefix="/organization", tags=["organization"])

# Le branding et les mentions légales engagent l'agence : réservés aux admins.
AdminRequired = Depends(require_role(UserRole.ADMIN))

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@router.get("", response_model=OrganizationProfileOut)
async def get_profile(organization: CurrentOrganization) -> OrganizationProfileOut:
    """Profil complet de l'agence : identité, marque et mentions légales."""
    return OrganizationProfileOut.model_validate(organization, from_attributes=True)


@router.put("", response_model=OrganizationProfileOut, dependencies=[AdminRequired])
async def update_profile(
    payload: OrganizationProfileUpdate,
    organization: CurrentOrganization,
    session: AsyncSession = Depends(get_session),
) -> OrganizationProfileOut:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(organization, field, value)
    await session.commit()
    await session.refresh(organization)
    return OrganizationProfileOut.model_validate(organization, from_attributes=True)


@router.get("/branding", response_model=BrandingOut)
async def get_branding(organization: CurrentOrganization) -> BrandingOut:
    """Couleurs et logo, lus par le frontend pour teinter l'interface de l'agence."""
    return BrandingOut(
        name=organization.name,
        tagline=organization.tagline,
        primary=organization.brand_primary,
        ink=organization.brand_ink,
        accent=organization.brand_accent,
        has_logo=organization.logo_storage_key is not None,
        has_deck_template=organization.deck_template_key is not None,
    )


@router.post("/logo", response_model=OrganizationProfileOut, dependencies=[AdminRequired])
async def upload_logo(
    organization: CurrentOrganization,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> OrganizationProfileOut:
    """Logo affiché sur les factures et les rapports générés."""
    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Le logo doit être un PNG ou un JPEG"
        )
    content = await file.read()
    key = build_branding_key(organization.id, "logo", file.filename or "logo.png")
    await storage.ensure_bucket()
    await storage.upload(key, content, file.content_type)

    organization.logo_storage_key = key
    await session.commit()
    await session.refresh(organization)
    return OrganizationProfileOut.model_validate(organization, from_attributes=True)


@router.post(
    "/deck-template", response_model=OrganizationProfileOut, dependencies=[AdminRequired]
)
async def upload_deck_template(
    organization: CurrentOrganization,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> OrganizationProfileOut:
    """Gabarit PowerPoint de l'agence.

    Les rapports générés repartent de ce fichier : ses masques, ses polices et
    ses couleurs sont conservés, et seul le contenu des diapositives est produit
    par le portail. C'est ce qui permet à chaque agence de livrer un document
    indiscernable de ceux qu'elle fait à la main.
    """
    if file.content_type != PPTX_MIME and not (file.filename or "").endswith(
        (".pptx", ".potx")
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Le gabarit doit être un fichier PowerPoint (.pptx ou .potx)",
        )
    content = await file.read()
    key = build_branding_key(organization.id, "template", file.filename or "template.pptx")
    await storage.ensure_bucket()
    await storage.upload(key, content, PPTX_MIME)

    organization.deck_template_key = key
    await session.commit()
    await session.refresh(organization)
    return OrganizationProfileOut.model_validate(organization, from_attributes=True)


@router.delete(
    "/deck-template", response_model=OrganizationProfileOut, dependencies=[AdminRequired]
)
async def remove_deck_template(
    organization: CurrentOrganization,
    session: AsyncSession = Depends(get_session),
) -> OrganizationProfileOut:
    """Revenir au gabarit intégré du produit."""
    organization.deck_template_key = None
    await session.commit()
    await session.refresh(organization)
    return OrganizationProfileOut.model_validate(organization, from_attributes=True)
