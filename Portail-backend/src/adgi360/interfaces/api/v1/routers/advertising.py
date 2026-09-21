import json
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.accounts.entities import UserRole
from adgi360.domain.data.entities import build_social_key
from adgi360.infrastructure.advertising import AdvertisingApiClient
from adgi360.infrastructure.db.models import (
    AdvertisingConnectionModel,
    ClientModel,
    PlatformConnectionModel,
)
from adgi360.infrastructure.db.session import get_session
from adgi360.infrastructure.meta.client import MetaClient, get_meta_client
from adgi360.infrastructure.secrets import decrypt_secret, encrypt_secret
from adgi360.infrastructure.storage.client import FileStorage, get_storage
from adgi360.interfaces.api.deps import CurrentUser, require_role
from adgi360.interfaces.api.v1.schemas.advertising_schemas import (
    AdvertisingConnectionOut,
    AdvertisingConnectionUpdate,
    AdvertisingKpisOut,
    AdvertisingPlatformOut,
    CredentialFieldOut,
    InstagramPostOut,
    PlatformConnectionOut,
    PlatformConnectionUpdate,
)
from adgi360.shared.exceptions import ExternalServiceError, ValidationError

router = APIRouter(prefix="/advertising", tags=["advertising"])
AdminRequired = Depends(require_role(UserRole.ADMIN))

DATE_PRESETS = {"today", "yesterday", "last_7d", "last_14d", "last_30d", "this_month"}
IMAGE_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024

PLATFORMS = {
    "meta": {
        "label": "Meta Ads & Instagram",
        "description": "KPI Facebook/Instagram Ads et publication Instagram.",
        "fields": [
            {"key": "instagram_user_id", "label": "ID Instagram professionnel", "secret": False, "placeholder": "178414…"},
            {"key": "access_token", "label": "Jeton d’accès Meta", "placeholder": "EAAB…"},
            {"key": "instagram_access_token", "label": "Jeton Instagram dédié", "required": False, "placeholder": "Facultatif"},
        ],
    },
    "google_ads": {
        "label": "Google Ads",
        "description": "Dépenses, clics, conversions et valeur via GAQL.",
        "fields": [
            {"key": "access_token", "label": "Jeton OAuth 2.0", "placeholder": "ya29…"},
            {"key": "developer_token", "label": "Developer token", "placeholder": "22 caractères"},
            {"key": "login_customer_id", "label": "ID compte manager", "required": False, "secret": False, "placeholder": "Facultatif"},
        ],
    },
    "tiktok": {
        "label": "TikTok Ads",
        "description": "Reporting du compte annonceur TikTok Business.",
        "fields": [{"key": "access_token", "label": "Access token", "placeholder": "Jeton TikTok Business"}],
    },
    "linkedin": {
        "label": "LinkedIn Ads",
        "description": "Reporting Ad Analytics au niveau du compte.",
        "fields": [
            {"key": "access_token", "label": "Access token", "placeholder": "Jeton avec r_ads_reporting"},
            {"key": "api_version", "label": "Version API", "required": False, "secret": False, "placeholder": "202604"},
        ],
    },
    "snapchat": {
        "label": "Snap Ads",
        "description": "Statistiques agrégées du compte publicitaire Snapchat.",
        "fields": [{"key": "access_token", "label": "Access token", "placeholder": "Jeton Snap Marketing API"}],
    },
}


def _platform_definition(value: str) -> dict:
    definition = PLATFORMS.get(value)
    if not definition:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plateforme inconnue")
    return definition


@router.get("/platforms", response_model=list[AdvertisingPlatformOut])
async def list_platforms() -> list[AdvertisingPlatformOut]:
    return [
        AdvertisingPlatformOut(
            value=value,
            label=definition["label"],
            description=definition["description"],
            credential_fields=[CredentialFieldOut(**field) for field in definition["fields"]],
        )
        for value, definition in PLATFORMS.items()
    ]


@router.get("/connections", response_model=list[PlatformConnectionOut])
async def list_connections(
    user: CurrentUser,
    client_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> list[PlatformConnectionOut]:
    await _owned_client(client_id, user.organization_id, session)
    rows = list((await session.execute(select(PlatformConnectionModel).where(
        PlatformConnectionModel.organization_id == user.organization_id,
        PlatformConnectionModel.client_id == client_id,
    ))).scalars().all())
    out = [
        PlatformConnectionOut(
            platform=row.platform,
            label=PLATFORMS[row.platform]["label"],
            connected=True,
            client_id=client_id,
            account_id=row.account_id,
            configured_fields=json.loads(row.configured_fields or "[]"),
        )
        for row in rows if row.platform in PLATFORMS
    ]
    legacy = await _connection(user.organization_id, client_id, session)
    if legacy:
        out.append(PlatformConnectionOut(
            platform="meta",
            label=PLATFORMS["meta"]["label"],
            connected=True,
            client_id=client_id,
            account_id=legacy.meta_ad_account_id,
            configured_fields=[
                "instagram_user_id", "access_token",
                *(["instagram_access_token"] if legacy.instagram_access_token_encrypted else []),
            ],
        ))
    return out


@router.put("/connections/{platform}", response_model=PlatformConnectionOut, dependencies=[AdminRequired])
async def save_platform_connection(
    platform: str,
    payload: PlatformConnectionUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> PlatformConnectionOut:
    definition = _platform_definition(platform)
    await _owned_client(payload.client_id, user.organization_id, session)
    clean = {key: value.strip() for key, value in payload.credentials.items() if value.strip()}

    if platform == "meta":
        legacy = await _connection(user.organization_id, payload.client_id, session)
        required = [] if legacy else ["instagram_user_id", "access_token"]
        missing = [key for key in required if not clean.get(key)]
        if missing:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Champs requis : {', '.join(missing)}")
        if legacy is None:
            legacy = AdvertisingConnectionModel(
                organization_id=user.organization_id,
                client_id=payload.client_id,
                meta_ad_account_id=payload.account_id.strip(),
                instagram_user_id=clean["instagram_user_id"],
                meta_access_token_encrypted=encrypt_secret(clean["access_token"]),
            )
            session.add(legacy)
        else:
            legacy.meta_ad_account_id = payload.account_id.strip()
            legacy.instagram_user_id = clean.get("instagram_user_id", legacy.instagram_user_id)
            if clean.get("access_token"):
                legacy.meta_access_token_encrypted = encrypt_secret(clean["access_token"])
        if clean.get("instagram_access_token"):
            legacy.instagram_access_token_encrypted = encrypt_secret(clean["instagram_access_token"])
        await session.commit()
        fields = ["instagram_user_id", "access_token"] + (["instagram_access_token"] if legacy.instagram_access_token_encrypted else [])
        return PlatformConnectionOut(platform=platform, label=definition["label"], connected=True, client_id=payload.client_id, account_id=legacy.meta_ad_account_id, configured_fields=fields)

    row = (await session.execute(select(PlatformConnectionModel).where(
        PlatformConnectionModel.organization_id == user.organization_id,
        PlatformConnectionModel.client_id == payload.client_id,
        PlatformConnectionModel.platform == platform,
    ))).scalar_one_or_none()
    existing = json.loads(decrypt_secret(row.credentials_encrypted)) if row else {}
    credentials = {**existing, **clean}
    required = [f["key"] for f in definition["fields"] if f.get("required", True)]
    missing = [key for key in required if not credentials.get(key)]
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Champs requis : {', '.join(missing)}")
    if row is None:
        row = PlatformConnectionModel(organization_id=user.organization_id, client_id=payload.client_id, platform=platform, account_id=payload.account_id.strip(), credentials_encrypted="", configured_fields="[]")
        session.add(row)
    row.account_id = payload.account_id.strip()
    row.credentials_encrypted = encrypt_secret(json.dumps(credentials))
    row.configured_fields = json.dumps(sorted(credentials))
    await session.commit()
    await session.refresh(row)
    return PlatformConnectionOut(platform=platform, label=definition["label"], connected=True, client_id=payload.client_id, account_id=row.account_id, configured_fields=sorted(credentials))


@router.delete("/connections/{platform}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[AdminRequired])
async def delete_platform_connection(
    platform: str,
    user: CurrentUser,
    client_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> None:
    _platform_definition(platform)
    await _owned_client(client_id, user.organization_id, session)
    if platform == "meta":
        row = await _connection(user.organization_id, client_id, session)
    else:
        row = (await session.execute(select(PlatformConnectionModel).where(
            PlatformConnectionModel.organization_id == user.organization_id,
            PlatformConnectionModel.client_id == client_id,
            PlatformConnectionModel.platform == platform,
        ))).scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.commit()


@router.get("/connections/{platform}/kpis", response_model=AdvertisingKpisOut)
async def get_platform_kpis(
    platform: str,
    user: CurrentUser,
    client_id: str = Query(...),
    date_preset: str = Query("last_30d"),
    session: AsyncSession = Depends(get_session),
    meta: MetaClient = Depends(get_meta_client),
) -> AdvertisingKpisOut:
    _platform_definition(platform)
    await _owned_client(client_id, user.organization_id, session)
    if platform == "meta":
        legacy = await _connection(user.organization_id, client_id, session)
        if not legacy:
            raise HTTPException(status.HTTP_409_CONFLICT, "Meta n’est pas connecté")
        data = await meta.get_ad_kpis(legacy.meta_ad_account_id, decrypt_secret(legacy.meta_access_token_encrypted), date_preset)
    else:
        row = (await session.execute(select(PlatformConnectionModel).where(
            PlatformConnectionModel.organization_id == user.organization_id,
            PlatformConnectionModel.client_id == client_id,
            PlatformConnectionModel.platform == platform,
        ))).scalar_one_or_none()
        if not row:
            raise HTTPException(status.HTTP_409_CONFLICT, f"{PLATFORMS[platform]['label']} n’est pas connecté")
        data = await AdvertisingApiClient().fetch(platform, row.account_id, json.loads(decrypt_secret(row.credentials_encrypted)), date_preset)
    data.pop("platform", None)
    return AdvertisingKpisOut(**data)


async def _owned_client(client_id: str, organization_id: str, session: AsyncSession) -> ClientModel:
    client = await session.get(ClientModel, client_id)
    if client is None or client.organization_id != organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client introuvable")
    return client


async def _connection(organization_id: str, client_id: str, session: AsyncSession):
    result = await session.execute(
        select(AdvertisingConnectionModel).where(
            AdvertisingConnectionModel.organization_id == organization_id,
            AdvertisingConnectionModel.client_id == client_id,
        )
    )
    return result.scalar_one_or_none()


def _connection_out(connection: AdvertisingConnectionModel | None) -> AdvertisingConnectionOut:
    if connection is None:
        return AdvertisingConnectionOut(connected=False)
    return AdvertisingConnectionOut(
        connected=True,
        client_id=connection.client_id,
        meta_ad_account_id=connection.meta_ad_account_id,
        instagram_user_id=connection.instagram_user_id,
        has_meta_token=bool(connection.meta_access_token_encrypted),
        # Sans jeton Instagram dédié, on essaie le jeton Meta. Cela couvre les
        # applications configurées avec Facebook Login.
        has_instagram_token=bool(
            connection.instagram_access_token_encrypted
            or connection.meta_access_token_encrypted
        ),
    )


@router.get("/connection", response_model=AdvertisingConnectionOut)
async def get_connection(
    user: CurrentUser,
    client_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> AdvertisingConnectionOut:
    await _owned_client(client_id, user.organization_id, session)
    return _connection_out(await _connection(user.organization_id, client_id, session))


@router.put(
    "/connection",
    response_model=AdvertisingConnectionOut,
    dependencies=[AdminRequired],
)
async def save_connection(
    payload: AdvertisingConnectionUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> AdvertisingConnectionOut:
    await _owned_client(payload.client_id, user.organization_id, session)
    ad_account_id = payload.meta_ad_account_id.strip()
    instagram_user_id = payload.instagram_user_id.strip()
    if not ad_account_id or not instagram_user_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Les identifiants des comptes Meta et Instagram sont requis",
        )
    connection = await _connection(user.organization_id, payload.client_id, session)
    if connection is None:
        if not payload.meta_access_token:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Le jeton d'accès Meta est requis lors de la première connexion",
            )
        connection = AdvertisingConnectionModel(
            organization_id=user.organization_id,
            client_id=payload.client_id,
            meta_ad_account_id=ad_account_id,
            instagram_user_id=instagram_user_id,
            meta_access_token_encrypted=encrypt_secret(payload.meta_access_token.strip()),
            instagram_access_token_encrypted=(
                encrypt_secret(payload.instagram_access_token.strip())
                if payload.instagram_access_token
                else None
            ),
        )
        session.add(connection)
    else:
        connection.meta_ad_account_id = ad_account_id
        connection.instagram_user_id = instagram_user_id
        if payload.meta_access_token:
            connection.meta_access_token_encrypted = encrypt_secret(
                payload.meta_access_token.strip()
            )
        if payload.instagram_access_token:
            connection.instagram_access_token_encrypted = encrypt_secret(
                payload.instagram_access_token.strip()
            )
    await session.commit()
    await session.refresh(connection)
    return _connection_out(connection)


@router.delete(
    "/connection",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[AdminRequired],
)
async def remove_connection(
    user: CurrentUser,
    client_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _owned_client(client_id, user.organization_id, session)
    connection = await _connection(user.organization_id, client_id, session)
    if connection:
        await session.delete(connection)
        await session.commit()


@router.get("/kpis", response_model=AdvertisingKpisOut)
async def get_kpis(
    user: CurrentUser,
    client_id: str = Query(...),
    date_preset: str = Query("last_30d"),
    session: AsyncSession = Depends(get_session),
    meta: MetaClient = Depends(get_meta_client),
) -> AdvertisingKpisOut:
    if date_preset not in DATE_PRESETS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Période KPI invalide")
    await _owned_client(client_id, user.organization_id, session)
    connection = await _connection(user.organization_id, client_id, session)
    if connection is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Connecte d'abord un compte Meta")
    try:
        token = decrypt_secret(connection.meta_access_token_encrypted)
        data = await meta.get_ad_kpis(connection.meta_ad_account_id, token, date_preset)
        return AdvertisingKpisOut(**data)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.post("/instagram/posts", response_model=InstagramPostOut)
async def publish_instagram_post(
    user: CurrentUser,
    client_id: str = Form(...),
    caption: str = Form(..., min_length=1, max_length=2200),
    image: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
    meta: MetaClient = Depends(get_meta_client),
) -> InstagramPostOut:
    clean_caption = caption.strip()
    if not clean_caption:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "La légende ne peut pas être vide"
        )
    await _owned_client(client_id, user.organization_id, session)
    connection = await _connection(user.organization_id, client_id, session)
    if connection is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Connecte d'abord un compte Meta")
    if image.content_type not in IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "L'image Instagram doit être un fichier JPEG ou PNG",
        )
    content = await image.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "L'image dépasse la limite de 10 Mo du portail",
        )

    suffix = Path(image.filename or "post.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg" if image.content_type == "image/jpeg" else ".png"
    draft_id = str(uuid.uuid4())
    key = build_social_key(user.organization_id, draft_id, f"image{suffix}")
    await storage.ensure_bucket()
    await storage.upload(key, content, image.content_type)
    image_url = await storage.presigned_url(key, expires_in=3600)

    hostname = (urlparse(image_url).hostname or "").lower()
    if hostname in {"localhost", "127.0.0.1", "minio", "host.docker.internal"}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Meta ne peut pas lire le stockage local. Configure un stockage S3 public en production.",
        )

    try:
        encrypted = (
            connection.instagram_access_token_encrypted
            or connection.meta_access_token_encrypted
        )
        token = decrypt_secret(encrypted)
        post_id = await meta.publish_instagram_image(
            connection.instagram_user_id, token, image_url, clean_caption
        )
        return InstagramPostOut(id=post_id)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
