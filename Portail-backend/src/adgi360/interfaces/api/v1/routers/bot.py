"""Routes appelées par n8n pour le bot Telegram.

Authentification de service : un secret partagé dans l'en-tête X-Bot-Token
(credential « Header Auth » côté n8n). Aucun utilisateur ne se connecte ici ;
l'identité est portée par `telegram_user_id`, résolu à chaque appel.

Convention de réponse : 200 avec `{ok, message, ...}` pour toute issue métier,
y compris un refus. Une erreur HTTP signale une panne réelle et déclenche les
nouvelles tentatives de n8n.
"""

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.application.bot.telegram_bot import TelegramBotService
from adgi360.infrastructure.config.settings import settings
from adgi360.infrastructure.db.session import get_session
from adgi360.infrastructure.n8n.client import N8nClient, get_n8n_client
from adgi360.infrastructure.storage.client import FileStorage, get_storage
from adgi360.interfaces.api.v1.schemas.bot_schemas import BotLinkRequest, BotReviewRequest
from adgi360.shared.exceptions import ExternalServiceError


async def verify_bot_token(x_bot_token: Annotated[str | None, Header()] = None) -> None:
    if not settings.bot_api_token:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Bot désactivé : BOT_API_TOKEN non configuré"
        )
    if not hmac.compare_digest(settings.bot_api_token, x_bot_token or ""):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton du bot invalide")


router = APIRouter(prefix="/bot", tags=["bot"], dependencies=[Depends(verify_bot_token)])


@router.post("/link")
async def link_account(
    payload: BotLinkRequest, session: AsyncSession = Depends(get_session)
) -> dict:
    reply = await TelegramBotService(session).link(
        payload.telegram_user_id, payload.contact_user_id, payload.phone
    )
    return reply.as_dict()


@router.get("/clients")
async def list_clients(
    telegram_user_id: int = Query(...), session: AsyncSession = Depends(get_session)
) -> dict:
    return (await TelegramBotService(session).list_clients(telegram_user_id)).as_dict()


@router.post("/reviews")
async def launch_review(
    payload: BotReviewRequest,
    session: AsyncSession = Depends(get_session),
    n8n: N8nClient = Depends(get_n8n_client),
    storage: FileStorage = Depends(get_storage),
) -> dict:
    try:
        reply = await TelegramBotService(session).launch_review(
            telegram_user_id=payload.telegram_user_id,
            chat_id=payload.chat_id,
            client_query=payload.client,
            period=payload.period,
            instructions=payload.instructions,
            n8n=n8n,
            storage=storage,
        )
    except ExternalServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return reply.as_dict()


@router.get("/reviews")
async def recent_reviews(
    telegram_user_id: int = Query(...),
    limit: int = Query(5, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return (await TelegramBotService(session).recent_reviews(telegram_user_id, limit)).as_dict()


@router.get("/reviews/{review_id}/download")
async def report_download(
    review_id: str,
    telegram_user_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> dict:
    try:
        reply = await TelegramBotService(session).report_download(
            telegram_user_id, review_id, storage
        )
    except ExternalServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return reply.as_dict()
