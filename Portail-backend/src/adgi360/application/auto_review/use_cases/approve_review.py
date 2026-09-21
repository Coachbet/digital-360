from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.auto_review.entities import ReviewStatus
from adgi360.infrastructure.db.models import ReviewRequestModel
from adgi360.shared.exceptions import NotFoundError, ValidationError


class ApproveReviewUseCase:
    """Validation humaine d'un rapport généré.

    Rien n'est envoyé : une fois approuvé, le rapport est simplement
    téléchargeable depuis le portail, et c'est un humain qui décide de la suite.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, review_id: str) -> ReviewRequestModel:
        review = await self._session.get(ReviewRequestModel, review_id)
        if review is None:
            raise NotFoundError("Review introuvable")

        if review.status != ReviewStatus.AWAITING_APPROVAL.value:
            raise ValidationError(
                "Seul un rapport en attente de relecture peut être validé "
                f"(statut actuel : {review.status})"
            )
        if not review.report_storage_key:
            raise ValidationError("Aucun rapport n'est associé à cette review")

        review.status = ReviewStatus.APPROVED.value
        review.approved_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(review)
        return review
