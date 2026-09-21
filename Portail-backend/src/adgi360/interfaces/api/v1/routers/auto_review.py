from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.application.auto_review.use_cases.approve_review import ApproveReviewUseCase
from adgi360.application.auto_review.use_cases.launch_auto_review import LaunchAutoReviewUseCase
from adgi360.application.auto_review.use_cases.render_report import RenderReportUseCase
from adgi360.domain.auto_review.entities import ClientType, ReviewStatus
from adgi360.infrastructure.db.models import ClientModel, ReviewRequestModel
from adgi360.infrastructure.db.session import get_session
from adgi360.infrastructure.n8n.client import N8nClient, get_n8n_client
from adgi360.infrastructure.storage.client import FileStorage, get_storage
from adgi360.infrastructure.security import verify_callback_token
from adgi360.interfaces.api.deps import CurrentUser
from adgi360.interfaces.api.v1.schemas.auto_review_schemas import (
    AutoReviewCreate,
    AutoReviewDetailOut,
    AutoReviewOut,
    ClientTypeOut,
    RenderReportRequest,
    ReportDownloadOut,
)
from adgi360.shared.exceptions import ExternalServiceError, NotFoundError, ValidationError

router = APIRouter(prefix="/auto-review", tags=["auto-review"])


async def _get_owned_review(
    review_id: str, organization_id: str, session: AsyncSession
) -> ReviewRequestModel:
    review = await session.get(ReviewRequestModel, review_id)
    if review is None or review.organization_id != organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review introuvable")
    return review


@router.get("/client-types", response_model=list[ClientTypeOut])
async def list_client_types() -> list[ClientTypeOut]:
    """Liste fixe alimentant le menu déroulant du formulaire."""
    return [ClientTypeOut(value=t.value, label=t.label) for t in ClientType]


@router.post("", response_model=AutoReviewOut, status_code=status.HTTP_202_ACCEPTED)
async def launch_auto_review(
    payload: AutoReviewCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    n8n: N8nClient = Depends(get_n8n_client),
    storage: FileStorage = Depends(get_storage),
) -> ReviewRequestModel:
    use_case = LaunchAutoReviewUseCase(session, n8n, storage)
    try:
        return await use_case.execute(
            organization_id=user.organization_id,
            client_id=payload.client_id,
            client_type=payload.client_type,
            data_file_ids=payload.data_file_ids,
            additional_info=payload.additional_info,
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("", response_model=list[AutoReviewDetailOut])
async def list_reviews(
    user: CurrentUser,
    review_status: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[AutoReviewDetailOut]:
    """Liste les reviews de l'agence, la plus récente en tête."""
    query = (
        select(ReviewRequestModel, ClientModel)
        .join(ClientModel, ReviewRequestModel.client_id == ClientModel.id)
        .where(ReviewRequestModel.organization_id == user.organization_id)
    )
    if review_status:
        query = query.where(ReviewRequestModel.status == review_status)
    result = await session.execute(query.order_by(ReviewRequestModel.created_at.desc()))

    items: list[AutoReviewDetailOut] = []
    for review, client in result.all():
        items.append(
            AutoReviewDetailOut(
                **{c.name: getattr(review, c.name) for c in review.__table__.columns},
                client_name=client.name,
                status_label=ReviewStatus(review.status).label,
            )
        )
    return items


@router.post("/{review_id}/render", response_model=AutoReviewOut)
async def render_report(
    review_id: str,
    payload: RenderReportRequest,
    token: str = Query(..., description="Jeton de rappel émis au lancement"),
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> ReviewRequestModel:
    """Appelé par n8n une fois l'analyse IA terminée.

    Authentifié par un jeton HMAC lié à la review, et non par une session :
    n8n est un service, pas un utilisateur. Le jeton ne permet que de déposer
    le plan de CETTE review.
    """
    if not verify_callback_token(review_id, token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Jeton de rappel invalide")
    try:
        return await RenderReportUseCase(session, storage).execute(
            review_id, payload.model_dump()
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.post("/{review_id}/approve", response_model=AutoReviewOut)
async def approve_review(
    review_id: str, user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> ReviewRequestModel:
    """Validation humaine. Aucun envoi : le rapport devient téléchargeable."""
    await _get_owned_review(review_id, user.organization_id, session)
    try:
        return await ApproveReviewUseCase(session).execute(review_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.get("/{review_id}/report", response_model=ReportDownloadOut)
async def download_report(
    review_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> ReportDownloadOut:
    """URL temporaire pour télécharger le PowerPoint généré."""
    review = await _get_owned_review(review_id, user.organization_id, session)
    if not review.report_storage_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun rapport disponible")

    url = await storage.presigned_url(review.report_storage_key)
    return ReportDownloadOut(
        url=url,
        filename=review.report_filename or "rapport.pptx",
        expires_in=3600,
    )
